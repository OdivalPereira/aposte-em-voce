#!/usr/bin/env python3
"""Cria ou atualiza o bloco de adoção da Sociedade do Código no AGENTS.md de um projeto.

Padrão: simulação (mostra o diff, não grava). Use --aplicar para gravar.
Só o texto entre os marcadores é gerenciado; o resto do arquivo nunca é tocado.
O bloco carrega um hash: se alguém o editar à mão, o script recusa sobrescrever sem --forcar.
Sem dependências externas.
"""
import argparse
import difflib
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
BEGIN_RE = re.compile(r'<!-- sociedade-do-codigo:inicio(?P<attrs>[^>]*?)-->')
END_MARK = '<!-- sociedade-do-codigo:fim -->'
ATTR_RE = re.compile(r'(\w+)=(\S*)')
PASTA_PADRAO = 'sociedade'
PERFIS_PADRAO = ('docs/sociedade/perfil.md', 'docs/perfil.md', '.sociedade/perfil.md', 'perfil.md')


def versao_nucleo():
    texto = (SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
    achado = re.search(r'^\s*versao:\s*"?([0-9][0-9A-Za-z.\-]*)"?\s*$', texto, re.M)
    if not achado:
        raise SystemExit('erro: versão do núcleo não encontrada em SKILL.md')
    return achado.group(1)


def normalizar(texto):
    linhas = [linha.rstrip() for linha in texto.replace('\r\n', '\n').split('\n')]
    return '\n'.join(linhas).strip('\n')


def hash_corpo(corpo):
    return hashlib.sha256(normalizar(corpo).encode('utf-8')).hexdigest()[:12]


def gerar_corpo(nucleo, perfil, pasta, jules):
    modelo = (SKILL_DIR / 'assets' / 'agents-md-bloco.md').read_text(encoding='utf-8')

    def condicional(m):
        # {{#jules}}...{{/jules}}: a seção do executor júnior em nuvem só entra se o projeto o usa.
        return m.group(2) if (m.group(1) == 'jules' and jules) else ''

    modelo = re.sub(r'\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}', condicional, modelo, flags=re.S)
    for chave, valor in {'{{nucleo}}': nucleo, '{{perfil}}': perfil, '{{pasta}}': pasta}.items():
        modelo = modelo.replace(chave, valor)
    return re.sub(r'\n{3,}', '\n\n', normalizar(modelo))


def gerar_bloco(nucleo, perfil, pasta, jules):
    corpo = gerar_corpo(nucleo, perfil, pasta, jules)
    inicio = (f'<!-- sociedade-do-codigo:inicio nucleo={nucleo} perfil={perfil} '
              f'pasta={pasta} jules={"sim" if jules else "nao"} sha={hash_corpo(corpo)} -->')
    return f'{inicio}\n{corpo}\n{END_MARK}'


def achar_bloco(texto):
    inicio = BEGIN_RE.search(texto)
    if not inicio:
        return None
    fim = texto.find(END_MARK, inicio.end())
    if fim < 0:
        raise SystemExit('erro: marcador de início sem marcador de fim no AGENTS.md')
    atributos = dict(ATTR_RE.findall(inicio.group('attrs')))
    corpo = texto[inicio.end():fim].strip('\n')
    return {'inicio': inicio.start(), 'fim': fim + len(END_MARK), 'attrs': atributos, 'corpo': corpo}


def detectar_perfil(projeto):
    for candidato in PERFIS_PADRAO:
        if (projeto / candidato).is_file():
            return candidato, True
    return PERFIS_PADRAO[0], False


def inserir_no_inicio(texto, bloco):
    """Insere o bloco logo após o primeiro título de nível 1 (ou no começo, se não houver)."""
    linhas = texto.split('\n')
    idx = next((i for i, linha in enumerate(linhas) if linha.startswith('# ')), None)
    if idx is None:
        return f'{bloco}\n\n{texto.lstrip(chr(10))}'
    cabeca = '\n'.join(linhas[:idx + 1])
    cauda = '\n'.join(linhas[idx + 1:]).lstrip('\n')
    return f'{cabeca}\n\n{bloco}\n\n{cauda}' if cauda else f'{cabeca}\n\n{bloco}\n'


PONTEIROS = {
    'CLAUDE.md': '@AGENTS.md\n',
    'GEMINI.md': 'As regras deste projeto estão no `AGENTS.md` desta pasta. Leia-o e siga-o.\n',
}


def ponteiros(projeto, aplicar):
    """Q62: CLAUDE.md e GEMINI.md só apontam para o AGENTS.md. Cria o que falta; nunca reescreve."""
    for nome, conteudo in PONTEIROS.items():
        alvo = projeto / nome
        if alvo.is_file():
            texto = alvo.read_text(encoding='utf-8', errors='replace')
            ok = 'AGENTS.md' in texto
            print(f'[{"ok" if ok else "aviso"}] {nome} já existe' + ('' if ok else ': não aponta para o AGENTS.md; ajuste à mão'))
            continue
        if aplicar:
            alvo.write_text(conteudo, encoding='utf-8')
            print(f'[criado] {nome}')
        else:
            print(f'[criar] {nome} (simulação)')


def sincronizar(args):
    projeto = Path(args.projeto).resolve()
    alvo = projeto / 'AGENTS.md'
    existe = alvo.is_file()
    bruto = alvo.read_bytes().decode('utf-8') if existe else ''
    crlf = '\r\n' in bruto
    texto = bruto.replace('\r\n', '\n')
    bloco = achar_bloco(texto) if existe else None

    if not existe and not args.criar:
        print('erro: AGENTS.md não existe. Use --criar para criá-lo com o bloco.', file=sys.stderr)
        return 2

    anteriores = bloco['attrs'] if bloco else {}
    pasta = args.pasta or anteriores.get('pasta') or PASTA_PADRAO
    jules = args.jules if args.jules is not None else (anteriores.get('jules', 'sim') == 'sim')
    perfil, perfil_existe = (args.perfil, (projeto / args.perfil).is_file()) if args.perfil else (
        (anteriores['perfil'], (projeto / anteriores['perfil']).is_file()) if 'perfil' in anteriores
        else detectar_perfil(projeto))
    if not perfil_existe:
        print(f'aviso: perfil "{perfil}" ainda não existe; crie-o a partir de assets/perfil-modelo.md', file=sys.stderr)

    novo_bloco = gerar_bloco(args.nucleo or versao_nucleo(), perfil, pasta, jules)

    if bloco:
        if hash_corpo(bloco['corpo']) != bloco['attrs'].get('sha') and not args.forcar:
            print('erro: o bloco foi editado à mão (hash não confere). Revise ou use --forcar.', file=sys.stderr)
            return 2
        novo_texto = texto[:bloco['inicio']] + novo_bloco + texto[bloco['fim']:]
        rotulo = 'igual' if novo_texto == texto else 'atualizar bloco'
    else:
        base = texto.rstrip('\n')
        if not existe:
            base = f'# {projeto.name}'
        if args.posicao == 'inicio' and existe:
            novo_texto = inserir_no_inicio(texto, novo_bloco)
        else:
            novo_texto = f'{base}\n\n{novo_bloco}\n'
        rotulo = 'criar arquivo com bloco' if not existe else 'adicionar bloco'

    if args.verificar:
        atual = bool(bloco) and novo_texto == texto
        print('bloco em dia' if atual else 'bloco ausente ou desatualizado')
        return 0 if atual else 1

    if novo_texto == texto:
        print(f'[igual] {alvo}')
        if getattr(args, 'ponteiros', False):
            ponteiros(projeto, args.aplicar)
        return 0

    print(f'[{rotulo}] {alvo}')
    diff = difflib.unified_diff(texto.split('\n'), novo_texto.split('\n'), 'AGENTS.md (atual)', 'AGENTS.md (novo)', lineterm='')
    print('\n'.join(diff))
    if not args.aplicar:
        if getattr(args, 'ponteiros', False):
            ponteiros(projeto, False)
        print('\nSimulação: nada foi gravado. Use --aplicar para gravar.')
        return 0

    saida = novo_texto.replace('\n', '\r\n') if crlf else novo_texto
    fd, tmp = tempfile.mkstemp(dir=str(projeto), prefix='.AGENTS.md.')
    try:
        with os.fdopen(fd, 'wb') as arquivo:
            arquivo.write(saida.encode('utf-8'))
        os.replace(tmp, alvo)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(f'Gravado: {alvo}')
    if getattr(args, 'ponteiros', False):
        ponteiros(projeto, True)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--projeto', default='.', help='pasta do projeto (padrão: atual)')
    p.add_argument('--pasta', help=f'pasta do estado da rodada (padrão: o do bloco atual, senão {PASTA_PADRAO})')
    p.add_argument('--jules', dest='jules', action='store_true', default=None,
                   help='inclui a seção do executor júnior em nuvem (padrão: o do bloco atual, senão sim)')
    p.add_argument('--sem-jules', dest='jules', action='store_false',
                   help='remove a seção do executor júnior em nuvem')
    p.add_argument('--perfil', help='caminho do perfil, relativo ao projeto')
    p.add_argument('--nucleo', help='força a versão do núcleo no bloco (uso avançado)')
    p.add_argument('--aplicar', action='store_true', help='grava (sem isto, só simula)')
    p.add_argument('--forcar', action='store_true', help='sobrescreve mesmo que o bloco tenha sido editado à mão')
    p.add_argument('--criar', action='store_true', help='cria o AGENTS.md se não existir')
    p.add_argument('--ponteiros', action='store_true', help='cria CLAUDE.md e GEMINI.md apontando para o AGENTS.md (Q62)')
    p.add_argument('--posicao', choices=('fim', 'inicio'), default='fim',
                   help='onde inserir um bloco novo: fim (padrão) ou inicio, logo após o primeiro título; '
                        'use inicio em AGENTS.md longo (o Codex lê só os primeiros 32 KiB por padrão). '
                        'Bloco já existente permanece onde está')
    p.add_argument('--verificar', action='store_true', help='só confere se o bloco está em dia (código 1 se não)')
    return sincronizar(p.parse_args(argv))


if __name__ == '__main__':
    sys.exit(main())
