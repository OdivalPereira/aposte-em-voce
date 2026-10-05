#!/usr/bin/env python3
"""Conferência da ordem verificável (Q119, RM-1b F6).

Lê o bloco ```entregas de uma ordem e marca cada entrega como feita, não feita, não
verificada ou não preenchida, sem executar testes. Uma linha por entrega:

    ID | tipo | argumento [| argumento...]

Tipos:
  commit_existe <ref>
  arquivos_em <base>..<head> | <prefixo> [| <prefixo>...]   todos os arquivos alterados começam por um prefixo
  arquivo_existe <caminho>
  atestado_aprovado <arquivo> | <commit>                     do `sc.py entregar` (forma 1.3.0 completa, perfil de hoje e
                                                             `atestado_hash` conferido), APROVADO, commit igual ao informado
  parecer_valido <arquivo>                                   lint do parecer sem erro e com veredito
  hash_confere <arquivo> | <sha256>
  push_feito <ramo>                                          ramo remoto (origin) igual ao local; sem rede: não verificado
  delegacoes antigravity | <conversa> | <mínimo>             chamadas a invoke_subagent no log da conversa
  conversa_nova antigravity | <conversa>                     uma única ordem na conversa
  delegacoes claude | <sessão> | <mínimo>                    delegações com log em <sessão>/subagents/agent-*.jsonl
  conversa_nova claude | <sessão ou agente>                  uma única ordem na sessão ou no subagente (agent-<id>)
                                                             Log ausente ou ilegível reprova (falha fechada).
                                                             A pasta de projetos vem de SC_CLAUDE_PROJETOS.

Com --registrar, grava o resultado no registro.json como evento 'conferencia_registrada'.
Código de saída 0 só se todas as entregas estiverem feitas.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sc_status  # noqa: E402
from sc_registro import localizar_sociedade_da_etapa  # noqa: E402

FEITO, NAO_FEITO, NAO_VERIFICADO, NAO_PREENCHIDO = 'feito', 'não feito', 'não verificado', 'não preenchido'
BLOCO = re.compile(r'```entregas\s*\n(.*?)```', re.S)
MARCADOR = re.compile(r'<[^<>\n]+>')


def git(raiz, *args):
    r = subprocess.run(['git', '-C', str(raiz), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def arquivos_do_intervalo(raiz, base, head):
    """Caminhos alterados em base..head, lidos com `-z` e sem aspas (`core.quotepath=off`) e normalizados em NFC.
    `--no-renames`: numa renomeação contam a origem e o destino. None se o intervalo for inválido.
    Arquivos alterados exclusivamente em commits puros de governança não são imputados aos prefixos do candidato (Q178, Q149)."""
    r = subprocess.run(['git', '-C', str(raiz), '-c', 'core.quotepath=off', 'diff', '--name-only', '-z', '--no-renames', base, head],
                       capture_output=True)
    if r.returncode != 0:
        return None
    todos = [unicodedata.normalize('NFC', os.fsdecode(c)) for c in r.stdout.split(b'\0') if c]

    # Inspeciona commits de base..head para desconsiderar arquivos alterados exclusivamente em commits puros de governança
    r_rev = subprocess.run(['git', '-C', str(raiz), 'rev-list', '--reverse', f'{base}..{head}'],
                           capture_output=True, text=True)
    if r_rev.returncode != 0:
        return None
    commits = [c.strip() for c in r_rev.stdout.splitlines() if c.strip()]
    if not commits:
        return todos

    def _em_gov(rel):
        return rel == 'sociedade' or rel.startswith('sociedade/')

    commits_info = []
    tem_commits_produto = False
    for c in commits:
        r_c = subprocess.run(
            ['git', '-C', str(raiz), '-c', 'core.quotepath=off', 'diff-tree', '--no-commit-id', '--name-only', '-r', '-z', '--no-renames', '-m', c],
            capture_output=True
        )
        if r_c.returncode != 0:
            return None
        arqs = [unicodedata.normalize('NFC', os.fsdecode(x)) for x in r_c.stdout.split(b'\0') if x]
        if not arqs:
            continue
        arqs_unicos = set(arqs)
        eh_gov = all(_em_gov(x) for x in arqs_unicos)
        if not eh_gov:
            tem_commits_produto = True
        commits_info.append((arqs_unicos, eh_gov))

    viu_produto = False
    arqs_em_commits_nao_gov = set()
    for arqs_unicos, eh_gov in commits_info:
        if not eh_gov:
            viu_produto = True
            for x in arqs_unicos:
                arqs_em_commits_nao_gov.add(x)
            continue

        if not tem_commits_produto:
            for x in arqs_unicos:
                arqs_em_commits_nao_gov.add(x)
        elif not viu_produto:
            # Governança no início (Q178)
            continue
        else:
            # Commit em sociedade/ após commits de produto: perfil e regras exigem governança no início (Q178)
            for x in arqs_unicos:
                rel_clean = x.strip().lstrip('./')
                if rel_clean in ('sociedade/perfil.md', 'sociedade/regras.md'):
                    arqs_em_commits_nao_gov.add(x)

    # Exclui arquivos em sociedade/ que só foram alterados em commits estritamente de governança
    return [a for a in todos if not (_em_gov(a) and a not in arqs_em_commits_nao_gov)]


class ConversaResolvida(str):
    """Representa a conversa da rodada atual do Gandalf, mantendo a lista de todas as conversas das rodadas."""
    def __new__(cls, conv_id, todas_conversas=None):
        obj = super().__new__(cls, conv_id)
        obj.todas_conversas = list(todas_conversas) if todas_conversas else [conv_id]
        return obj


def obter_ultimo_commit_produto(raiz, ref='HEAD'):
    """Retorna o SHA do último commit que tocou arquivos fora de sociedade/.
    Se commits posteriores tocam exclusivamente sociedade/ (cauda de governança, Q149/Q178 / K2),
    retrocede pelo histórico a partir da ref até encontrar o commit de produto."""
    sha = git(raiz, 'rev-parse', '--verify', f'{ref}^{{commit}}')
    if not sha:
        return None
    atual = sha
    while atual:
        r_c = subprocess.run(
            ['git', '-C', str(raiz), '-c', 'core.quotepath=off', 'diff-tree', '--no-commit-id', '--name-only', '-r', '-z', '--no-renames', '-m', atual],
            capture_output=True
        )
        if r_c.returncode != 0:
            break
        arqs = [unicodedata.normalize('NFC', os.fsdecode(x)) for x in r_c.stdout.split(b'\0') if x]
        if not arqs:
            pai = git(raiz, 'rev-parse', '--verify', f'{atual}^')
            if not pai:
                return atual
            atual = pai
            continue
        eh_gov = all(x == 'sociedade' or x.startswith('sociedade/') for x in arqs)
        if not eh_gov:
            return atual
        pai = git(raiz, 'rev-parse', '--verify', f'{atual}^')
        if not pai:
            return atual
        atual = pai
    return sha


def ler_entregas(texto):
    m = BLOCO.search(texto)
    if not m:
        raise ValueError('A ordem não tem bloco ```entregas.')
    itens = []
    for linha in m.group(1).splitlines():
        linha = linha.strip()
        if not linha or linha.startswith('#'):
            continue
        partes = [p.strip() for p in linha.split('|')]
        if len(partes) < 2:
            raise ValueError(f'Entrega malformada: "{linha}". Use "ID | tipo | argumentos".')
        itens.append({'id': partes[0], 'tipo': partes[1], 'args': partes[2:]})
    return itens


def _sha256(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def _normalizar_caminho_posix(c):
    if not c:
        return ''
    s = str(c).strip().strip('"').strip("'")
    if s.startswith('file://'):
        s = s[7:]
    try:
        return Path(s).resolve().as_posix()
    except Exception:
        return s


def _extrair_uris_workspace(uris_raw):
    caminhos = set()
    if not uris_raw:
        return caminhos
    s_raw = str(uris_raw).strip()
    if not s_raw:
        return caminhos
    try:
        parsed = json.loads(s_raw)
        if isinstance(parsed, list):
            for item in parsed:
                if item:
                    caminhos.add(_normalizar_caminho_posix(item))
            return caminhos
        elif isinstance(parsed, str):
            caminhos.add(_normalizar_caminho_posix(parsed))
            return caminhos
    except Exception:
        pass
    for item in s_raw.split(','):
        item = item.strip()
        if item:
            caminhos.add(_normalizar_caminho_posix(item))
    return caminhos


def _extrair_pastas_declaradas(texto):
    """Extrai caminhos declarados formalmente no prompt inicial (Pasta: ..., Worktree: ... ou <user_information>)."""
    declaradas = set()
    if not isinstance(texto, str):
        return declaradas
    for m in re.finditer(r'(?:^|[\s\n\r])(?:Pasta|Worktree):\s*([^\s\n\r`\'"]+)', texto, re.I):
        c = _normalizar_caminho_posix(m.group(1))
        if c:
            declaradas.add(c)
    for m in re.finditer(r'([/][^\s\n\r`\'"]+)\s*->\s*[^\s\n\r`\'"]+', texto):
        c = _normalizar_caminho_posix(m.group(1))
        if c:
            declaradas.add(c)
    return declaradas


def _obter_especialistas_ativos(pasta_sociedade):
    """Obtém conjunto de nomes em minúsculas dos especialistas com estado ativo no perfil."""
    import sc_perfil
    especialistas = set()
    papeis_lideranca = {'arquiteto', 'coordenador', 'revisor independente', 'revisor'}
    try:
        perfil = sc_perfil.carregar_perfil(pasta_sociedade)
        for p in perfil.papeis:
            papel = (p.get('papel') or '').strip().lower()
            estado = (p.get('estado') or '').strip().lower()
            if estado == 'ativo' and papel not in papeis_lideranca:
                nome = (p.get('nome') or '').strip().lower()
                for n in re.split(r'[,/]', nome):
                    n = n.strip()
                    if n:
                        especialistas.add(n)
    except Exception:
        pass
    return especialistas


def _contar_delegacoes_antigravity(log_path, especialistas_ativos):
    """Conta chamadas invoke_subagent filtrando apenas especialistas do perfil ativo. Self não conta (Q182)."""
    log_p = Path(log_path)
    if not log_p.is_file():
        return None
    qtd_validas = 0
    try:
        with log_p.open(encoding='utf-8', errors='replace') as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    passo = json.loads(linha)
                except Exception:
                    continue
                for tc in passo.get('tool_calls') or []:
                    if tc.get('name') != 'invoke_subagent':
                        continue
                    args = tc.get('args') or {}
                    subs = args.get('Subagents') or []
                    if isinstance(subs, str):
                        try:
                            subs = json.loads(subs)
                        except Exception:
                            matches = re.findall(r'"(?:Role|TypeName|name)"\s*:\s*"([^"]+)"', subs)
                            subs = [{'TypeName': m} for m in matches] if matches else [1]
                    if not isinstance(subs, list):
                        subs = [subs]
                    if not subs and ('TypeName' in args or 'Role' in args):
                        subs = [args]
                    for sub in subs:
                        if isinstance(sub, dict):
                            t_nome = (sub.get('TypeName') or sub.get('Role') or sub.get('name') or '').strip().lower()
                        elif isinstance(sub, str):
                            t_nome = sub.strip().lower()
                        else:
                            continue
                        if t_nome == 'self':
                            # Q182: self não conta
                            continue
                        if t_nome == 'especialista' or (especialistas_ativos and t_nome in especialistas_ativos):
                            qtd_validas += 1
                        elif not especialistas_ativos and t_nome:
                            qtd_validas += 1
        return qtd_validas
    except Exception:
        return None


def resolver_conversas_etapa(etapa, pasta_sociedade=None, brain_dir=None, summaries_db=None):
    """Resolve @<etapa> para as conversas do Antigravity abertas no worktree em cada rodada (K3 / K4).
    Retorna (lista_de_conversas, motivo_de_erro). Em caso de sucesso, motivo_de_erro é None."""
    from sc_registro import Registro, localizar_sociedade_da_etapa, localizar_sociedade_canonica
    try:
        soc = Path(pasta_sociedade) if pasta_sociedade else localizar_sociedade_da_etapa(etapa)
    except Exception:
        soc = None

    if not soc or not soc.is_dir():
        soc = localizar_sociedade_canonica()

    pasta_wt = soc.parent.resolve() if soc else None
    if not pasta_wt or not pasta_wt.exists():
        return [], f'worktree da etapa "{etapa}" não encontrado'

    pasta_wt_norm = pasta_wt.as_posix()
    # K3: identidade estrita de worktree. NÃO aceitar common_git (raiz principal).
    pastas_validas = {pasta_wt_norm}
    pasta_raiz_git = None
    try:
        cg = subprocess.run(['git', '-C', str(pasta_wt), 'rev-parse', '--path-format=absolute', '--git-common-dir'], capture_output=True, text=True).stdout.strip()
        if cg.endswith('/.git'):
            pasta_raiz_git = Path(cg[:-5]).resolve().as_posix()
        elif cg:
            pasta_raiz_git = Path(cg).resolve().as_posix()
    except Exception:
        pass
    ramo_etapa = git(pasta_wt, 'branch', '--show-current')

    try:
        reg = Registro(soc)
        eventos = reg.dados.get('eventos', [])
    except Exception as e:
        return [], f'erro ao ler registro da etapa "{etapa}": {e}'

    passagens = [
        ev for ev in eventos
        if ev.get('tipo') == 'passagem' and (ev.get('dados') or {}).get('para') == 'gandalf'
        and (not (ev.get('dados') or {}).get('etapa') or (ev.get('dados') or {}).get('etapa') == etapa)
    ]
    if not passagens:
        return [], f'nenhum evento de passagem para o Gandalf registrado na etapa "{etapa}"'

    passagens_dt = []
    for p in passagens:
        ts_str = p.get('timestamp') or (p.get('dados') or {}).get('data_hora')
        if not ts_str:
            continue
        try:
            dt = datetime.fromisoformat(str(ts_str).replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            passagens_dt.append(dt)
        except Exception:
            continue

    if not passagens_dt:
        return [], f'timestamp da passagem para Gandalf inválido ou ausente na etapa "{etapa}"'

    passagens_dt.sort()
    ts_primeira_passagem = passagens_dt[0]

    b_dir = Path(brain_dir) if brain_dir else (Path.home() / '.gemini' / 'antigravity' / 'brain')
    s_db = Path(summaries_db) if summaries_db else (Path.home() / '.gemini' / 'antigravity' / 'conversation_summaries.db')

    info_conversas = {}

    if s_db and s_db.is_file():
        try:
            import sqlite3
            conn = sqlite3.connect(s_db)
            cur = conn.cursor()
            cur.execute("SELECT conversation_id, last_user_input_time, last_modified_time, workspace_uris FROM conversation_summaries")
            for cid, l_input, l_mod, uris in cur.fetchall():
                t_str = l_input or l_mod
                if not t_str:
                    continue
                try:
                    t_dt = datetime.fromisoformat(str(t_str).replace('Z', '+00:00'))
                    if t_dt.tzinfo is None:
                        t_dt = t_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if t_dt < ts_primeira_passagem:
                    continue
                uris_cands = _extrair_uris_workspace(uris)
                info_conversas[cid] = {
                    'cid': cid,
                    't_inicio': t_dt,
                    'pastas_estruturadas': set(uris_cands),
                    'pastas_declaradas': set(),
                    'ramos_estruturados': set(),
                    'menciona_ordem': False,
                    'menciona_gandalf': False,
                }
            conn.close()
        except Exception:
            pass

    if b_dir and b_dir.is_dir():
        for t_file in b_dir.glob('*/.system_generated/logs/transcript*.jsonl'):
            cid = t_file.parents[2].name
            try:
                with t_file.open(encoding='utf-8', errors='replace') as f:
                    primeira_linha = f.readline()
                if not primeira_linha.strip():
                    continue
                o = json.loads(primeira_linha)
                c_at = o.get('created_at')
                t_dt = None
                if c_at:
                    try:
                        t_dt = datetime.fromisoformat(str(c_at).replace('Z', '+00:00'))
                        if t_dt.tzinfo is None:
                            t_dt = t_dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        t_dt = None

                caminhos_explicit = set()
                for k in ('workspace', 'workspace_uris', 'workspaces', 'cwd', 'app_data_dir'):
                    if k in o and o[k]:
                        caminhos_explicit.update(_extrair_uris_workspace(o[k]))

                ramos_explicit = set()
                for k in ('branch', 'git_branch'):
                    if k in o and o[k]:
                        ramos_explicit.add(str(o[k]).strip())

                texto_busca = o.get('content') or primeira_linha
                if not isinstance(texto_busca, str):
                    texto_busca = str(texto_busca)

                pastas_declaradas = _extrair_pastas_declaradas(texto_busca)
                ordem_mencionada = (f"ordens/{etapa}.md" in texto_busca or f"{etapa}.md" in texto_busca or f"etapa {etapa}" in texto_busca.lower())
                gandalf_mencionado = 'gandalf' in texto_busca.lower()

                if cid not in info_conversas:
                    if t_dt and t_dt < ts_primeira_passagem:
                        continue
                    info_conversas[cid] = {
                        'cid': cid,
                        't_inicio': t_dt or ts_primeira_passagem,
                        'pastas_estruturadas': caminhos_explicit,
                        'pastas_declaradas': pastas_declaradas,
                        'ramos_estruturados': ramos_explicit,
                        'menciona_ordem': ordem_mencionada,
                        'menciona_gandalf': gandalf_mencionado,
                    }
                else:
                    if t_dt:
                        info_conversas[cid]['t_inicio'] = t_dt
                    info_conversas[cid]['pastas_estruturadas'].update(caminhos_explicit)
                    info_conversas[cid]['pastas_declaradas'].update(pastas_declaradas)
                    info_conversas[cid]['ramos_estruturados'].update(ramos_explicit)
                    info_conversas[cid]['menciona_ordem'] = info_conversas[cid]['menciona_ordem'] or ordem_mencionada
                    info_conversas[cid]['menciona_gandalf'] = info_conversas[cid]['menciona_gandalf'] or gandalf_mencionado
            except Exception:
                continue

    def _tem_vinculo_estruturado(info):
        # K3: A identidade usa estritamente campos estruturados de workspace que apontem para o worktree da etapa
        # ou ramo da etapa
        if any(p in pastas_validas for p in info.get('pastas_estruturadas', set())):
            return True
        if ramo_etapa and ramo_etapa in info.get('ramos_estruturados', set()):
            return True
        if any(r == f'etapa/{etapa}' or r == etapa for r in info.get('ramos_estruturados', set())):
            return True
        return False

    def _eh_divergente(info):
        pe = info.get('pastas_estruturadas', set())
        pd = info.get('pastas_declaradas', set())
        todas = pe | pd
        if todas and not any(p in pastas_validas for p in todas) and not _tem_vinculo_estruturado(info):
            if pasta_raiz_git and all(p == pasta_raiz_git for p in todas):
                return False
            return True
        return False

    conversas_por_rodada = []
    num_passagens = len(passagens_dt)

    for k in range(num_passagens):
        ts_inicio = passagens_dt[k]
        ts_fim = passagens_dt[k + 1] if (k + 1 < num_passagens) else None

        cands_rodada = []
        sem_campo_rodada = []

        for cid, info in info_conversas.items():
            t = info['t_inicio']
            if t < ts_inicio:
                continue
            if ts_fim and t >= ts_fim:
                continue
            if _eh_divergente(info):
                continue
            if _tem_vinculo_estruturado(info):
                cands_rodada.append(info)
            elif info.get('menciona_ordem'):
                sem_campo_rodada.append(info)

        if not cands_rodada:
            if k == num_passagens - 1:
                if sem_campo_rodada:
                    return [], f'sem campo estruturado de workspace para a etapa "{etapa}" no Antigravity'
                return [], f'nenhuma conversa do Antigravity encontrada para a etapa "{etapa}" após a passagem'
            continue

        if len(cands_rodada) == 1:
            conversas_por_rodada.append(cands_rodada[0]['cid'])
        else:
            # K4: Ambiguidade só é reportada se houver múltiplas conversas conflitantes dentro da mesma rodada
            gandalf_cands = [c for c in cands_rodada if c.get('menciona_ordem') and c.get('menciona_gandalf')]
            if not gandalf_cands:
                gandalf_cands = [c for c in cands_rodada if c.get('menciona_ordem')]
            cands_filtradas = gandalf_cands if gandalf_cands else cands_rodada

            if len(cands_filtradas) > 1:
                return [], f'ambiguidade: {len(cands_filtradas)} conversas do Antigravity encontradas para a etapa "{etapa}" após a passagem'

            conversas_por_rodada.append(cands_filtradas[0]['cid'])

    if not conversas_por_rodada:
        return [], f'nenhuma conversa do Antigravity encontrada para a etapa "{etapa}" após a passagem'

    return conversas_por_rodada, None


def resolver_conversa_etapa(etapa, pasta_sociedade=None, brain_dir=None, summaries_db=None):
    """Resolve @<etapa> para o ID da conversa do Antigravity aberta no worktree após a passagem para Gandalf."""
    cids, motivo = resolver_conversas_etapa(etapa, pasta_sociedade=pasta_sociedade, brain_dir=brain_dir, summaries_db=summaries_db)
    if not cids:
        return None, motivo
    return ConversaResolvida(cids[-1], todas_conversas=cids), None


def conferir_item(item, raiz):
    tipo, args = item['tipo'], item['args']
    if any(MARCADOR.search(a) for a in args) or not args:
        return NAO_PREENCHIDO, 'argumento com marcador <...> ou vazio'
    caminho = lambda rel: (raiz / rel) if not Path(rel).is_absolute() else Path(rel)  # noqa: E731

    if tipo == 'commit_existe':
        ref = args[0]
        sha = git(raiz, 'rev-parse', '--verify', f'{ref}^{{commit}}')
        if not sha:
            return NAO_FEITO, f'commit {ref} não existe'
        sha_produto = obter_ultimo_commit_produto(raiz, sha)
        sha_avaliar = sha_produto or sha
        if len(args) > 1:
            esperado = git(raiz, 'rev-parse', '--verify', f'{args[1]}^{{commit}}') or args[1]
            esperado_sha = git(raiz, 'rev-parse', '--verify', f'{esperado}^{{commit}}')
            esperado_produto = obter_ultimo_commit_produto(raiz, esperado) if esperado_sha else esperado
            bate = (sha.startswith(esperado[:7]) or esperado.startswith(sha[:7]) or
                    sha_avaliar.startswith(esperado[:7]) or esperado.startswith(sha_avaliar[:7]) or
                    (esperado_produto and (sha_avaliar.startswith(esperado_produto[:7]) or esperado_produto.startswith(sha_avaliar[:7]))))
            if not bate:
                return NAO_FEITO, f'commit {sha[:12]}, esperado {esperado[:12]}'
            if not (sha.startswith(esperado[:7]) or esperado.startswith(sha[:7])):
                c_antigo = esperado_sha if (esperado_sha and sha_avaliar.startswith(esperado_sha[:7])) else sha_avaliar
                c_recente = sha
                r_diff = subprocess.run(
                    ['git', '-C', str(raiz), '-c', 'core.quotepath=off', 'diff', '--name-only', '-z', '--no-renames', c_antigo, c_recente],
                    capture_output=True
                )
                if r_diff.returncode == 0:
                    diff_arqs = [unicodedata.normalize('NFC', os.fsdecode(x)) for x in r_diff.stdout.split(b'\0') if x]
                    tocou_fora = [x for x in diff_arqs if not (x == 'sociedade' or x.startswith('sociedade/'))]
                    if tocou_fora:
                        return NAO_FEITO, f'commit {sha[:12]}, esperado {esperado[:12]} (alterações fora de sociedade/)'
            return FEITO, sha_avaliar[:12]
        return FEITO, sha_avaliar[:12]

    if tipo == 'arquivos_em':
        if '..' not in args[0] or len(args) < 2:
            return NAO_PREENCHIDO, 'use "<base>..<head> | <prefixo>"'
        base, head = args[0].split('..', 1)
        arquivos = arquivos_do_intervalo(raiz, base, head)
        if arquivos is None:
            return NAO_FEITO, f'intervalo inválido: {args[0]}'
        prefixos = [unicodedata.normalize('NFC', p) for p in args[1:]]
        fora = [a for a in arquivos if not any(a.startswith(p) for p in prefixos)]
        if not arquivos:
            return NAO_FEITO, 'nenhum arquivo alterado no intervalo'
        return (FEITO, f'{len(arquivos)} arquivos, todos nos prefixos') if not fora else \
               (NAO_FEITO, f'{len(fora)} fora dos prefixos: {", ".join(fora[:5])}')

    if tipo == 'arquivo_existe':
        return (FEITO, args[0]) if caminho(args[0]).exists() else (NAO_FEITO, f'{args[0]} não existe')

    if tipo == 'atestado_aprovado':
        arq = caminho(args[0])
        if not arq.is_file():
            return NAO_FEITO, f'{args[0]} não existe'
        try:
            at = json.loads(arq.read_text(encoding='utf-8'))
        except ValueError:
            return NAO_FEITO, 'atestado não é JSON válido'
        if not isinstance(at, dict) or at.get('status') != 'APROVADO':
            return NAO_FEITO, f'status {at.get("status") if isinstance(at, dict) else "?"}'
        ok, motivo = sc_status.hash_do_atestado_confere(at)  # B15: atestado escrito à mão ou alterado não vale
        if not ok:
            return NAO_FEITO, motivo
        perfil = raiz / 'sociedade' / 'perfil.md'  # B17b: a mesma forma que o `decidir` exige (avulso e --area parcial caem)
        ok, motivo = sc_status.forma_do_atestado(at, hashlib.sha256(perfil.read_bytes()).hexdigest() if perfil.is_file() else None)
        if not ok:
            return NAO_FEITO, motivo
        if len(args) > 1:
            esperado = git(raiz, 'rev-parse', '--verify', f'{args[1]}^{{commit}}') or args[1]
            if not at.get('commit'):
                return NAO_FEITO, 'atestado sem commit (versão anterior à 1.2.0)'
            at_commit = at['commit']
            at_commit_sha = git(raiz, 'rev-parse', '--verify', f'{at_commit}^{{commit}}')
            bate = (esperado.startswith(at_commit[:7]) or at_commit.startswith(esperado[:7]))
            if not bate:
                # K2: Cauda de governança pós-atestado (Q149/Q178)
                is_ancestor = False
                if at_commit_sha and esperado:
                    res_anc = subprocess.run(
                        ['git', '-C', str(raiz), 'merge-base', '--is-ancestor', at_commit_sha, esperado],
                        capture_output=True
                    )
                    is_ancestor = (res_anc.returncode == 0)
                if is_ancestor:
                    r_diff = subprocess.run(
                        ['git', '-C', str(raiz), '-c', 'core.quotepath=off', 'diff', '--name-only', '-z', '--no-renames', at_commit_sha, esperado],
                        capture_output=True
                    )
                    if r_diff.returncode == 0:
                        diff_arqs = [unicodedata.normalize('NFC', os.fsdecode(x)) for x in r_diff.stdout.split(b'\0') if x]
                        tocou_fora = [x for x in diff_arqs if not (x == 'sociedade' or x.startswith('sociedade/'))]
                        if not tocou_fora:
                            bate = True
                        else:
                            return NAO_FEITO, f'atestado do commit {at_commit[:12]}, esperado {esperado[:12]} (alterações fora de sociedade/ após atestado: {", ".join(tocou_fora[:3])})'
                if not bate:
                    return NAO_FEITO, f'atestado do commit {at_commit[:12]}, esperado {esperado[:12]}'
        if not at.get('total_arquivos_inspecionados'):
            return NAO_FEITO, 'atestado aprovado sem nenhum arquivo inspecionado'
        return FEITO, f'APROVADO, {at["total_arquivos_inspecionados"]} arquivos, commit {str(at.get("commit"))[:12]}'

    if tipo == 'parecer_valido':
        arq = caminho(args[0])
        if not arq.is_file():
            return NAO_FEITO, f'{args[0]} não existe'
        lint = Path(__file__).resolve().parents[2] / 'sc-revisao' / 'scripts' / 'lint_parecer.py'
        r = subprocess.run([sys.executable, '-B', str(lint), str(arq)], capture_output=True, text=True)
        veredito = re.search(r'veredito:\s*(aceitar com ressalvas|n[ãa]o aceitar|aceitar)', arq.read_text(encoding='utf-8'), re.I)
        if r.returncode != 0:
            return NAO_FEITO, 'lint do parecer com erro: ' + (r.stdout.strip().splitlines() or [''])[0][:100]
        return (FEITO, f'veredito: {veredito.group(1)}') if veredito else (NAO_FEITO, 'sem veredito')

    if tipo == 'hash_confere':
        arq = caminho(args[0])
        if not arq.is_file() or len(args) < 2:
            return NAO_FEITO, f'{args[0]} não existe ou hash ausente'
        real = _sha256(arq)
        return (FEITO, real[:12]) if real == args[1].lower() else (NAO_FEITO, f'hash real {real[:12]}')

    if tipo == 'push_feito':
        local = git(raiz, 'rev-parse', '--verify', f'refs/heads/{args[0]}')
        if not local:
            return NAO_FEITO, f'ramo local {args[0]} não existe'
        remoto = git(raiz, 'ls-remote', 'origin', f'refs/heads/{args[0]}')
        if remoto is None:
            return NAO_VERIFICADO, 'sem acesso ao remoto'
        sha_remoto = remoto.split()[0] if remoto else ''
        return (FEITO, local[:12]) if sha_remoto == local else (NAO_FEITO, f'remoto {sha_remoto[:12] or "ausente"}, local {local[:12]}')

    if tipo in ('delegacoes', 'conversa_nova'):
        from sc_sessao import medir, ErroSessao
        if args[0] not in ('antigravity', 'claude') or len(args) < 2:
            return NAO_PREENCHIDO, 'use "antigravity | <conversa>" ou "claude | <sessão>"'
        ident = args[1].strip()
        todas_conversas = [ident]
        if args[0] == 'antigravity' and ident.startswith('@'):
            etapa_alvo = ident[1:].strip()
            if not etapa_alvo or etapa_alvo == 'etapa':
                etapa_alvo = raiz.name
            conv_id, motivo = resolver_conversa_etapa(etapa_alvo, pasta_sociedade=raiz / 'sociedade')
            if not conv_id:
                if motivo and 'sem campo estruturado' in motivo:
                    return NAO_VERIFICADO, motivo
                return NAO_FEITO, motivo
            ident = str(conv_id)
            todas_conversas = getattr(conv_id, 'todas_conversas', [ident])

        if tipo == 'conversa_nova':
            # K4: conversa_nova valida que em cada rodada há apenas uma ordem por conversa
            for cid in todas_conversas:
                try:
                    if args[0] == 'claude':
                        m = medir('claude', sessao=cid)
                    else:
                        m = medir('antigravity', conversa=cid)
                except ErroSessao as e:
                    return NAO_FEITO, str(e)
                if not m.get('conversa_nova'):
                    return NAO_FEITO, f'{m.get("ordens_na_conversa", "?")} ordens na mesma conversa'
            return FEITO, '1 ordem na conversa'

        # tipo == 'delegacoes'
        minimo = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
        total_delegacoes = 0
        pasta_soc = raiz / 'sociedade'
        especialistas = _obter_especialistas_ativos(pasta_soc)

        for cid in todas_conversas:
            try:
                if args[0] == 'claude':
                    m = medir('claude', sessao=cid)
                else:
                    m = medir('antigravity', conversa=cid)
            except ErroSessao as e:
                return NAO_FEITO, str(e)
            if 'delegacoes_total' not in m:
                return NAO_FEITO, 'o identificador é de um subagente, não de uma sessão; delegações não medidas'
            del_conv = m['delegacoes_total']
            if args[0] == 'antigravity' and m.get('log'):
                validas = _contar_delegacoes_antigravity(m['log'], especialistas)
                if validas is not None:
                    del_conv = validas
            total_delegacoes += del_conv

        return (FEITO, f'{total_delegacoes} delegações') if total_delegacoes >= minimo else \
               (NAO_FEITO, f'{total_delegacoes} delegações, mínimo {minimo}')

    return NAO_PREENCHIDO, f'tipo desconhecido: {tipo}'


def conferir(ordem, raiz=None):
    ordem = Path(ordem)
    raiz = Path(raiz) if raiz else Path(git(ordem.parent, 'rev-parse', '--show-toplevel') or ordem.parent)
    itens = ler_entregas(ordem.read_text(encoding='utf-8'))
    resultado = []
    for it in itens:
        estado, detalhe = conferir_item(it, raiz)
        resultado.append({'id': it['id'], 'tipo': it['tipo'], 'estado': estado, 'detalhe': detalhe})
    return {
        'ordem': str(ordem),
        'etapa': ordem.stem,
        'conferido_em': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'commit': git(raiz, 'rev-parse', 'HEAD'),
        'itens': resultado,
        'feitos': sum(1 for r in resultado if r['estado'] == FEITO),
        'total': len(resultado),
    }


def registrar(rel, pasta_sociedade=None, autor='conferência automática'):
    from sc_registro import Registro
    reg = Registro(pasta_sociedade or localizar_sociedade_da_etapa(rel['etapa']))  # B11a

    def gerador(_dados):
        return [{'tipo': 'conferencia_registrada', 'dados': {
            'etapa': rel['etapa'], 'ordem': rel['ordem'], 'commit': rel['commit'],
            'feitos': rel['feitos'], 'total': rel['total'],
            'itens': [{k: i[k] for k in ('id', 'tipo', 'estado', 'detalhe')} for i in rel['itens']],
        }}]
    reg.aplicar_mutacao(gerador, autor=autor, aplicar=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ordem', required=True, help='arquivo da ordem com o bloco ```entregas')
    ap.add_argument('--raiz', help='raiz do repositório (padrão: a da ordem)')
    ap.add_argument('--registrar', action='store_true', help='grava o resultado no registro.json')
    ap.add_argument('--pasta-sociedade', help='pasta do registro (padrão: sociedade/ do worktree da etapa, se existir; '
                    'senão a canônica)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        rel = conferir(a.ordem, a.raiz)
    except (OSError, ValueError) as e:
        print(f'erro: {e}', file=sys.stderr)
        return 2
    if a.registrar:
        registrar(rel, Path(a.pasta_sociedade) if a.pasta_sociedade else None)
    if a.json:
        print(json.dumps(rel, ensure_ascii=False, indent=2))
    else:
        print(f'Conferência de {rel["ordem"]}: {rel["feitos"]} de {rel["total"]} feitas')
        for r in rel['itens']:
            print(f'  [{r["estado"]:^14}] {r["id"]:<5} {r["tipo"]:<18} {r["detalhe"]}')
    return 0 if rel['feitos'] == rel['total'] else 1


if __name__ == '__main__':
    sys.exit(main())
