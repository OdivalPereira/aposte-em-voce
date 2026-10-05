"""Testes para conformidade do portão pré-devolução e conferência com Q178 e Q149.

Q178 (Governança no início): Quando uma etapa altera regras ou perfil, o commit de
governança sai antes do despacho. Commits estritamente de governança (100% dos arquivos
em sociedade/) em base..HEAD não pertencem ao candidato de produto e não configuram
violação de governança por parte deste.

Q149 (Cauda de governança): Commits posteriores estritamente em sociedade/ entram no
mesmo PR e também não configuram violação.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, RAIZ, SKILLS, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
import sc_conferir  # noqa: E402
import sc_pre_devolucao  # noqa: E402

SC = NUCLEO / 'scripts' / 'sc.py'
AMBIENTE = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
UNITTEST = 'python3 -B -m unittest discover -s tests'

PERFIL = """# Perfil sintético

## Missão
Projeto sintético de testes Q178/Q149.

## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Coordenador | Gandalf | Claude Code (nuvem) | Anthropic | Modelo B | high | ativo | 2026-10-03 | subagente |

## Portão por área
*Lida pelo `sc.py entregar`.*

| Área | Pasta | Testes | Timeout (s) | Prefixos |
|---|---|---|---|---|
| app | `.` | `{APP}` | 120 | `*` (tudo fora de `pacote/`, `sociedade/` e `docs/`) |
| pacote | `pacote` | `{PACOTE}` | 120 | `pacote/` |

