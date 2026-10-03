#!/usr/bin/env python3
"""Comandos do pipeline da Sociedade do Código, um por estação.

  sc.py ordem    --etapa <ID>                      2. cria sociedade/ordens/<ID>.md a partir do modelo
  sc.py entregar --etapa <ID> --base <commit>      3. portão sobre base..HEAD e atestado em sociedade/pareceres/
  sc.py conferir --ordem <arquivo> [--registrar]   4. marca cada entrega como feita ou não feita
  sc.py sessao   <antigravity|codex|claude>        4. mede uma sessão pelo log do aplicativo
  sc.py revisar  --etapa <ID> --base <commit>      5. cópia descartável do candidato para o revisor
  sc.py estado [--artefato <arquivo>]              6. gera sociedade/estado.md, estado.html e, se pedido, o painel

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
from sc_registro import localizar_sociedade_canonica  # noqa: E402

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
    soc = Path(a.pasta_sociedade) if a.pasta_sociedade else localizar_sociedade_canonica()
    destino = soc / 'ordens' / f'{_id(a.etapa)}.md'
    if destino.exists():
        raise SystemExit(f'erro: a ordem já existe: {destino}')
    modelo = (AQUI.parent / 'assets' / 'ordem-modelo.md').read_text(encoding='utf-8')
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(modelo.replace('<ID>', a.etapa), encoding='utf-8')
    print(f'ordem criada: {destino}\nPreencha objetivo, leitura, fatias e o bloco de entregas; depois peça a aprovação do usuário.')
    return 0


def cmd_entregar(a):
    import sc_pre_devolucao
    soc = Path(a.pasta_sociedade) if a.pasta_sociedade else localizar_sociedade_canonica(Path(a.pasta_projeto))
    nome = f'atestado-{_id(a.etapa)}' + (f'-{_id(a.fatia)}' if a.fatia else '') + '.json'
    saida = soc / 'pareceres' / nome
    argv = ['--etapa', a.etapa, '--pasta-projeto', a.pasta_projeto, '--base', a.base,
            '--papel', a.papel, '--saida-json', str(saida), '--pasta-sociedade', str(soc)]
    if a.fatia:
        argv += ['--fatia', a.fatia]
    if a.comando_teste:
        argv += ['--comando-teste', a.comando_teste]
    rc = sc_pre_devolucao.main(argv)
    print(f'\natestado: {saida}')
    return rc


def cmd_conferir(a):
    import sc_conferir
    argv = ['--ordem', a.ordem] + (['--registrar'] if a.registrar else []) + (['--raiz', a.raiz] if a.raiz else []) \
        + (['--json'] if a.json else [])
    return sc_conferir.main(argv)


def cmd_sessao(a):
    import sc_sessao
    argv = [a.app] + (['--log', a.log] if a.log else []) + (['--pasta', a.pasta] if a.pasta else []) \
        + (['--conversa', a.conversa] if a.conversa else []) + (['--json'] if a.json else [])
    return sc_sessao.main(argv)


def cmd_estado(a):
    import sc_resumo
    argv = (['--pasta-sociedade', a.pasta_sociedade] if a.pasta_sociedade else []) \
        + (['--sem-html'] if a.sem_html else []) + (['--imprimir'] if a.imprimir else []) \
        + (['--artefato', a.artefato] if a.artefato else [])
    return sc_resumo.main(argv)


def cmd_revisar(a):
    """Prepara uma cópia descartável com dois commits (base e candidato) para o revisor independente."""
    soc = Path(a.pasta_sociedade) if a.pasta_sociedade else localizar_sociedade_canonica()
    raiz = soc.parent
    etapa = _id(a.etapa)
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
    shutil.copy(skills / 'sc-revisao' / 'references' / 'protocolo-revisao.md', destino / 'PROTOCOLO-REVISAO.md')
    shutil.copy(skills / 'sc-revisao' / 'assets' / 'parecer-modelo.md', destino / 'revisao-saida' / 'parecer-modelo.md')
    (destino / 'ORDEM-REVISAO.md').write_text(f'''# Ordem de revisão independente — etapa {etapa}

Você é o revisor independente, de fornecedor diferente de todos os implementadores. Não implemente nem corrija nada.

- Cópia: esta pasta. Base: commit "base ({base[:7]})". Candidato: "candidato ({head[:7]})", que é o HEAD.
- Alterações: git diff HEAD~1 HEAD
- Critérios: o plano e a ordem da etapa {etapa}, dentro desta cópia.
- Método: PROTOCOLO-REVISAO.md desta pasta (passo 0, oito lentes, matriz de cobertura).

Regras: não altere nada fora de revisao-saida/; sondas só em revisao-saida/ ou no diretório temporário;
não use rede nem leia outras pastas; distinga executado de lido; falha de ambiente não é defeito.

Parecer: revisao-saida/parecer.md, pelo modelo revisao-saida/parecer-modelo.md. Ao terminar, informe o SHA-256
(sha256sum revisao-saida/parecer.md).
''', encoding='utf-8')
    with open(destino / '.git' / 'info' / 'exclude', 'a', encoding='utf-8') as f:
        f.write('ORDEM-REVISAO.md\nPROTOCOLO-REVISAO.md\nrevisao-saida/\n')
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

    p = sub.add_parser('entregar', help='portão sobre base..HEAD e atestado')
    p.add_argument('--etapa', required=True)
    p.add_argument('--base', required=True, help='commit de partida (da fatia ou da etapa)')
    p.add_argument('--fatia')
    p.add_argument('--pasta-projeto', default='.', help='pasta onde os testes rodam')
    p.add_argument('--comando-teste')
    p.add_argument('--papel', default='Coordenador')
    p.add_argument('--pasta-sociedade')
    p.set_defaults(func=cmd_entregar)

    p = sub.add_parser('conferir', help='confere a lista de entregas de uma ordem')
    p.add_argument('--ordem', required=True)
    p.add_argument('--registrar', action='store_true')
    p.add_argument('--raiz')
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_conferir)

    p = sub.add_parser('sessao', help='mede uma sessão pelo log do aplicativo')
    p.add_argument('app', choices=('antigravity', 'codex', 'claude'))
    p.add_argument('--log')
    p.add_argument('--pasta')
    p.add_argument('--conversa')
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=cmd_sessao)

    p = sub.add_parser('revisar', help='prepara a cópia descartável para o revisor')
    p.add_argument('--etapa', required=True)
    p.add_argument('--base', required=True)
    p.add_argument('--head', default='HEAD')
    p.add_argument('--destino')
    p.add_argument('--pasta-sociedade')
    p.set_defaults(func=cmd_revisar)

    p = sub.add_parser('estado', help='gera sociedade/estado.md e estado.html')
    p.add_argument('--pasta-sociedade')
    p.add_argument('--sem-html', action='store_true')
    p.add_argument('--imprimir', action='store_true')
    p.add_argument('--artefato', help='grava também o painel em fragmento HTML, pronto para publicar como página')
    p.set_defaults(func=cmd_estado)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == '__main__':
    sys.exit(main())
