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
    `--no-renames`: numa renomeação contam a origem e o destino. None se o intervalo for inválido."""
    r = subprocess.run(['git', '-C', str(raiz), '-c', 'core.quotepath=off', 'diff', '--name-only', '-z', '--no-renames', base, head],
                       capture_output=True)
    if r.returncode != 0:
        return None
    return [unicodedata.normalize('NFC', os.fsdecode(c)) for c in r.stdout.split(b'\0') if c]


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


def resolver_conversa_etapa(etapa, pasta_sociedade=None, brain_dir=None, summaries_db=None):
    """Resolve @<etapa> para o ID da conversa do Antigravity aberta no worktree após a passagem para Gandalf."""
    from sc_registro import Registro, localizar_sociedade_da_etapa, localizar_sociedade_canonica
    try:
        soc = Path(pasta_sociedade) if pasta_sociedade else localizar_sociedade_da_etapa(etapa)
    except Exception:
        soc = None

    if not soc or not soc.is_dir():
        soc = localizar_sociedade_canonica()

    pasta_wt = soc.parent.resolve() if soc else None
    if not pasta_wt or not pasta_wt.exists():
        return None, f'worktree da etapa "{etapa}" não encontrado'

    pasta_wt_norm = pasta_wt.as_posix()

    try:
        reg = Registro(soc)
        eventos = reg.dados.get('eventos', [])
    except Exception as e:
        return None, f'erro ao ler registro da etapa "{etapa}": {e}'

    passagens = [
        ev for ev in eventos
        if ev.get('tipo') == 'passagem' and (ev.get('dados') or {}).get('para') == 'gandalf'
        and (not (ev.get('dados') or {}).get('etapa') or (ev.get('dados') or {}).get('etapa') == etapa)
    ]
    if not passagens:
        return None, f'nenhum evento de passagem para o Gandalf registrado na etapa "{etapa}"'

    passagem_ev = passagens[-1]
    ts_str = passagem_ev.get('timestamp') or (passagem_ev.get('dados') or {}).get('data_hora')
    if not ts_str:
        return None, f'timestamp da passagem para Gandalf ausente na etapa "{etapa}"'
    try:
        ts_passagem = datetime.fromisoformat(str(ts_str).replace('Z', '+00:00'))
        if ts_passagem.tzinfo is None:
            ts_passagem = ts_passagem.replace(tzinfo=timezone.utc)
    except Exception:
        return None, f'timestamp da passagem para Gandalf inválido: "{ts_str}"'

    b_dir = Path(brain_dir) if brain_dir else (Path.home() / '.gemini' / 'antigravity' / 'brain')
    s_db = Path(summaries_db) if summaries_db else (Path.home() / '.gemini' / 'antigravity' / 'conversation_summaries.db')

    candidatas = set()

    if s_db and s_db.is_file():
        try:
            import sqlite3
            conn = sqlite3.connect(s_db)
            cur = conn.cursor()
            cur.execute("SELECT conversation_id, last_user_input_time, last_modified_time, workspace_uris FROM conversation_summaries")
            for cid, l_input, l_mod, uris in cur.fetchall():
                uris_cands = _extrair_uris_workspace(uris)
                if pasta_wt_norm not in uris_cands:
                    continue
                t_str = l_input or l_mod
                if not t_str:
                    continue
                try:
                    t_dt = datetime.fromisoformat(str(t_str).replace('Z', '+00:00'))
                    if t_dt.tzinfo is None:
                        t_dt = t_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if t_dt >= ts_passagem:
                    candidatas.add(cid)
            conn.close()
        except Exception:
            pass

    padrao_pasta = re.compile(r'(?:^|[\s\'"`,;:(<\[])' + re.escape(pasta_wt_norm) + r'(?:$|[\s\'"`,;:)>\]]|\.(?:\s|$))')

    if b_dir and b_dir.is_dir():
        for t_file in b_dir.glob('*/.system_generated/logs/transcript*.jsonl'):
            cid = t_file.parents[2].name
            try:
                with t_file.open(encoding='utf-8', errors='replace') as f:
                    primeira_linha = f.readline()
                if not primeira_linha.strip():
                    if cid in candidatas:
                        candidatas.remove(cid)
                    continue
                o = json.loads(primeira_linha)
                c_at = o.get('created_at')
                if not c_at:
                    if cid in candidatas:
                        candidatas.remove(cid)
                    continue
                t_dt = datetime.fromisoformat(str(c_at).replace('Z', '+00:00'))
                if t_dt.tzinfo is None:
                    t_dt = t_dt.replace(tzinfo=timezone.utc)
                if t_dt < ts_passagem:
                    if cid in candidatas:
                        candidatas.remove(cid)
                    continue

                caminhos_explicit = set()
                for k in ('workspace', 'workspace_uris', 'workspaces', 'cwd'):
                    if k in o and o[k]:
                        caminhos_explicit.update(_extrair_uris_workspace(o[k]))
                if caminhos_explicit:
                    if pasta_wt_norm not in caminhos_explicit:
                        if cid in candidatas:
                            candidatas.remove(cid)
                        continue
                else:
                    texto_busca = o.get('content') or primeira_linha
                    if not isinstance(texto_busca, str):
                        texto_busca = str(texto_busca)
                    if not padrao_pasta.search(texto_busca):
                        if cid in candidatas:
                            candidatas.remove(cid)
                        continue

                candidatas.add(cid)
            except Exception:
                if cid in candidatas:
                    candidatas.remove(cid)
                continue

    if len(candidatas) > 1 and b_dir and b_dir.is_dir():
        gandalf_cands = set()
        for cid in candidatas:
            t_file = b_dir / cid / '.system_generated' / 'logs' / 'transcript.jsonl'
            if t_file.is_file():
                try:
                    with t_file.open(encoding='utf-8', errors='replace') as f:
                        line1 = f.readline()
                    if 'Para: Gandalf' in line1 or 'para: gandalf' in line1.lower():
                        gandalf_cands.add(cid)
                except Exception:
                    pass
        if gandalf_cands:
            candidatas = gandalf_cands

    if not candidatas:
        return None, f'nenhuma conversa do Antigravity encontrada para a etapa "{etapa}" após a passagem'
    if len(candidatas) > 1:
        return None, f'ambiguidade: {len(candidatas)} conversas do Antigravity encontradas para a etapa "{etapa}" após a passagem'

    return list(candidatas)[0], None


def conferir_item(item, raiz):
    tipo, args = item['tipo'], item['args']
    if any(MARCADOR.search(a) for a in args) or not args:
        return NAO_PREENCHIDO, 'argumento com marcador <...> ou vazio'
    caminho = lambda rel: (raiz / rel) if not Path(rel).is_absolute() else Path(rel)  # noqa: E731

    if tipo == 'commit_existe':
        sha = git(raiz, 'rev-parse', '--verify', f'{args[0]}^{{commit}}')
        return (FEITO, sha[:12]) if sha else (NAO_FEITO, f'commit {args[0]} não existe')

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
            if not esperado.startswith(at['commit'][:7]) and not at['commit'].startswith(esperado[:7]):
                return NAO_FEITO, f'atestado do commit {at["commit"][:12]}, esperado {esperado[:12]}'
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
        if args[0] == 'antigravity' and ident.startswith('@'):
            etapa_alvo = ident[1:].strip()
            if not etapa_alvo or etapa_alvo == 'etapa':
                etapa_alvo = raiz.name
            conv_id, motivo = resolver_conversa_etapa(etapa_alvo, pasta_sociedade=raiz / 'sociedade')
            if not conv_id:
                return NAO_FEITO, motivo
            ident = conv_id
        try:
            if args[0] == 'claude':
                m = medir('claude', sessao=ident)
            else:
                m = medir('antigravity', conversa=ident)
        except ErroSessao as e:
            return NAO_FEITO, str(e)
        if tipo == 'conversa_nova':
            return (FEITO, '1 ordem na conversa') if m['conversa_nova'] else \
                   (NAO_FEITO, f'{m["ordens_na_conversa"]} ordens na mesma conversa')
        if 'delegacoes_total' not in m:
            return NAO_FEITO, 'o identificador é de um subagente, não de uma sessão; delegações não medidas'
        minimo = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
        return (FEITO, f'{m["delegacoes_total"]} delegações') if m['delegacoes_total'] >= minimo else \
               (NAO_FEITO, f'{m["delegacoes_total"]} delegações, mínimo {minimo}')

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