## Estado
- Resumo: `sociedade/estado.md`
"""


def git(raiz, *args):
    return subprocess.run(
        ['git', '-C', str(raiz), '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', *args],
        capture_output=True, text=True, check=True, env=AMBIENTE
    ).stdout.strip()


def commit(raiz, msg):
    git(raiz, 'add', '-A')
    git(raiz, 'commit', '-q', '-m', msg)
    return git(raiz, 'rev-parse', 'HEAD')


def teste_py(nome='T'):
    return f'import unittest\n\n\nclass {nome}(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n'


class RepoTesteQ178:
    def __init__(self, tmp):
        self.raiz = Path(tmp) / 'repo'
        self.soc = self.raiz / 'sociedade'
        (self.soc / 'pareceres').mkdir(parents=True)
        (self.raiz / 'tests').mkdir()
        (self.raiz / 'pacote' / 'tests').mkdir(parents=True)
        (self.raiz / 'docs').mkdir()
        git(self.raiz, 'init', '-q')
        self.perfil = self.soc / 'perfil.md'
        self.perfil.write_text(PERFIL.replace('{APP}', UNITTEST).replace('{PACOTE}', UNITTEST), encoding='utf-8')
        (self.raiz / '.gitignore').write_text('node_modules/\ndist/\nsociedade/.registro.lock\n', encoding='utf-8')
        (self.raiz / 'tests' / 'test_app.py').write_text(teste_py('App'), encoding='utf-8')
        (self.raiz / 'pacote' / 'tests' / 'test_pacote.py').write_text(teste_py('Pacote'), encoding='utf-8')
        (self.raiz / 'docs' / 'nota.md').write_text('# Nota\n', encoding='utf-8')
        self.base = commit(self.raiz, 'base')

    def entregar(self, *extra):
        return rodar(SC, 'entregar', '--etapa', 'q178-teste', '--base', self.base, '--pasta-projeto', self.raiz,
                     '--pasta-sociedade', self.soc, *extra, cwd=self.raiz, env=AMBIENTE)

    def atestado(self):
        return json.loads((self.soc / 'pareceres' / 'atestado-q178-teste.json').read_text(encoding='utf-8'))

    def escrever(self, rel, texto='x = 1\n'):
        alvo = self.raiz / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding='utf-8')
        return alvo

    def commitar(self, rel, texto='x = 1\n', msg=None):
        self.escrever(rel, texto)
        return commit(self.raiz, msg or f'feat: {rel}')


class TestPortaoGovernancaQ178(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name
        self.r = RepoTesteQ178(self.tmp)

    def test_etapa_com_commit_de_governanca_no_inicio_q178_aprova(self):
        """Q178: Commit puramente em sociedade/ no início da etapa é governança válida e não reprova."""
        # 1. Commit de governança no início (100% em sociedade/)
        self.r.escrever('sociedade/regras.md', '# Regras atualizadas (Q178)\n')
        self.r.escrever('sociedade/ordens/etapa-01.md', '# Ordem da etapa\n')
        commit(self.r.raiz, 'sociedade(etapa-01): governança no início (Q178)')

        # 2. Commit de produto pelo especialista
        self.r.commitar('pacote/modulo.py', 'def soma(a, b): return a + b\n')

        # 3. Portão deve APROVAR
        res_entregar = self.r.entregar()
        self.assertEqual(res_entregar.returncode, 0, f'Portão falhou: {res_entregar.stderr}\n{res_entregar.stdout}')
        at = self.r.atestado()
        self.assertEqual(at['status'], 'APROVADO')
        self.assertEqual(at['erros'], [])
        self.assertEqual(at['portao']['areas_tocadas'], ['pacote'])

        # 4. sc_conferir com arquivos_em deve resultar em FEITO
        ordem = Path(self.tmp) / 'ordem.md'
        ordem.write_text(
            f'# Ordem\n\n```entregas\nE1 | arquivos_em | {self.r.base}..HEAD | pacote/\n```\n',
            encoding='utf-8'
        )
        res_conferir = rodar(SC, 'conferir', '--ordem', ordem, '--raiz', self.r.raiz, '--json',
                             cwd=self.r.raiz, env=AMBIENTE)
        self.assertEqual(res_conferir.returncode, 0, f'Conferir falhou: {res_conferir.stdout}')
        itens = json.loads(res_conferir.stdout)['itens']
        self.assertEqual(itens[0]['estado'], 'feito')
        self.assertIn('todos nos prefixos', itens[0]['detalhe'])

    def test_commit_misto_com_sociedade_reprova_governanca(self):
        """Candidato que toca sociedade/ em commit que também toca produto viola governança."""
        # 1. Commit de governança no início legítimo (100% sociedade/)
        self.r.commitar('sociedade/regras.md', '# Regras legítimas\n', msg='sociedade: Q178 início')

        # 2. Commit misto violador (produto + sociedade/)
        self.r.escrever('pacote/modulo.py', 'def func(): pass\n')
        self.r.escrever('sociedade/perfil.md', '# Perfil adulterado pelo candidato\n')
        commit(self.r.raiz, 'feat(pacote): adulterando governanca indevidamente')

        # 3. Portão deve REPROVAR acusando violação apenas de perfil.md
        res_entregar = self.r.entregar()
        self.assertNotEqual(res_entregar.returncode, 0)
        at = self.r.atestado()
        self.assertEqual(at['status'], 'REPROVADO')
        erros = at.get('erros', [])
        self.assertTrue(any('sociedade/perfil.md' in e for e in erros), f'Erro esperado não encontrado: {erros}')
        self.assertFalse(any('sociedade/regras.md' in e for e in erros), f'Falso positivo em regras.md: {erros}')

        # 4. sc_conferir também aponta arquivos fora do prefixo
        ordem = Path(self.tmp) / 'ordem.md'
        ordem.write_text(
            f'# Ordem\n\n```entregas\nE1 | arquivos_em | {self.r.base}..HEAD | pacote/\n```\n',
            encoding='utf-8'
        )
        res_conferir = rodar(SC, 'conferir', '--ordem', ordem, '--raiz', self.r.raiz, '--json',
                             cwd=self.r.raiz, env=AMBIENTE)
        itens = json.loads(res_conferir.stdout)['itens']
        self.assertEqual(itens[0]['estado'], 'não feito')
        self.assertIn('sociedade/perfil.md', itens[0]['detalhe'])

    def test_cauda_de_governanca_q149_aprova(self):
        """Q149: Commit de governança posterior ao produto (cauda) não reprova."""
        # 1. Commit de governança no início (Q178)
        self.r.commitar('sociedade/ordens/etapa.md', '# Ordem\n', msg='sociedade: Q178')

        # 2. Commit de produto
        self.r.commitar('pacote/app.py', 'print("ok")\n', msg='feat: produto')

        # 3. Commit de cauda de governança (Q149)
        self.r.commitar('sociedade/registro.json', '{"eventos": []}\n', msg='sociedade: cauda Q149')

        # 4. Portão deve APROVAR
        res_entregar = self.r.entregar()
        self.assertEqual(res_entregar.returncode, 0, f'Portão falhou: {res_entregar.stderr}')
        at = self.r.atestado()
        self.assertEqual(at['status'], 'APROVADO')

        # 5. sc_conferir arquivos_em deve ignorar ambos os commits de governança
        ordem = Path(self.tmp) / 'ordem.md'
        ordem.write_text(
            f'# Ordem\n\n```entregas\nE1 | arquivos_em | {self.r.base}..HEAD | pacote/\n```\n',
            encoding='utf-8'
        )
        res_conferir = rodar(SC, 'conferir', '--ordem', ordem, '--raiz', self.r.raiz, '--json',
                             cwd=self.r.raiz, env=AMBIENTE)
        self.assertEqual(res_conferir.returncode, 0)
        itens = json.loads(res_conferir.stdout)['itens']
        self.assertEqual(itens[0]['estado'], 'feito')

    def test_funcoes_diretas_de_candidato_e_intervalo(self):
        """Testa diretamente obter_arquivos_candidato e arquivos_do_intervalo em múltiplos cenários."""
        # 1. Commit inicial de governança pura
        self.r.commitar('sociedade/regras.md', '# Regras Q178\n', msg='sociedade: Q178')
        # 2. Commit de produto
        self.r.commitar('pacote/lib.py', 'X = 42\n', msg='feat: produto')
        # 3. Commit de cauda de governança pura
        self.r.commitar('sociedade/pareceres/nota.md', '# Nota\n', msg='sociedade: Q149')

        cand = sc_pre_devolucao.obter_arquivos_candidato(self.r.raiz, self.r.base, self.r.soc)
        self.assertEqual(cand['governanca'], [])
        self.assertEqual(cand['caminhos'], ['pacote/lib.py'])
        self.assertEqual([p.name for p in cand['arquivos']], ['lib.py'])

        intervalo = sc_conferir.arquivos_do_intervalo(self.r.raiz, self.r.base, 'HEAD')
        self.assertEqual(intervalo, ['pacote/lib.py'])

        # 4. Adiciona commit misto com violação de governança
        self.r.escrever('pacote/extra.py', 'Y = 10\n')
        self.r.escrever('sociedade/hacker.md', '# Invasão\n')
        commit(self.r.raiz, 'feat(pacote): misto irregular')

        cand_misto = sc_pre_devolucao.obter_arquivos_candidato(self.r.raiz, self.r.base, self.r.soc)
        self.assertIn('sociedade/hacker.md', cand_misto['governanca'])
        self.assertNotIn('sociedade/regras.md', cand_misto['governanca'])
        self.assertNotIn('sociedade/pareceres/nota.md', cand_misto['governanca'])
        self.assertIn('pacote/extra.py', cand_misto['caminhos'])

        intervalo_misto = sc_conferir.arquivos_do_intervalo(self.r.raiz, self.r.base, 'HEAD')
        self.assertIn('sociedade/hacker.md', intervalo_misto)
        self.assertNotIn('sociedade/regras.md', intervalo_misto)
        self.assertIn('pacote/lib.py', intervalo_misto)
        self.assertIn('pacote/extra.py', intervalo_misto)


if __name__ == '__main__':
    unittest.main()
