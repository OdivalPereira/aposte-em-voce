#!/usr/bin/env python3
"""Confere se o perfil de um projeto tem o mínimo exigido pelo núcleo da Sociedade do Código.

Aceita Markdown livre: um campo vale se aparecer como título (## Missão) ou rótulo em
negrito (**Missão:**). Código de saída 1 se faltar campo obrigatório. Sem dependências.
"""
import argparse
import re
import sys
from pathlib import Path

OBRIGATORIOS = {
    'Missão': ('missão', 'missao'),
    'Autoridades': ('autoridades',),
    'Papel × ferramenta': ('papel × ferramenta', 'papel x ferramenta', 'papel e ferramenta'),
}
RECOMENDADOS = {
    'Executores locais': ('executores locais',),
    'Papéis locais': ('papéis locais', 'papeis locais'),
    'Regras de domínio': ('regras de domínio', 'regras de dominio'),
    'Limites e paradas': ('limites', 'paradas'),
    'Comandos': ('comandos',),
}
TITULO = re.compile(r'^\s{0,3}#{1,6}\s*(.+?)\s*#*\s*$', re.M)
NEGRITO = re.compile(r'\*\*([^*\n]{2,60}?)\s*:?\*\*')
MARCADOR = re.compile(r'<[A-Za-zÀ-ú][^<>\n]{1,40}>')


def rotulos(texto):
    achados = [m.group(1).lower() for m in TITULO.finditer(texto)]
    achados += [m.group(1).lower() for m in NEGRITO.finditer(texto)]
    return achados


def tem(campos, aliases):
    return any(alias in rotulo for rotulo in campos for alias in aliases)


def validar(caminho):
    texto = Path(caminho).read_text(encoding='utf-8')
    campos = rotulos(texto)
    faltam = [nome for nome, aliases in OBRIGATORIOS.items() if not tem(campos, aliases)]
    avisos = [f'campo recomendado ausente: {nome}' for nome, aliases in RECOMENDADOS.items() if not tem(campos, aliases)]
    sem_html = re.sub(r'`[^`\n]*`', '', texto)
    marcadores = MARCADOR.findall(sem_html)
    if marcadores:
        avisos.append(f'{len(marcadores)} marcador(es) do modelo ainda sem preencher (ex.: {marcadores[0]})')
    return faltam, avisos


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('perfil', help='caminho do perfil (Markdown)')
    args = p.parse_args(argv)
    if not Path(args.perfil).is_file():
        print(f'erro: arquivo não encontrado: {args.perfil}', file=sys.stderr)
        return 2
    faltam, avisos = validar(args.perfil)
    for nome in faltam:
        print(f'FALTA (obrigatório): {nome}')
    for aviso in avisos:
        print(f'aviso: {aviso}')
    if faltam:
        return 1
    print('perfil com o mínimo exigido')
    return 0


if __name__ == '__main__':
    sys.exit(main())
