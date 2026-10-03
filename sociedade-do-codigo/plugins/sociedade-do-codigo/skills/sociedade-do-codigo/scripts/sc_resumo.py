#!/usr/bin/env python3
"""Resumo de estado de uma tela (Q119, Q99): `sociedade/estado.md` e `sociedade/estado.html`.

Junta, sem interpretar: papéis do perfil, etapas do registro.json (critérios, achados abertos,
pareceres), a última conferência de cada ordem, os atestados do portão e o Git (ramo, commits
recentes, worktrees). Separa o que foi declarado do que foi verificado. Só leitura: grava
apenas os dois arquivos de saída. O HTML é autocontido e serve de painel para o celular.

Uso:
  sc_resumo.py [--pasta-sociedade <pasta>] [--saida <pasta>] [--sem-html] [--imprimir]
"""
import argparse
import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sc_registro import localizar_sociedade_canonica, derivar_estado  # noqa: E402

LIMITE_MD = 5 * 1024  # Q99: andamento e estado com até 5 KB


def git(raiz, *args):
    r = subprocess.run(['git', '-C', str(raiz), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ''


def coletar(pasta_soc):
    pasta_soc = Path(pasta_soc).resolve()
    raiz = pasta_soc.parent
    dados = {'projeto': raiz.name, 'gerado_em': datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC'),
             'papeis': [], 'etapas': [], 'conferencias': [], 'atestados': [], 'commits': [], 'worktrees': [],
             'ramo': git(raiz, 'rev-parse', '--abbrev-ref', 'HEAD'), 'head': git(raiz, 'rev-parse', '--short', 'HEAD'),
             'avisos': [], 'emulacao': False}
    # perfil
    try:
        from sc_perfil import carregar_perfil
        perfil = carregar_perfil(pasta_soc / 'perfil.md')
        dados['papeis'] = [{k: p.get(k, '') for k in ('papel', 'nome', 'plataforma', 'fornecedor', 'modelo', 'estado')}
                           for p in perfil.listar_papeis()]
        dados['emulacao'] = perfil.emulacao
    except Exception as e:
        dados['avisos'].append(f'perfil não lido: {e}')
    # registro
    reg_arq = pasta_soc / 'registro.json'
    if reg_arq.is_file():
        try:
            reg = json.loads(reg_arq.read_text(encoding='utf-8'))
            est = derivar_estado(reg)
            for e in (est.get('etapas') or {}).values():
                crit = e.get('criterios', {})
                achados = [a for a in e.get('achados', {}).values() if a.get('estado') in ('aberto', 'contestado')]
                pareceres = e.get('pareceres', [])
                dados['etapas'].append({
                    'id': e['id'], 'estado': e.get('estado'), 'objetivo': e.get('objetivo', ''),
                    'responsavel': e.get('responsavel', ''),
                    'criterios': f"{sum(1 for c in crit.values() if c.get('atendido'))}/{len(crit)}",
                    'achados_abertos': {s: sum(1 for a in achados if a.get('severidade') == s)
                                        for s in ('bloqueador', 'relevante', 'opcional')},
                    'parecer': (pareceres[-1].get('veredito') if pareceres else None),
                    'revisor': (pareceres[-1].get('revisor') if pareceres else None),
                    'exige_revisao': e.get('exigir_revisao', True),
                    'aceite_em_emulacao': bool(e.get('aceite_em_emulacao')),
                    'independencia': e.get('independencia'),
                })
            ultimas = {}
            for ev in reg.get('eventos', []):
                if ev.get('tipo') == 'conferencia_registrada':
                    d = ev.get('dados', {})
                    ultimas[d.get('etapa')] = {**d, 'quando': ev.get('timestamp', '')}
            dados['conferencias'] = list(ultimas.values())
        except Exception as e:
            dados['avisos'].append(f'registro.json não lido: {e}')
    else:
        dados['avisos'].append('sem registro.json: nenhuma etapa registrada pelo pacote')
    # atestados
    for arq in sorted((pasta_soc / 'pareceres').glob('atestado*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:6]:
        try:
            at = json.loads(arq.read_text(encoding='utf-8'))
        except ValueError:
            continue
        dados['atestados'].append({'arquivo': arq.name, 'status': at.get('status'), 'etapa': at.get('etapa_id'),
                                   'commit': (at.get('commit') or '')[:10], 'arquivos': at.get('total_arquivos_inspecionados'),
                                   'versao': at.get('versao'), 'quando': (at.get('timestamp') or '')[:16]})
    # git
    for linha in git(raiz, 'log', '-8', '--format=%h%x09%ad%x09%s', '--date=format:%d/%m %H:%M').splitlines():
        h, d, s = (linha.split('\t') + ['', ''])[:3]
        dados['commits'].append({'hash': h, 'data': d, 'assunto': s})
    atual = {}
    for linha in git(raiz, 'worktree', 'list', '--porcelain').splitlines() + ['']:
        if not linha.strip():
            if atual.get('worktree') and Path(atual['worktree']).resolve() != raiz.resolve():
                dados['worktrees'].append({'caminho': atual['worktree'].replace(str(Path.home()), '~'),
                                           'ramo': atual.get('branch', '').replace('refs/heads/', '')})
            atual = {}
            continue
        k, _, v = linha.partition(' ')
        atual[k] = v
    return dados


def rotulo_parecer(e):
    """Parecer da etapa; o aceite em emulação (B02) é marcado e nunca conta como independente."""
    if not e.get('parecer'):
        return None
    return f"{e['parecer']} (aceite em emulação; independência: não)" if e.get('aceite_em_emulacao') else e['parecer']


def pendencias(d):
    """O que precisa de atenção, derivado dos dados (sem opinião)."""
    itens = []
    for e in d['etapas']:
        if e['estado'] == 'aberta':
            itens.append(f"Etapa {e['id']} aberta (responsável: {e['responsavel']}); critérios {e['criterios']}.")
        if e['achados_abertos']['bloqueador']:
            itens.append(f"Etapa {e['id']}: {e['achados_abertos']['bloqueador']} bloqueador(es) aberto(s).")
        if e['exige_revisao'] and not e['parecer'] and e['estado'] != 'encerrada':
            itens.append(f"Etapa {e['id']}: aguardando revisão independente.")
    if d.get('emulacao'):
        itens.append('Modo emulação ligado: R1–R3 valem como aviso; nenhum aceite conta como revisão independente.')
    for e in d['etapas']:
        if e.get('aceite_em_emulacao'):
            itens.append(f"Etapa {e['id']}: aceite em emulação (independência: não).")
    for c in d['conferencias']:
        if c.get('feitos') != c.get('total'):
            itens.append(f"Ordem {c.get('etapa')}: {c.get('total', 0) - c.get('feitos', 0)} entrega(s) não feita(s) na última conferência.")
    for a in d['atestados'][:1]:
        if a['status'] != 'APROVADO':
            itens.append(f"Último atestado ({a['arquivo']}) {a['status']}.")
    return itens or ['Nada pendente registrado.']


def gerar_md(d):
    L = [f"# Estado — {d['projeto']}", '',
         f"Gerado por `sc.py estado` em {d['gerado_em']}. Ramo `{d['ramo']}` em `{d['head']}`. Não edite à mão.", '',
         '## Precisa de atenção']
    L += [f'- {p}' for p in pendencias(d)]
    if d['papeis']:
        L += ['', '## Papéis', '| Papel | Nome | Ocupante | Estado |', '|---|---|---|---|']
        L += [f"| {p['papel']} | {p['nome']} | {p['modelo']} ({p['fornecedor']}) | {p['estado']} |" for p in d['papeis']]
    if d['etapas']:
        L += ['', '## Etapas', '| Etapa | Estado | Critérios | Achados abertos (B/R/O) | Parecer |', '|---|---|---|---|---|']
        for e in d['etapas']:
            a = e['achados_abertos']
            L.append(f"| {e['id']} | {e['estado']} | {e['criterios']} | {a['bloqueador']}/{a['relevante']}/{a['opcional']} | {rotulo_parecer(e) or '—'} |")
    if d['conferencias']:
        L += ['', '## Conferências (verificado por script)']
        for c in d['conferencias']:
            L.append(f"- {c.get('etapa')}: {c.get('feitos')} de {c.get('total')} entregas feitas ({c.get('quando', '')[:16]})")
            L += [f"  - {i['id']} {i['tipo']}: {i['estado']}" for i in c.get('itens', []) if i['estado'] != 'feito']
    if d['atestados']:
        L += ['', '## Atestados do portão']
        L += [f"- {a['arquivo']}: {a['status']}, {a['arquivos']} arquivos, commit {a['commit'] or '—'}" for a in d['atestados'][:4]]
    if d['worktrees']:
        L += ['', '## Trabalho em andamento'] + [f"- `{w['ramo']}` em `{w['caminho']}`" for w in d['worktrees']]
    L += ['', '## Commits recentes'] + [f"- `{c['hash']}` {c['data']} {c['assunto'][:70]}" for c in d['commits'][:6]]
    if d['avisos']:
        L += ['', '## Avisos'] + [f'- {a}' for a in d['avisos']]
    texto = '\n'.join(L) + '\n'
    if len(texto.encode('utf-8')) > LIMITE_MD:
        texto = texto.encode('utf-8')[:LIMITE_MD - 60].decode('utf-8', 'ignore') + '\n\n*(resumo cortado no limite de 5 KB)*\n'
    return texto


def gerar_html(d, fragmento=False):
    """HTML autocontido; com fragmento=True, sem html/head/body (para publicar como página privada)."""
    esc = html.escape
    pend = pendencias(d)
    alerta = pend != ['Nada pendente registrado.']
    def chip(estado):
        classe = {'feito': 'ok', 'APROVADO': 'ok', 'encerrada': 'ok', 'aceitar': 'ok', 'ativo': 'ok',
                  'não feito': 'mau', 'REPROVADO': 'mau', 'nao_aceitar': 'mau',
                  'aberta': 'meio', 'espera': 'meio', 'aceite em emulação': 'meio', 'reserva': 'neutro'}.get(str(estado), 'neutro')
        return f'<span class="chip {classe}">{esc(str(estado or "—"))}</span>'
    partes = [f'<header><p class="rot">Sociedade do Código · estado</p><h1>{esc(d["projeto"])}</h1>'
              f'<p class="meta">Ramo <code>{esc(d["ramo"])}</code> em <code>{esc(d["head"])}</code> · gerado em {esc(d["gerado_em"])}</p></header>']
    partes.append(f'<section class="cartao {"alerta" if alerta else "calmo"}"><h2>Precisa de atenção</h2><ul>'
                  + ''.join(f'<li>{esc(p)}</li>' for p in pend) + '</ul></section>')
    if d['conferencias']:
        blocos = []
        for c in d['conferencias']:
            itens = ''.join(f'<li>{chip(i["estado"])} <b>{esc(i["id"])}</b> {esc(i["tipo"])} <small>{esc(str(i.get("detalhe", "")))}</small></li>' for i in c.get('itens', []))
            blocos.append(f'<div class="bloco"><h3>{esc(str(c.get("etapa")))} <small>{c.get("feitos")} de {c.get("total")} feitas</small></h3><ul class="lista">{itens}</ul></div>')
        partes.append('<section><h2>Entregas conferidas por script</h2>' + ''.join(blocos) + '</section>')
    if d['etapas']:
        linhas = ''.join(f'<tr><td><b>{esc(e["id"])}</b><br><small>{esc(e["objetivo"][:80])}</small></td><td>{chip(e["estado"])}</td>'
                         f'<td class="num">{esc(e["criterios"])}</td><td class="num">{e["achados_abertos"]["bloqueador"]}/{e["achados_abertos"]["relevante"]}/{e["achados_abertos"]["opcional"]}</td>'
                         f'<td>{chip(e["parecer"]) if e["parecer"] else "—"}'
                         f'{"<br>" + chip("aceite em emulação") + "<small>independência: não</small>" if e.get("aceite_em_emulacao") else ""}</td></tr>'
                         for e in d['etapas'])
        partes.append('<section><h2>Etapas</h2><div class="rolagem"><table><thead><tr><th>Etapa</th><th>Estado</th><th>Critérios</th><th>Achados B/R/O</th><th>Parecer</th></tr></thead>'
                      f'<tbody>{linhas}</tbody></table></div></section>')
    if d['papeis']:
        linhas = ''.join(f'<li><b>{esc(p["nome"])}</b> · {esc(p["papel"])} <small>{esc(p["modelo"])} ({esc(p["fornecedor"])})</small> {chip(p["estado"])}</li>' for p in d['papeis'])
        partes.append(f'<section><h2>Papéis</h2><ul class="lista">{linhas}</ul></section>')
    if d['atestados']:
        linhas = ''.join(f'<li>{chip(a["status"])} {esc(a["arquivo"])} <small>{a["arquivos"]} arquivos · commit {esc(a["commit"] or "—")}</small></li>' for a in d['atestados'][:4])
        partes.append(f'<section><h2>Atestados do portão</h2><ul class="lista">{linhas}</ul></section>')
    if d['worktrees']:
        partes.append('<section><h2>Trabalho em andamento</h2><ul class="lista">' + ''.join(
            f'<li><code>{esc(w["ramo"])}</code> <small>{esc(w["caminho"])}</small></li>' for w in d['worktrees']) + '</ul></section>')
    partes.append('<section><h2>Commits recentes</h2><ul class="lista">' + ''.join(
        f'<li><code>{esc(c["hash"])}</code> <small>{esc(c["data"])}</small> {esc(c["assunto"][:80])}</li>' for c in d['commits'][:6]) + '</ul></section>')
    corpo = '\n'.join(partes)
    estilo = f'''<style>
:root{{--chao:#F4F6F1;--sup:#fff;--tinta:#1B2631;--apag:#5E6A70;--linha:#D5DCD3;--ok:#2E7D4F;--oks:#DCEEE2;--mau:#B23A2E;--maus:#F6DEDA;--meio:#B26F16;--meios:#F5E7D0;--neu:#E6EAE6}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--chao:#11171A;--sup:#182024;--tinta:#E3E9E4;--apag:#9AA6A3;--linha:#2B373C;--ok:#6CC592;--oks:#193326;--mau:#EE7A6C;--maus:#3B1F1C;--meio:#E3A54E;--meios:#3A2B16;--neu:#242E31}}}}
:root[data-theme="dark"]{{color-scheme:dark;--chao:#11171A;--sup:#182024;--tinta:#E3E9E4;--apag:#9AA6A3;--linha:#2B373C;--ok:#6CC592;--oks:#193326;--mau:#EE7A6C;--maus:#3B1F1C;--meio:#E3A54E;--meios:#3A2B16;--neu:#242E31}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--chao);color:var(--tinta);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:760px;margin:0 auto;padding:24px 16px 48px;display:flex;flex-direction:column;gap:22px}}
h1{{margin:4px 0;font-size:1.7rem}}h2{{font-size:1.05rem;margin:0 0 8px}}h3{{font-size:.98rem;margin:6px 0}}.rot{{margin:0;font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:var(--apag)}}
.meta,small{{color:var(--apag)}}code{{font-family:ui-monospace,Menlo,monospace;font-size:.88em}}
.cartao{{border-radius:10px;padding:14px 16px;background:var(--sup);border:1px solid var(--linha)}}.cartao.alerta{{border-left:5px solid var(--meio)}}.cartao.calmo{{border-left:5px solid var(--ok)}}
.cartao ul,.lista{{margin:0;padding-left:0;list-style:none;display:flex;flex-direction:column;gap:6px}}.cartao li{{padding-left:2px}}
.chip{{display:inline-block;font-size:.72rem;font-weight:600;border-radius:999px;padding:1px 9px;margin-right:4px;background:var(--neu)}}
.chip.ok{{background:var(--oks);color:var(--ok)}}.chip.mau{{background:var(--maus);color:var(--mau)}}.chip.meio{{background:var(--meios);color:var(--meio)}}
.rolagem{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:.92rem}}th,td{{text-align:left;padding:8px;border-bottom:1px solid var(--linha);vertical-align:top}}
th{{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--apag)}}.num{{font-variant-numeric:tabular-nums}}
.bloco{{background:var(--sup);border:1px solid var(--linha);border-radius:10px;padding:10px 14px;margin-bottom:10px}}
</style>'''
    if fragmento:
        return f'<title>Estado da Sociedade</title>\n{estilo}\n<main>\n{corpo}\n</main>\n'
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>Estado da Sociedade</title>{estilo}</head><body><main>\n{corpo}\n</main></body></html>\n')



def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pasta-sociedade', help='pasta sociedade/ (padrão: a canônica)')
    ap.add_argument('--saida', help='pasta de saída (padrão: a pasta sociedade/)')
    ap.add_argument('--sem-html', action='store_true')
    ap.add_argument('--imprimir', action='store_true', help='mostra o estado.md no terminal')
    ap.add_argument('--artefato', help='grava também um fragmento HTML (sem html/head/body) para publicar como página')
    a = ap.parse_args(argv)
    pasta = Path(a.pasta_sociedade) if a.pasta_sociedade else localizar_sociedade_canonica()
    if not pasta.is_dir():
        print(f'erro: pasta sociedade/ não encontrada: {pasta}', file=sys.stderr)
        return 1
    d = coletar(pasta)
    saida = Path(a.saida) if a.saida else pasta
    saida.mkdir(parents=True, exist_ok=True)
    md = gerar_md(d)
    (saida / 'estado.md').write_text(md, encoding='utf-8')
    if a.artefato:
        Path(a.artefato).write_text(gerar_html(d, fragmento=True), encoding='utf-8')
    if not a.sem_html:
        (saida / 'estado.html').write_text(gerar_html(d), encoding='utf-8')
    print(md if a.imprimir else f'estado gerado em {saida}/estado.md' + ('' if a.sem_html else ' e estado.html'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
