#!/usr/bin/env python3
"""Medição objetiva de uma sessão de agente pelo log local do aplicativo (Q141, Q126).

Lê o log do Antigravity (transcript.jsonl), do Codex (rollout .jsonl) ou do Claude Code
(sessão .jsonl) e devolve só metadados e contagens: passos, mensagens do usuário, modelo e
esforço, ferramentas usadas, delegações, arquivos mais relidos, execuções de teste e
leituras fora da pasta permitida. Nunca reproduz conteúdo de arquivo nem de mensagem.
No Claude Code soma também as contagens de uso do log (entrada, cache escrito, cache lido e
saída) por agente e por modelo, contando cada mensagem uma vez. Estimar consumo, custo ou
cota continua proibido: só vale o que o log registra.

Uso:
  sc_sessao.py antigravity [--conversa <id> | --log <transcript.jsonl>] [--json]
  sc_sessao.py codex --pasta <pasta permitida> [--log <rollout.jsonl>] [--json]
  sc_sessao.py claude [--pasta <pasta do projeto>] [--log <sessao.jsonl> | --sessao <id>] [--projetos <pasta>] [--desde <ISO 8601>] [--json]

Sem --log, usa a sessão mais recente do aplicativo (no Codex, a mais recente que menciona a pasta).
No Claude Code, lê também os subagentes da sessão (<sessão>/subagents/agent-*.jsonl). A pasta de
projetos vem de --projetos, da variável SC_CLAUDE_PROJETOS ou de ~/.claude/projects.
--desde mede só o trecho a partir do instante (ISO 8601; sem fuso, UTC). Log ausente
ou ilegível é erro (falha fechada), nunca zero.
"""
import argparse
import collections
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
AG_BRAIN = HOME / '.gemini' / 'antigravity' / 'brain'
AG_CONVERSATIONS = HOME / '.gemini' / 'antigravity' / 'conversations'
CODEX_SESSOES = HOME / '.codex' / 'sessions'
CLAUDE_PROJETOS = HOME / '.claude' / 'projects'
TESTE = re.compile(r'unittest|pytest|sc_pre_devolucao|sc\.py entregar|validar_pacote|npm (?:run )?test')
# Leitura de arquivo feita por comando de terminal (cat, head, tail, sed -n, less, nl):
# conta como leitura, para a releitura não escapar da medição quando o agente não usa a ferramenta de leitura.
LEITURA_CMD = re.compile(r"(?:^|[\s;&|(])(?:cat|head|tail|less|nl|sed\s+-n\s+(?:'[^']*'|\"[^\"]*\"|\S+))"
                         r"(?:\s+-{1,2}[\w=-]+(?:\s+\d+)?)*\s+((?:[~./]|[\w-]+/)[^\s;&|<>'\"]+)")
CAMINHO = re.compile(r'(?:/home/[^\s"\'`\\,;)|>]+|~/[^\s"\'`\\,;)|>]+)')
SENSIVEIS = ('pareceres/calibracao', 'comparacao-conjunto', '.codex/memories', 'gabarito')


class ErroSessao(Exception):
    """Log ausente ou ilegível."""


def ler_jsonl(caminho):
    for linha in Path(caminho).read_text(encoding='utf-8', errors='replace').splitlines():
        if linha.strip():
            try:
                yield json.loads(linha)
            except json.JSONDecodeError:
                continue


