#!/usr/bin/env python3
"""Confere estrutura e coerência de um parecer do Revisor Independente (modelo assets/parecer-modelo.md).

Regras: campos do cabeçalho; seções Independência, Critérios e evidências, Achados e "O que não verifiquei"
(não vazia); estados da tabela em {executada, lida, não verificada}; "aceitar" não convive com critério não
verificada nem com achado bloqueador; achado bloqueador pede "não aceitar".
Código de saída 1 se houver erro; 0 caso contrário. Sem dependências externas.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

TITULO = re.compile(r'^##\s+Parecer do Revisor Independente\s*$', re.M | re.I)
CAMPO = re.compile(r'^-\s+([^:\n]+):\s*(.*)$')
CABECALHO = re.compile(r'^#{2,3}\s+(.+?)\s*$')
SHAS = re.compile(r'^[0-9a-fA-F]{7,40}\.\.\.?[0-9a-fA-F]{7,40}$')
MARCADOR = re.compile(r'<[^<>\n]{1,120}>')
VEREDITOS = ('aceitar', 'aceitar com ressalvas', 'nao aceitar')
ESTADOS = ('executada', 'lida', 'nao verificada')
SEVERIDADES = ('bloqueador', 'relevante', 'opcional')
SECOES = {'independencia': 'Independência', 'criterios e evidencias': 'Critérios e evidências',
          'achados': 'Achados', 'o que nao verifiquei': 'O que não verifiquei'}


def norm(texto):
    sem = unicodedata.normalize('NFD', texto.strip().lower())
    return ''.join(c for c in sem if unicodedata.category(c) != 'Mn')


def ultimo_parecer(texto):
    achados = list(TITULO.finditer(texto))
    if not achados:
        return None
    inicio = achados[-1].end()
    fim = re.search(r'^##\s(?!#)', texto[inicio:], re.M)
    return texto[inicio:inicio + fim.start()] if fim else texto[inicio:]


def dividir(bloco):
    """Cabeçalho (campos) e seções ### por nome normalizado."""
    campos, secoes, atual = {}, {}, None
    for linha in bloco.split('\n'):
        h = CABECALHO.match(linha)
        if h and linha.startswith('###'):
            atual = norm(h.group(1))
            secoes[atual] = []
            continue
        if atual is None:
            m = CAMPO.match(linha.strip())
            if m:
                campos[norm(m.group(1))] = m.group(2).strip()
        else:
            secoes[atual].append(linha)
    return campos, {k: '\n'.join(v).strip() for k, v in secoes.items()}


def linhas_tabela(texto):
    linhas = []
    for linha in texto.split('\n'):
        s = linha.strip()
        if not s.startswith('|'):
            continue
        celulas = [c.strip() for c in s.strip('|').split('|')]
        if all(re.fullmatch(r':?-{2,}:?', c) for c in celulas if c):
            continue
        linhas.append(celulas)
    return linhas[1:] if linhas else []  # descarta o cabeçalho da tabela


