"""Testes de migração de registros legados para cadeia estrita de hash (Achado K1).

Cobre os requisitos de K1 da rodada 2 da etapa d1b-robustez:
- Registro com eventos 1..41 sem hash, 42..51 com hash e sem corte_cadeia no disco: carregamento válido.
- Gravação de mutação via aplicar_mutacao ou via conferir --registrar: corte_cadeia é atribuído como 42 (não 52);
  o arquivo continua íntegro e re-carregável sem erro.
- Preservação da integridade e recusa estrita de adulterações antes e depois do corte.
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
MOD_CONFERIR = carregar(NUCLEO / 'scripts' / 'sc_conferir.py', 'sc_conferir')
Registro = MOD_REGISTRO.Registro
ErroRegistroCorrompido = MOD_REGISTRO.ErroRegistroCorrompido


def _criar_fixture_legado_com_cadeia(pasta_sociedade, total_legados=41, total_cadeia=10):
    """Cria registro.json sintético com eventos legados sem hash seguidos por cadeia com hash, sem corte_cadeia."""
    pasta_sociedade = Path(pasta_sociedade)
    pasta_sociedade.mkdir(parents=True, exist_ok=True)
    reg_path = pasta_sociedade / 'registro.json'

    eventos = []
    # Eventos legados 1..41 sem hash nem prev_hash
    for seq in range(1, total_legados + 1):
        eventos.append({
            'id': f'EVT-{seq:06d}',
            'seq': seq,
            'tipo': 'nota_registrada',
            'timestamp': f'2026-10-01T10:{seq:02d}:00Z',
            'autor': 'Gandalf',
            'dados': {'nota': f'evento legado {seq}'},
        })

    # Eventos 42..51 com cadeia de hash íntegra
    ultimo_hash = ''
    inicio_cadeia = total_legados + 1
    fim_cadeia = total_legados + total_cadeia
    for seq in range(inicio_cadeia, fim_cadeia + 1):
        ev = {
            'id': f'EVT-{seq:06d}',
            'seq': seq,
            'tipo': 'nota_registrada',
            'timestamp': f'2026-10-01T11:{seq - total_legados:02d}:00Z',
            'autor': 'Gandalf',
            'simulacao': False,
            'dados': {'nota': f'evento cadeia {seq}'},
            'prev_hash': ultimo_hash,
        }
        ev['hash'] = MOD_REGISTRO.calcular_hash_evento(ev)
        ultimo_hash = ev['hash']
        eventos.append(ev)

    dados = {
        'versao_formato': MOD_REGISTRO.VERSAO_FORMATO,
        'projeto_id': 'projeto-legado-k1',
        'caminho_canonico': str(pasta_sociedade.parent),
        'revisao': 1,
        'criado_em': '2026-10-01T10:00:00Z',
        'atualizado_em': '2026-10-01T11:10:00Z',
        'eventos': eventos,
        'resumos_externos': {},
    }
    # Sem corte_cadeia gravado previamente
    reg_path.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding='utf-8')
    return reg_path, inicio_cadeia, fim_cadeia


class TesteRegistroMigracaoLegado(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.reg_path, self.corte_esperado, self.ultimo_seq = _criar_fixture_legado_com_cadeia(
            self.pasta_sociedade, total_legados=41, total_cadeia=10
        )

    def _ler_dados_disco(self):
        return json.loads(self.reg_path.read_text(encoding='utf-8'))

    def _gravar_dados_disco(self, dados):
        self.reg_path.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding='utf-8')

    # ==================== 1. Carregamento Válido Sem corte_cadeia ====================

    def test_carregamento_registro_legado_sem_corte_valido(self):
        """Registro com 1..41 sem hash e 42..51 com hash carrega com sucesso."""
        dados_disco = self._ler_dados_disco()
        self.assertNotIn('corte_cadeia', dados_disco)

        reg = Registro(self.pasta_sociedade)
        self.assertIsNone(reg.corte_cadeia)
        self.assertEqual(len(reg.eventos), 51)
        self.assertEqual(reg.eventos[0]['seq'], 1)
        self.assertNotIn('hash', reg.eventos[0])
        self.assertEqual(reg.eventos[41]['seq'], 42)
        self.assertTrue(reg.eventos[41]['hash'])
        self.assertEqual(reg.eventos[41]['prev_hash'], '')
        self.assertEqual(reg.eventos[-1]['seq'], 51)
        self.assertTrue(reg.eventos[-1]['hash'])

    # ==================== 2. Gravação de Mutação (aplicar_mutacao) ====================

    def test_mutacao_via_aplicar_mutacao_atribui_corte_42(self):
        """Gravação de novo evento atribui corte_cadeia=42 (primeiro com hash) e não 52."""
        reg = Registro(self.pasta_sociedade)
        self.assertIsNone(reg.corte_cadeia)

        disco_atualizado, eventos_novos = reg.aplicar_mutacao(
            lambda d: [{'tipo': 'nota_registrada', 'dados': {'nota': 'evento 52'}}],
            autor='Elrond',
            aplicar=True,
        )

        self.assertEqual(disco_atualizado['corte_cadeia'], 42)
        self.assertEqual(len(eventos_novos), 1)
        self.assertEqual(eventos_novos[0]['seq'], 52)
        self.assertTrue(eventos_novos[0]['hash'])

        # Verifica persistência no disco
        dados_disco = self._ler_dados_disco()
        self.assertIn('corte_cadeia', dados_disco)
        self.assertEqual(dados_disco['corte_cadeia'], 42)
        self.assertNotEqual(dados_disco['corte_cadeia'], 52)
        self.assertEqual(len(dados_disco['eventos']), 52)

        # O arquivo continua íntegro e re-carregável sem erro
        reg_recarregado = Registro(self.pasta_sociedade)
        self.assertEqual(reg_recarregado.corte_cadeia, 42)
        self.assertEqual(len(reg_recarregado.eventos), 52)
        self.assertEqual(reg_recarregado.eventos[-1]['prev_hash'], reg_recarregado.eventos[-2]['hash'])

    def test_mutacao_simulada_atribui_corte_42_em_memoria(self):
        """Em simulação (aplicar=False), corte_cadeia é 42 em memória e disco fica intocado."""
        reg = Registro(self.pasta_sociedade)
        disco_sim, eventos = reg.aplicar_mutacao(
            lambda d: [{'tipo': 'nota_registrada', 'dados': {'nota': 'evento simulação'}}],
            autor='Elrond',
            aplicar=False,
        )
        self.assertEqual(disco_sim['corte_cadeia'], 42)
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]['seq'], 52)

        # Disco não foi alterado
        dados_disco = self._ler_dados_disco()
        self.assertNotIn('corte_cadeia', dados_disco)
        self.assertEqual(len(dados_disco['eventos']), 51)

    # ==================== 3. Gravação via conferir --registrar ====================

    def test_gravacao_via_conferir_registrar_atribui_corte_42(self):
        """Executar conferir --registrar grava conferencia_registrada com corte_cadeia=42."""
        # Prepara arquivo de ordem sintética
        ordem_path = self.pasta_sociedade / 'ordens' / 'etapa-teste.md'
        ordem_path.parent.mkdir(parents=True, exist_ok=True)
        ordem_path.write_text(
            '# Ordem Etapa Teste\n\n'
            '```entregas\n'
            'E1 | hash_confere | sociedade/registro.json | '
            f'{MOD_REGISTRO.calcular_hash_conteudo(self.reg_path.read_bytes())}\n'
            '```\n',
            encoding='utf-8'
        )

        rel = MOD_CONFERIR.conferir(ordem_path, raiz=self.p)
        MOD_CONFERIR.registrar(rel, pasta_sociedade=self.pasta_sociedade)

        dados_disco = self._ler_dados_disco()
        self.assertEqual(dados_disco['corte_cadeia'], 42)
        self.assertEqual(len(dados_disco['eventos']), 52)
        self.assertEqual(dados_disco['eventos'][-1]['tipo'], 'conferencia_registrada')
        self.assertEqual(dados_disco['eventos'][-1]['seq'], 52)

        # Recarregamento sem erro
        reg = Registro(self.pasta_sociedade)
        self.assertEqual(reg.corte_cadeia, 42)
        self.assertEqual(len(reg.eventos), 52)

    # ==================== 4. Importar Resumo em Legado ====================

    def test_importar_resumo_atribui_corte_42(self):
        """importar_resumo_projeto em legado define corte_cadeia=42 e não 52."""
        reg = Registro(self.pasta_sociedade)
        resumo = {
            'projeto_origem_id': 'outro-projeto',
            'etapa_id': 'E0',
            'revisao_origem': 1,
            'concluida': True,
            'simulacao': False,
            'elegivel_publicacao': True,
        }
        resumo['resumo_hash'] = MOD_REGISTRO.calcular_hash_conteudo(
            json.dumps(resumo, sort_keys=True)
        )
        reg.importar_resumo_projeto(resumo, autor='Elrond')

        dados_disco = self._ler_dados_disco()
        self.assertEqual(dados_disco['corte_cadeia'], 42)
        self.assertEqual(len(dados_disco['eventos']), 52)

        reg_recarregado = Registro(self.pasta_sociedade)
        self.assertEqual(reg_recarregado.corte_cadeia, 42)

    # ==================== 5. Adulterações Antes do Corte ====================

    def test_evento_legado_com_hash_apos_migracao_recusado(self):
        """Após migração com corte=42, evento legado < 42 com hash deve ser recusado."""
        reg = Registro(self.pasta_sociedade)
        reg.aplicar_mutacao(
            lambda d: [{'tipo': 'nota_registrada', 'dados': {'nota': 'novo'}}],
            autor='Elrond',
            aplicar=True,
        )

        dados = self._ler_dados_disco()
        self.assertEqual(dados['corte_cadeia'], 42)
        # Adultera o evento 10 inserindo hash indevido
        dados['eventos'][9]['hash'] = 'invalido_antes_do_corte'
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('anterior ao corte da cadeia', str(ctx.exception))

    def test_evento_legado_com_prev_hash_apos_migracao_recusado(self):
        """Após migração com corte=42, evento legado < 42 com prev_hash deve ser recusado."""
        reg = Registro(self.pasta_sociedade)
        reg.aplicar_mutacao(
            lambda d: [{'tipo': 'nota_registrada', 'dados': {'nota': 'novo'}}],
            autor='Elrond',
            aplicar=True,
        )

        dados = self._ler_dados_disco()
        self.assertEqual(dados['corte_cadeia'], 42)
        dados['eventos'][9]['prev_hash'] = ''
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('anterior ao corte da cadeia', str(ctx.exception))

    # ==================== 6. Adulterações Depois do Corte ====================

    def test_adulteracao_dados_apos_corte_recusada(self):
        """Adulterar payload de evento da cadeia (seq 45) rompe verificação de hash."""
        reg = Registro(self.pasta_sociedade)
        reg.aplicar_mutacao(
            lambda d: [{'tipo': 'nota_registrada', 'dados': {'nota': 'novo'}}],
            autor='Elrond',
            aplicar=True,
        )

        dados = self._ler_dados_disco()
        dados['eventos'][44]['dados']['nota'] = 'ADULTERADO'
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('Hash corrompido no evento', str(ctx.exception))

    def test_remocao_hash_na_cauda_apos_corte_recusada(self):
        """Remover hash do último evento (seq 52) viola hash obrigatório pós-corte."""
        reg = Registro(self.pasta_sociedade)
        reg.aplicar_mutacao(
            lambda d: [{'tipo': 'nota_registrada', 'dados': {'nota': 'novo'}}],
            autor='Elrond',
            aplicar=True,
        )

        dados = self._ler_dados_disco()
        dados['eventos'][-1].pop('hash', None)
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('sem hash obrigatório', str(ctx.exception))

    def test_rompimento_cadeia_prev_hash_recusado(self):
        """Alterar prev_hash do evento 46 rompe a cadeia."""
        reg = Registro(self.pasta_sociedade)
        reg.aplicar_mutacao(
            lambda d: [{'tipo': 'nota_registrada', 'dados': {'nota': 'novo'}}],
            autor='Elrond',
            aplicar=True,
        )

        dados = self._ler_dados_disco()
        ev = dados['eventos'][45]
        ev['prev_hash'] = '0' * 64
        ev['hash'] = MOD_REGISTRO.calcular_hash_evento(ev)
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('Cadeia de hash rompida no evento', str(ctx.exception))

    # ==================== 7. Adulterações Antes da Migração (Sem corte_cadeia) ====================

    def test_adulteracao_sem_corte_cadeia_recusada(self):
        """Mesmo antes de gravar mutação (corte_cadeia=None), adulterações são detectadas."""
        dados = self._ler_dados_disco()
        self.assertNotIn('corte_cadeia', dados)
        # Adultera payload do evento 42
        dados['eventos'][41]['dados']['nota'] = 'ADULTERADO'
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('Hash corrompido no evento', str(ctx.exception))

    def test_evento_sem_hash_apos_inicio_da_cadeia_sem_corte_cadeia_recusado(self):
        """Evento sem hash no meio da cadeia quando corte_cadeia é None é recusado."""
        dados = self._ler_dados_disco()
        # Remove hash do evento 45
        dados['eventos'][44].pop('hash', None)
        self._gravar_dados_disco(dados)

        with self.assertRaises(ErroRegistroCorrompido) as ctx:
            Registro(self.pasta_sociedade)
        self.assertIn('Cadeia de integridade rompida', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
