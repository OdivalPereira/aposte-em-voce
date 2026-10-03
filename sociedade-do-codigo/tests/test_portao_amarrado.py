"""B11, B11c: o portão amarrado ao perfil (`sc.py entregar`), por área. Repositório temporário e dados sintéticos.

Cobre a leitura da tabela "Portão por área", a área de um caminho (prefixo mais longo, `.github/` nas duas), a contagem
de testes (unittest, Vitest, Playwright), a árvore suja, o timeout e o conteúdo do atestado. As sondas adversariais
(DG-03, DG-09, DG-11) ficam em `tests/adversarial/`.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, RAIZ, SKILLS, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
import sc_perfil  # noqa: E402
import sc_pre_devolucao  # noqa: E402

SC = NUCLEO / 'scripts' / 'sc.py'
AMBIENTE = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
UNITTEST = 'python3 -B -m unittest discover -s tests'

PERFIL = """# Perfil sintético

## Missão
Projeto sintético do portão por área.

## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Coordenador | Gandalf | Claude Code (nuvem) | Anthropic | Modelo B | high | ativo | 2026-10-03 | subagente |

## Portão por área
*Lida pelo `sc.py entregar`.*

| Área | Pasta | Testes | Timeout (s) | Prefixos |
|---|---|---|---|---|
| app | `.` | `{APP}` | {TIMEOUT_APP} | `*` (tudo fora de `pacote/`, `sociedade/` e `docs/`) |
| pacote | `pacote` | `{PACOTE}` | 120 | `pacote/` |

