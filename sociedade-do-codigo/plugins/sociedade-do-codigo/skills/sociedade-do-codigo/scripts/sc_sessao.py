#!/usr/bin/env python3
"""Medição objetiva de uma sessão de agente pelo log local do aplicativo (Q141, Q126).

Lê o log do Antigravity (transcript.jsonl), do Codex (rollout .jsonl) ou do Claude Code
(sessão .jsonl) e devolve só metadados e contagens: passos, mensagens do usuário, modelo e
esforço, ferramentas usadas, delegações, arquivos mais relidos, execuções de teste e
leituras fora da pasta permitida. Nunca reproduz conteúdo de arquivo nem de mensagem, e
nunca converte nada em tokens, custo ou cota.

Uso:
  sc_sessao.py antigravity [--conversa <id> | --log <transcript.jsonl>] [--json]
  sc_sessao.py codex --pasta <pasta permitida> [--log <rollout.jsonl>] [--json]
  sc_sessao.py claude [--pasta <pasta do projeto>] [--log <sessao.jsonl>] [--json]

Sem --log, usa a sessão mais recente do aplicativo (no Codex, a mais recente que menciona a pasta).
"""
import argparse
import collections
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
AG_BRAIN = HOME / '.gemini' / 'antigravity' / 'brain'
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
    return {
        'aplicativo': 'antigravity',
        'log': str(log),
        'conversa': Path(log).parents[2].name if len(Path(log).parents) > 2 else None,
        'inicio': inicio, 'fim': fim, 'duracao_min': duracao_min(inicio, fim),
        'passos': len(passos),
        'ordens_na_conversa': ordens,
        'conversa_nova': ordens == 1,
        'delegacoes_total': sum(delegacoes_por_ordem),
        'delegacoes_por_ordem': delegacoes_por_ordem,
        'ferramentas': dict(ferramentas.most_common()),
        'execucoes_de_teste': testes,
        'arquivos_relidos': relidos(lidos),
    }


# ------------------------------------------------------------------------ Codex

def log_codex(pasta):
    candidatos = sorted(CODEX_SESSOES.rglob('rollout-*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
    for arq in candidatos:
        texto = arq.read_text(encoding='utf-8', errors='replace')
        if pasta in texto and '"codex-auto-review"' not in texto:
            return arq
    raise ErroSessao('Nenhuma sessão do Codex menciona essa pasta.')


def _texto_mensagem(payload):
    return ' '.join(c.get('text', '') for c in payload.get('content', []) if isinstance(c, dict))


def medir_codex(log, pasta):
    pasta = normalizar(pasta)
    linhas = list(ler_jsonl(log))
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
    }


# ------------------------------------------------------------------ Claude Code

def log_claude(pasta=None):
    if pasta:
        slug = re.sub(r'[^A-Za-z0-9]', '-', str(Path(pasta).resolve()))
        base = CLAUDE_PROJETOS / slug
        candidatos = sorted(base.glob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True) if base.is_dir() else []
    else:
        candidatos = sorted(CLAUDE_PROJETOS.glob('*/*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidatos:
        raise ErroSessao('Nenhuma sessão do Claude Code encontrada.')
    return candidatos[0]


def medir_claude(log, pasta=None):
    pasta_n = normalizar(Path(pasta).resolve()) if pasta else None
    ferramentas, ferramentas_sub, lidos = collections.Counter(), collections.Counter(), collections.Counter()
    modelos, esforcos, fora = collections.Counter(), collections.Counter(), collections.Counter()
    mensagens = passos = delegacoes = testes = 0
    inicio = fim = None
    for o in ler_jsonl(log):
        ts = o.get('timestamp')
        if ts:
            inicio = inicio or ts
            fim = ts
        tipo = o.get('type')
        msg = o.get('message') if isinstance(o.get('message'), dict) else {}
        lateral = bool(o.get('isSidechain'))
        if tipo == 'user' and not lateral and o.get('turnOrigin') == 'human':
            mensagens += 1
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
    return {
        'aplicativo': 'claude',
        'log': str(log),
        'inicio': inicio, 'fim': fim, 'duracao_min': duracao_min(inicio, fim),
        'mensagens_do_usuario': mensagens,
        'passos_do_agente': passos,
        'modelos': dict(modelos.most_common()),
        'esforcos': dict(esforcos.most_common()),
        'delegacoes_por_subagente': delegacoes,
        'ferramentas': dict(ferramentas.most_common()),
        'ferramentas_dos_subagentes': dict(ferramentas_sub.most_common()),
        'execucoes_de_teste': testes,
        'arquivos_relidos': relidos(lidos),
        'caminhos_fora_da_pasta': dict(fora.most_common(10)) if pasta_n else None,
    }


# ------------------------------------------------------------------------ saída

def medir(app, log=None, pasta=None, conversa=None):
    if app == 'antigravity':
        return medir_antigravity(Path(log) if log else log_antigravity(conversa))
    if app == 'codex':
        if not pasta:
            raise ErroSessao('codex exige --pasta (a pasta permitida da sessão).')
        return medir_codex(Path(log) if log else log_codex(normalizar(pasta)), pasta)
    if app == 'claude':
        return medir_claude(Path(log) if log else log_claude(pasta), pasta)
    raise ErroSessao(f'Aplicativo desconhecido: {app}')


def imprimir(rel):
    for chave, valor in rel.items():
        if isinstance(valor, dict):
            print(f'{chave}:')
            for k, v in (valor or {}).items():
                print(f'    {v:>5}  {k}')
            if not valor:
                print('    (nenhum)')
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
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        rel = medir(a.app, a.log, a.pasta, a.conversa)
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
