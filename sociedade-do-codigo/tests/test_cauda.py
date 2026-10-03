"""B06: cauda de governança. Commit de produto depois do SHA do parecer derruba o parecer; commit só de `sociedade/` não derruba."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_ciclo as tc  # noqa: E402
from util import NUCLEO  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
from sc_ciclo import parecer_vale  # noqa: E402


class TestParecerVale(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        tc.git(self.raiz, 'init', '-q')
        (self.raiz / 'sociedade').mkdir()
        (self.raiz / 'app.py').write_text('x = 1\n', encoding='utf-8')
        (self.raiz / 'sociedade' / 'registro.json').write_text('{}\n', encoding='utf-8')
        self.revisado = tc.commit(self.raiz, 'produto revisado')

    def faz(self, arquivo, msg):
        caminho = self.raiz / arquivo
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(msg + '\n', encoding='utf-8')
        return tc.commit(self.raiz, msg)

    def test_o_proprio_commit_revisado_vale(self):
        self.assertTrue(parecer_vale(self.raiz, self.revisado, self.revisado)[0])

    def test_commit_so_de_sociedade_nao_derruba(self):
        self.faz('sociedade/pareceres/parecer-x.md', 'parecer')
        topo = self.faz('sociedade/evolucao.md', 'evolução')
        ok, motivo = parecer_vale(self.raiz, self.revisado, topo)
        self.assertTrue(ok, motivo)

    def test_commit_de_produto_depois_derruba(self):
        topo = self.faz('app.py', 'x = 2')
        ok, motivo = parecer_vale(self.raiz, self.revisado, topo)
        self.assertFalse(ok)
        self.assertIn('toca fora de sociedade/', motivo)

    def test_produto_no_meio_da_cauda_derruba_mesmo_com_governanca_depois(self):
        self.faz('app.py', 'x = 3')
        topo = self.faz('sociedade/estado.md', 'estado')
        self.assertFalse(parecer_vale(self.raiz, self.revisado, topo)[0])

    def test_commit_misto_derruba(self):
        (self.raiz / 'sociedade' / 'a.md').write_text('a\n', encoding='utf-8')
        (self.raiz / 'extra.py').write_text('y\n', encoding='utf-8')
        topo = tc.commit(self.raiz, 'misto')
        self.assertFalse(parecer_vale(self.raiz, self.revisado, topo)[0])

    def test_pasta_parecida_com_sociedade_nao_vale(self):
        topo = self.faz('sociedade-x/arquivo.md', 'fora')
        self.assertFalse(parecer_vale(self.raiz, self.revisado, topo)[0])

    def test_merge_na_cauda_derruba(self):
        tc.git(self.raiz, 'checkout', '-q', '-b', 'lateral')
        self.faz('sociedade/lateral.md', 'lateral')
        tc.git(self.raiz, 'checkout', '-q', '-')
        self.faz('sociedade/principal.md', 'principal')
        tc.git(self.raiz, 'merge', '-q', '--no-ff', '-m', 'merge', 'lateral')
        self.assertFalse(parecer_vale(self.raiz, self.revisado, tc.git(self.raiz, 'rev-parse', 'HEAD'))[0])

    def test_commit_que_nao_e_ancestral_ou_nao_existe(self):
        outro = self.faz('sociedade/b.md', 'b')
        tc.git(self.raiz, 'checkout', '-q', '-b', 'paralelo', self.revisado)
        paralelo = self.faz('sociedade/c.md', 'c')
        self.assertFalse(parecer_vale(self.raiz, outro, paralelo)[0])
        self.assertFalse(parecer_vale(self.raiz, '0123456789abcdef', paralelo)[0])


class TestDecidirRecusaComCauda(tc.Base):
    def test_produto_depois_do_parecer_derruba_o_parecer_e_o_decidir_recusa(self):
        self.fluxo_ate_o_parecer()
        (self.p.raiz / 'soma.py').write_text('def soma(a, b):\n    return b + a\n', encoding='utf-8')
        tc.git(self.p.raiz, 'add', 'soma.py')
        tc.git(self.p.raiz, 'commit', '-q', '-m', 'fix: depois do parecer')
        self.recusa(self.p.decidir('aceitar', '--por', 'Odival Sintético'), 'o parecer não vale')
        self.assertEqual(self.p.eventos('decisao_registrada'), [])
        self.assertEqual(self.p.registro().estado()['etapas']['soma']['estado'], 'aberta')

    def test_governanca_depois_do_parecer_nao_derruba(self):
        self.fluxo_ate_o_parecer()
        tc.commit(self.p.raiz, 'sociedade: atestado e parecer')
        self.ok(self.p.decidir('aceitar', '--por', 'Odival Sintético'))
        self.assertEqual(self.p.registro().estado()['etapas']['soma']['estado'], 'encerrada')

    def test_head_anterior_a_ponta_do_ramo_da_etapa_e_recusado(self):
        """F6 (achado 7): `--head` não pode ser anterior à ponta de `etapa/<ID>`; recusa antes de gravar."""
        self.fluxo_ate_o_parecer()
        (self.p.raiz / 'extra.py').write_text('y = 2\n', encoding='utf-8')
        tc.git(self.p.raiz, 'add', 'extra.py')
        tc.git(self.p.raiz, 'commit', '-q', '-m', 'feat: extra')
        tc.git(self.p.raiz, 'branch', '-f', 'etapa/soma', 'HEAD')
        r = self.recusa(self.p.decidir('aceitar', '--por', 'Odival Sintético', '--head', self.p.head), 'anterior à ponta do ramo')
        self.assertIn('etapa/soma', r.stderr)
        self.assertEqual(self.p.eventos('decisao_registrada'), [])
        self.assertEqual(self.p.registro().estado()['etapas']['soma']['estado'], 'aberta')

    def test_head_igual_ou_posterior_a_ponta_do_ramo_vale(self):
        self.fluxo_ate_o_parecer()
        tc.git(self.p.raiz, 'branch', '-f', 'etapa/soma', self.p.head)
        tc.commit(self.p.raiz, 'sociedade: atestado e parecer')  # governança depois da ponta do ramo
        self.ok(self.p.decidir('aceitar', '--por', 'Odival Sintético', '--head', 'HEAD'))
        self.assertEqual(self.p.registro().estado()['etapas']['soma']['estado'], 'encerrada')

    def test_head_igual_a_ponta_do_ramo_vale(self):
        self.fluxo_ate_o_parecer()
        tc.git(self.p.raiz, 'branch', '-f', 'etapa/soma', self.p.head)
        self.ok(self.p.decidir('aceitar', '--por', 'Odival Sintético', '--head', self.p.head))

    def test_sem_ramo_da_etapa_o_head_informado_segue_valendo(self):
        self.fluxo_ate_o_parecer()
        self.ok(self.p.decidir('aceitar', '--por', 'Odival Sintético', '--head', self.p.head))


if __name__ == '__main__':
    unittest.main()