## Estado
- Resumo: `sociedade/estado.md`
"""


def git(raiz, *args):
    return subprocess.run(['git', '-C', str(raiz), '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false',
                           *args], capture_output=True, text=True, check=True, env=AMBIENTE).stdout.strip()


def commit(raiz, msg):
    git(raiz, 'add', '-A')
    git(raiz, 'commit', '-q', '-m', msg)
    return git(raiz, 'rev-parse', 'HEAD')


def teste_py(nome='T', corpo='def test_a(self):\n        self.assertTrue(True)'):
    return f'import unittest\n\n\nclass {nome}(unittest.TestCase):\n    {corpo}\n'


class Repo:
    """Dois projetos num repositório: `app` na raiz (coringa) e `pacote/`, cada um com 1 teste que roda."""

    def __init__(self, tmp, app=UNITTEST, pacote=UNITTEST, timeout_app=120):
        self.raiz = Path(tmp) / 'repo'
        self.soc = self.raiz / 'sociedade'
        (self.soc / 'pareceres').mkdir(parents=True)
        (self.raiz / 'tests').mkdir()
        (self.raiz / 'pacote' / 'tests').mkdir(parents=True)
        (self.raiz / 'docs').mkdir()
        git(self.raiz, 'init', '-q')
        self.perfil = self.soc / 'perfil.md'
        self.perfil.write_text(PERFIL.replace('{APP}', app).replace('{PACOTE}', pacote)
                               .replace('{TIMEOUT_APP}', str(timeout_app)), encoding='utf-8')
        (self.raiz / '.gitignore').write_text('node_modules/\ndist/\nsociedade/.registro.lock\n', encoding='utf-8')
        (self.raiz / 'tests' / 'test_app.py').write_text(teste_py('App'), encoding='utf-8')
        (self.raiz / 'pacote' / 'tests' / 'test_pacote.py').write_text(teste_py('Pacote'), encoding='utf-8')
        (self.raiz / 'docs' / 'nota.md').write_text('# Nota\n', encoding='utf-8')
        self.base = commit(self.raiz, 'base')

    def entregar(self, *extra):
        return rodar(SC, 'entregar', '--etapa', 'a1', '--base', self.base, '--pasta-projeto', self.raiz,
                     '--pasta-sociedade', self.soc, *extra, cwd=self.raiz, env=AMBIENTE)

    def atestado(self):
        return json.loads((self.soc / 'pareceres' / 'atestado-a1.json').read_text(encoding='utf-8'))

    def escrever(self, rel, texto='x = 1\n'):
        alvo = self.raiz / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding='utf-8')
        return alvo

    def commitar(self, rel, texto='x = 1\n'):
        self.escrever(rel, texto)
        return commit(self.raiz, f'feat: {rel}')


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def repo(self, **kw):
        return Repo(self.tmp, **kw)

    def nomes(self, at):
        return [a['area'] for a in at['portao']['areas']]


class TestLeituraDoPerfil(unittest.TestCase):
    def tabela(self, linhas):
        return ('# P\n\n## Portão por área\n| Área | Pasta | Testes | Timeout (s) | Prefixos |\n|---|---|---|---|---|\n'
                + '\n'.join(linhas) + '\n\n## Estado\n- x\n')

    def test_le_a_tabela_e_ignora_o_comentario_dos_prefixos(self):
        areas = sc_perfil.ler_portao_por_area(PERFIL.replace('{APP}', 'npm test').replace('{PACOTE}', UNITTEST)
                                              .replace('{TIMEOUT_APP}', '900'))
        self.assertEqual([a['nome'] for a in areas], ['app', 'pacote'])
        app, pacote = areas
        self.assertEqual((app['pasta'], app['comando'], app['timeout'], app['prefixos'], app['coringa']),
                         ('.', 'npm test', 900, [], True))
        self.assertEqual((pacote['pasta'], pacote['comando'], pacote['timeout'], pacote['prefixos'], pacote['coringa']),
                         ('pacote', UNITTEST, 120, ['pacote'], False))

    def test_le_o_perfil_do_projeto_real_sem_tratar_o_comentario_como_prefixo(self):
        texto = self.tabela(['| app | `.` | `npm test` | 900 | `*` (tudo fora de `sociedade-do-codigo/`, `sociedade/` e `docs/`) |',
                             '| pacote | `sociedade-do-codigo` | `python3 -B -m unittest discover -s tests` | 600 | `sociedade-do-codigo/` |'])
        areas = sc_perfil.ler_portao_por_area(texto)
        self.assertEqual(areas[0]['prefixos'], [])
        self.assertEqual(areas[1]['prefixos'], ['sociedade-do-codigo'])

    def test_recusa_com_mensagem_clara(self):
        casos = {
            'sem a seção': ('# P\n\n## Comandos\n- Testes: `npm test`\n', 'não tem a seção'),
            'sem tabela': ('# P\n\n## Portão por área\nsó texto\n', 'não tem tabela'),
            'comando vazio': (self.tabela(['| app | `.` | `` | 10 | `*` |']), 'não tem comando de testes'),
            'comando nenhum': (self.tabela(['| app | `.` | nenhum | 10 | `*` |']), 'não tem comando de testes'),
            'timeout inválido': (self.tabela(['| app | `.` | `npm test` | dez | `*` |']), 'timeout inválido'),
            'timeout zero': (self.tabela(['| app | `.` | `npm test` | 0 | `*` |']), 'timeout inválido'),
            'pasta fora do repositório': (self.tabela(['| app | `../fora` | `npm test` | 10 | `*` |']), 'pasta fora'),
            'prefixo repetido': (self.tabela(['| a | `.` | `x` | 10 | `p/` |', '| b | `.` | `y` | 10 | `p/` |']), 'está nas áreas'),
            'dois coringas': (self.tabela(['| a | `.` | `x` | 10 | `*` |', '| b | `.` | `y` | 10 | `*` |']), 'coringa'),
            'sem prefixos': (self.tabela(['| a | `.` | `x` | 10 |  |']), 'não tem prefixos'),
        }
        for nome, (texto, trecho) in casos.items():
            with self.subTest(nome):
                with self.assertRaises(sc_perfil.ErroPortao) as cm:
                    sc_perfil.ler_portao_por_area(texto)
                self.assertIn(trecho, str(cm.exception))


class TestAreaDoCaminho(unittest.TestCase):
    def setUp(self):
        self.areas = sc_perfil.ler_portao_por_area(
            PERFIL.replace('{APP}', 'npm test').replace('{PACOTE}', UNITTEST).replace('{TIMEOUT_APP}', '900'))

    def test_prefixo_mais_longo_e_coringa(self):
        for rel, esperado in {'pacote/x.py': ['pacote'], 'pacote/tests/t.py': ['pacote'], 'src/a.ts': ['app'],
                              'README.md': ['app'], 'pacotex/a.py': ['app'], 'pacote': ['pacote']}.items():
            self.assertEqual(sc_perfil.areas_do_caminho(rel, self.areas), esperado, rel)

    def test_github_conta_para_as_duas_e_sociedade_e_docs_para_nenhuma(self):
        self.assertEqual(sc_perfil.areas_do_caminho('.github/workflows/status.yml', self.areas), ['app', 'pacote'])
        self.assertEqual(sc_perfil.areas_do_caminho('sociedade/perfil.md', self.areas), [])
        self.assertEqual(sc_perfil.areas_do_caminho('docs/onda-1.md', self.areas), [])

    def test_prefixo_mais_longo_vence_o_menor(self):
        texto = ('# P\n\n## Portão por área\n| Área | Pasta | Testes | Timeout (s) | Prefixos |\n|---|---|---|---|---|\n'
                 '| a | `.` | `x` | 10 | `*` |\n| b | `b` | `y` | 10 | `b/` |\n| c | `b/c` | `z` | 10 | `b/c/` |\n')
        areas = sc_perfil.ler_portao_por_area(texto)
        self.assertEqual(sc_perfil.areas_do_caminho('b/c/f.py', areas), ['c'])
        self.assertEqual(sc_perfil.areas_do_caminho('b/f.py', areas), ['b'])
        self.assertEqual(sc_perfil.areas_do_caminho('f.py', areas), ['a'])

    def test_nfc_e_nfd_dao_a_mesma_area(self):
        texto = ('# P\n\n## Portão por área\n| Área | Pasta | Testes | Timeout (s) | Prefixos |\n|---|---|---|---|---|\n'
                 '| a | `.` | `x` | 10 | `*` |\n| b | `b` | `y` | 10 | `relatório/` |\n')
        areas = sc_perfil.ler_portao_por_area(texto)
        for forma in ('NFC', 'NFD'):
            rel = unicodedata.normalize(forma, 'relatório/x.md')
            self.assertEqual(sc_perfil.areas_do_caminho(rel, areas), ['b'], forma)

    def test_areas_tocadas_na_ordem_do_perfil(self):
        self.assertEqual(sc_perfil.areas_tocadas(['pacote/a.py', 'src/b.ts', 'docs/c.md'], self.areas), ['app', 'pacote'])
        self.assertEqual(sc_perfil.areas_tocadas(['pacote/a.py'], self.areas), ['pacote'])
        self.assertEqual(sc_perfil.areas_tocadas(['docs/c.md', 'sociedade/x'], self.areas), [])


class TestContagemDeTestes(unittest.TestCase):
    def test_unittest(self):
        saida = '....\n' + '-' * 70 + '\nRan 12 tests in 1.2s\n\nOK (skipped=3, expected failures=2)\n'
        self.assertEqual(sc_pre_devolucao.contar_testes(saida), {'total': 12, 'pulados': 3, 'falhos': 0})
        falha = 'Ran 5 tests in 0.1s\n\nFAILED (failures=2, errors=1, skipped=1)\n'
        self.assertEqual(sc_pre_devolucao.contar_testes(falha), {'total': 5, 'pulados': 1, 'falhos': 3})
        self.assertEqual(sc_pre_devolucao.contar_testes('Ran 0 tests in 0.000s\n\nNO TESTS RAN\n')['total'], 0)

    def test_vitest_com_e_sem_cores(self):
        saida = ' Test Files  2 passed (2)\n      Tests  7 passed | 2 skipped (9)\n   Duration  1.2s\n'
        self.assertEqual(sc_pre_devolucao.contar_testes(saida), {'total': 9, 'pulados': 2, 'falhos': 0})
        colorida = '\x1b[2m      Tests \x1b[22m \x1b[1m\x1b[32m3 passed\x1b[39m\x1b[22m\x1b[90m (3)\x1b[39m\n'
        self.assertEqual(sc_pre_devolucao.contar_testes(colorida), {'total': 3, 'pulados': 0, 'falhos': 0})
        falha = '      Tests  1 failed | 4 passed | 1 todo (6)\n'
        self.assertEqual(sc_pre_devolucao.contar_testes(falha), {'total': 6, 'pulados': 1, 'falhos': 1})

    def test_playwright(self):
        saida = 'Running 6 tests using 2 workers\n\n  1 skipped\n  4 passed (3.4s)\n  1 failed\n'
        self.assertEqual(sc_pre_devolucao.contar_testes(saida), {'total': 6, 'pulados': 1, 'falhos': 1})
        self.assertEqual(sc_pre_devolucao.contar_testes('  2 did not run\n')['pulados'], 2)

    def test_vitest_e_playwright_no_mesmo_comando_somam(self):
        saida = '      Tests  4 passed (4)\n\nRunning 2 tests using 1 worker\n  2 passed (1s)\n'
        self.assertEqual(sc_pre_devolucao.contar_testes(saida), {'total': 6, 'pulados': 0, 'falhos': 0})

    def test_saida_que_ninguem_reconhece_conta_zero(self):
        self.assertEqual(sc_pre_devolucao.contar_testes('tudo certo\n'), {'total': 0, 'pulados': 0, 'falhos': 0})
        self.assertEqual(sc_pre_devolucao.contar_testes('Test Files  1 passed (1)\n')['total'], 0)


class TestArvore(Base):
    def test_status_z_traz_renomeacao_com_destino_e_origem_e_nome_sem_aspas(self):
        r = self.repo()
        git(r.raiz, 'mv', 'docs/nota.md', 'docs/nota nova.md')
        r.escrever('novo ç.txt')
        caminhos = sc_pre_devolucao.listar_arvore(r.raiz)
        self.assertEqual(sorted(caminhos), ['docs/nota nova.md', 'docs/nota.md', 'novo ç.txt'])

    def test_ignorados_nao_aparecem(self):
        r = self.repo()
        r.escrever('node_modules/pkg/index.js')
        r.escrever('dist/main.js')
        self.assertEqual(sc_pre_devolucao.listar_arvore(r.raiz), [])


class TestPortao(Base):
    def test_aprova_com_node_modules_presente_e_ignorado(self):
        r = self.repo()
        r.escrever('node_modules/pkg/index.js', 'module.exports = 1\n')
        r.escrever('dist/main.js', 'x\n')
        r.commitar('app.py')
        res = r.entregar()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        at = r.atestado()
        self.assertEqual(at['status'], 'APROVADO')
        self.assertEqual(at['verificacoes']['arvore_limpa'], {'ok': True, 'suja': []})
        self.assertNotIn('node_modules/pkg/index.js', at['arquivos_inspecionados'])

    def test_atestado_grava_por_area_comando_timeout_contagem_perfil_e_commit(self):
        r = self.repo()
        head = r.commitar('pacote/mod.py')
        self.assertEqual(r.entregar().returncode, 0)
        at = r.atestado()
        self.assertEqual(at['commit'], head)
        self.assertEqual(at['versao'], '1.3.0')
        portao = at['portao']
        self.assertEqual(portao['perfil_sha256'], hashlib.sha256(r.perfil.read_bytes()).hexdigest())
        self.assertEqual(portao['commit'], head)
        self.assertEqual(self.nomes(at), ['pacote'])
        area = portao['areas'][0]
        self.assertEqual((area['comando'], area['timeout_s'], area['pasta'], area['codigo'], area['ok']),
                         (UNITTEST, 120, 'pacote', 0, True))
        self.assertEqual(area['testes'], {'total': 1, 'pulados': 0, 'falhos': 0})
        self.assertEqual(at['verificacoes']['testes']['totais'], {'total': 1, 'pulados': 0, 'falhos': 0})

    def test_sem_area_roda_so_as_areas_que_base_head_toca(self):
        r = self.repo()
        r.commitar('pacote/mod.py')
        r.entregar()
        self.assertEqual(self.nomes(r.atestado()), ['pacote'])
        r.commitar('src/app.py')
        r.entregar()
        self.assertEqual(self.nomes(r.atestado()), ['app', 'pacote'])

    def test_area_so_roda_aquela_mesmo_sem_ser_tocada(self):
        r = self.repo()
        r.commitar('pacote/mod.py')
        self.assertEqual(r.entregar('--area', 'app').returncode, 0)
        at = r.atestado()
        self.assertEqual(self.nomes(at), ['app'])
        self.assertEqual(at['portao']['area_pedida'], 'app')

    def test_github_conta_para_as_duas_areas(self):
        r = self.repo()
        r.commitar('.github/pull_request_template.md', '## Etapa\n')
        self.assertEqual(r.entregar().returncode, 0)
        self.assertEqual(self.nomes(r.atestado()), ['app', 'pacote'])

    def test_area_desconhecida_reprova(self):
        r = self.repo()
        r.commitar('pacote/mod.py')
        res = r.entregar('--area', 'nao-existe')
        self.assertNotEqual(res.returncode, 0)
        self.assertTrue(any('Área desconhecida' in e for e in r.atestado()['erros']))

    def test_so_docs_e_sociedade_nao_toca_area_e_reprova(self):
        r = self.repo()
        r.commitar('docs/outra.md', '# Outra\n')
        self.assertNotEqual(r.entregar().returncode, 0)
        self.assertTrue(any('não toca nenhuma área' in e for e in r.atestado()['erros']))

    def test_arvore_suja_reprova_em_todas_as_formas(self):
        casos = {
            'arquivo novo': lambda r: r.escrever('novo.py'),
            'arquivo rastreado modificado': lambda r: r.escrever('pacote/mod.py', 'x = 2\n'),
            'arquivo no índice sem commit': lambda r: (r.escrever('staged.py'), git(r.raiz, 'add', 'staged.py')),
            'renomeação sem commit': lambda r: git(r.raiz, 'mv', 'pacote/mod.py', 'pacote/mod2.py'),
            'arquivo removido sem commit': lambda r: (r.raiz / 'pacote' / 'mod.py').unlink(),
        }
        for nome, sujar in casos.items():
            with self.subTest(nome):
                with tempfile.TemporaryDirectory() as tmp:
                    r = Repo(tmp)
                    r.commitar('pacote/mod.py')
                    sujar(r)
                    res = r.entregar()
                    self.assertNotEqual(res.returncode, 0, res.stdout)
                    at = r.atestado()
                    self.assertEqual(at['status'], 'REPROVADO')
                    self.assertTrue(any('Árvore suja' in e for e in at['erros']), at['erros'])
                    self.assertFalse(at['verificacoes']['arvore_limpa']['ok'])

    def test_mudanca_em_sociedade_sem_commit_nao_suja(self):
        r = self.repo()
        r.commitar('pacote/mod.py')
        (r.soc / 'andamento.md').write_text('registro de governança em andamento\n', encoding='utf-8')
        self.assertEqual(r.entregar().returncode, 0)

    def test_teste_que_suja_a_arvore_reprova(self):
        r = self.repo(pacote='python3 -B -c "open(\'lixo.txt\', \'w\').write(\'x\')" && ' + UNITTEST)
        r.commitar('pacote/mod.py')
        res = r.entregar()
        self.assertNotEqual(res.returncode, 0, res.stdout)
        self.assertTrue(any('A árvore mudou durante o portão' in e for e in r.atestado()['erros']))

    def test_timeout_do_perfil_reprova_e_mata_o_comando(self):
        """O comando dorme 30 s e o perfil dá 1 s: o portão reprova em poucos segundos e registra o timeout."""
        r = self.repo(app='python3 -B -c "import time; time.sleep(30)"', timeout_app=1)
        r.commitar('src/app.py')
        inicio = time.monotonic()
        r.entregar('--area', 'app')
        self.assertLess(time.monotonic() - inicio, 20)
        area = r.atestado()['portao']['areas'][0]
        self.assertEqual(area['timeout_s'], 1)
        self.assertTrue(area['timeout_estourado'])
        self.assertTrue(any('timeout de 1 s' in e for e in r.atestado()['erros']))

    def test_teste_que_falha_reprova(self):
        r = self.repo()
        r.commitar('pacote/tests/test_falha.py', teste_py('Falha', 'def test_a(self):\n        self.fail("sonda")'))
        self.assertNotEqual(r.entregar().returncode, 0)
        area = r.atestado()['portao']['areas'][0]
        self.assertEqual(area['testes']['falhos'], 1)
        self.assertFalse(area['ok'])

    def test_perfil_sem_a_secao_reprova_com_mensagem_clara(self):
        r = self.repo()
        r.commitar('pacote/mod.py')
        texto = r.perfil.read_text(encoding='utf-8')
        r.perfil.write_text(texto[:texto.index('## Portão por área')], encoding='utf-8')
        res = r.entregar()
        self.assertNotEqual(res.returncode, 0)
        self.assertTrue(any('não tem a seção "Portão por área"' in e for e in r.atestado()['erros']))

    def test_comando_teste_e_recusado_e_nao_grava_atestado(self):
        r = self.repo()
        r.commitar('pacote/mod.py')
        res = r.entregar('--comando-teste', 'true')
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('--comando-teste é recusado', res.stderr)
        self.assertFalse((r.soc / 'pareceres' / 'atestado-a1.json').exists())

    def test_baixo_nivel_tambem_recusa_comando_no_modo_por_area(self):
        r = self.repo()
        r.commitar('pacote/mod.py')
        res = rodar(NUCLEO / 'scripts' / 'sc_pre_devolucao.py', '--portao-por-area', '--comando-teste', 'true',
                    '--base', r.base, '--pasta-projeto', r.raiz, '--pasta-sociedade', r.soc, cwd=r.raiz, env=AMBIENTE)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('não aceita --comando-teste', res.stderr)

    def test_saida_do_atestado_lista_as_areas_no_terminal(self):
        r = self.repo()
        r.commitar('pacote/mod.py')
        res = r.entregar()
        self.assertIn('área pacote [OK]', res.stdout)


class TestTextosDoCiclo(unittest.TestCase):
    def test_nenhuma_skill_cita_sc_rodada_parecer_e_o_sc_revisao_manda_usar_o_sc_py(self):
        for arq in SKILLS.rglob('*.md'):
            texto = arq.read_text(encoding='utf-8')
            self.assertNotIn('sc_rodada.py parecer', texto, arq)
            self.assertNotIn('sc_rodada parecer', texto, arq)
        revisao = (SKILLS / 'sc-revisao' / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('sc.py revisar --etapa <ID> --parecer', revisao)

    def test_nenhum_texto_de_skill_manda_usar_comando_teste_no_entregar(self):
        for arq in SKILLS.rglob('*.md'):
            for linha in arq.read_text(encoding='utf-8').splitlines():
                if 'entregar' in linha and '--comando-teste' in linha:
                    self.assertIn('recusa', linha, f'{arq}: {linha}')

    @unittest.skipUnless((RAIZ.parent / '.github' / 'pull_request_template.md').is_file(),
                         'pacote fora do repositório do projeto: sem modelo de PR')
    def test_modelo_de_pr_manda_conferir_o_diff_de_github_e_pareceres(self):
        modelo = (RAIZ.parent / '.github' / 'pull_request_template.md').read_text(encoding='utf-8')
        self.assertIn('Conferi o diff de `.github/` e `sociedade/pareceres/`', modelo)


if __name__ == '__main__':
    unittest.main()
