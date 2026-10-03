"""Apoio das sondas adversariais (B09): repositório git temporário e dados sintéticos.

Copiado de `tests/test_ciclo.py` (classe `Projeto`) de propósito: as sondas não podem mudar junto com um teste
que elas vigiam. Nada aqui é teste (o nome começa com `_`); os arquivos `test_dg0N_*.py` importam este módulo.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTES = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TESTES))
from util import NUCLEO, SKILLS, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
import sc_ciclo  # noqa: E402,F401
import sc_status  # noqa: E402,F401
from sc_registro import Registro  # noqa: E402

SC = NUCLEO / 'scripts' / 'sc.py'
SC_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'
LINT = SKILLS / 'sc-revisao' / 'scripts' / 'lint_parecer.py'
MODELO_PARECER = SKILLS / 'sc-revisao' / 'assets' / 'parecer-modelo.md'
TESTE_PROJETO = 'python3 -B -m unittest discover -s tests'
# Sem configuração global de git: a falta de `user.name` precisa ser real nas sondas.
AMBIENTE = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}

PERFIL = """# Perfil sintético

## Missão
Projeto sintético das sondas.
{EXTRA_MISSAO}
## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | Claude Code (nuvem) | Anthropic | Modelo A | high | ativo | 2026-10-03 | sessão principal |
| Revisor Independente | Barbárvore | Claude Code (nuvem) | Anthropic | Modelo A | high | ativo | 2026-10-03 | subagente |
| Coordenador | Gandalf | Claude Code (nuvem) | Anthropic | Modelo B | high | ativo | 2026-10-03 | subagente |
{MODO}"""

MODO_EMULACAO = """
## Modo emulação (Q147)
- **Emulação:** {VALOR}.
"""


def git(raiz, *args):
    return subprocess.run(['git', '-C', str(raiz), '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false',
                           *args], capture_output=True, text=True, check=True, env=AMBIENTE).stdout.strip()


def commit(raiz, msg):
    git(raiz, 'add', '-A')
    git(raiz, 'commit', '-q', '-m', msg)
    return git(raiz, 'rev-parse', 'HEAD')


def texto_perfil(emulacao='sim', modo=None, extra_missao=''):
    """`emulacao`: 'sim', 'não' ou None (sem a seção). `modo` troca a seção inteira (casos de falsificação)."""
    if modo is None:
        modo = MODO_EMULACAO.replace('{VALOR}', emulacao) if emulacao is not None else ''
    return PERFIL.replace('{EXTRA_MISSAO}', extra_missao).replace('{MODO}', modo)


def parecer_texto(head, base, veredito='aceitar', nivel='Nível C (mesmo fornecedor)', etapa='soma',
                  revisor='Barbárvore (Claude Code)', fornecedor='Anthropic'):
    return f"""## Parecer do Revisor Independente
- etapa: {etapa}
- entrega: commit {head[:7]}
- commit: {head}
- base..head: {base[:7]}..{head[:7]}
- revisor: {revisor} · fornecedor: {fornecedor} · sessão: sess_sintetica
- modelo: modelo-sintetico · esforço: não exposto
- independência: {nivel}
- veredito: {veredito}
- data: 03/10/2026 10:00

### Independência
Não implementei nem corrigi nada desta entrega. Revisão sintética da sonda.

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| soma funciona | `python3 -m unittest discover -s tests` verde | executada |

### Achados
nenhum

