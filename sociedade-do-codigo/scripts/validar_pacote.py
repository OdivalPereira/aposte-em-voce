#!/usr/bin/env python3
"""Valida o pacote da Sociedade do Código antes de publicar ou empacotar.

Confere: VERSION e pacote.json; cada skill (formato Agent Skills: nome igual à pasta, regras do nome,
descrição até 1024 caracteres, corpo com menos de 500 linhas, versão igual à do pacote, arquivos citados
existem); manifestos iguais aos que gen_manifests.py geraria; caminhos dos marketplaces; definições de
agentes dos adaptadores; scripts Python compilam; nenhum termo de projeto específico nem segredo aparente
dentro do núcleo e dos adaptadores.

Código de saída 1 se houver erro. Sem dependências externas.
"""
import argparse
import importlib.util
import json
import py_compile
import re
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NOME_SKILL = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
SEMVER = re.compile(r'^\d+\.\d+\.\d+$')
# termos que nunca podem aparecer no núcleo (são de projetos, marcas ou stacks específicas)
PROIBIDOS = ['nosso timão', 'nosso timao', 'nosso_timao', 'palandir', 'corinthians', 'pedro raul',
             'supabase', 'vercel', 'bitrix', 'alterdata', 'domínio sistemas', 'dominio sistemas']
# A 2.0 proíbe medição de consumo: nenhum texto do pacote pode mandar contar, estimar ou relatar gasto.
# Só pega o verbo junto do objeto, para não acusar as próprias regras que proíbem a prática.
MEDICAO = re.compile(r'(?:estim\w+|calcul\w+|medi\w+|conte|contar|relat\w+|registr\w+)'
                     r'[^.\n]{0,40}(?:tokens|consumo|custo|gasto)', re.I)
MEDICAO_OK = re.compile(r'\b(?:n[ãa]o|nunca|jamais|nenhum\w*|nada|sem|proib\w+|aus[êe]ncia|dispens\w+)\b', re.I)
SEGREDOS = re.compile(r'(?:AIza[0-9A-Za-z_\-]{30,}|gh[pousr]_[0-9A-Za-z]{30,}|sk-[0-9A-Za-z_\-]{30,}|'
                      r'-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[abprs]-[0-9A-Za-z-]{20,})')
# Q102: checagens estruturais que substituem os testes de redação
LIMITE_PAPEL = 2560            # camada essencial de cada papel (Q96)
LIMITE_SKILL = 6000            # SKILL.md de cada skill
LIMITE_CARGA_COORDENADOR = 12288   # método lido pelo coordenador antes da tarefa (diagnóstico de 25/09)
LIMITE_MD_LEITURA = 60000      # todo o Markdown das skills: trava de crescimento (3.0.0 ~55 KB; 2.1.0 ~250 KB)
SECOES_PAPEL = ('## Faz', '## Não faz', '## Entrega')
# Termos de regras revogadas ou de estilo proibido (Q17, Q21, Q84, D-RT-001, Q100)
REVOGADOS = [re.compile(r, re.I) for r in (
    r'escala tripartite', r'\bn[íi]vel\s*[0-3]\b', r'n[íi]veis\s*0', r'revis[ãa]o cont[íi]nua',
    r'no m[áa]ximo 5 caminhos', r'separa[çc][ãa]o ontol[óo]gica', r'\b30 pilares\b', r'fail-closed',
    r'\bonze pap[ée]is\b')]
CAMINHO_ABSOLUTO = re.compile(r'file:///|/home/[a-z]')
LINK_MD = re.compile(r'\[[^\]]+\]\(([^)\s#]+)(?:#[^)]*)?\)')
EXTENSOES_TEXTO = {'.md', '.py', '.json', '.modelo', '.txt', '.toml', '.yml', '.yaml', ''}
REF_ARQUIVO = [re.compile(r'(?:^|[\s`(])((?:references|assets|scripts)/[\w./-]+)'),
               re.compile(r'<pasta-da-skill>/((?:references|assets|scripts)/[\w./-]+)')]


