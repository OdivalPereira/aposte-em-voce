"""Testes estritos da cadeia de integridade (hash, prev_hash e corte explícito) no Registro.

Cobre os requisitos de F1 da etapa d1b-robustez e o fechamento do achado A02:
- Corte explícito e gravado entre formato antigo e cadeia
- Aceite de eventos legados estritamente antes do corte
- Recusa de eventos adulterados
- Recusa estrita de remoção de hash ou prev_hash na cauda e ao longo da cadeia
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from util import NUCLEO, carregar

MOD_REGISTRO = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REGISTRO.Registro
ErroRegistroCorrompido = MOD_REGISTRO.ErroRegistroCorrompido
ErroValidacaoRegistro = MOD_REGISTRO.ErroValidacaoRegistro


class TesteRegistroCadeiaEstrita(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.reg_path = self.pasta_sociedade / 'registro.json'
        self.reg = Registro.inicializar(self.pasta_sociedade, 'projeto-teste', str(self.p))

    def _ler_dados_disco(self):
        return json.loads(self.reg_path.read_text(encoding='utf-8'))

    def _gravar_dados_disco(self, dados):
        self.reg_path.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding='utf-8')

    # ==================== 1. Corte Explícito Gravado ====================

    def test_corte_explicito_gravado_na_primeira_mutacao(self):
        # Ao inicializar sem eventos, corte_cadeia ainda não é fixado
        dados_ini = self._ler_dados_disco()
        self.assertNotIn('corte_cadeia', dados_ini)
        self.assertIsNone(self.reg.corte_cadeia)

        # Primeira mutação grava corte explícito igual ao seq do primeiro evento da cadeia
        self.reg.abrir_etapa('E1', 'Objetivo E1', 'plano', 'aut', 'base1', ['C1'])
        dados = self._ler_dados_disco()
        self.assertIn('corte_cadeia', dados)
        self.assertEqual(dados['corte_cadeia'], 1)
        self.assertEqual(self.reg.corte_cadeia, 1)

        # O evento 1 possui prev_hash vazio e hash SHA-256 válido
        ev1 = dados['eventos'][0]
        self.assertEqual(ev1['seq'], 1)
        self.assertEqual(ev1['prev_hash'], '')
        self.assertTrue(ev1['hash'])
        self.assertEqual(ev1['hash'], MOD_REGISTRO.calcular_hash_evento(ev1))

    def test_corte_preservado_em_mutacoes_subsequentes(self):
        self.reg.abrir_etapa('E1', 'Objetivo E1', 'plano', 'aut', 'base1', ['C1'])
        self.assertEqual(self.reg.corte_cadeia, 1)

        self.reg.passar_bastao('E1', 'Galadriel', autor='Gandalf', nota='bastão')
        dados = self._ler_dados_disco()
        self.assertEqual(dados['corte_cadeia'], 1)
        self.assertEqual(len(dados['eventos']), 2)

        # Evento 2 encadeia sobre o hash do evento 1
        ev1, ev2 = dados['eventos'][0], dados['eventos'][1]
        self.assertEqual(ev2['prev_hash'], ev1['hash'])
        self.assertEqual(ev2['hash'], MOD_REGISTRO.calcular_hash_evento(ev2))

    def test_corte_explicito_em_mutacao_simulada(self):
        disco_sim, eventos = self.reg.abrir_etapa(
            'E1', 'Objetivo E1', 'plano', 'aut', 'base1', ['C1'], aplicar=False
        )
        self.assertEqual(disco_sim['corte_cadeia'], 1)
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]['seq'], 1)
        self.assertTrue(eventos[0]['hash'])

    # ==================== 2. Legado Antes do Corte ====================

    def test_legado_antes_do_corte_aceito(self):
        # Simula registro legado com evento seq 1 sem hash
        dados_legado = self._ler_dados_disco()
        dados_legado['eventos'] = [{
            'id': 'EVT-000001',
            'seq': 1,
            'tipo': 'nota_registrada',
            'timestamp': '2026-10-01T12:00:00Z',
            'autor': 'Legado',
            'dados': {'nota': 'evento legado anterior ao hash'},
        }]
        self._gravar_dados_disco(dados_legado)

        # Recarrega com sucesso como legado (sem corte definido ainda)
        reg_leg = Registro(self.pasta_sociedade)
        self.assertIsNone(reg_leg.corte_cadeia)
        self.assertEqual(len(reg_leg.eventos), 1)

        # Aplica mutação que inicia a cadeia no seq 2
        reg_leg.aplicar_mutacao(
            lambda d: [{'tipo': 'nota_registrada', 'dados': {'nota': 'primeiro da cadeia'}}],
            autor='Elrond',
            aplicar=True,
        )

        dados_migrados = self._ler_dados_disco()
        self.assertEqual(dados_migrados['corte_cadeia'], 2)
        self.assertEqual(len(dados_migrados['eventos']), 2)

        # Seq 1 é legado sem hash; Seq 2 é o corte da cadeia com hash
        ev1 = dados_migrados['eventos'][0]
        ev2 = dados_migrados['eventos'][1]
        self.assertNotIn('hash', ev1)
        self.assertNotIn('prev_hash', ev1)
        self.assertEqual(ev2['seq'], 2)
        self.assertEqual(ev2['prev_hash'], '')
        self.assertTrue(ev2['hash'])

        # Recarregamento via Registro valida o corte e o legado com sucesso
        reg_recarregado = Registro(self.pasta_sociedade)
        self.assertEqual(reg_recarregado.corte_cadeia, 2)
        self.assertEqual(len(reg_recarregado.eventos), 2)

    def test_evento_com_hash_antes_do_corte_recusado(self):
        # Se corte_cadeia é 2, o evento 1 deve ser puramente formato antigo (sem hash)
        dados = self._ler_dados_disco()
        dados['corte_cadeia'] = 2
        dados['eventos'] = [
            {
                'id': 'EVT-000001',
                'seq': 1,
                'tipo': 'nota_registrada',
                'timestamp': '2026-10-01T12:00:00Z',
                'autor': 'Tester',
                'hash': 'inconsistente_antes_do_corte',
                'dados': {},
            },
            {
                'id': 'EVT-000002',
                'seq': 2,
                'tipo': 'nota_registrada',
                'timestamp': '2026-10-01T12:01:00Z',
                'autor': 'Tester',
                'prev_hash': '',
                'dados': {},
            },
        ]
        dados['eventos'][1]['hash'] = MOD_REGISTRO.calcular_hash_evento(dados['eventos'][1])
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('anterior ao corte da cadeia', str(ctx.exception))

    # ==================== 3. Remoção de Hash na Cauda (Escape A02) ====================

    def test_remocao_hash_na_cauda_sem_legado_lanca_erro(self):
        # A02 central: registro novo, omitir hash e prev_hash do último evento
        self.reg.abrir_etapa('E1', 'Objetivo E1', 'plano', 'aut', 'base1', ['C1'])

        dados = self._ler_dados_disco()
        self.assertEqual(dados['corte_cadeia'], 1)
        ev_cauda = dados['eventos'][-1]
        ev_cauda.pop('hash', None)
        ev_cauda.pop('prev_hash', None)
        ev_cauda['dados']['objetivo'] = 'ADULTERADO'
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('sem hash obrigatório', str(ctx.exception))

    def test_remocao_hash_na_cauda_com_legado_lanca_erro(self):
        # A02 com legado: evento 1 legado, corte no seq 2, evento 2 na cauda sem hash
        dados = self._ler_dados_disco()
        dados['corte_cadeia'] = 2
        dados['eventos'] = [
            {
                'id': 'EVT-000001',
                'seq': 1,
                'tipo': 'nota_registrada',
                'timestamp': '2026-10-01T12:00:00Z',
                'autor': 'Legado',
                'dados': {'nota': 'legado'},
            },
            {
                'id': 'EVT-000002',
                'seq': 2,
                'tipo': 'nota_registrada',
                'timestamp': '2026-10-01T12:01:00Z',
                'autor': 'Invasor',
                'dados': {'nota': 'tentativa de omitir hash na cauda pós-legado'},
            },
        ]
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('sem hash obrigatório', str(ctx.exception))

    def test_remocao_prev_hash_na_cauda_lanca_erro(self):
        self.reg.abrir_etapa('E1', 'Objetivo E1', 'plano', 'aut', 'base1', ['C1'])

        dados = self._ler_dados_disco()
        ev_cauda = dados['eventos'][-1]
        ev_cauda.pop('prev_hash', None)
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('sem prev_hash obrigatório', str(ctx.exception))

    # ==================== 4. Adulterações e Rompimento de Cadeia ====================

    def test_adulteracao_conteudo_com_hash_mantido_lanca_erro(self):
        self.reg.abrir_etapa('E1', 'Objetivo E1', 'plano', 'aut', 'base1', ['C1'])

        dados = self._ler_dados_disco()
        dados['eventos'][-1]['dados']['objetivo'] = 'ADULTERADO'
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('Hash corrompido no evento', str(ctx.exception))

    def test_adulteracao_prev_hash_rompe_cadeia(self):
        self.reg.abrir_etapa('E1', 'Objetivo E1', 'plano', 'aut', 'base1', ['C1'])
        self.reg.passar_bastao('E1', 'Galadriel', autor='Gandalf')

        dados = self._ler_dados_disco()
        ev2 = dados['eventos'][1]
        ev2['prev_hash'] = 'f' * 64
        ev2['hash'] = MOD_REGISTRO.calcular_hash_evento(ev2)
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('Cadeia de hash rompida no evento', str(ctx.exception))

    def test_evento_sem_hash_no_meio_da_cadeia_lanca_erro(self):
        self.reg.abrir_etapa('E1', 'Objetivo E1', 'plano', 'aut', 'base1', ['C1'])
        self.reg.passar_bastao('E1', 'Galadriel', autor='Gandalf')
        self.reg.passar_bastao('E1', 'Elrond', autor='Gandalf')

        dados = self._ler_dados_disco()
        # Omitir hash do evento intermediário (seq 2)
        dados['eventos'][1].pop('hash', None)
        dados['eventos'][1].pop('prev_hash', None)
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('sem hash obrigatório', str(ctx.exception))

    # ==================== 5. Validação de corte_cadeia Inválido ====================

    def test_corte_cadeia_invalido_tipo_lanca_erro(self):
        dados = self._ler_dados_disco()
        dados['corte_cadeia'] = 'um'
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('Campo "corte_cadeia" inválido', str(ctx.exception))

    def test_corte_cadeia_invalido_booleano_lanca_erro(self):
        dados = self._ler_dados_disco()
        dados['corte_cadeia'] = True
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('Campo "corte_cadeia" inválido', str(ctx.exception))

    def test_corte_cadeia_invalido_negativo_lanca_erro(self):
        dados = self._ler_dados_disco()
        dados['corte_cadeia'] = 0
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('Campo "corte_cadeia" inválido', str(ctx.exception))

    def test_corte_cadeia_superior_ao_proximo_evento_lanca_erro(self):
        dados = self._ler_dados_disco()
        dados['eventos'] = [{
            'id': 'EVT-000001',
            'seq': 1,
            'tipo': 'nota_registrada',
            'timestamp': '2026-10-01T12:00:00Z',
            'autor': 'Legado',
            'dados': {'nota': 'legado'},
        }]
        # Temos 1 evento legado (seq 1). Próximo esperado seria 2. corte_cadeia = 10 é salto indevido
        dados['corte_cadeia'] = 10
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('superior ao próximo evento esperado', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