def analisar(texto):
    bloco = ultimo_parecer(texto)
    if bloco is None:
        return ['bloco "## Parecer do Revisor Independente" não encontrado'], [], None
    erros, avisos = [], []
    campos, secoes = dividir(bloco)

    for chave, nome in (('rodada', 'rodada'), ('entrega', 'entrega'), ('base..head', 'base..head'),
                        ('revisor', 'revisor'), ('veredito', 'veredito')):
        v = campos.get(chave)
        if v is None or not v:
            erros.append(f'campo ausente ou vazio: {nome}')
        elif MARCADOR.search(v):
            erros.append(f'campo com marcador do modelo sem preencher: {nome}')
    bh = campos.get('base..head', '')
    if bh and not MARCADOR.search(bh) and not SHAS.match(bh):
        erros.append('base..head deve ser <sha7>..<sha7> (7 a 40 hexadecimais)')
    revisor = norm(campos.get('revisor', ''))
    if revisor and not MARCADOR.search(revisor):
        if 'sessao' not in revisor:
            erros.append('revisor deve declarar a sessão (ID real)')
        if 'fornecedor' not in revisor:
            erros.append('revisor deve declarar o fornecedor (independência é por fornecedor)')
    veredito = norm(campos.get('veredito', ''))
    if veredito and not MARCADOR.search(veredito) and veredito not in VEREDITOS:
        erros.append('veredito deve ser: aceitar, aceitar com ressalvas ou não aceitar')
    indep = norm(campos.get('independencia', ''))
    if indep:
        if MARCADOR.search(campos['independencia']):
            erros.append('campo com marcador do modelo sem preencher: independência')
        elif not any(n in indep for n in ('nivel a', 'nivel b', 'nivel c', 'a (', 'b (', 'c (', 'externo', 'sessao isolada', 'modelo distinto')):
            avisos.append('independência no cabeçalho deve declarar Nível A, Nível B ou Nível C')

    for chave, nome in SECOES.items():
        if chave not in secoes:
            erros.append(f'seção ausente: {nome}')
        elif not secoes[chave]:
            erros.append(f'seção vazia: {nome}')
    if 'independencia' in secoes and secoes['independencia']:
        t = norm(secoes['independencia'])
        if MARCADOR.search(secoes['independencia']):
            erros.append('Independência ainda tem marcador do modelo (apague ou preencha)')
        if 'nao implementei' not in t and 'nao corrigi' not in t:
            avisos.append('Independência deve declarar que o revisor não implementou nem corrigiu a entrega')

    tem_nao_verificada = False
    linhas = linhas_tabela(secoes.get('criterios e evidencias', ''))
    if 'criterios e evidencias' in secoes and not linhas:
        erros.append('tabela critério-evidência sem linhas')
    for c in linhas:
        if len(c) < 3:
            erros.append(f'linha da tabela com menos de 3 colunas: {"|".join(c)[:60]}')
            continue
        estado = norm(c[2])
        if MARCADOR.search(c[2]) or MARCADOR.search(c[0]) or MARCADOR.search(c[1]):
            erros.append(f'linha da tabela com marcador sem preencher: {c[0][:40]}')
            continue
        if estado not in ESTADOS:
            erros.append(f'estado inválido "{c[2]}" (use executada, lida ou não verificada): {c[0][:40]}')
            continue
        if estado == 'nao verificada':
            tem_nao_verificada = True
        if estado == 'executada' and '`' not in c[1]:
            avisos.append(f'critério "{c[0][:40]}": estado executada sem comando entre crases na evidência')
        if not c[1].strip():
            erros.append(f'critério "{c[0][:40]}" sem evidência')

    bloqueante = False
    achados = secoes.get('achados', '')
    if achados and norm(achados).strip('.- ') not in ('nenhum', 'nenhuma', 'nenhum achado'):
        itens = [l for l in achados.split('\n') if l.strip().startswith('-')]
        if not itens:
            avisos.append('Achados sem itens no formato "- [severidade] descrição"')
        for item in itens:
            if MARCADOR.search(item) and item.strip().startswith('- [<'):
                erros.append('achado com marcador do modelo sem preencher')
                continue
            m = re.match(r'^-\s*\[([^\]]+)\]', item.strip())
            if not m or norm(m.group(1)) not in SEVERIDADES:
                erros.append(f'achado sem severidade válida (bloqueador, relevante, opcional): {item.strip()[:60]}')
            elif norm(m.group(1)) == 'bloqueador':
                bloqueante = True
    nv = secoes.get('o que nao verifiquei', '')
    if nv and MARCADOR.search(nv) and nv.strip().startswith('- <'):
        erros.append('"O que não verifiquei" ainda tem o marcador do modelo')
    if tem_nao_verificada and 'o que nao verifiquei' in secoes and 'verific' not in norm(nv) and len(nv) < 10:
        avisos.append('há critério não verificado; detalhe-o em "O que não verifiquei"')

    if veredito == 'aceitar':
        if tem_nao_verificada:
            erros.append('veredito "aceitar" não combina com critério "não verificada" (use "aceitar com ressalvas")')
        if bloqueante:
            erros.append('veredito "aceitar" não combina com achado bloqueador')
    if bloqueante and veredito in ('aceitar com ressalvas',):
        erros.append('achado bloqueador pede veredito "não aceitar"')
    return erros, avisos, campos


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('arquivo', help='arquivo Markdown com o parecer (o último bloco vale)')
    args = p.parse_args(argv)
    caminho = Path(args.arquivo)
    if not caminho.is_file():
        print(f'erro: arquivo não encontrado: {caminho}', file=sys.stderr)
        return 2
    erros, avisos, campos = analisar(caminho.read_text(encoding='utf-8'))
    for e in erros:
        print(f'ERRO: {e}')
    for a in avisos:
        print(f'aviso: {a}')
    if erros:
        return 1
    print(f'parecer válido (veredito: {campos.get("veredito")})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
