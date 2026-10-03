"""B01: o ciclo da etapa pelo `sc.py` (abrir, entregar, revisar --parecer, decidir). Repositório temporário e dados sintéticos.

Teste de fumaça: uma etapa trivial fecha só com os comandos que o README documenta.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, RAIZ, SKILLS, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
import sc_ciclo  # noqa: E402
import sc_status  # noqa: E402
from sc_registro import Registro  # noqa: E402

SC = NUCLEO / 'scripts' / 'sc.py'
PASSAGEM = NUCLEO / 'scripts' / 'sc_passagem.py'
LINT = SKILLS / 'sc-revisao' / 'scripts' / 'lint_parecer.py'
TESTE_PROJETO = 'python3 -B -m unittest discover -s tests'
# Sem configuração global de git: a falta de `user.name` precisa ser real nos testes.
AMBIENTE = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}

PERFIL = """# Perfil sintético

## Missão
Projeto sintético do ciclo.

## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Revisor Independente | Barbárvore | Claude Code (nuvem) | Anthropic | Modelo A | high | ativo | 2026-10-03 | subagente |
| Coordenador | Gandalf | Claude Code (nuvem) | Anthropic | Modelo B | high | ativo | 2026-10-03 | subagente |

## Modo emulação (Q147)
- **Emulação:** {EMUL}.
"""


def git(raiz, *args):
    return subprocess.run(['git', '-C', str(raiz), '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false',
                           *args], capture_output=True, text=True, check=True, env=AMBIENTE).stdout.strip()


def commit(raiz, msg):
    git(raiz, 'add', '-A')
    git(raiz, 'commit', '-q', '-m', msg)
    return git(raiz, 'rev-parse', 'HEAD')


def parecer_texto(head, base, veredito='aceitar', nivel='Nível C (mesmo fornecedor)', commit_revisado=None, etapa='soma'):
    return f"""## Parecer do Revisor Independente
- etapa: {etapa}
- entrega: commit {head[:7]}
- commit: {commit_revisado or head}
- base..head: {base[:7]}..{head[:7]}
- revisor: Barbárvore (Claude Code) · fornecedor: Anthropic · sessão: sess_sintetica
- modelo: modelo-sintetico · esforço: não exposto
- independência: {nivel}
- veredito: {veredito}
- data: 03/10/2026 10:00

### Independência
Não implementei nem corrigi nada desta entrega. Revisão interna, em emulação.

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| soma funciona | `python3 -m unittest discover -s tests` verde | executada |

### Achados
nenhum

