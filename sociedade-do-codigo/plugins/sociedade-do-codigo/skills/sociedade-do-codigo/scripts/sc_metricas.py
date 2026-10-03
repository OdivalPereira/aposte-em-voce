#!/usr/bin/env python3
"""Métricas por etapa e linha de sociedade/evolucao.md (Q153, B10).

Mede pelo registro (revisões, bloqueadores, trocas de papel, avisos de cota) e pelo log da
sessão do Claude Code (comandos do método, erros, edições manuais em arquivos de controle).
O que o script não consegue medir, Odival informa por parâmetro: intervenções, minutos dele e
os achados que escaparam ao aceite. Parâmetro ausente vira "n/d", nunca estimativa. Não mede
nem converte nada em tokens, custo ou cota.

Uso:
  sc_metricas.py --etapa <ID> [--pasta-sociedade <pasta>] [--log <sessao.jsonl>]... [--sessao <id>]
                 [--intervencoes N] [--minutos N] [--escaparam N] [--versao-metodo V]
Imprime a linha da tabela; com --gravar, acrescenta-a a sociedade/evolucao.md.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sc_registro import ErroRegistro, Registro, localizar_sociedade_canonica  # noqa: E402
from sc_sessao import ErroSessao, ler_jsonl_estrito, localizar_claude, subagentes_claude  # noqa: E402

COLUNAS = ('Etapa', 'Versão do método', 'Revisões até o aceite', 'Bloqueadores achados', 'Escaparam ao aceite',
           'Trocas de papel', 'Eventos de cota', 'Comandos', 'Erros', 'Edições manuais', 'Intervenções',
           'Minutos de Odival', 'Dentro da meta?')
METAS = {'Comandos': 12, 'Edições manuais': 0, 'Intervenções': 5, 'Minutos de Odival': 30}  # regras.md §6.2
ND = 'n/d'

# Arquivos de controle: só scripts do método os gravam (regras.md §7). Escrita à mão conta como edição manual.
CONTROLE = re.compile(r'(?:^|/)sociedade/(?:registro\.json|estado\.md|rodada\.md|historico\.md|evolucao\.md'
                      r'|pareceres/atestado-[^/\s]+\.json)$')
COMANDO_METODO = re.compile(r'(?:^|[\s;&|(])(?:python3?\s+(?:-\w+\s+)*)?(?:\S*/)?sc\.py\s+([a-z][a-z-]*)')
_CTRL = (r'[^\s\'"<>|;&]*sociedade/(?:registro\.json|estado\.md|rodada\.md|historico\.md|evolucao\.md'
         r'|pareceres/atestado-[^/\s\'"]+\.json)')
# Escrita por terminal no arquivo de controle: redirecionamento, tee, sed -i, ou mv/cp com ele como destino.
ESCRITA_CONTROLE = re.compile(r'(?:>>?\s*|\btee\s+(?:-\w+\s+)*|\bsed\s+(?:-\w+\s+)*-\w*i\w*\s[^|;&]*?'
                              r'|\b(?:mv|cp)\s+[^|;&]*?\s)(' + _CTRL + r')(?=\s*(?:$|[|;&)]))')
ERRO_BASH = re.compile(r'^\s*Exit code [1-9]')


def eh_arquivo_de_controle(caminho):
    return bool(CONTROLE.search(str(caminho).replace('\\', '/')))


def medir_log(linhas):
    """Comandos do método (`sc.py <comando>`), erros e edições manuais num log já lido (lista de dicts)."""
    pendentes, comandos, erros, edicoes = {}, [], [], []
    for o in linhas:
        conteudo = (o.get('message') or {}).get('content')
        if not isinstance(conteudo, list):
            continue
        for b in conteudo:
            if not isinstance(b, dict):
                continue
            if o.get('type') == 'assistant' and b.get('type') == 'tool_use':
                nome, entrada = b.get('name'), b.get('input') or {}
                if nome == 'Bash':
                    cmd = str(entrada.get('command', ''))
                    achados = COMANDO_METODO.findall(cmd)
                    for sub in achados:
                        comandos.append(sub)
                        pendentes.setdefault(b.get('id'), []).append(sub)
                    for alvo in ESCRITA_CONTROLE.findall(cmd):
                        edicoes.append(f'Bash: {alvo}')
                elif nome in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit') and \
                        eh_arquivo_de_controle(entrada.get('file_path') or entrada.get('notebook_path') or ''):
                    edicoes.append(f'{nome}: {entrada.get("file_path") or entrada.get("notebook_path")}')
            elif o.get('type') == 'user' and b.get('type') == 'tool_result' and b.get('tool_use_id') in pendentes:
                texto = b.get('content')
                if isinstance(texto, list):
                    texto = ' '.join(x.get('text', '') for x in texto if isinstance(x, dict))
                if b.get('is_error') or ERRO_BASH.match(str(texto or '')):
                    erros.extend(pendentes[b['tool_use_id']])
    return {'comandos': comandos, 'erros': erros, 'edicoes_manuais': edicoes}


def medir_logs(logs, incluir_subagentes=True):
    """Soma `medir_log` sobre os logs informados (e os subagentes de cada sessão). Log ausente ou ilegível: ErroSessao."""
    total = {'comandos': [], 'erros': [], 'edicoes_manuais': []}
    visto = set()
    for log in logs:
        alvo = [Path(log), *(subagentes_claude(log) if incluir_subagentes else [])]
        for a in alvo:
            if a in visto:
                continue
            visto.add(a)
            for k, v in medir_log(ler_jsonl_estrito(a)).items():
                total[k].extend(v)
    return total


def medir_registro(dados, etapa_id):
    """Contagens do registro para a etapa: revisões, bloqueadores, trocas de papel e avisos de cota."""
    abertura = encerramento = None
    revisoes = bloqueadores = 0
    for ev in dados.get('eventos', []):
        d, tipo = ev.get('dados') or {}, ev.get('tipo')
        if tipo == 'etapa_aberta' and d.get('etapa_id') == etapa_id:
            abertura = ev.get('timestamp')
        elif tipo == 'etapa_encerrada' and d.get('etapa_id') == etapa_id:
            encerramento = ev.get('timestamp')
        elif d.get('etapa_id') != etapa_id:
            continue
        elif tipo == 'parecer_registrado':
            revisoes += 1
        elif tipo == 'achado_registrado' and d.get('severidade') == 'bloqueador':
            bloqueadores += 1
    if abertura is None:
        raise ValueError(f'Etapa "{etapa_id}" não encontrada no registro.')

    def na_janela(ev):
        return ev.get('timestamp', '') >= abertura and (encerramento is None or ev.get('timestamp', '') <= encerramento)
    eventos = dados.get('eventos', [])
    return {
        'revisoes': revisoes,
        'bloqueadores': bloqueadores,
        'trocas_de_papel': sum(1 for e in eventos if e.get('tipo') == 'papel_trocado' and na_janela(e)),
        'eventos_de_cota': sum(1 for e in eventos if e.get('tipo') == 'aviso_cota_registrado' and na_janela(e)),
    }


def dentro_da_meta(valores):
    """'não' se qualquer meta foi estourada; 'n/d' se nada estourou mas falta medida; senão 'sim'."""
    medidos = {k: valores.get(k) for k in METAS if isinstance(valores.get(k), int)}
    if any(medidos[k] > METAS[k] for k in medidos):
        return 'não'
    return ND if len(medidos) < len(METAS) else 'sim'


def versao_do_metodo():
    for pai in Path(__file__).resolve().parents:
        manifesto = pai / 'plugin.json'
        if manifesto.is_file():
            try:
                return str(json.loads(manifesto.read_text(encoding='utf-8')).get('version') or ND)
            except ValueError:
                break
    return ND


def medir_etapa(dados_registro, etapa_id, logs=(), intervencoes=None, minutos_odival=None,
                escaparam_ao_aceite=None, versao_metodo=None, incluir_subagentes=True):
    """Métricas da etapa. `logs`: sessões do Claude Code (caminhos .jsonl); sem logs, comandos, erros e
    edições manuais ficam n/d. Intervenções, minutos e escaparam são parâmetros de Odival (None = n/d)."""
    reg = medir_registro(dados_registro, etapa_id)
    if logs:
        sessao = medir_logs(logs, incluir_subagentes)
        comandos, erros, edicoes = len(sessao['comandos']), len(sessao['erros']), len(sessao['edicoes_manuais'])
    else:
        sessao = {'comandos': [], 'erros': [], 'edicoes_manuais': []}
        comandos = erros = edicoes = None
    valores = {'Etapa': etapa_id, 'Versão do método': versao_metodo or versao_do_metodo(),
               'Revisões até o aceite': reg['revisoes'], 'Bloqueadores achados': reg['bloqueadores'],
               'Escaparam ao aceite': escaparam_ao_aceite, 'Trocas de papel': reg['trocas_de_papel'],
               'Eventos de cota': reg['eventos_de_cota'], 'Comandos': comandos, 'Erros': erros,
               'Edições manuais': edicoes, 'Intervenções': intervencoes, 'Minutos de Odival': minutos_odival}
    valores['Dentro da meta?'] = dentro_da_meta(valores)
    return {'valores': valores, 'detalhe': sessao}


def linha_evolucao(metricas):
    """Linha da tabela de sociedade/evolucao.md, na ordem de COLUNAS."""
    return '| ' + ' | '.join(ND if metricas['valores'][c] is None else str(metricas['valores'][c]) for c in COLUNAS) + ' |'


def acrescentar_linha(evolucao, linha):
    """Acrescenta a linha ao fim da tabela de evolucao.md; a etapa não pode ter duas linhas."""
    caminho = Path(evolucao)
    texto = caminho.read_text(encoding='utf-8')
    etapa = linha.split('|')[1].strip()
    if re.search(rf'^\|\s*{re.escape(etapa)}\s*\|', texto, re.M):
        raise ValueError(f'evolucao.md já tem linha da etapa "{etapa}".')
    caminho.write_text(texto.rstrip('\n') + '\n' + linha + '\n', encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--etapa', required=True)
    ap.add_argument('--pasta-sociedade', help='pasta do registro (padrão: sociedade/ canônica)')
    ap.add_argument('--log', action='append', default=[], help='log da sessão (.jsonl); repetível')
    ap.add_argument('--sessao', action='append', default=[], help='identificador de sessão do Claude Code; repetível')
    ap.add_argument('--projetos', help='pasta de projetos do Claude Code')
    ap.add_argument('--intervencoes', type=int)
    ap.add_argument('--minutos', type=int)
    ap.add_argument('--escaparam', type=int)
    ap.add_argument('--versao-metodo')
    ap.add_argument('--gravar', action='store_true', help='acrescenta a linha a evolucao.md da pasta da sociedade')
    a = ap.parse_args(argv)
    try:
        pasta = Path(a.pasta_sociedade) if a.pasta_sociedade else Path(localizar_sociedade_canonica())
        logs = list(a.log)
        for s in a.sessao:
            tipo, caminho = localizar_claude(s, a.projetos)
            if tipo != 'sessao':
                raise ErroSessao(f'{s} é um subagente; informe a sessão.')
            logs.append(str(caminho))
        m = medir_etapa(Registro(pasta).dados, a.etapa, logs, a.intervencoes, a.minutos, a.escaparam, a.versao_metodo)
        linha = linha_evolucao(m)
        if a.gravar:
            acrescentar_linha(pasta / 'evolucao.md', linha)
    except (ErroSessao, ErroRegistro, ValueError, OSError) as e:
        print(f'erro: {e}', file=sys.stderr)
        return 1
    print(linha)
    return 0


if __name__ == '__main__':
    sys.exit(main())
