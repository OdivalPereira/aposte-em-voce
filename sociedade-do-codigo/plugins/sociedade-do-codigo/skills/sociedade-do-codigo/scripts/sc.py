#!/usr/bin/env python3
"""Comandos do pipeline da Sociedade do Código, um por estação.

  sc.py ordem    --etapa <ID>                      2. cria sociedade/ordens/<ID>.md a partir do modelo
  sc.py abrir    --etapa <ID> --ordem <arquivo> --base <commit>   3. abre a etapa no registro, a partir da ordem
  sc.py entregar --etapa <ID> --base <commit> [--area <nome>]   3. portão por área sobre base..HEAD e atestado em sociedade/pareceres/
  sc.py conferir --ordem <arquivo> [--registrar]   4. marca cada entrega como feita ou não feita
  sc.py sessao   <antigravity|codex|claude>        4. mede uma sessão pelo log do aplicativo
  sc.py revisar  --etapa <ID> --base <commit>      5. cópia descartável do candidato para o revisor
  sc.py revisar  --etapa <ID> --parecer <arquivo> --head <commit>   5. registra o parecer (lint e commit conferidos)
  sc.py decidir  --etapa <ID> aceitar|corrigir|rejeitar|sem-aceite --por <nome>   6. decisão, métricas e encerramento
  sc.py estado [--artefato <arquivo>]              6. gera sociedade/estado.md, estado.html e, se pedido, o painel

Durante a etapa, os comandos com --etapa (e `conferir`, pelo nome da ordem) leem e gravam a `sociedade/` do worktree da
etapa (`~/.sociedade/trabalho/<projeto>/<etapa>/sociedade`) se ela existir; `--pasta-sociedade` vale antes de tudo.

Cada subcomando mostra a ajuda completa com -h. Os scripts de baixo nível continuam disponíveis.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from sc_registro import localizar_sociedade_canonica, localizar_sociedade_da_etapa  # noqa: E402
import sc_ciclo  # noqa: E402

ID_VALIDO = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')


def _id(etapa):
    if not ID_VALIDO.match(etapa or '') or '..' in etapa:
        raise SystemExit(f'erro: identificador de etapa inválido: "{etapa}" (letras, números, ".", "_", "-").')
    return etapa


def _git(raiz, *args):
    r = subprocess.run(['git', '-C', str(raiz), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f'erro: git {" ".join(args)}: {r.stderr.strip()}')
    return r.stdout.strip()


def cmd_ordem(a):
    soc = _soc(a, _id(a.etapa))
    destino = soc / 'ordens' / f'{_id(a.etapa)}.md'
    if destino.exists():
        raise SystemExit(f'erro: a ordem já existe: {destino}')
    modelo = (AQUI.parent / 'assets' / 'ordem-modelo.md').read_text(encoding='utf-8')
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(modelo.replace('<ID>', a.etapa), encoding='utf-8')
    print(f'ordem criada: {destino}\nPreencha objetivo, leitura, fatias e o bloco de entregas; depois peça a aprovação do usuário.')
    return 0


def cmd_passar(a):
    etapa = _id(a.etapa)
    para = a.para.lower()
    soc = _soc(a, etapa)
    from sc_perfil import carregar_perfil
    perfil = carregar_perfil(soc)
    reg = None
    try:
        from sc_registro import Registro
        reg = Registro(soc)
    except Exception:
        pass

    if para == 'gandalf':
        p_info = perfil.obter_papel('coordenador') or perfil.obter_papel('gandalf') or {}
        ferramenta = p_info.get('plataforma') or 'Antigravity'
        modelo = p_info.get('modelo') or 'Gemini 3.8 Flash'
        esforco = p_info.get('esforco') or 'high'
        if a.pasta_sociedade:
            pasta_wt = Path(a.pasta_sociedade).parent.resolve()
        else:
            pasta_wt = localizar_sociedade_da_etapa(etapa, pasta_base=soc).parent.resolve()
        if not pasta_wt.exists():
            raise SystemExit(f'erro: pasta do worktree da etapa não encontrada: {pasta_wt}')
        linha1 = f"{ferramenta}, {modelo}, esforço {esforco} (conversa nova)"
        linha2 = str(pasta_wt)
        linha3 = f"Para: Gandalf. Execute a ordem sociedade/ordens/{etapa}.md."
    elif para == 'barbarvore':
        p_info = perfil.obter_papel('revisor') or perfil.obter_papel('barbarvore') or {}
        ferramenta = p_info.get('plataforma') or 'Codex'
        modelo = p_info.get('modelo') or 'GPT-6 Sol'
        esforco = p_info.get('esforco') or 'high'
        raiz = soc.parent
        projeto = re.sub(r'[^A-Za-z0-9._-]+', '_', raiz.name)
        pasta_rev = (raiz.parent / f'revisao-{etapa}').resolve()
        if not pasta_rev.exists():
            pasta_rev = (Path.home() / '.sociedade' / 'trabalho' / projeto / f'revisao-{etapa}').resolve()
        if not pasta_rev.exists():
            pasta_alt = (Path.home() / '.sociedade' / 'revisar' / projeto / etapa).resolve()
            if pasta_alt.exists():
                pasta_rev = pasta_alt
        if not pasta_rev.exists():
            raise SystemExit(f'erro: cópia de revisão não encontrada: {pasta_rev}')
        ordem_path = soc / 'ordens' / f'{etapa}.md'
        rev_linha = ''
        if ordem_path.is_file():
            for l in ordem_path.read_text(encoding='utf-8').splitlines():
                l_strip = l.strip()
                if l_strip.lower().startswith(('revisão independente:', 'revisao independente:')):
                    rev_linha = l_strip
                    break
        if not rev_linha:
            rev_linha = f"Revisão independente da etapa {etapa}."
        linha1 = f"{ferramenta}, {modelo}, esforço {esforco} (conversa nova)"
        linha2 = str(pasta_rev)
        linha3 = f"Para: Barbárvore. {rev_linha} Parecer: revisao-saida/parecer.md."
    else:
        raise SystemExit(f'erro: papel de destino inválido: "{para}". Use "gandalf" ou "barbarvore".')

    if reg:
        from sc_registro import agora_iso
        def gerador(dados):
            return [{
                'tipo': 'passagem',
                'dados': {
                    'etapa': etapa,
                    'para': para,
                    'papel': 'coordenador' if para == 'gandalf' else 'revisor',
                    'ferramenta': ferramenta,
                    'modelo': modelo,
                    'esforco': esforco,
                    'pasta': linha2,
                    'linha': linha3,
                    'data_hora': agora_iso(),
                }
            }]
        reg.aplicar_mutacao(gerador, autor='Círdan', aplicar=True)

    print(linha1)
    print(linha2)
    print(linha3)
    return 0


def cmd_entregar(a):
    import sc_pre_devolucao
    if a.comando_teste is not None:
        print('erro: --comando-teste é recusado. O comando e o timeout dos testes vêm só da seção "Portão por área" do '
              'perfil (sociedade/perfil.md); use --area <nome> para rodar uma área só.', file=sys.stderr)
        return 2
    etapa = _id(a.etapa)
    soc = Path(a.pasta_sociedade) if a.pasta_sociedade else localizar_sociedade_da_etapa(etapa, Path(a.pasta_projeto))
    nome = f'atestado-{etapa}' + (f'-{_id(a.fatia)}' if a.fatia else '') + '.json'
    saida = soc / 'pareceres' / nome
    argv = ['--etapa', a.etapa, '--pasta-projeto', a.pasta_projeto, '--base', a.base,
            '--papel', a.papel, '--saida-json', str(saida), '--pasta-sociedade', str(soc), '--portao-por-area']
    if a.fatia:
        argv += ['--fatia', a.fatia]
    if a.area:
        argv += ['--area', a.area]
    rc = sc_pre_devolucao.main(argv)
    print(f'\natestado: {saida}')
    return rc


def cmd_conferir(a):
    import sc_conferir
    soc = a.pasta_sociedade
    if not soc and a.registrar:  # B11a: a ordem é <etapa>.md; o registro é o da sociedade/ da etapa
        soc = str(localizar_sociedade_da_etapa(Path(a.ordem).stem))
    argv = ['--ordem', a.ordem] + (['--registrar'] if a.registrar else []) + (['--raiz', a.raiz] if a.raiz else []) \
        + (['--pasta-sociedade', soc] if soc else []) + (['--json'] if a.json else [])
    return sc_conferir.main(argv)


def _executar(funcao, *args, **kw):
    """Roda uma função de sc_ciclo: imprime as linhas que ela devolve; a recusa vira `erro:` e saída 1."""
    try:
        for linha in funcao(*args, **kw):
            print(linha)
    except (sc_ciclo.ErroCiclo, sc_ciclo.ErroRegistro, sc_ciclo.ErroSessao) as e:
        print(f'erro: {e}', file=sys.stderr)
        return 1
    return 0


def _soc(a, etapa=None):
    """B11a: `--pasta-sociedade`; senão a `sociedade/` do worktree da etapa, se existir; senão a canônica."""
    if a.pasta_sociedade:
        return Path(a.pasta_sociedade)
    return localizar_sociedade_da_etapa(etapa) if etapa else localizar_sociedade_canonica()


def cmd_abrir(a):
    return _executar(sc_ciclo.abrir, _soc(a, a.etapa), a.etapa, a.ordem, a.base, a.bastao)


def cmd_decidir(a):
    return _executar(sc_ciclo.decidir, _soc(a, _id(a.etapa)), _id(a.etapa), a.acao, a.por, a.head, a.motivo, a.minutos, a.intervencoes,
                     a.escaparam, a.log, a.sessao, a.projetos, desde=a.desde)


def cmd_sessao(a):
    import sc_sessao
    argv = [a.app] + (['--log', a.log] if a.log else []) + (['--pasta', a.pasta] if a.pasta else []) \
        + (['--conversa', a.conversa] if a.conversa else []) + (['--sessao', a.sessao] if a.sessao else []) \
        + (['--projetos', a.projetos] if a.projetos else []) + (['--desde', a.desde] if a.desde else []) + (['--json'] if a.json else [])
    return sc_sessao.main(argv)


def cmd_estado(a):
    import sc_resumo
    soc = a.pasta_sociedade or str(localizar_sociedade_da_etapa(a.etapa))  # B11a: worktree da etapa, se existir
    argv = ['--pasta-sociedade', soc] \
        + (['--sem-html'] if a.sem_html else []) + (['--imprimir'] if a.imprimir else []) \
        + (['--artefato', a.artefato] if a.artefato else [])
    return sc_resumo.main(argv)


def cmd_revisar(a):
    """Prepara a cópia descartável para o revisor; com --parecer, registra o parecer pronto no registro."""
    etapa = _id(a.etapa)
    soc = _soc(a, etapa)  # B11a e B17b: a sociedade/ do worktree da etapa, com ou sem --parecer
    raiz = soc.parent
    if a.parecer:
        return _executar(sc_ciclo.registrar_parecer, soc, etapa, a.parecer, a.head, a.implementador or None)
    if not a.base:
        raise SystemExit('erro: informe --base (preparar a cópia) ou --parecer (registrar o parecer).')
    base = _git(raiz, 'rev-parse', '--verify', f'{a.base}^{{commit}}')
    head = _git(raiz, 'rev-parse', '--verify', f'{a.head}^{{commit}}')
    projeto = re.sub(r'[^A-Za-z0-9._-]+', '_', raiz.name)
    destino = Path(a.destino) if a.destino else Path.home() / '.sociedade' / 'trabalho' / projeto / f'revisao-{etapa}'
    if destino.exists():
        raise SystemExit(f'erro: {destino} já existe. Apague a cópia anterior ou use --destino.')
    destino.mkdir(parents=True)
    _git(destino, 'init', '-q')
    for ref, msg in ((base, f'base ({base[:7]})'), (head, f'candidato ({head[:7]})')):
        for item in destino.iterdir():
            if item.name != '.git':
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        arquivo = subprocess.run(['git', '-C', str(raiz), 'archive', ref], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(destino)], input=arquivo, check=True)
        _git(destino, 'add', '-A')
        _git(destino, '-c', 'user.name=revisao', '-c', 'user.email=revisao@localhost', '-c', 'commit.gpgsign=false',
             '-c', 'core.hooksPath=/dev/null', 'commit', '-q', '--allow-empty', '-m', msg)
    skills = AQUI.parent.parent
    (destino / 'revisao-saida').mkdir()
    for rel in (f'ordens/{etapa}.md', *(p.relative_to(soc).as_posix() for p in sorted((soc / 'pareceres').glob(f'atestado-{etapa}*.json'))),
                'perfil.md'):  # B17b: o que o revisor lê e ainda não está nos commits (o atestado nasce depois do código)
        if (soc / rel).is_file() and not (destino / 'sociedade' / rel).exists():
            (destino / 'sociedade' / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(soc / rel, destino / 'sociedade' / rel)
    shutil.copy(skills / 'sc-revisao' / 'references' / 'protocolo-revisao.md', destino / 'PROTOCOLO-REVISAO.md')
    shutil.copy(skills / 'sc-revisao' / 'assets' / 'parecer-modelo.md', destino / 'revisao-saida' / 'parecer-modelo.md')
    (destino / 'ORDEM-REVISAO.md').write_text(f'''# Ordem de revisão independente — etapa {etapa}

Você é o revisor independente, de fornecedor diferente de todos os implementadores. Não implemente nem corrija nada.

- Cópia: esta pasta. Base: commit "base ({base[:7]})". Candidato: "candidato ({head[:7]})", que é o HEAD.
- Alterações: git diff HEAD~1 HEAD
- Critérios: o plano e a ordem da etapa {etapa}, dentro desta cópia (sociedade/ordens/{etapa}.md; o atestado e o perfil também estão em sociedade/).
- Método: PROTOCOLO-REVISAO.md desta pasta (passo 0, oito lentes, matriz de cobertura).

Regras: não altere nada fora de revisao-saida/; sondas só em revisao-saida/ ou no diretório temporário;
não use rede nem leia outras pastas; distinga executado de lido; falha de ambiente não é defeito.

Parecer: revisao-saida/parecer.md, pelo modelo revisao-saida/parecer-modelo.md. Ao terminar, informe o SHA-256
(sha256sum revisao-saida/parecer.md).
''', encoding='utf-8')
    with open(destino / '.git' / 'info' / 'exclude', 'a', encoding='utf-8') as f:
        f.write('ORDEM-REVISAO.md\nPROTOCOLO-REVISAO.md\nrevisao-saida/\nsociedade/\n')
    print(f'''Cópia para revisão pronta: {destino}
Commits: base {base[:7]}, candidato {head[:7]}

1. No aplicativo do revisor, desligue as memórias e abra uma CONVERSA NOVA com esta pasta como projeto.
2. Envie: Confirme com pwd que está em {destino}. Não consulte memórias nem leia fora desta pasta. Leia ORDEM-REVISAO.md e execute a revisão.
3. Depois, confira a sessão: sc.py sessao codex --pasta {destino}''')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('ordem', help='cria a ordem de uma etapa a partir do modelo')
    p.add_argument('--etapa', required=True)
    p.add_argument('--pasta-sociedade')
    p.set_defaults(func=cmd_ordem)

    p = sub.add_parser('passar', help='passagem entre ferramentas (Q175)')
    p.add_argument('--etapa', required=True)
    p.add_argument('--para', required=True, choices=['gandalf', 'barbarvore'], help='papel de destino')
    p.add_argument('--pasta-sociedade')
    p.set_defaults(func=cmd_passar)

    p = sub.add_parser('abrir', help='abre a etapa no registro a partir da ordem aprovada')
    p.add_argument('--etapa', required=True, help='ID novo: minúsculas, números e "-" (até 40)')
    p.add_argument('--ordem', required=True, help='arquivo da ordem aprovada')
    p.add_argument('--base', required=True, help='commit de partida da etapa')
    p.add_argument('--bastao', default='Coordenador')
    p.add_argument('--pasta-sociedade')
    p.set_defaults(func=cmd_abrir)

    p = sub.add_parser('entregar', help='portão sobre base..HEAD e atestado')
    p.add_argument('--etapa', required=True)
    p.add_argument('--base', required=True, help='commit de partida (da fatia ou da etapa)')
    p.add_argument('--fatia')
    p.add_argument('--pasta-projeto', default='.', help='pasta onde os testes rodam')
    p.add_argument('--area', help='roda só esta área do "Portão por área" (padrão: as que base..HEAD toca)')
    p.add_argument('--comando-teste', help=argparse.SUPPRESS)  # recusado: o comando vem só do perfil (B11)
    p.add_argument('--papel', default='Coordenador')
    p.add_argument('--pasta-sociedade')
    p.set_defaults(func=cmd_entregar)

    p = sub.add_parser('conferir', help='confere a lista de entregas de uma ordem')
    p.add_argument('--ordem', required=True)
    p.add_argument('--registrar', action='store_true')
    p.add_argument('--raiz')
    p.add_argument('--pasta-sociedade', help='pasta do registro (padrão: sociedade/ do worktree da etapa, se existir)')
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_conferir)

    p = sub.add_parser('sessao', help='mede uma sessão pelo log do aplicativo')
    p.add_argument('app', choices=('antigravity', 'codex', 'claude'))
    p.add_argument('--log')
    p.add_argument('--pasta')
    p.add_argument('--conversa')
    p.add_argument('--sessao', help='identificador da sessão (ou do subagente) do Claude Code')
    p.add_argument('--projetos', help='pasta de projetos do Claude Code')
    p.add_argument('--desde', help='mede só o trecho a partir deste instante (ISO 8601; sem fuso, UTC)')
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_sessao)

    p = sub.add_parser('revisar', help='prepara a cópia para o revisor; com --parecer, registra o parecer')
    p.add_argument('--etapa', required=True)
    p.add_argument('--base', help='sem --parecer: commit de partida da cópia descartável')
    p.add_argument('--head', default='HEAD', help='SHA revisado (candidato)')
    p.add_argument('--destino')
    p.add_argument('--parecer', help='arquivo do parecer pronto: lint, commit igual ao head e registro')
    p.add_argument('--implementador', action='append', help='Nome[:Fornecedor]; padrão: o responsável da etapa')
    p.add_argument('--pasta-sociedade')
    p.set_defaults(func=cmd_revisar)

    p = sub.add_parser('decidir', help='decisão de Odival: aceitar, corrigir, rejeitar ou sem-aceite')
    p.add_argument('--etapa', required=True)
    p.add_argument('acao', choices=sc_ciclo.ACOES)
    p.add_argument('--por', help='quem decide (padrão: git config user.name; sem nenhum dos dois, recusa)')
    p.add_argument('--head', help='head do PR (padrão: ramo etapa/<ID>, senão HEAD)')
    p.add_argument('--motivo')
    p.add_argument('--minutos', type=int, help='minutos de Odival (opcional; sem ele a métrica é n/d)')
    p.add_argument('--intervencoes', type=int, help='intervenções de Odival (opcional)')
    p.add_argument('--escaparam', type=int, help='achados que escaparam ao aceite (opcional)')
    p.add_argument('--log', action='append', default=[], help='log de sessão para as métricas (repetível)')
    p.add_argument('--sessao', action='append', default=[], help='sessão do Claude Code para as métricas (repetível)')
    p.add_argument('--projetos', help='pasta de projetos do Claude Code')
    p.add_argument('--desde', help='consumo só do trecho a partir deste instante (ISO 8601; sem fuso, UTC)')
    p.add_argument('--pasta-sociedade')
    p.set_defaults(func=cmd_decidir)

    p = sub.add_parser('estado', help='gera sociedade/estado.md e estado.html')
    p.add_argument('--etapa', help='etapa cujo worktree tem a sociedade/ (padrão: o worktree em que a pasta atual está)')
    p.add_argument('--pasta-sociedade')
    p.add_argument('--sem-html', action='store_true')
    p.add_argument('--imprimir', action='store_true')
    p.add_argument('--artefato', help='grava também o painel em fragmento HTML, pronto para publicar como página')
    p.set_defaults(func=cmd_estado)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == '__main__':
    sys.exit(main())