### O que não verifiquei
- Nada além do critério acima.
"""


class Projeto:
    """Repositório temporário com `sociedade/`, um commit base e um commit de produto (a etapa trivial)."""

    def __init__(self, tmp, emulacao='sim'):
        self.raiz = Path(tmp)
        self.soc = self.raiz / 'sociedade'
        (self.soc / 'ordens').mkdir(parents=True)
        (self.raiz / 'tests').mkdir()
        git(self.raiz, 'init', '-q')
        (self.soc / 'perfil.md').write_text(PERFIL.replace('{EMUL}', emulacao), encoding='utf-8')
        (self.soc / 'ordens' / 'soma.md').write_text('# Ordem soma — somar dois números\n', encoding='utf-8')
        (self.raiz / 'app.py').write_text('x = 1\n', encoding='utf-8')
        (self.raiz / '.gitignore').write_text('sociedade/.registro.lock\n', encoding='utf-8')
        self.base = commit(self.raiz, 'base')
        (self.raiz / 'soma.py').write_text('def soma(a, b):\n    return a + b\n', encoding='utf-8')
        (self.raiz / 'tests' / 'test_soma.py').write_text(
            'import sys, unittest\nsys.path.insert(0, ".")\nfrom soma import soma\n\n\n'
            'class T(unittest.TestCase):\n    def test_soma(self):\n        self.assertEqual(soma(1, 2), 3)\n', encoding='utf-8')
        self.head = commit(self.raiz, 'feat: soma')

    def sc(self, *args, env=None):
        return rodar(SC, *args, '--pasta-sociedade', self.soc, cwd=self.raiz, env=env or AMBIENTE)

    def abrir(self, etapa='soma', base=None):
        return self.sc('abrir', f'--etapa={etapa}', '--ordem', self.soc / 'ordens' / 'soma.md', '--base', base or self.base)

    def entregar(self, etapa='soma'):
        return self.sc('entregar', '--etapa', etapa, '--base', self.base, '--pasta-projeto', self.raiz,
                       '--comando-teste', TESTE_PROJETO)

    def revisar(self, arquivo, head=None):
        return self.sc('revisar', '--etapa', 'soma', '--parecer', arquivo, '--head', head or self.head)

    def decidir(self, acao='aceitar', *extra):
        return self.sc('decidir', '--etapa', 'soma', acao, *extra)

    def registro(self):
        return Registro(self.soc)

    def eventos(self, tipo):
        return [e['dados'] for e in self.registro().eventos if e['tipo'] == tipo]


class Base(unittest.TestCase):
    emulacao = 'sim'

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        raiz = Path(self._tmp.name) / 'repo'
        raiz.mkdir()
        self.p = Projeto(raiz, emulacao=self.emulacao)

    def ok(self, res):
        self.assertEqual(res.returncode, 0, f'stdout: {res.stdout}\nstderr: {res.stderr}')
        return res

    def recusa(self, res, trecho):
        self.assertNotEqual(res.returncode, 0, f'deveria recusar: {res.stdout}')
        self.assertIn(trecho, res.stderr)
        return res

    def parecer(self, **kw):
        arq = Path(self._tmp.name) / 'parecer-rascunho.md'
        arq.write_text(parecer_texto(self.p.head, self.p.base, **kw), encoding='utf-8')
        return arq

    def fluxo_ate_o_parecer(self):
        self.ok(self.p.abrir())
        self.ok(self.p.entregar())
        self.ok(self.p.revisar(self.parecer()))


class TestFumaca(Base):
    """A etapa trivial fecha só com os comandos do README."""

    def test_comandos_do_readme_existem(self):
        readme = (RAIZ / 'README.md').read_text(encoding='utf-8')
        for trecho in ('sc.py abrir', 'sc.py entregar', 'sc.py revisar', '--parecer', 'sc.py decidir'):
            self.assertIn(trecho, readme, f'README sem "{trecho}"')
        citados = set(re.findall(r'sc\.py\s+([a-z]+)', readme))
        self.assertTrue({'abrir', 'entregar', 'revisar', 'decidir'} <= citados)
        for cmd in citados:
            r = rodar(SC, cmd, '-h')
            self.assertEqual(r.returncode, 0, f'o README cita sc.py {cmd}, que não existe: {r.stderr}')

    def test_etapa_trivial_fecha_so_com_os_comandos_do_readme(self):
        p = self.p
        self.ok(p.abrir())
        self.assertEqual([e['etapa_id'] for e in p.eventos('etapa_aberta')], ['soma'])
        self.ok(p.entregar())
        atestado = json.loads((p.soc / 'pareceres' / 'atestado-soma.json').read_text(encoding='utf-8'))
        self.assertEqual((atestado['status'], atestado['commit']), ('APROVADO', p.head))
        parecer = self.parecer()
        self.assertEqual(rodar(LINT, parecer).returncode, 0)
        self.ok(p.revisar(parecer))
        reg = p.eventos('parecer_registrado')
        self.assertEqual(reg[-1]['commit'], p.head)
        self.assertTrue((p.soc / 'pareceres' / 'parecer-soma.md').is_file())

        r = self.ok(p.decidir('aceitar', '--por', 'Odival Sintético', '--minutos', '7', '--intervencoes', '2'))
        self.assertIn('git push origin etapa/soma', r.stdout)  # não publica status: manda commitar sociedade/ e dar push
        dec = p.eventos('decisao_registrada')[-1]
        self.assertEqual((dec['acao'], dec['quem'], dec['commit']), ('aceitar', 'Odival Sintético', p.head))
        self.assertTrue(dec['aceite_em_emulacao'])
        self.assertEqual(dec['independencia'], 'não')
        etapa = p.registro().estado()['etapas']['soma']
        self.assertEqual(etapa['estado'], 'encerrada')
        self.assertEqual([d['acao'] for d in etapa['decisoes']], ['aceitar'])
        self.assertTrue(etapa['aceite_em_emulacao'])
        linha = [l for l in (p.soc / 'evolucao.md').read_text(encoding='utf-8').splitlines() if l.startswith('| soma |')]
        self.assertEqual(len(linha), 1)
        celulas = [c.strip() for c in linha[0].strip('|').split('|')]
        self.assertEqual((celulas[10], celulas[11]), ('2', '7'))  # intervenções e minutos informados
        self.assertEqual(celulas[7], 'n/d')  # sem log de sessão, comandos não medidos

        # O status `aceite` (job do Actions) aceita o registro gerado, com a cauda só de sociedade/.
        commit(p.raiz, 'sociedade(soma): decisão aceitar')
        topo = git(p.raiz, 'rev-parse', 'HEAD')
        r1 = sc_status.verificar_aceite(p.raiz, 'etapa/soma', topo)
        self.assertTrue(r1['ok'], r1['motivo'])
        self.assertEqual(r1['commit'], p.head)
        self.assertTrue(sc_status.verificar_portao(p.raiz, 'etapa/soma', topo)['ok'])

    def test_aceite_ligado_ao_registro_pelo_verificador_com_registro_gerado(self):
        self.fluxo_ate_o_parecer()
        self.ok(self.p.decidir('aceitar', '--por', 'Odival Sintético'))
        r = sc_status.verificar_aceite(self.p.raiz, 'etapa/soma', self.p.head, registro=self.p.registro().carregar_dados())
        self.assertTrue(r['ok'], r['motivo'])

    def test_sem_emulacao_a_marca_nao_sai_e_mesmo_fornecedor_e_recusado(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t) / 'r'
            raiz.mkdir()
            p = Projeto(raiz, emulacao='não')
            self.ok(p.abrir())
            arq = Path(t) / 'parecer.md'
            arq.write_text(parecer_texto(p.head, p.base, nivel='Nível A (fornecedor diferente)'), encoding='utf-8')
            self.recusa(p.revisar(arq), 'Independência violada')

    def test_sem_emulacao_o_aceite_de_parecer_nivel_a_mantem_independencia_sim(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t) / 'r'
            raiz.mkdir()
            p = Projeto(raiz, emulacao='não')
            self.ok(p.abrir())
            self.ok(p.entregar())
            arq = Path(t) / 'parecer.md'
            texto = parecer_texto(p.head, p.base, nivel='Nível A (fornecedor diferente)')
            arq.write_text(texto.replace('Barbárvore (Claude Code) · fornecedor: Anthropic',
                                         'Revisor Sintético (Codex) · fornecedor: OpenAI'), encoding='utf-8')
            self.ok(p.sc('revisar', '--etapa', 'soma', '--parecer', arq, '--head', p.head, '--implementador', 'Elrond:Anthropic'))
            self.ok(p.decidir('aceitar', '--por', 'Odival Sintético'))
            dec = p.eventos('decisao_registrada')[-1]
            self.assertFalse(dec.get('aceite_em_emulacao'))
            self.assertNotEqual(dec.get('independencia'), 'não')
            etapa = p.registro().estado()['etapas']['soma']
            self.assertEqual(etapa['independencia'], 'sim')


class TestDecidirRecusa(Base):
    def test_sem_atestado(self):
        self.ok(self.p.abrir())
        self.recusa(self.p.decidir('aceitar', '--por', 'Odival Sintético'), 'sem atestado')
        self.assertEqual(self.p.registro().estado()['etapa_atual']['id'], 'soma')

    def test_sem_parecer(self):
        self.ok(self.p.abrir())
        self.ok(self.p.entregar())
        self.recusa(self.p.decidir('aceitar', '--por', 'Odival Sintético'), 'sem parecer')

    def test_sem_por_e_sem_git_user_name(self):
        self.fluxo_ate_o_parecer()
        self.recusa(self.p.decidir('aceitar'), 'Não há nome padrão')
        self.assertEqual(self.p.eventos('decisao_registrada'), [])

    def test_sem_por_usa_o_git_config(self):
        self.fluxo_ate_o_parecer()
        git(self.p.raiz, 'config', 'user.name', 'Pessoa Configurada')
        self.ok(self.p.decidir('aceitar'))
        self.assertEqual(self.p.eventos('decisao_registrada')[-1]['quem'], 'Pessoa Configurada')

    def test_decisor_nao_pode_ser_agente_nem_claude(self):
        """F6 (achado 5): `--por` e `git config user.name` com nome de agente do perfil ou "Claude" são recusados."""
        self.fluxo_ate_o_parecer()
        nomes = ('Gandalf', 'gandalf', 'Círdan', 'cirdan', 'Barbárvore', 'barbarvore2', 'Aragorn', 'Elrond',
                 'Galadriel', 'Legolas', 'Jules', 'jules_agent', 'Claude', 'CLAUDE', 'Claude Code', 'claudé')
        for nome in nomes:
            with self.subTest(por=nome):
                r = self.recusa(self.p.decidir('aceitar', '--por', nome), 'nome de agente')
                self.assertIn('--por <nome da pessoa>', r.stderr)
        git(self.p.raiz, 'config', 'user.name', 'Elrond')
        self.recusa(self.p.decidir('aceitar'), '--por <nome da pessoa>')
        self.assertEqual(self.p.eventos('decisao_registrada'), [])
        self.assertEqual(self.p.registro().estado()['etapas']['soma']['estado'], 'aberta')

    def test_decisor_agente_recusado_tambem_em_corrigir_rejeitar_e_sem_aceite(self):
        self.ok(self.p.abrir())
        for acao in ('corrigir', 'rejeitar', 'sem-aceite'):
            with self.subTest(acao=acao):
                self.recusa(self.p.decidir(acao, '--por', 'Gandalf', '--motivo', 'x'), 'nome de agente')
        self.assertEqual(self.p.eventos('decisao_registrada'), [])

    def test_nomes_de_pessoa_parecidos_nao_sao_recusados(self):
        self.ok(self.p.abrir())
        self.ok(self.p.decidir('corrigir', '--por', 'Gandalfo Pereira', '--motivo', 'x'))
        self.assertEqual(self.p.eventos('decisao_registrada')[-1]['quem'], 'Gandalfo Pereira')

    def test_variante_da_tabela_de_identificadores_do_perfil_e_recusada(self):
        perfil = self.p.soc / 'perfil.md'
        perfil.write_text(perfil.read_text(encoding='utf-8') + (
            '\n## Identificadores de agente\n\n| Identificador | Papel | Nome | Variantes reconhecidas |\n|---|---|---|---|\n'
            '| fulano | Outro | Fulano | fulano, fulano_bot |\n'), encoding='utf-8')
        self.ok(self.p.abrir())
        self.recusa(self.p.decidir('corrigir', '--por', 'Fulano_Bot'), 'nome de agente')
        self.ok(self.p.decidir('corrigir', '--por', 'Odival Sintético'))

    def test_perfil_ilegivel_usa_a_lista_minima_embutida(self):
        from sc_perfil import nome_de_agente
        for nome in ('Gandalf', 'Claude Code', 'Jules', 'Barbárvore'):
            self.assertTrue(nome_de_agente(nome, None), nome)
        self.assertFalse(nome_de_agente('Odival Sintético', None))
        self.assertFalse(nome_de_agente('', None))

    def test_mensagem_final_manda_commitar_no_ramo_da_etapa(self):
        self.fluxo_ate_o_parecer()
        r = self.ok(self.p.decidir('aceitar', '--por', 'Odival Sintético'))
        self.assertIn('git push origin etapa/soma', r.stdout)
        self.assertIn('ramo etapa/soma, no worktree dessa etapa', r.stdout)

    def test_atestado_reprovado_nao_aceita(self):
        self.fluxo_ate_o_parecer()
        arq = self.p.soc / 'pareceres' / 'atestado-soma.json'
        dados = json.loads(arq.read_text(encoding='utf-8'))
        dados['status'] = 'REPROVADO'
        arq.write_text(json.dumps(dados), encoding='utf-8')
        self.recusa(self.p.decidir('aceitar', '--por', 'Odival Sintético'), 'atestado não aprovado')

    def test_parecer_de_outro_sha_que_o_atestado(self):
        self.ok(self.p.abrir())
        (self.p.raiz / 'extra.py').write_text('y = 2\n', encoding='utf-8')
        git(self.p.raiz, 'add', 'extra.py')
        git(self.p.raiz, 'commit', '-q', '-m', 'feat: extra')
        novo = git(self.p.raiz, 'rev-parse', 'HEAD')
        self.ok(self.p.entregar())  # atestado do commit novo
        self.ok(self.p.revisar(self.parecer(), head=self.p.head))  # parecer do commit antigo
        self.recusa(self.p.decidir('aceitar', '--por', 'Odival Sintético'), 'não são do mesmo SHA')
        self.assertNotEqual(novo, self.p.head)

    def test_parecer_nao_aceitar_nao_deixa_aceitar(self):
        self.ok(self.p.abrir())
        self.ok(self.p.entregar())
        self.ok(self.p.revisar(self.parecer(veredito='não aceitar')))
        self.recusa(self.p.decidir('aceitar', '--por', 'Odival Sintético'), 'não aceitar')

    def test_etapa_inexistente_ou_encerrada(self):
        self.fluxo_ate_o_parecer()
        self.ok(self.p.decidir('aceitar', '--por', 'Odival Sintético'))
        self.recusa(self.p.decidir('aceitar', '--por', 'Odival Sintético'), 'não está aberta')


class TestDesfechos(Base):
    def test_corrigir_deixa_a_etapa_aberta_e_a_decisao_legivel(self):
        self.ok(self.p.abrir())
        self.ok(self.p.decidir('corrigir', '--por', 'Odival Sintético', '--motivo', 'ajustar a soma'))
        etapa = self.p.registro().estado()['etapas']['soma']
        self.assertEqual(etapa['estado'], 'aberta')
        self.assertEqual([(d['acao'], d['quem'], d['referencia']) for d in etapa['decisoes']],
                         [('corrigir', 'Odival Sintético', 'ajustar a soma')])

    def test_rejeitar_e_sem_aceite_encerram_sem_publicar(self):
        for acao in ('rejeitar', 'sem-aceite'):
            with self.subTest(acao=acao), tempfile.TemporaryDirectory() as t:
                raiz = Path(t) / 'r'
                raiz.mkdir()
                p = Projeto(raiz)
                self.ok(p.abrir())
                self.ok(p.decidir(acao, '--por', 'Odival Sintético', '--motivo', 'fora do escopo'))
                etapa = p.registro().estado()['etapas']['soma']
                self.assertEqual((etapa['estado'], etapa['desfecho'], etapa['elegivel_publicacao']), ('encerrada', acao, False))
                self.assertEqual(etapa['decisoes'][-1]['acao'], acao)
                self.assertFalse((p.soc / 'evolucao.md').exists())
                r = sc_status.verificar_aceite(p.raiz, 'etapa/soma', p.head, registro=p.registro().carregar_dados())
                self.assertFalse(r['ok'])  # a decisão final não é "aceitar": o status fica vermelho

    def test_acao_invalida(self):
        self.ok(self.p.abrir())
        self.assertNotEqual(self.p.sc('decidir', '--etapa', 'soma', 'talvez', '--por', 'X').returncode, 0)


class TestAbrir(Base):
    def test_ordem_inexistente(self):
        r = self.p.sc('abrir', '--etapa', 'soma', '--ordem', self.p.soc / 'ordens' / 'nao-existe.md', '--base', self.p.base)
        self.recusa(r, 'ordem não encontrada')
        self.assertFalse((self.p.soc / 'registro.json').exists())

    def test_base_que_nao_resolve(self):
        self.recusa(self.p.abrir(base='0123456789abcdef'), 'não resolve a um commit')

    def test_etapa_ja_aberta(self):
        self.ok(self.p.abrir())
        self.recusa(self.p.abrir(), 'já foi aberta')
        self.assertEqual(len(self.p.eventos('etapa_aberta')), 1)

    def test_outra_etapa_ativa_bloqueia(self):
        self.ok(self.p.abrir())
        r = self.p.sc('abrir', '--etapa', 'outra', '--ordem', self.p.soc / 'ordens' / 'soma.md', '--base', self.p.base)
        self.recusa(r, 'já existe etapa ativa')

    def test_registra_base_ordem_e_criterio(self):
        self.ok(self.p.abrir())
        ab = self.p.eventos('etapa_aberta')[0]
        self.assertEqual(ab['base_efetiva'], self.p.base)
        self.assertEqual(ab['criterios'], ['portao'])
        self.assertTrue(ab['autorizacao_ref'].startswith('ordem_sha256:'))


class TestRevisarParecer(Base):
    def test_sem_parecer_continua_preparando_a_copia(self):
        destino = Path(self._tmp.name) / 'copia'
        self.ok(self.p.sc('revisar', '--etapa', 'soma', '--base', self.p.base, '--head', self.p.head, '--destino', destino))
        self.assertTrue((destino / 'ORDEM-REVISAO.md').is_file())
        self.assertFalse((self.p.soc / 'registro.json').exists())

    def test_parecer_invalido_e_recusado(self):
        self.ok(self.p.abrir())
        arq = self.parecer()
        arq.write_text(arq.read_text(encoding='utf-8').replace('nenhum', '- [grave] algo'), encoding='utf-8')
        self.recusa(self.p.revisar(arq), 'parecer inválido')
        self.assertEqual(self.p.eventos('parecer_registrado'), [])

    def test_commit_diferente_do_head_revisado(self):
        self.ok(self.p.abrir())
        arq = self.parecer(commit_revisado=self.p.base)
        r = self.p.revisar(arq)  # o lint recusa antes: commit difere do head de base..head
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.p.eventos('parecer_registrado'), [])

    def test_parecer_de_outro_commit_que_o_head_informado(self):
        self.ok(self.p.abrir())
        self.recusa(self.p.revisar(self.parecer(), head=self.p.base), 'parecer de outro commit')

    def test_sem_commit_no_parecer(self):
        self.ok(self.p.abrir())
        arq = self.parecer()
        arq.write_text(re.sub(r'^- commit:.*\n', '', arq.read_text(encoding='utf-8'), flags=re.M), encoding='utf-8')
        self.recusa(self.p.revisar(arq), 'commit')

    def test_marca_de_emulacao_sai_sozinha(self):
        self.ok(self.p.abrir())
        arq = self.parecer(nivel='Nível A (fornecedor diferente)')
        self.ok(self.p.revisar(arq))
        ev = self.p.eventos('parecer_registrado')[-1]
        self.assertTrue(ev['aceite_em_emulacao'])
        self.assertEqual((ev['independencia'], ev['commit']), ('não', self.p.head))

    def test_exige_etapa_aberta(self):
        self.recusa(self.p.revisar(self.parecer()), 'registro ilegível ou ausente')

    def test_parecer_de_outra_etapa_e_recusado_sem_gravar(self):
        """F6 (achado 8): o campo `etapa:` do parecer tem de ser o de `--etapa`."""
        self.ok(self.p.abrir())
        self.ok(self.p.entregar())
        self.recusa(self.p.revisar(self.parecer(etapa='outra-etapa')), 'parecer de outra etapa')
        self.assertEqual(self.p.eventos('parecer_registrado'), [])
        self.assertFalse((self.p.soc / 'pareceres' / 'parecer-soma.md').exists())

    def test_parecer_com_base_diferente_da_base_da_etapa_e_recusado(self):
        self.ok(self.p.abrir())
        self.ok(self.p.entregar())
        arq = Path(self._tmp.name) / 'parecer-base.md'
        arq.write_text(parecer_texto(self.p.head, self.p.head), encoding='utf-8')  # base..head com base errada
        self.recusa(self.p.revisar(arq), 'não é a base da etapa')
        self.assertEqual(self.p.eventos('parecer_registrado'), [])


class TestTemplateDoParecer(Base):
    """Item 9: o parecer gerado por `sc_passagem exportar-revisao` traz `- commit:` e passa no lint depois de preenchido."""

    def test_template_passa_no_lint(self):
        self.ok(self.p.abrir())
        saida = Path(self._tmp.name) / 'pacote.md'
        self.ok(rodar(PASSAGEM, 'exportar-revisao', '--pasta-projeto', self.p.raiz, '--pasta-sociedade', self.p.soc,
                      '--etapa', 'soma', '--base', self.p.base, '--head', self.p.head, '--revisor', 'Barbárvore',
                      '--fornecedor-revisor', 'Anthropic', '--saida', saida))
        pacote = saida.read_text(encoding='utf-8')
        modelo = pacote.split('```markdown\n', 1)[1].split('```', 1)[0]
        self.assertIn(f'- commit: {self.p.head}', modelo)
        self.assertEqual(sc_ciclo.lint_parecer.commit_revisado(modelo), self.p.head)
        preenchido = (modelo.replace('[aceitar | nao_aceitar]', 'aceitar').replace('<id>', 'sess_sintetica')
                      .replace('[comando executado e saída]', '`python3 -m unittest` verde')
                      .replace('[executada/lida/não verificada]', 'executada')
                      .replace('- [bloqueador|relevante|opcional] TITULO\n  Condição: ...\n  Esperado: ...\n  Evidência: ...', 'nenhum')
                      .replace('[Resumo sucinto da avaliação]', 'Resumo.')
                      .replace('- [item não verificado, ou "nada"]', '- nada'))
        arq = Path(self._tmp.name) / 'gerado.md'
        arq.write_text(preenchido, encoding='utf-8')
        r = rodar(LINT, arq)
        self.assertEqual(r.returncode, 0, r.stdout)


class TestLigacaoDaSessao(unittest.TestCase):
    """Item 5: `sc.py sessao claude --sessao --projetos` e o `conferir` aceitam as entregas do Claude, ponta a ponta."""

    def setUp(self):
        import test_sessao_claude as ts
        self.ts = ts
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.projetos = Path(self._tmp.name) / 'projetos'
        pasta = self.projetos / ts.PROJ
        ts.jsonl(pasta / 's1.jsonl', [ts.ordem(), ts.chamada('t1'), ts.resultado('t1'), ts.chamada('t2'), ts.resultado('t2')])
        ts.jsonl(pasta / 's1' / 'subagents' / 'agent-aaa.jsonl', [ts.ordem('ordem'), ts.passo()])
        ts.jsonl(pasta / 's1' / 'subagents' / 'agent-bbb.jsonl', [ts.ordem('ordem'), ts.passo()])

    def test_cmd_sessao_repassa_sessao_e_projetos(self):
        r = rodar(SC, 'sessao', 'claude', '--sessao', 's1', '--projetos', self.projetos, '--json')
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads(r.stdout)
        self.assertEqual((m['delegacoes_total'], m['conversa_nova']), (2, True))

    def test_cmd_sessao_com_sessao_inexistente_falha(self):
        r = rodar(SC, 'sessao', 'claude', '--sessao', 'nao-existe', '--projetos', self.projetos)
        self.assertNotEqual(r.returncode, 0)

    def test_conferir_aceita_delegacoes_e_conversa_nova_do_claude(self):
        raiz = Path(self._tmp.name) / 'repo'
        raiz.mkdir()
        git(raiz, 'init', '-q')
        ordem = raiz / 'ordem.md'
        ordem.write_text('# Ordem\n\n```entregas\nE1 | delegacoes | claude | s1 | 2\nE2 | conversa_nova | claude | aaa\n'
                         'E3 | delegacoes | claude | s1 | 3\n```\n', encoding='utf-8')
        env = {**AMBIENTE, 'SC_CLAUDE_PROJETOS': str(self.projetos)}
        r = rodar(SC, 'conferir', '--ordem', ordem, '--raiz', raiz, '--json', env=env)
        itens = {i['id']: i for i in json.loads(r.stdout)['itens']}
        self.assertEqual(itens['E1']['estado'], 'feito', r.stdout)
        self.assertEqual(itens['E2']['estado'], 'feito', r.stdout)
        self.assertEqual(itens['E3']['estado'], 'não feito', r.stdout)  # mínimo 3, só 2 delegações


if __name__ == '__main__':
    unittest.main()
