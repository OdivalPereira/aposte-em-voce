#!/usr/bin/env python3
"""Confere um lote de tarefas Jules (modelo assets/tarefa-jules.md) antes do despacho. Não despacha nada.

Verifica: campos obrigatórios, placeholders não preenchidos, classe (R2 exige --permitir-r2), base no formato
branch@sha, caminhos locais e segredos aparentes, arquivos permitidos × proibidos, sobreposição de arquivos
entre tarefas do lote (PRs conflitantes) e contrapressão (PRs abertos, cota e simultâneas livres).

Código de saída: 1 se houver erro; 0 caso contrário. Sem dependências externas.
"""
import argparse
import fnmatch
import re
import sys
import unicodedata
from pathlib import Path

ROTULOS = {
    'tarefa': 'Tarefa',
    'classe': 'Classe',
    'repositorio e base': 'Repositório e base',
    'objetivo': 'Objetivo',
    'arquivos permitidos': 'Arquivos permitidos',
    'nao tocar': 'Não tocar',
    'comportamento a preservar': 'Comportamento a preservar',
    'como provar que esta pronto': 'Como provar que está pronto',
    'tamanho esperado': 'Tamanho esperado',
    'retorno': 'Retorno',
    'fora de escopo': 'Fora de escopo',
}
OBRIGATORIOS = ['tarefa', 'classe', 'repositorio e base', 'objetivo', 'arquivos permitidos', 'nao tocar',
                'como provar que esta pronto', 'tamanho esperado', 'retorno']
COMENTARIO = re.compile(r'<!--.*?-->', re.S)
MARCADOR = re.compile(r'<[^<>\n]{1,80}>')
BASE = re.compile(r'@\s*[0-9a-fA-F]{7,40}\b')
LOCAL = re.compile(r'(?<![\w/])(?:/(?:home|Users|tmp|mnt|root|var|etc)/|[A-Za-z]:\\|~/|file://)')
SEGREDO = re.compile(r'(?:AIza[0-9A-Za-z_\-]{20,}|gh[pousr]_[0-9A-Za-z]{30,}|sk-[0-9A-Za-z_\-]{20,}|'
                     r'-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:api[_-]?key|token|secret|senha|password)\s*[=:]\s*\S{8,})', re.I)
GLOBO = re.compile(r'[*?\[]')


def sem_acento(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto.lower()) if unicodedata.category(c) != 'Mn')


LINHA_ROTULO = re.compile(r'^\s*([^:\n]{3,40}):\s*(.*)$')


def analisar(texto):
    """Devolve lista de tarefas: dict rótulo(normalizado) -> valor. Ignora comentários HTML."""
    texto = COMENTARIO.sub('', texto)
    tarefas, atual, rotulo = [], None, None
    for linha in texto.split('\n'):
        m = LINHA_ROTULO.match(linha)
        chave = sem_acento(m.group(1).strip()) if m else None
        if m and chave in ROTULOS:
            if chave == 'tarefa':
                atual = {}
                tarefas.append(atual)
            if atual is None:
                continue
            atual[chave] = m.group(2).strip()
            rotulo = chave
        elif atual is not None and rotulo and linha.strip():
            atual[rotulo] = (atual[rotulo] + '\n' + linha.strip()).strip()
    return tarefas


def lista_caminhos(valor):
    itens = []
    for parte in re.split(r'[,\n;]', valor):
        parte = parte.strip().lstrip('-*').strip().strip('`').strip()
        if parte and parte.lower() not in ('nenhum', 'nenhuma', 'n/a'):
            itens.append(normalizar(parte))
    return itens


def normalizar(caminho):
    c = caminho.strip().replace('\\', '/')
    while c.startswith('./'):
        c = c[2:]
    return c.rstrip('/') or '.'


def cabeca(caminho):
    """Parte literal antes do primeiro curinga, cortada na última barra (diretório)."""
    m = GLOBO.search(caminho)
    if not m:
        return caminho
    trecho = caminho[:m.start()]
    return trecho.rsplit('/', 1)[0] if '/' in trecho else ''


def sobrepoe(a, b):
    """Conservador: True se os dois caminhos ou padrões podem alcançar o mesmo arquivo."""
    if a == b or a == '.' or b == '.':
        return True
    if a.startswith(b + '/') or b.startswith(a + '/'):
        return True
    if GLOBO.search(a) or GLOBO.search(b):
        if fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a):
            return True
        ha, hb = cabeca(a), cabeca(b)
        return ha == hb or ha.startswith(hb + '/') or hb.startswith(ha + '/') or not ha or not hb
    return False


