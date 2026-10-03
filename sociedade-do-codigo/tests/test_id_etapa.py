"""B08: identificador de etapa validado (^[a-z0-9][a-z0-9-]{0,39}$), só para etapas novas; o `_id` legado segue nos demais comandos."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_ciclo as tc  # noqa: E402
from util import NUCLEO, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
from sc_ciclo import ErroCiclo, validar_id_novo  # noqa: E402

VALIDOS = ['a', '0', 'm0-destravar', 'etapa-1', 'a' * 40, '9-9']
INVALIDOS = ['', 'A', 'Etapa', 'a_b', 'a.b', '-x', 'x y', '../fora', 'a/b', 'a' * 41, 'é', 'a\n', '--ordem']


class TestValidacao(unittest.TestCase):
    def test_validos(self):
        for v in VALIDOS:
            with self.subTest(id=v):
                self.assertEqual(validar_id_novo(v), v)

    def test_invalidos(self):
        for v in INVALIDOS:
            with self.subTest(id=v):
                with self.assertRaises(ErroCiclo):
                    validar_id_novo(v)

    def test_none(self):
        with self.assertRaises(ErroCiclo):
            validar_id_novo(None)


class TestAbrirComId(tc.Base):
    def test_abrir_recusa_id_invalido_sem_tocar_o_registro(self):
        for v in ('Etapa', 'a_b', '-x', 'a' * 41, '../fora'):
            with self.subTest(id=v):
                r = self.p.abrir(etapa=v)
                self.recusa(r, 'identificador de etapa inválido')
        self.assertFalse((self.p.soc / 'registro.json').exists())

    def test_abrir_aceita_id_no_limite(self):
        self.ok(self.p.abrir(etapa='a' * 40))


class TestLegado(tc.Base):
    """Etapas e comandos existentes não quebram: o ID legado continua valendo fora do `abrir`."""

    def test_ordem_e_entregar_seguem_com_id_legado(self):
        self.ok(rodar(tc.SC, 'ordem', '--etapa', 'SC-E5', '--pasta-sociedade', self.p.soc))
        self.assertTrue((self.p.soc / 'ordens' / 'SC-E5.md').is_file())

    def test_decidir_em_etapa_legada_ja_aberta(self):
        reg = tc.Registro.inicializar(self.p.soc, 'proj', str(self.p.raiz), versao_inicial=self.p.base)
        reg.abrir_etapa('SC_E5.legada', 'Meta', 'plano', 'aut', self.p.base, ['fatia_1'])
        self.ok(self.p.sc('decidir', '--etapa', 'SC_E5.legada', 'corrigir', '--por', 'Odival Sintético'))
        self.assertEqual(self.p.registro().estado()['etapas']['SC_E5.legada']['decisoes'][-1]['acao'], 'corrigir')

    def test_aceitar_em_etapa_com_criterios_proprios_lista_o_que_falta_e_nao_decide(self):
        reg = tc.Registro.inicializar(self.p.soc, 'proj', str(self.p.raiz), versao_inicial=self.p.base)
        reg.abrir_etapa('soma', 'Meta', 'plano', 'aut', self.p.base, ['fatia_1', 'C1: algo conferido'])
        self.ok(self.p.entregar())
        self.ok(self.p.revisar(self.parecer()))
        r = self.recusa(self.p.decidir('aceitar', '--por', 'Odival Sintético'), 'a etapa não pode ser encerrada')
        self.assertIn('fatia_1', r.stderr)
        self.assertEqual(self.p.eventos('decisao_registrada'), [])

    def test_decidir_nao_aceita_id_com_caminho(self):
        self.assertNotEqual(self.p.sc('decidir', '--etapa', '../x', 'aceitar', '--por', 'X').returncode, 0)


if __name__ == '__main__':
    unittest.main()
