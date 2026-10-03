"""Políticas Q144 (A2-P02: parecer que decide) e Q145 (A2-P11: impacto padrão desconhecido)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, carregar  # noqa: E402

REG = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = REG.Registro
estado_de = REG.derivar_estado
condicoes = REG.verificar_condicoes_encerramento_estado


class TestPoliticasA2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.soc = Path(self.tmp.name) / 'sociedade'
        self.soc.mkdir()
        self.reg = Registro.inicializar(self.soc, 'teste', self.tmp.name, versao_inicial='v1')
        self.reg = Registro(self.soc)
        self.reg.abrir_etapa('E1', 'objetivo', 'plano', 'aut', 'v1', ['C1'])
        self.reg.registrar_tarefa('E1', 'T1', especialista='Gandalf', descricao='t', fornecedor='Google')
        self.reg.atualizar_tarefa('E1', 'T1', 'concluida')
        self.reg.registrar_evidencia('E1', 'C1', 'python3 -m unittest', 0, 'Ran 3 tests\nOK', versao_entrega='v1')

    def tearDown(self):
        self.tmp.cleanup()

    def parecer(self, pid, veredito, nivel, versao='v1', fornecedor='OpenAI', revisor='Barbárvore'):
        kw = {'nivel_independencia': nivel}
        if nivel != 'A':
            kw['justificativa_independencia'] = 'sessão distinta do mesmo fornecedor, revisão interna'
        self.reg.registrar_parecer('E1', pid, revisor, fornecedor, ['Gandalf:Google'], versao, veredito,
                                   {'C1': veredito != 'nao_aceitar'}, **kw)

    def avaliar(self):
        ok, bloqueios, elegivel = condicoes(estado_de(Registro(self.soc).dados), 'E1')
        return ok, bloqueios, elegivel

    def test_q144_interno_aceitando_depois_do_independente_nao_rebaixa(self):
        self.parecer('P1', 'aceitar', 'A')
        self.parecer('P2', 'aceitar', 'C', fornecedor='OpenAI', revisor='Outra sessão')
        ok, bloqueios, elegivel = self.avaliar()
        self.assertTrue(ok, bloqueios)
        self.assertTrue(elegivel)

    def test_q144_interno_rejeitando_depois_do_independente_bloqueia(self):
        self.parecer('P1', 'aceitar', 'A')
        self.parecer('P2', 'nao_aceitar', 'C', fornecedor='OpenAI', revisor='Outra sessão')
        ok, bloqueios, _ = self.avaliar()
        self.assertFalse(ok)
        self.assertTrue(any('Q144' in b for b in bloqueios), bloqueios)

    def test_q144_sem_parecer_independente_nao_fica_elegivel(self):
        self.parecer('P1', 'aceitar', 'C', fornecedor='OpenAI', revisor='Outra sessão')
        _, _, elegivel = self.avaliar()
        self.assertFalse(elegivel)

    def test_q145_versao_nova_depois_do_parecer_bloqueia_ate_classificar(self):
        self.parecer('P1', 'aceitar', 'A')
        self.reg.registrar_versao('E1', 'v2')  # padrão agora é desconhecido
        ok, bloqueios, _ = self.avaliar()
        self.assertFalse(ok)
        self.assertTrue(any('impacto desconhecido' in b for b in bloqueios), bloqueios)
        self.reg.registrar_versao('E1', 'v2', impacto='sem_alto')
        ok, bloqueios, _ = self.avaliar()
        self.assertTrue(ok, bloqueios)

    def test_q145_impacto_alto_exige_nova_revisao(self):
        self.parecer('P1', 'aceitar', 'A')
        self.reg.registrar_versao('E1', 'v2', impacto='alto')
        ok, bloqueios, _ = self.avaliar()
        self.assertFalse(ok)
        self.parecer('P2', 'aceitar', 'A', versao='v2')
        ok, bloqueios, _ = self.avaliar()
        self.assertTrue(ok, bloqueios)


if __name__ == '__main__':
    unittest.main()