def frontmatter(texto):
    """Lê o frontmatter YAML simples (chaves, um nível de aninhamento e listas). Devolve (dict, corpo)."""
    if not texto.startswith('---\n'):
        return None, texto
    fim = texto.find('\n---', 4)
    if fim < 0:
        return None, texto
    bloco, corpo = texto[4:fim], texto[fim + 4:].lstrip('\n')
    campos, atual = {}, None
    for linha in bloco.split('\n'):
        if not linha.strip() or linha.lstrip().startswith('#'):
            continue
        if linha[0] in ' \t':
            s = linha.strip()
            if atual is None:
                continue
            if s.startswith('- '):
                if not isinstance(campos[atual], list):
                    campos[atual] = []
                campos[atual].append(s[2:].strip())
            elif ':' in s:
                if not isinstance(campos[atual], dict):
                    campos[atual] = {}
                k, _, v = s.partition(':')
                campos[atual][k.strip()] = v.strip().strip('"\'')
            continue
        k, _, v = linha.partition(':')
        atual = k.strip()
        v = v.strip()
        campos[atual] = {} if v == '' else v.strip('"\'')
    return campos, corpo


def arquivos_texto(base):
    for c in sorted(base.rglob('*')):
        if c.is_file() and c.suffix in EXTENSOES_TEXTO and '.git' not in c.parts and '__pycache__' not in c.parts:
            yield c


