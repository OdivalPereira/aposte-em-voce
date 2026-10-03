"""Sondas DG-09 (B11): o portão não pode aprovar o que não testou. Fechado pela B11 (portão amarrado ao perfil).

Achado original: o `sc.py entregar` aceitava `--comando-teste` livre e dava APROVADO com `true`, com 0 testes ou com
todos os testes pulados. Agora: `--comando-teste` é recusado; o comando e o timeout vêm só da seção "Portão por área"
do perfil canônico; 0 testes e todos pulados reprovam. Todas as sondas deste arquivo são verdes.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cenario import Base, commit, git, texto_perfil  # noqa: E402

POR = ('--por', 'Odival Sintético')


class SondaDG09(Base):

    def _atestado(self, p):
        return json.loads(p.atestado().read_text(encoding='utf-8'))

    def test_DG09_comando_teste_livre_e_recusado(self):
        """Achado: `entregar --comando-teste "true"` aprovava qualquer candidato. Reproduz: com um comando que passaria,
        o comando é recusado, nenhum atestado é gravado e o aceite não existe."""
        p = self.p
        self.ok(p.abrir())
        r = p.sc('entregar', '--etapa', 'soma', '--base', p.base, '--pasta-projeto', p.raiz, '--comando-teste', 'true')
        self.recusa(r, '--comando-teste é recusado')
        self.assertFalse(p.atestado().exists(), 'a recusa não pode deixar atestado')
        self.recusa(p.decidir('aceitar', *POR), 'sem atestado')
        self.sem_decisao()

    def test_DG09_zero_testes_reprova(self):
        """Achado: um comando que sai com 0 sem rodar teste nenhum virava APROVADO. Reproduz: o perfil declara um comando
        que não roda teste; o atestado sai REPROVADO por "0 testes" e o aceite é recusado."""
        p = self.novo_projeto(perfil=texto_perfil('sim', testes='python3 -c pass'))
        self.ok(p.abrir())
        p.entregar()
        at = self._atestado(p)
        self.assertEqual(at['status'], 'REPROVADO')
        self.assertTrue(any('0 testes' in e for e in at['erros']), at['erros'])
        self.assertEqual(at['portao']['areas'][0]['testes']['total'], 0)
        p.revisar(p.escrever_parecer())
        self.recusa(p.decidir('aceitar', *POR), 'atestado não aprovado')

    def test_DG09_suite_vazia_do_unittest_reprova(self):
        """Variante: o `unittest` que descobre 0 testes ("Ran 0 tests", saída 0) também reprova."""
        p = self.novo_projeto(perfil=texto_perfil('sim', testes='python3 -B -m unittest discover -s vazio'))
        (p.raiz / 'vazio').mkdir()
        (p.raiz / 'vazio' / 'nada.py').write_text('x = 1\n', encoding='utf-8')
        commit(p.raiz, 'feat: suíte vazia')
        self.ok(p.abrir())
        p.entregar()
        at = self._atestado(p)
        self.assertEqual(at['status'], 'REPROVADO')
        self.assertTrue(any('0 testes' in e for e in at['erros']), at['erros'])

    def test_DG09_todos_pulados_reprova(self):
        """Achado: suíte com todos os testes pulados (`skipped=N`, saída 0) virava APROVADO. Reproduz: todos pulados;
        o atestado sai REPROVADO e conta os pulados."""
        p = self.p
        (p.raiz / 'tests' / 'test_soma.py').write_text(
            'import unittest\n\n\nclass T(unittest.TestCase):\n    @unittest.skip("sonda")\n'
            '    def test_a(self):\n        self.fail()\n\n    @unittest.skip("sonda")\n    def test_b(self):\n'
            '        self.fail()\n', encoding='utf-8')
        commit(p.raiz, 'test: tudo pulado')
        self.ok(p.abrir())
        p.entregar()
        at = self._atestado(p)
        self.assertEqual(at['status'], 'REPROVADO')
        testes = at['portao']['areas'][0]['testes']
        self.assertEqual((testes['total'], testes['pulados']), (2, 2))
        self.assertTrue(any('pulados' in e for e in at['erros']), at['erros'])
        self.recusa(p.decidir('aceitar', *POR))

    def test_DG09_candidato_nao_troca_o_comando_no_perfil(self):
        """Variante: o candidato enfraquece o comando em `sociedade/perfil.md` no próprio commit. Reproduz: o commit de
        produto troca a coluna Testes; o portão reprova (sociedade/ em commit do candidato é governança violada, Q60)."""
        p = self.p
        perfil = p.soc / 'perfil.md'
        perfil.write_text(perfil.read_text(encoding='utf-8').replace(
            '`python3 -B -m unittest discover -s tests`', '`python3 -c "print(1)"`'), encoding='utf-8')
        commit(p.raiz, 'feat: troca o comando de teste')
        self.ok(p.abrir())
        p.entregar()
        at = self._atestado(p)
        self.assertEqual(at['status'], 'REPROVADO')
        self.assertTrue(any('governança' in e and 'sociedade/perfil.md' in e for e in at['erros']), at['erros'])

    def test_DG09_controle_suite_com_testes_aprova(self):
        """Controle (verde): o cenário padrão, com 1 teste que roda, é APROVADO e o atestado traz a contagem."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        at = self._atestado(p)
        self.assertEqual(at['status'], 'APROVADO')
        self.assertEqual(at['portao']['areas'][0]['testes'], {'total': 1, 'pulados': 0, 'falhos': 0})
        self.assertEqual(git(p.raiz, 'rev-parse', 'HEAD'), at['commit'])


if __name__ == '__main__':
    unittest.main()