def duracao_min(inicio, fim):
    try:
        a = datetime.fromisoformat(str(inicio).replace('Z', '+00:00'))
        b = datetime.fromisoformat(str(fim).replace('Z', '+00:00'))
        return int((b - a).total_seconds() // 60)
    except (ValueError, TypeError):
        return None


def normalizar(caminho):
    return str(caminho).replace('~/', str(HOME) + '/').rstrip('.:')


def leituras_por_comando(comando):
    """Arquivos lidos por comandos de terminal dentro de uma linha de comando."""
    return [m.group(1).replace(str(HOME), '~') for m in LEITURA_CMD.finditer(str(comando or ''))]


def relidos(contagem, limite=8):
    return {k: v for k, v in contagem.most_common(limite) if v > 1}


# ------------------------------------------------------------------ Antigravity

def inspecionar_base_antigravity(conversa=None):
    """Lê as bases de ~/.gemini/antigravity/conversations/ e tenta extrair tokens; se não expuser, sai 'n/d' com hipóteses."""
    banco = None
    if conversa:
        cand = AG_CONVERSATIONS / f'{conversa}.db'
        if cand.is_file():
            banco = cand
    if not banco and AG_CONVERSATIONS.is_dir():
        dbs = sorted(AG_CONVERSATIONS.glob('*.db'), key=lambda p: p.stat().st_mtime, reverse=True)
        if dbs:
            banco = dbs[0]

    tokens_expostos = False
    if banco and banco.is_file():
        try:
            import sqlite3
            conn = sqlite3.connect(banco)
            cur = conn.cursor()
            cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
            tabelas = cur.fetchall()
            for _, sql in tabelas:
                if sql and any(k in sql.lower() for k in ('tokens', 'input_tokens', 'output_tokens', 'prompt_tokens')):
                    tokens_expostos = True
                    break
            conn.close()
        except Exception:
            pass

    hipoteses = [
        '1. Bases SQLite do Antigravity (~/.gemini/antigravity/conversations/*.db) armazenam dados brutos e metadados em blobs protobuf sem colunas de tokens explícitas.',
        '2. A telemetria e faturamento de tokens do Gemini são geridos e contabilizados pelo backend em nuvem do Google, sem replicação de contadores locais.',
        '3. O transcript local (transcript.jsonl) registra apenas chamadas de ferramentas e mensagens sem os campos de usageMetadata retornados pela API.'
    ]
    return {
        'consumo': 'n/d',
        'motivo': 'Tokens não expostos localmente nas bases do Antigravity (Q12)',
        'hipoteses': hipoteses
    }


def log_antigravity(conversa=None):
    if conversa:
        arq = AG_BRAIN / conversa / '.system_generated' / 'logs' / 'transcript.jsonl'
        if not arq.is_file():
            raise ErroSessao(f'Conversa do Antigravity não encontrada: {conversa}')
        return arq
    candidatos = sorted(AG_BRAIN.glob('*/.system_generated/logs/transcript.jsonl'),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidatos:
        raise ErroSessao('Nenhuma conversa do Antigravity encontrada.')
    return candidatos[0]


def medir_antigravity(log):
    passos = list(ler_jsonl(log))
    ferramentas, lidos = collections.Counter(), collections.Counter()
    delegacoes_por_ordem, testes, ordens = [], 0, 0
    for o in passos:
        if o.get('type') == 'USER_INPUT':
            ordens += 1
            delegacoes_por_ordem.append(0)
        for tc in o.get('tool_calls') or []:
            nome = tc.get('name')
            ferramentas[nome] += 1
            args = tc.get('args', {}) or {}
            if nome == 'invoke_subagent' and delegacoes_por_ordem:
                delegacoes_por_ordem[-1] += 1
            if nome == 'view_file':
                lidos[str(args.get('AbsolutePath', '')).strip('"').replace(str(HOME), '~')] += 1
            if nome == 'run_command':
                linha_cmd = str(args.get('CommandLine', ''))
                if TESTE.search(linha_cmd):
                    testes += 1
                for arq in leituras_por_comando(linha_cmd):
                    lidos[arq] += 1
    inicio = passos[0].get('created_at') if passos else None
    fim = passos[-1].get('created_at') if passos else None
    conversa_id = Path(log).parents[2].name if len(Path(log).parents) > 2 else None
    dados_consumo = inspecionar_base_antigravity(conversa_id)

    return {
        'aplicativo': 'antigravity',
        'log': str(log),
        'conversa': conversa_id,
        'inicio': inicio, 'fim': fim, 'duracao_min': duracao_min(inicio, fim),
        'passos': len(passos),
        'ordens_na_conversa': ordens,
        'conversa_nova': ordens == 1,
        'delegacoes_total': sum(delegacoes_por_ordem),
        'delegacoes_por_ordem': delegacoes_por_ordem,
        'ferramentas': dict(ferramentas.most_common()),
        'execucoes_de_teste': testes,
        'arquivos_relidos': relidos(lidos),
        'consumo': dados_consumo['consumo'],
        'motivo_consumo': dados_consumo['motivo'],
        'hipoteses_consumo': dados_consumo['hipoteses'],
    }


# ------------------------------------------------------------------------ Codex

def consumo_codex(log):
    """Soma entrada, cache lido e saída pelo log de rollout do Codex (~/.codex/sessions)."""
    linhas = list(ler_jsonl(log)) if isinstance(log, (str, Path)) else list(log)
    entrada = 0
    cache_lido = 0
    cache_escrito = 0
    saida = 0
    mensagens = 0
    modelos = set()
    for o in linhas:
        if o.get('type') == 'turn_context':
            m = (o.get('payload') or {}).get('model')
            if m:
                modelos.add(m)
        p = o.get('payload') or {}
        if p.get('type') == 'token_count':
            info = p.get('info') or {}
            u = info.get('last_token_usage') or info.get('total_token_usage') or {}
            if u:
                mensagens += 1
                entrada += int(u.get('input_tokens') or 0)
                cache_lido += int(u.get('cached_input_tokens') or 0)
                cache_escrito += int(u.get('cache_write_input_tokens') or 0)
                saida += int(u.get('output_tokens') or 0)
            continue
        u = p.get('usage') or o.get('usage') or {}
        if u:
            mensagens += 1
            entrada += int(u.get('input_tokens') or 0)
            cache_lido += int(u.get('cached_input_tokens') or 0)
            cache_escrito += int(u.get('cache_write_input_tokens') or 0)
            saida += int(u.get('output_tokens') or 0)
            if p.get('model'):
                modelos.add(p.get('model'))
    modelo_str = ', '.join(sorted(modelos)) if modelos else 'codex'
    tabela = [{
        'agente': 'barbarvore',
        'modelo': modelo_str,
        'mensagens': mensagens,
        'entrada': entrada,
        'cache_escrito': cache_escrito,
        'cache_lido': cache_lido,
        'saida': saida
    }] if mensagens else []
    total = {
        'mensagens': mensagens,
        'entrada': entrada,
        'cache_escrito': cache_escrito,
        'cache_lido': cache_lido,
        'saida': saida
    }
    return {
        'por_agente_e_modelo': tabela,
        'total': total
    }


def log_codex(pasta=None):
    candidatos = sorted(CODEX_SESSOES.rglob('rollout-*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
    if pasta:
        for arq in candidatos:
            texto = arq.read_text(encoding='utf-8', errors='replace')
            if pasta in texto and '"codex-auto-review"' not in texto:
                return arq
        raise ErroSessao('Nenhuma sessão do Codex menciona essa pasta.')
    if candidatos:
        return candidatos[0]
    raise ErroSessao('Nenhuma sessão do Codex encontrada.')


def _texto_mensagem(payload):
    return ' '.join(c.get('text', '') for c in payload.get('content', []) if isinstance(c, dict))


def medir_codex(log, pasta=None):
    linhas = list(ler_jsonl(log))
    if not pasta:
        for o in linhas:
            if o.get('type') == 'turn_context':
                cwd = (o.get('payload') or {}).get('cwd')
                if cwd:
                    pasta = cwd
                    break
        if not pasta:
            pasta = str(Path.cwd())
    pasta = normalizar(pasta)
    turnos, mensagens, fora, lidos = [], 0, collections.Counter(), collections.Counter()
    memoria_injetada = memoria_lida = relativos = testes = 0
    sensiveis = collections.Counter()
    for o in linhas:
        p = o.get('payload') if isinstance(o.get('payload'), dict) else {}
        bruto = json.dumps(o, ensure_ascii=False)
        for s in SENSIVEIS:
            sensiveis[s] += bruto.count(s)
        if o.get('type') == 'turn_context':
            turnos.append((p.get('model'), p.get('effort'), p.get('cwd')))
        if p.get('type') == 'message' and p.get('role') in ('developer', 'system') and 'memory_summary' in bruto:
            memoria_injetada += 1
        if p.get('type') == 'message' and p.get('role') == 'user':
            t = _texto_mensagem(p).lstrip()
            if not t.startswith(('<environment_context', '<recommended_plugins', '# AGENTS', '<user_instructions')):
                mensagens += 1
        if p.get('type') in ('custom_tool_call', 'function_call'):
            entrada = str(p.get('input') or p.get('arguments') or '')
            if '.codex/memories' in entrada:
                memoria_lida += 1
            if re.search(r'(^|[\s"\'])\.\.(/|\s|"|$)', entrada):
                relativos += 1
            if TESTE.search(entrada):
                testes += 1
            for arq in leituras_por_comando(entrada.replace('\\n', '\n')):
                lidos[arq] += 1
            for c in CAMINHO.findall(entrada):
                c = normalizar(c)
                if not (c.startswith(pasta) or c.startswith('/tmp')):
                    fora[c[:120]] += 1
    inicio = linhas[0].get('timestamp') if linhas else None
    fim = linhas[-1].get('timestamp') if linhas else None
    return {
        'aplicativo': 'codex',
        'log': str(log),
        'inicio': inicio, 'fim': fim, 'duracao_min': duracao_min(inicio, fim),
        'mensagens_do_usuario': mensagens,
        'conversa_nova': mensagens == 1,
        'modelos_esforcos': sorted({f'{m} / {e}' for m, e, _ in turnos}),
        'pasta_da_sessao_e_a_permitida': bool(turnos) and all(normalizar(c or '').startswith(pasta) for *_, c in turnos),
        'memoria_injetada': memoria_injetada > 0,
        'memoria_lida_por_comando': memoria_lida,
        'comandos_com_caminho_acima': relativos,
        'execucoes_de_teste': testes,
        'arquivos_relidos': relidos(lidos),
        'caminhos_fora_da_pasta': dict(fora.most_common(15)),
        'mencoes_sensiveis': {k: v for k, v in sensiveis.items() if v},
        'consumo': consumo_codex(linhas),
    }


# ------------------------------------------------------------------ Claude Code

def projetos_claude(projetos=None):
    """Pasta dos projetos do Claude Code: parâmetro, variável SC_CLAUDE_PROJETOS ou o padrão."""
    return Path(projetos or os.environ.get('SC_CLAUDE_PROJETOS') or CLAUDE_PROJETOS)


def ler_jsonl_estrito(caminho):
    """Lê o log do Claude Code; ausente, ilegível ou sem nenhuma linha JSON válida é ErroSessao."""
    try:
        texto = Path(caminho).read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as e:
        raise ErroSessao(f'Log ausente ou ilegível: {caminho} ({type(e).__name__})') from e
    linhas = []
    for linha in texto.splitlines():
        if linha.strip():
            try:
                obj = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                linhas.append(obj)
    if not linhas:
        raise ErroSessao(f'Log sem nenhuma linha JSON válida: {caminho}')
    return linhas


def log_claude(pasta=None, projetos=None):
    base_projetos = projetos_claude(projetos)
    if pasta:
        slug = re.sub(r'[^A-Za-z0-9]', '-', str(Path(pasta).resolve()))
        base = base_projetos / slug
        candidatos = sorted(base.glob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True) if base.is_dir() else []
    else:
        candidatos = sorted(base_projetos.glob('*/*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidatos:
        raise ErroSessao('Nenhuma sessão do Claude Code encontrada.')
    return candidatos[0]


_IDENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')


def localizar_claude(ident, projetos=None):
    """Acha a sessão (<id>.jsonl) ou o subagente (agent-<id>.jsonl) pelo identificador. Devolve (tipo, caminho)."""
    if not ident or not _IDENT.match(str(ident)):
        raise ErroSessao(f'Identificador inválido: {ident!r}')
    base = projetos_claude(projetos)
    sessoes = sorted(base.glob(f'*/{ident}.jsonl')) if base.is_dir() else []
    if sessoes:
        return 'sessao', sessoes[0]
    agente = str(ident) if str(ident).startswith('agent-') else f'agent-{ident}'
    agentes = sorted(base.glob(f'*/*/subagents/{agente}.jsonl')) if base.is_dir() else []
    if agentes:
        return 'agente', agentes[0]
    raise ErroSessao(f'Sessão ou subagente do Claude Code não encontrado: {ident}')


def subagentes_claude(log):
    """Logs dos subagentes da sessão: <sessão>/subagents/agent-*.jsonl."""
    pasta = Path(log).with_suffix('') / 'subagents'
    return sorted(pasta.glob('agent-*.jsonl')) if pasta.is_dir() else []


def _e_ordem(o):
    """Mensagem de usuário que não é resultado de ferramenta nem nota do sistema (isMeta)."""
    if o.get('type') != 'user' or o.get('isMeta'):
        return False
    conteudo = (o.get('message') or {}).get('content')
    if isinstance(conteudo, str):
        return bool(conteudo.strip())
    return isinstance(conteudo, list) and any(isinstance(b, dict) and b.get('type') == 'text' for b in conteudo) \
        and not any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in conteudo)


def _delegacoes_do(linhas):
    return [b.get('id') or f'sem-id-{i}' for i, o in enumerate(linhas) if o.get('type') == 'assistant'
            for b in ((o.get('message') or {}).get('content') or [])
            if isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('name') in ('Agent', 'Task')]


def medir_subagente(log):
    linhas = ler_jsonl_estrito(log)
    ordens = sum(1 for o in linhas if _e_ordem(o))
    meta = {}
    try:
        meta = json.loads(Path(log).with_suffix('.meta.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        pass
    return {
        'agente': Path(log).stem.removeprefix('agent-'),
        'tipo': meta.get('agentType') if isinstance(meta, dict) else None,
        'log': str(log),
        'passos': sum(1 for o in linhas if o.get('type') == 'assistant'),
        'ordens_na_conversa': ordens,
        'conversa_nova': ordens == 1,
        'delegacoes': len(_delegacoes_do(linhas)),
    }


_USO = (('entrada', 'input_tokens'), ('cache_escrito', 'cache_creation_input_tokens'),
        ('cache_lido', 'cache_read_input_tokens'), ('saida', 'output_tokens'))
_PARA = re.compile(r'^\s*Para:\s*([^\s·,.:;()\[\]]+)')


def instante(valor):
    """ISO 8601 (com Z, offset ou sem fuso = UTC) em datetime com fuso; inválido: ValueError."""
    d = datetime.fromisoformat(str(valor).strip().replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _desde(desde):
    if desde in (None, ''):
        return None
    try:
        return instante(desde)
    except ValueError as e:
        raise ErroSessao(f'--desde inválido: {desde!r} (use ISO 8601, ex.: 2026-10-03T12:00:00Z)') from e


def _texto_da_ordem(o):
    c = (o.get('message') or {}).get('content')
    if isinstance(c, list):
        c = ' '.join(b.get('text', '') for b in c if isinstance(b, dict) and b.get('type') == 'text')
    return c if isinstance(c, str) else ''


def nome_do_agente(log, linhas, principal=False):
    """'principal'; senão o agentType do .meta.json; senão o papel de 'Para: <Papel>' no 1º pedido; senão agent-<id>."""
    if principal:
        return 'principal'
    try:
        meta = json.loads(Path(log).with_suffix('.meta.json').read_text(encoding='utf-8'))
        if isinstance(meta, dict) and str(meta.get('agentType') or '').strip():
            return str(meta['agentType']).strip().lower()
    except (OSError, ValueError):
        pass
    for o in linhas:
        if o.get('type') == 'user':
            m = _PARA.match(_texto_da_ordem(o))
            if m:
                return m.group(1).lower()
            if _texto_da_ordem(o).strip():
                break
    return Path(log).stem


def _mensagens_de_uso(log, linhas, agente, desde):
    """(id, agente, modelo, {entrada, cache_escrito, cache_lido, saida}) de cada registro assistant com uso."""
    for i, o in enumerate(linhas):
        msg = o.get('message') if isinstance(o.get('message'), dict) else {}
        uso, modelo = msg.get('usage'), msg.get('model')
        if o.get('type') != 'assistant' or not isinstance(uso, dict) or not modelo or modelo == '<synthetic>':
            continue
        if desde:
            try:
                if instante(o.get('timestamp')) < desde:
                    continue
            except ValueError:  # sem instante válido não dá para provar que está no trecho
                continue
        num = {k: (uso.get(c) if isinstance(uso.get(c), int) and uso.get(c) > 0 else 0) for k, c in _USO}
        yield msg.get('id') or f'{log}#{i}', agente, modelo, num


def consumo_claude(logs, desde=None, incluir_subagentes=True):
    """Soma o uso do log por agente e modelo (principal e subagents/). Uma mensagem conta uma vez, mesmo
    partida em blocos ou repetida entre arquivos; com valores divergentes, fica o de maior saída."""
    inicio, vistas = _desde(desde), {}
    for log in logs:
        for arq in [Path(log), *(subagentes_claude(log) if incluir_subagentes else [])]:
            linhas = ler_jsonl_estrito(arq)
            ag = nome_do_agente(arq, linhas, principal=(arq == Path(log)))
            for id_, agente, modelo, num in _mensagens_de_uso(arq, linhas, ag, inicio):
                if id_ not in vistas or num['saida'] > vistas[id_][2]['saida']:
                    vistas[id_] = (agente, modelo, num)
    linhas_ = {}
    for agente, modelo, num in vistas.values():
        l = linhas_.setdefault((agente, modelo), {'agente': agente, 'modelo': modelo, 'mensagens': 0, **{k: 0 for k, _ in _USO}})
        l['mensagens'] += 1
        for k, _ in _USO:
            l[k] += num[k]
    tabela = sorted(linhas_.values(), key=lambda x: (-x['saida'], x['agente'], x['modelo']))
    total = {'mensagens': sum(x['mensagens'] for x in tabela), **{k: sum(x[k] for x in tabela) for k, _ in _USO}}
    return {'desde': inicio.isoformat() if inicio else None, 'por_agente_e_modelo': tabela, 'total': total}


def consumo_tolerante(logs, desde=None):
    """Para o `decidir`: consumo do log, ou None se não houver log, se ele não puder ser lido ou se não
    tiver nenhum registro de uso no trecho (a coluna sai n/d)."""
    if not logs:
        return None
    try:
        c = consumo_claude(logs, desde)
    except (ErroSessao, OSError, ValueError):
        return None
    return c if c['total']['mensagens'] else None


def medir_claude(log, pasta=None, desde=None):
    pasta_n = normalizar(Path(pasta).resolve()) if pasta else None
    ferramentas, ferramentas_sub, lidos = collections.Counter(), collections.Counter(), collections.Counter()
    modelos, esforcos, fora = collections.Counter(), collections.Counter(), collections.Counter()
    mensagens = passos = delegacoes = testes = ordens = 0
    inicio = fim = None
    linhas = ler_jsonl_estrito(log)
    for o in linhas:
        ts = o.get('timestamp')
        if ts:
            inicio = inicio or ts
            fim = ts
        tipo = o.get('type')
        msg = o.get('message') if isinstance(o.get('message'), dict) else {}
        lateral = bool(o.get('isSidechain'))
        if tipo == 'user' and not lateral and o.get('turnOrigin') == 'human':
            mensagens += 1
        if not lateral and _e_ordem(o):
            ordens += 1
        if tipo != 'assistant':
            continue
        passos += 1
        if msg.get('model'):
            modelos[msg['model']] += 1
        if o.get('effort'):
            esforcos[o['effort']] += 1
        for bloco in msg.get('content') or []:
            if not isinstance(bloco, dict) or bloco.get('type') != 'tool_use':
                continue
            nome = bloco.get('name', '')
            entrada = bloco.get('input') or {}
            (ferramentas_sub if lateral else ferramentas)[nome] += 1
            if nome in ('Agent', 'Task') and not lateral:
                delegacoes += 1
            if nome == 'Read':
                lidos[str(entrada.get('file_path', '')).replace(str(HOME), '~')] += 1
            texto = json.dumps(entrada, ensure_ascii=False)
            if nome == 'Bash':
                comando = str(entrada.get('command', ''))
                if TESTE.search(comando):
                    testes += 1
                for arq in leituras_por_comando(comando):
                    lidos[arq] += 1
            if pasta_n:
                for c in CAMINHO.findall(texto):
                    c = normalizar(c)
                    if not (c.startswith(pasta_n) or c.startswith('/tmp') or '/.claude/' in c or '/.sociedade/' in c):
                        fora[c[:120]] += 1
    subagentes = [medir_subagente(a) for a in subagentes_claude(log)]
    chamadas = len(_delegacoes_do(linhas)) + sum(a['delegacoes'] for a in subagentes)
    com_execucao = sum(1 for a in subagentes if a['passos'] > 0)
    return {
        'aplicativo': 'claude',
        'log': str(log),
        'sessao': Path(log).stem,
        'inicio': inicio, 'fim': fim, 'duracao_min': duracao_min(inicio, fim),
        'mensagens_do_usuario': mensagens,
        'ordens_na_conversa': ordens,
        'conversa_nova': ordens == 1,
        'delegacoes_chamadas': chamadas,
        'delegacoes_total': min(chamadas, com_execucao),
        'subagentes': subagentes,
        'passos_do_agente': passos,
        'modelos': dict(modelos.most_common()),
        'esforcos': dict(esforcos.most_common()),
        'delegacoes_por_subagente': delegacoes,
        'ferramentas': dict(ferramentas.most_common()),
        'ferramentas_dos_subagentes': dict(ferramentas_sub.most_common()),
        'execucoes_de_teste': testes,
        'arquivos_relidos': relidos(lidos),
        'caminhos_fora_da_pasta': dict(fora.most_common(10)) if pasta_n else None,
        'consumo': consumo_claude([log], desde),
    }


# ------------------------------------------------------------------------ saída

def medir(app, log=None, pasta=None, conversa=None, projetos=None, sessao=None, desde=None):
    if desde and app != 'claude':
        raise ErroSessao('--desde só vale para o Claude Code.')
    if app == 'antigravity':
        return medir_antigravity(Path(log) if log else log_antigravity(conversa))
    if app == 'codex':
        if not pasta and not log:
            pasta = str(Path.cwd())
        return medir_codex(Path(log) if log else log_codex(normalizar(pasta) if pasta else None), pasta)
    if app == 'claude':
        if not log and sessao:
            tipo, achado = localizar_claude(sessao, projetos)
            if tipo != 'sessao':
                return {**medir_subagente(achado), 'consumo': consumo_claude([achado], desde, incluir_subagentes=False)}
            log = achado
        return medir_claude(Path(log) if log else log_claude(pasta, projetos), pasta, desde)
    raise ErroSessao(f'Aplicativo desconhecido: {app}')


def imprimir_consumo(c):
    print('consumo' + (f' (desde {c["desde"]})' if c.get('desde') else '') + ':')
    cab = ('agente', 'modelo', 'entrada', 'cache escrito', 'cache lido', 'saída')
    linhas = [(x['agente'], x['modelo'], *(f'{x[k]:,}'.replace(',', '.') for k in ('entrada', 'cache_escrito', 'cache_lido', 'saida')))
              for x in c['por_agente_e_modelo']]
    t = c['total']
    linhas.append(('total', '', *(f'{t[k]:,}'.replace(',', '.') for k in ('entrada', 'cache_escrito', 'cache_lido', 'saida'))))
    larg = [max(len(str(r[i])) for r in [cab, *linhas]) for i in range(6)]
    for r in [cab, *linhas]:
        print('    ' + '  '.join(str(v).ljust(larg[i]) if i < 2 else str(v).rjust(larg[i]) for i, v in enumerate(r)))


def imprimir(rel):
    for chave, valor in rel.items():
        if chave == 'consumo' and isinstance(valor, dict) and 'por_agente_e_modelo' in valor:
            imprimir_consumo(valor)
        elif chave == 'hipoteses_consumo' and isinstance(valor, list):
            print('hipóteses para ausência de tokens expostos (Q12):')
            for h in valor:
                print(f'    {h}')
        elif isinstance(valor, dict):
            print(f'{chave}:')
            for k, v in (valor or {}).items():
                print(f'    {v:>5}  {k}')
            if not valor:
                print('    (nenhum)')
        elif isinstance(valor, list) and valor and all(isinstance(x, dict) for x in valor):
            print(f'{chave}:')
            for x in valor:
                print('    ' + ', '.join(f'{k}={v}' for k, v in x.items() if k != 'log'))
        elif isinstance(valor, list):
            print(f'{chave}: {", ".join(str(x) for x in valor) or "(nenhum)"}')
        else:
            print(f'{chave}: {valor}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('app', choices=('antigravity', 'codex', 'claude'))
    ap.add_argument('--log', help='arquivo de log; sem ele, usa a sessão mais recente')
    ap.add_argument('--pasta', help='pasta permitida (Codex) ou pasta do projeto (Claude)')
    ap.add_argument('--conversa', help='identificador da conversa do Antigravity (pasta em brain/)')
    ap.add_argument('--sessao', help='identificador da sessão (ou do subagente) do Claude Code')
    ap.add_argument('--projetos', help='pasta de projetos do Claude Code (padrão: SC_CLAUDE_PROJETOS ou ~/.claude/projects)')
    ap.add_argument('--desde', help='só o trecho a partir deste instante (ISO 8601; sem fuso, UTC); Claude Code')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        rel = medir(a.app, a.log, a.pasta, a.conversa, a.projetos, a.sessao, a.desde)
    except ErroSessao as e:
        print(f'erro: {e}', file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(rel, ensure_ascii=False, indent=2))
    else:
        imprimir(rel)
    return 0


if __name__ == '__main__':
    sys.exit(main())