def validar(raiz=RAIZ):
    erros, avisos = [], []
    versao_arq = raiz / 'VERSION'
    versao = versao_arq.read_text(encoding='utf-8').strip() if versao_arq.is_file() else ''
    if not SEMVER.match(versao):
        erros.append('VERSION ausente ou fora do formato x.y.z')
    pj = raiz / 'pacote.json'
    dados = {}
    if not pj.is_file():
        erros.append('pacote.json ausente')
    else:
        try:
            dados = json.loads(pj.read_text(encoding='utf-8'))
        except ValueError as e:
            erros.append(f'pacote.json inválido: {e}')
        for k in ('name', 'marketplace', 'displayName', 'description', 'shortDescription', 'category',
                  'author', 'repository', 'license', 'keywords'):
            if k not in dados:
                erros.append(f'pacote.json sem a chave "{k}"')
    nome_plugin = dados.get('name', '')
    pasta_plugin = raiz / 'plugins' / nome_plugin
    if nome_plugin and not pasta_plugin.is_dir():
        erros.append(f'pasta do plugin ausente: plugins/{nome_plugin}')

    # skills
    skills_dir = pasta_plugin / 'skills'
    skills = sorted(p for p in skills_dir.iterdir() if p.is_dir()) if skills_dir.is_dir() else []
    if not skills:
        erros.append('nenhuma skill encontrada')
    nomes = set()
    for sk in skills:
        arq = sk / 'SKILL.md'
        rot = f'skill {sk.name}'
        if not arq.is_file():
            erros.append(f'{rot}: SKILL.md ausente')
            continue
        texto = arq.read_text(encoding='utf-8')
        fm, corpo = frontmatter(texto)
        if fm is None:
            erros.append(f'{rot}: frontmatter ausente ou malformado')
            continue
        nome = fm.get('name', '')
        if nome != sk.name:
            erros.append(f'{rot}: name ("{nome}") deve ser igual ao nome da pasta')
        if not NOME_SKILL.match(nome) or len(nome) > 64:
            erros.append(f'{rot}: name deve ter até 64 caracteres, a-z, 0-9 e hífens sem hífen duplo, inicial ou final')
        nomes.add(nome)
        desc = fm.get('description', '')
        if not isinstance(desc, str) or not desc.strip():
            erros.append(f'{rot}: description ausente')
        elif len(desc) > 1024:
            erros.append(f'{rot}: description com {len(desc)} caracteres (máximo 1024)')
        if len(corpo.split('\n')) >= 500:
            erros.append(f'{rot}: corpo com 500 linhas ou mais')
        meta = fm.get('metadata', {})
        if not isinstance(meta, dict) or meta.get('versao') != versao:
            erros.append(f'{rot}: metadata.versao deve ser {versao}')
        citados = set()
        for rx in REF_ARQUIVO:
            citados.update(m.group(1).rstrip('.,:;') for m in rx.finditer(corpo))
        for rel in sorted(citados):
            if not (sk / rel).exists():
                erros.append(f'{rot}: arquivo citado não existe: {rel}')
        for sub in ('scripts', 'references', 'assets'):
            d = sk / sub
            if d.is_dir() and not any(d.iterdir()):
                avisos.append(f'{rot}: pasta {sub}/ vazia')

    # manifestos
    gen = raiz / 'scripts' / 'gen_manifests.py'
    if gen.is_file() and dados and versao:
        spec = importlib.util.spec_from_file_location('gen_manifests_val', gen)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for rel, obj in mod.gerar(dados, versao).items():
            alvo = raiz / rel
            if not alvo.is_file():
                erros.append(f'manifesto ausente: {rel} (rode scripts/gen_manifests.py --escrever)')
            elif alvo.read_text(encoding='utf-8') != mod.serializar(obj):
                erros.append(f'manifesto desatualizado: {rel} (rode scripts/gen_manifests.py --escrever)')
        for rel in ('.claude-plugin/marketplace.json',):
            alvo = raiz / rel
            if alvo.is_file():
                for pl in json.loads(alvo.read_text(encoding='utf-8')).get('plugins', []):
                    if not (raiz / pl.get('source', '')).is_dir():
                        erros.append(f'{rel}: source inexistente: {pl.get("source")}')
        alvo = raiz / '.agents/plugins/marketplace.json'
        if alvo.is_file():
            for pl in json.loads(alvo.read_text(encoding='utf-8')).get('plugins', []):
                if not (raiz / pl.get('source', {}).get('path', '')).is_dir():
                    erros.append(f'.agents/plugins/marketplace.json: path inexistente: {pl.get("source")}')
    else:
        erros.append('não foi possível verificar os manifestos (gen_manifests.py, pacote.json ou VERSION ausentes)')

    # agentes dos adaptadores
    for arq in sorted((raiz / 'adapters').glob('*/agents/*.md')):
        fm, _ = frontmatter(arq.read_text(encoding='utf-8'))
        rot = f'agente {arq.parent.parent.name}/{arq.name}'
        if fm is None:
            erros.append(f'{rot}: frontmatter ausente ou malformado')
            continue
        if fm.get('name') != arq.stem:
            erros.append(f'{rot}: name deve ser igual ao nome do arquivo')
        if not fm.get('description'):
            erros.append(f'{rot}: description ausente')
        if arq.parent.parent.name == 'antigravity':
            if fm.get('subagent') != 'true':
                erros.append(f'{rot}: subagent deve ser true')
            if not isinstance(fm.get('tools'), list) or not fm['tools']:
                erros.append(f'{rot}: tools deve ser uma lista')
        if arq.parent.parent.name == 'claude' and not fm.get('tools'):
            avisos.append(f'{rot}: sem tools (herdaria todas as ferramentas)')

    # scripts compilam
    with tempfile.TemporaryDirectory() as tmp:
        for py in sorted(raiz.rglob('*.py')):
            if '.git' in py.parts or '__pycache__' in py.parts or 'tests' in py.parts:
                continue
            try:
                py_compile.compile(str(py), cfile=str(Path(tmp) / 'x.pyc'), doraise=True)
            except py_compile.PyCompileError as e:
                erros.append(f'script não compila: {py.relative_to(raiz)}: {e.msg.strip()[:80]}')

    # termos proibidos no núcleo e nos adaptadores; segredos em todo o pacote
    for base in (raiz / 'plugins', raiz / 'adapters'):
        for arq in arquivos_texto(base):
            bruto = arq.read_text(encoding='utf-8', errors='ignore')
            texto = bruto.lower()
            for termo in PROIBIDOS:
                if termo in texto:
                    erros.append(f'termo de projeto específico "{termo}" em {arq.relative_to(raiz)}')
            # só em texto de instrução (o que o agente lê); scripts têm testes próprios
            if arq.suffix in ('.md', '.modelo'):
                for linha in bruto.splitlines():
                    # a frase vale se for uma proibição ("nunca estime o consumo"); senão, é instrução de medir
                    if MEDICAO.search(linha) and not MEDICAO_OK.search(linha):
                        erros.append(f'instrução de medir consumo em {arq.relative_to(raiz)}: '
                                     f'"{linha.strip()[:70]}"')
    for arq in arquivos_texto(raiz):
        if 'tests' in arq.parts:
            continue
        if SEGREDOS.search(arq.read_text(encoding='utf-8', errors='ignore')):
            erros.append(f'possível segredo em {arq.relative_to(raiz)}')
    erros.extend(checagens_estruturais(raiz, pasta_plugin))
    return erros, avisos


