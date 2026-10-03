#!/usr/bin/env python3
"""Confere se os arquivos declarados para cada executor de uma fatia são disjuntos.

Regra do núcleo: um arquivo, um executor por fatia. Duas listas que se cruzam viram trabalho
sobrescrito, que só aparece na revisão — retrabalho caro. Rode antes de despachar.

Entrada, de qualquer uma das formas:
  --par "Elrond: src/db/schema.sql, src/db/migrate.ts"   (repetível)
  arquivo.md                                             (linhas "- Nome: caminho, caminho")
  -                                                      (o mesmo, pela entrada padrão)

Considera conflito: caminho igual, caminho dentro de pasta declarada por outro, e padrão
com curinga que casa com caminho de outro. Normaliza "./x" e barras repetidas.

Saída: lista de conflitos e código 1; sem conflitos, código 0. Não despacha nada.
"""
import argparse
import fnmatch
import re
import sys
from pathlib import PurePosixPath

LINHA = re.compile(r'^\s*[-*]?\s*([^:]{1,60}?)\s*:\s*(.+?)\s*$')
CURINGA = re.compile(r'[*?\[]')


def normalizar(caminho):
    c = caminho.strip().strip('`"\'').replace('\\', '/')
    while '//' in c:
        c = c.replace('//', '/')
    if c.startswith('./'):
        c = c[2:]
    return c.rstrip('/')


def ler_pares(texto):
    """Extrai [(executor, [caminhos])] de linhas 'Nome: a, b'. Ignora cabeçalhos e vazias."""
    pares = []
    for linha in texto.splitlines():
        if not linha.strip() or linha.lstrip().startswith('#'):
            continue
        m = LINHA.match(linha)
        if not m:
            continue
        nome = m.group(1).strip()
        caminhos = [normalizar(c) for c in m.group(2).split(',') if normalizar(c)]
        if caminhos:
            pares.append((nome, caminhos))
    return pares


def conflito(a, b):
    """Motivo do choque entre dois caminhos declarados, ou None."""
    if CURINGA.search(a) or CURINGA.search(b):
        if fnmatch.fnmatch(b, a) or fnmatch.fnmatch(a, b):
            return 'padrão casa com o caminho'
        return None
    if a == b:
        return 'mesmo caminho'
    pa, pb = PurePosixPath(a), PurePosixPath(b)
    if pa == pb or pb in pa.parents:
        return f'"{a}" está dentro de "{b}"'
    if pa in pb.parents:
        return f'"{b}" está dentro de "{a}"'
    return None


def verificar(pares):
    problemas = []
    for i, (nome_a, caminhos_a) in enumerate(pares):
        vistos = {}
        for c in caminhos_a:
            if c in vistos:
                problemas.append(f'{nome_a}: caminho repetido na própria lista ({c})')
            vistos[c] = True
        for nome_b, caminhos_b in pares[i + 1:]:
            for ca in caminhos_a:
                for cb in caminhos_b:
                    motivo = conflito(ca, cb)
                    if motivo:
                        problemas.append(f'{nome_a} e {nome_b} disputam {ca} × {cb} ({motivo})')
    return problemas


def main(argv=None):
    p = argparse.ArgumentParser(description='Confere disjunção de arquivos entre executores de uma fatia.')
    p.add_argument('arquivo', nargs='?', help='arquivo com linhas "- Nome: caminho, caminho" (use - para stdin)')
    p.add_argument('--par', action='append', default=[], help='"Nome: caminho, caminho" (repetível)')
    a = p.parse_args(argv)

    texto = '\n'.join(a.par)
    if a.arquivo == '-':
        texto += '\n' + sys.stdin.read()
    elif a.arquivo:
        try:
            texto += '\n' + open(a.arquivo, encoding='utf-8').read()
        except OSError as e:
            print(f'erro: não consegui ler {a.arquivo} ({e.__class__.__name__})', file=sys.stderr)
            return 2

    pares = ler_pares(texto)
    if not pares:
        print('erro: nenhum par "Nome: caminhos" reconhecido', file=sys.stderr)
        return 2
    if len(pares) == 1:
        print(f'um executor só ({pares[0][0]}): nada a cruzar')
        return 0

    problemas = verificar(pares)
    for prob in problemas:
        print(f'conflito: {prob}')
    if problemas:
        print('\nTorne as tarefas sequenciais ou reparta os arquivos antes de despachar.')
        return 1
    total = sum(len(c) for _, c in pares)
    print(f'disjunto: {len(pares)} executores, {total} caminhos, nenhum cruzamento')
    return 0


if __name__ == '__main__':
    sys.exit(main())