def verificar(tarefas, permitir_r2=False, restam=None, livres=None, prs_abertos=None, max_prs=8):
    erros, avisos, notas = [], [], []
    if not tarefas:
        return ['nenhuma tarefa encontrada (cada bloco começa com "Tarefa:")'], avisos, notas
    permitidos = {}
    slugs = set()
    for i, t in enumerate(tarefas, 1):
        nome = t.get('tarefa') or f'#{i}'
        for k in OBRIGATORIOS:
            v = t.get(k)
            if v is None or not v.strip():
                erros.append(f'{nome}: campo ausente ou vazio: {ROTULOS[k]}')
            elif MARCADOR.search(v):
                erros.append(f'{nome}: {ROTULOS[k]} ainda tem marcador do modelo sem preencher')
        if nome in slugs:
            erros.append(f'{nome}: identificador de tarefa repetido')
        slugs.add(nome)
        classe = (t.get('classe') or '').strip().upper()
        if classe in ('R0', 'R1'):
            if classe == 'R1':
                notas.append(f'{nome}: R1 exige plano aprovado antes (na API, requirePlanApproval) e revisão individual')
        elif classe == 'R2':
            if not permitir_r2:
                erros.append(f'{nome}: classe R2 não vai ao Jules por padrão (use --permitir-r2 só com ordem explícita, plano aprovado e revisão específica)')
            else:
                notas.append(f'{nome}: R2 liberada por ordem explícita; exija plano aprovado e revisão específica')
        elif classe and not MARCADOR.search(classe):
            erros.append(f'{nome}: classe deve ser R0, R1 ou R2')
        base = t.get('repositorio e base', '')
        if base and not MARCADOR.search(base) and not BASE.search(base):
            erros.append(f'{nome}: "Repositório e base" deve trazer branch e SHA (por exemplo "@a1b2c3d")')
        conteudo = '\n'.join(t.values())
        if LOCAL.search(conteudo):
            erros.append(f'{nome}: contém caminho ou link local; o Jules roda na nuvem e não os enxerga')
        if SEGREDO.search(conteudo):
            erros.append(f'{nome}: parece conter segredo; remova (segredo não vai em prompt remoto)')
        perm = lista_caminhos(t.get('arquivos permitidos', ''))
        proib = lista_caminhos(t.get('nao tocar', ''))
        permitidos[nome] = perm
        for a in perm:
            if a in ('.', '*', '**', '**/*'):
                erros.append(f'{nome}: "Arquivos permitidos" amplo demais ({a})')
            for b in proib:
                # permitido igual ou dentro de um proibido; pasta permitida com exceção proibida é legítima
                if a == b or a.startswith(b + '/') or fnmatch.fnmatch(a, b):
                    erros.append(f'{nome}: "{a}" está em "Arquivos permitidos" e em "Não tocar" ({b})')
        if 'rascunho' not in sem_acento(t.get('retorno', '')):
            avisos.append(f'{nome}: "Retorno" não pede PR em rascunho')
        if not t.get('comportamento a preservar', '').strip():
            avisos.append(f'{nome}: sem "Comportamento a preservar"')
    nomes = list(permitidos)
    for i in range(len(nomes)):
        for j in range(i + 1, len(nomes)):
            for a in permitidos[nomes[i]]:
                for b in permitidos[nomes[j]]:
                    if sobrepoe(a, b):
                        erros.append(f'sobreposição entre {nomes[i]} e {nomes[j]}: "{a}" × "{b}" (lote exige arquivos disjuntos)')
    # contrapressão e capacidade
    total = len(tarefas)
    pode = total
    if prs_abertos is not None and prs_abertos >= max_prs:
        erros.append(f'contrapressão: {prs_abertos} PRs abertos aguardando revisão (teto {max_prs}); não despache mais, esvazie a fila')
        pode = 0
    if restam is not None:
        pode = min(pode, max(restam, 0))
    if livres is not None:
        pode = min(pode, max(livres, 0))
    if prs_abertos is not None and prs_abertos < max_prs:
        pode = min(pode, max_prs - prs_abertos)
    if pode < total:
        avisos.append(f'capacidade: pode despachar {pode} de {total} tarefas agora; despache na ordem do arquivo e guarde o resto')
    return erros, avisos, notas


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('arquivo', nargs='+', help='arquivo(s) Markdown com tarefas no modelo assets/tarefa-jules.md')
    p.add_argument('--permitir-r2', action='store_true', help='aceita classe R2 (ordem explícita)')
    p.add_argument('--restam', type=int, help='vagas restantes na cota de 24 h (veja jules_cota.py)')
    p.add_argument('--simultaneas-livres', type=int, help='vagas livres de tarefas simultâneas')
    p.add_argument('--prs-abertos', type=int, help='PRs do Jules abertos aguardando revisão')
    p.add_argument('--max-prs-abertos', type=int, default=3, help='teto de PRs abertos (padrão 3; perfil: jules.max_prs_abertos)')
    args = p.parse_args(argv)
    tarefas = []
    for nome in args.arquivo:
        caminho = Path(nome)
        if not caminho.is_file():
            print(f'erro: arquivo não encontrado: {caminho}', file=sys.stderr)
            return 2
        tarefas.extend(analisar(caminho.read_text(encoding='utf-8')))
    erros, avisos, notas = verificar(tarefas, args.permitir_r2, args.restam, args.simultaneas_livres,
                                     args.prs_abertos, args.max_prs_abertos)
    for e in erros:
        print(f'ERRO: {e}')
    for a in avisos:
        print(f'aviso: {a}')
    for n in notas:
        print(f'nota: {n}')
    if erros:
        return 1
    print(f'lote válido: {len(tarefas)} tarefa(s), arquivos disjuntos')
    return 0


if __name__ == '__main__':
    sys.exit(main())