def checagens_estruturais(raiz, pasta_plugin):
    """Q102: estrutura, tamanho, carga de leitura, caminhos, links e termos revogados."""
    erros = []
    skills = pasta_plugin / 'skills'
    papeis = skills / 'sc-papeis' / 'references'
    if papeis.is_dir():
        for arq in sorted(papeis.glob('papel-*.md')):
            tam = len(arq.read_bytes())
            if tam > LIMITE_PAPEL:
                erros.append(f'papel com {tam} bytes (máximo {LIMITE_PAPEL}): {arq.relative_to(raiz)}')
            texto = arq.read_text(encoding='utf-8')
            for sec in SECOES_PAPEL:
                if sec not in texto:
                    erros.append(f'papel sem a seção "{sec}": {arq.relative_to(raiz)}')
    for sk in sorted(skills.glob('*/SKILL.md')) if skills.is_dir() else []:
        tam = len(sk.read_bytes())
        if tam > LIMITE_SKILL:
            erros.append(f'SKILL.md com {tam} bytes (máximo {LIMITE_SKILL}): {sk.relative_to(raiz)}')
    carga = [skills / 'sociedade-do-codigo' / 'SKILL.md', skills / 'sc-papeis' / 'SKILL.md',
             papeis / 'papel-gandalf.md', skills / 'sc-execucao' / 'SKILL.md']
    if all(c.is_file() for c in carga):
        total = sum(len(c.read_bytes()) for c in carga)
        if total > LIMITE_CARGA_COORDENADOR:
            erros.append(f'carga de leitura do coordenador com {total} bytes (máximo {LIMITE_CARGA_COORDENADOR})')
    if skills.is_dir():
        total_md = sum(len(m.read_bytes()) for m in skills.rglob('*.md'))
        if total_md > LIMITE_MD_LEITURA:
            erros.append(f'Markdown das skills com {total_md} bytes (máximo {LIMITE_MD_LEITURA})')
    bases = [b for b in (raiz / 'plugins', raiz / 'adapters', raiz / 'modulos', raiz / 'docs') if b.is_dir()]
    for base in bases:
        for arq in arquivos_texto(base):
            if arq.suffix not in ('.md', '.modelo', '.py', '.json'):
                continue
            texto = arq.read_text(encoding='utf-8', errors='ignore')
            if CAMINHO_ABSOLUTO.search(texto):
                erros.append(f'caminho absoluto de máquina em {arq.relative_to(raiz)}')
            if arq.suffix == '.md':
                for m in LINK_MD.finditer(texto):
                    alvo = m.group(1)
                    if '://' in alvo or alvo.startswith('mailto:'):
                        continue
                    if not (arq.parent / alvo).exists():
                        erros.append(f'link quebrado em {arq.relative_to(raiz)}: {alvo}')
                if base.name in ('plugins', 'adapters') or arq.name == 'README.md':
                    for rx in REVOGADOS:
                        if rx.search(texto):
                            erros.append(f'termo de regra revogada ("{rx.pattern}") em {arq.relative_to(raiz)}')
                    if re.search(r'\bodival\b', texto, re.I):
                        erros.append(f'nome do usuário em texto genérico: {arq.relative_to(raiz)}')
    readme = raiz / 'README.md'
    if readme.is_file():
        texto = readme.read_text(encoding='utf-8')
        for rx in REVOGADOS:
            if rx.search(texto):
                erros.append(f'termo de regra revogada ("{rx.pattern}") em README.md')
    return erros


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--raiz', default=str(RAIZ), help='raiz do pacote (padrão: a deste script)')
    args = p.parse_args(argv)
    erros, avisos = validar(Path(args.raiz).resolve())
    for e in erros:
        print(f'ERRO: {e}')
    for a in avisos:
        print(f'aviso: {a}')
    if erros:
        return 1
    print('pacote válido')
    return 0


if __name__ == '__main__':
    sys.exit(main())