### O que não verifiquei
- Nada além do critério acima.
"""


def exigir_ok(res):
    if res.returncode != 0:
        raise AssertionError(f'comando falhou ({res.returncode})\nstdout: {res.stdout}\nstderr: {res.stderr}')
    return res


class Projeto:
    """Repositório temporário com `sociedade/`, um commit base e um commit de produto (a etapa trivial)."""

    def __init__(self, tmp, emulacao='sim', perfil=None):
        self.tmp = Path(tmp)
        self.raiz = self.tmp / 'repo'
        self.raiz.mkdir()
        self.soc = self.raiz / 'sociedade'
        (self.soc / 'ordens').mkdir(parents=True)
        (self.raiz / 'tests').mkdir()
        git(self.raiz, 'init', '-q')
        (self.soc / 'perfil.md').write_text(perfil if perfil is not None else texto_perfil(emulacao), encoding='utf-8')
        (self.soc / 'ordens' / 'soma.md').write_text('# Ordem soma — somar dois números\n', encoding='utf-8')
        (self.raiz / 'app.py').write_text('x = 1\n', encoding='utf-8')
        (self.raiz / '.gitignore').write_text('sociedade/.registro.lock\n', encoding='utf-8')
        self.base = commit(self.raiz, 'base')
        (self.raiz / 'soma.py').write_text('def soma(a, b):\n    return a + b\n', encoding='utf-8')
        (self.raiz / 'tests' / 'test_soma.py').write_text(
            'import sys, unittest\nsys.path.insert(0, ".")\nfrom soma import soma\n\n\n'
            'class T(unittest.TestCase):\n    def test_soma(self):\n        self.assertEqual(soma(1, 2), 3)\n', encoding='utf-8')
        self.head = commit(self.raiz, 'feat: soma')

    # ---- comandos documentados ----
    def sc(self, *args, env=None):
        return rodar(SC, *args, '--pasta-sociedade', self.soc, cwd=self.raiz, env=env or AMBIENTE)

    def rodada(self, *args):
        """Comando legado do `sc_rodada` (sempre com --aplicar), para as sondas do que ainda é declarativo."""
        return rodar(SC_RODADA, *args, '--aplicar', '--pasta', self.soc, cwd=self.raiz, env=AMBIENTE)

    def abrir(self, etapa='soma', base=None):
        return self.sc('abrir', f'--etapa={etapa}', '--ordem', self.soc / 'ordens' / 'soma.md', '--base', base or self.base)

    def entregar(self, etapa='soma'):
        return self.sc('entregar', '--etapa', etapa, '--base', self.base, '--pasta-projeto', self.raiz,
                       '--comando-teste', TESTE_PROJETO)

    def revisar(self, arquivo, head=None, *extra):
        return self.sc('revisar', '--etapa', 'soma', '--parecer', arquivo, '--head', head or self.head, *extra)

    def decidir(self, acao='aceitar', *extra):
        return self.sc('decidir', '--etapa', 'soma', acao, *extra)

    def estado_md(self):
        return self.sc('estado', '--imprimir', '--sem-html')

    # ---- leitura do registro ----
    def registro(self):
        return Registro(self.soc)

    def eventos(self, tipo):
        return [e['dados'] for e in self.registro().eventos if e['tipo'] == tipo]

    def etapa(self, etapa='soma'):
        return self.registro().estado()['etapas'][etapa]

    def escrever_parecer(self, nome='parecer-rascunho.md', head=None, **kw):
        arq = self.tmp / nome
        arq.write_text(parecer_texto(head or self.head, self.base, **kw), encoding='utf-8')
        return arq

    def fluxo_ate_o_parecer(self, **kw):
        """abrir, entregar e revisar --parecer: só comandos documentados."""
        exigir_ok(self.abrir())
        exigir_ok(self.entregar())
        exigir_ok(self.revisar(self.escrever_parecer(**kw)))

    def atestado(self, etapa='soma'):
        return self.soc / 'pareceres' / f'atestado-{etapa}.json'

    def commitar_governanca(self, msg='sociedade(soma): governança'):
        """Commit que toca só `sociedade/` (é o commit que o `decidir` manda fazer)."""
        git(self.raiz, 'add', 'sociedade')
        git(self.raiz, 'commit', '-q', '-m', msg)
        return git(self.raiz, 'rev-parse', 'HEAD')

    def commitar_produto(self, nome='extra.py', conteudo='y = 2\n', msg='feat: extra'):
        (self.raiz / nome).write_text(conteudo, encoding='utf-8')
        git(self.raiz, 'add', '--', nome)  # só o arquivo de produto: nada de `sociedade/` num commit do candidato
        git(self.raiz, 'commit', '-q', '-m', msg)
        return git(self.raiz, 'rev-parse', 'HEAD')

    def topo(self):
        return git(self.raiz, 'rev-parse', 'HEAD')


class Base(unittest.TestCase):
    emulacao = 'sim'
    perfil = None

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.p = Projeto(self._tmp.name, emulacao=self.emulacao, perfil=self.perfil)

    def ok(self, res):
        return exigir_ok(res)

    def recusa(self, res, trecho=None):
        self.assertNotEqual(res.returncode, 0, f'deveria recusar; stdout: {res.stdout}')
        if trecho is not None:
            self.assertIn(trecho, res.stderr)
        return res

    def sem_decisao(self):
        """A recusa não deixou rastro: nenhuma decisão registrada e a etapa segue aberta."""
        self.assertEqual(self.p.eventos('decisao_registrada'), [])
        self.assertEqual(self.p.etapa()['estado'], 'aberta')

    def novo_projeto(self, **kw):
        """Segundo repositório temporário na mesma sonda (outra chave de emulação, outro perfil)."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Projeto(tmp.name, **kw)


def preencher_modelo_de_parecer(head, base, etapa='soma', nivel='Nível C (mesmo fornecedor)', veredito='aceitar'):
    """Preenche `sc-revisao/assets/parecer-modelo.md` com dados sintéticos, só trocando os marcadores.

    Falha se sobrar algum marcador `<...>`: o modelo não pode ter campo que a sonda não saiba preencher."""
    texto = MODELO_PARECER.read_text(encoding='utf-8')
    valores = {
        '<ID>': etapa,
        '<commit congelado ou PR>': f'commit {head[:7]}',
        '<SHA do commit revisado, 7 a 40 hexadecimais, igual ao head de base..head>': head,
        '<sha7>..<sha7>': f'{base[:7]}..{head[:7]}',
        '<papel e ferramenta> · fornecedor: <fornecedor> · sessão: <id>':
            'Barbárvore (Claude Code) · fornecedor: Anthropic · sessão: sess_sintetica',
        '<modelo configurado> · esforço: <esforço configurado|não exposto>': 'modelo-sintetico · esforço: não exposto',
        '<Nível A (fornecedor diferente), Nível B (sessão distinta) ou Nível C (mesmo fornecedor)>': nivel,
        '<aceitar, aceitar com ressalvas ou não aceitar>': veredito,
        '<dd/mm/aaaa hh:mm>': '03/10/2026 10:00',
        'Implementação feita pelo fornecedor <fornecedor>; minha revisão é de fornecedor <diferente|igual: revisão interna>.':
            'Implementação feita pelo fornecedor Anthropic; minha revisão é de fornecedor igual: revisão interna.',
        '<defeito ou necessidade, com referência do plano>': 'somar dois números (ordem soma)',
        '<comandos, opções, funções públicas>': '`soma(a, b)`',
        '<quais e quem muda>': 'nenhum estado persistente',
        '| <critério> | <comando executado e resultado, ou arquivo e trecho lido> | <executada, lida ou não verificada> |':
            '| soma funciona | `python3 -m unittest discover -s tests` verde | executada |',
        '| <critério> | <sonda, "lida" ou "n/a (motivo)"> | | | | | | | |':
            '| soma funciona | S1 | S2 | lida | n/a (sem escape) | S3 | n/a (sem concorrência) | lida | S4 |',
        '- [<severidade>] <lente> · <descrição> (<arquivo:linha>)': 'nenhum',
        '- <item>': '- Nada além do critério acima.',
    }
    for chave in sorted(valores, key=len, reverse=True):
        texto = texto.replace(chave, valores[chave])
    sobras = sorted(set(re.findall(r'<[^<>\n]+>', texto)))
    if sobras:
        raise AssertionError(f'marcadores do modelo sem valor sintético na sonda: {sobras}')
    return texto


def atestado_a_mao(commit_sha, etapa='soma'):
    """Atestado escrito à mão, com todos os campos que o `decidir` e a conferência leem e nenhum teste rodado."""
    return {'tipo': 'atestado_pre_devolucao', 'etapa_id': etapa, 'status': 'APROVADO', 'commit': commit_sha,
            'total_arquivos_inspecionados': 3, 'verificacoes': {}, 'erros': []}


def eventos_do_arquivo(soc):
    return [e['tipo'] for e in json.loads((Path(soc) / 'registro.json').read_text(encoding='utf-8'))['eventos']]
