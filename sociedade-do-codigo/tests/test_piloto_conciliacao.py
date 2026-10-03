import json
import tempfile
import unittest
from pathlib import Path

from util import NUCLEO, carregar

DIR_FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'conciliacao'
MOD_CONC = carregar(DIR_FIXTURES / 'conciliador.py', 'conciliador')
ConciliadorBancario = MOD_CONC.ConciliadorBancario
calcular_hash_dados = MOD_CONC.calcular_hash_dados

MOD_REG = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REG.Registro
agora_iso = MOD_REG.agora_iso


class TestePilotoConciliacao(unittest.TestCase):
    def setUp(self):
        with open(DIR_FIXTURES / 'extrato_ficticio.json', 'r', encoding='utf-8') as f:
            self.extrato = json.load(f)
        with open(DIR_FIXTURES / 'lancamentos_contabeis.json', 'r', encoding='utf-8') as f:
            self.razao = json.load(f)

    def test_quantidade_e_integridade_das_fixtures(self):
        """Verifica se as fixtures cumprem o critério Q45 (30 a 40 lançamentos de extrato)."""
        self.assertEqual(len(self.extrato), 35, 'Extrato deve conter entre 30 e 40 lançamentos')
        self.assertGreaterEqual(len(self.razao), 35, 'Razão deve conter registros contábeis equivalentes')
        
        # Hashes estáveis
        h_ext = calcular_hash_dados(self.extrato)
        h_raz = calcular_hash_dados(self.razao)
        self.assertEqual(len(h_ext), 64)
        self.assertEqual(len(h_raz), 64)

    def test_conciliacao_completa_e_regras_de_dominio(self):
        """Executa a conciliação completa e valida regras contábeis (1:1, 1:N, divergências, tarifas)."""
        conc = ConciliadorBancario(self.extrato, self.razao)
        conc.executar_ate_o_fim()
        relatorio = conc.obter_relatorio_final()
        resumo = relatorio['resumo']

        # Total processado
        self.assertEqual(resumo['total_lancamentos_extrato'], 35)

        # 1:N consolidado da folha salarial (EXT-006)
        self.assertEqual(resumo['total_conciliados_1_para_n'], 1)
        folha_n = relatorio['detalhes']['conciliados_1_para_n'][0]
        self.assertEqual(folha_n['extrato_id'], 'EXT-006')
        self.assertEqual(folha_n['quantidade_itens'], 6)
        self.assertEqual(folha_n['valor_extrato'], 28450.00)

        # Divergência de valor na NF-4490 (EXT-035 vs LCT-036)
        self.assertEqual(resumo['total_divergencias_valor'], 1)
        div = relatorio['detalhes']['divergencias_valor'][0]
        self.assertEqual(div['documento'], 'NF-4490')
        self.assertEqual(div['valor_extrato'], 1200.00)
        self.assertEqual(div['valor_razao'], 1250.00)
        self.assertEqual(div['diferenca'], -50.00)

        # Tarifas e pendências de extrato
        # EXT-002 (-85), EXT-013 (-12.50), EXT-030 (-120) -> tarifas
        # EXT-034 (-320) -> cobrança desconhecida
        self.assertEqual(resumo['total_pendencias_extrato'], 4)
        pend_motivos = [p['motivo'] for p in relatorio['detalhes']['pendencias_extrato']]
        self.assertEqual(pend_motivos.count('tarifa_a_apropriar'), 3)
        self.assertEqual(pend_motivos.count('sem_registro_contabil'), 1)

        # Pendências no razão: cheque não compensado (LCT-037) e provisão JCP (LCT-038)
        self.assertEqual(resumo['total_pendencias_razao'], 2)
        docs_razao = [p['documento'] for p in relatorio['detalhes']['pendencias_razao']]
        self.assertIn('CHQ-881', docs_razao)
        self.assertIn('JCP-202610', docs_razao)

        # Conciliados 1:1 exatos: 35 total - 1 (1:N) - 1 (divergência) - 4 (pendências) = 29
        self.assertEqual(resumo['total_conciliados_1_para_1'], 29)

        # Taxa de conciliação automática
        self.assertGreaterEqual(resumo['taxa_conciliacao_automatica'], 80.0)

    def test_interrupcao_e_retomada_controlada_q46(self):
        """Demonstra interrupção no meio do processamento e retomada idêntica (Q46)."""
        # Execução contínua de referência
        ref = ConciliadorBancario(self.extrato, self.razao)
        ref.executar_ate_o_fim()
        relatorio_ref = ref.obter_relatorio_final()

        # Execução 1: interrompida no 18º passo
        sessao_1 = ConciliadorBancario(self.extrato, self.razao)
        sessao_1.executar_ate_o_fim(limite_passos=18)
        self.assertEqual(sessao_1.indice_progresso, 18)
        checkpoint = sessao_1.salvar_checkpoint()

        # Execução 2: retomada por outra sessão a partir do checkpoint
        sessao_2 = ConciliadorBancario(self.extrato, self.razao)
        sessao_2.carregar_checkpoint(checkpoint)
        self.assertEqual(sessao_2.indice_progresso, 18)

        # Conclui os passos restantes
        sessao_2.executar_ate_o_fim()
        self.assertEqual(sessao_2.indice_progresso, 35)
        relatorio_retomado = sessao_2.obter_relatorio_final()

        # O resultado após a retomada deve ser 100% idêntico ao contínuo
        self.assertEqual(relatorio_retomado['resumo'], relatorio_ref['resumo'])
        self.assertEqual(relatorio_retomado['detalhes'], relatorio_ref['detalhes'])
        self.assertEqual(
            relatorio_retomado['integridade']['hash_resultado'],
            relatorio_ref['integridade']['hash_resultado']
        )

    def test_integracao_piloto_com_registro_sociedade(self):
        """Valida acompanhamento do piloto Palandir via eventos e evidências no registro.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pasta_soc = Path(tmpdir) / 'sociedade'
            reg = Registro.inicializar(pasta_soc, 'piloto_palandir', str(tmpdir))

            # 1. Abre etapa do piloto
            reg.abrir_etapa(
                etapa_id='SC-E4-PILOTO',
                objetivo='Executar piloto de conciliação bancária Palandir com 35 lançamentos e retomada Q46',
                plano_ref='planejamento.md#E4',
                autorizacao_ref='A-PILOTO-001',
                base_efetiva='head-e4',
                criterios=['C_CONCILIACAO_35_LANCAMENTOS', 'C_RETOMADA_INTERRUPCAO_Q46']
            )

            # 2. Registra tarefas dos especialistas
            reg.registrar_tarefa(
                etapa_id='SC-E4-PILOTO',
                tarefa_id='T-E4-01',
                especialista='Elrond',
                descricao='Preparação das fixtures e persistência de dados de conciliação',
                fornecedor='google'
            )

            reg.registrar_tarefa(
                etapa_id='SC-E4-PILOTO',
                tarefa_id='T-E4-02',
                especialista='Galadriel',
                descricao='Auditoria de regras contábeis, divergências e teste de retomada Q46',
                fornecedor='google'
            )

            # 3. Executa conciliação e gera evidências
            conc = ConciliadorBancario(self.extrato, self.razao)
            conc.executar_ate_o_fim()
            rel = conc.obter_relatorio_final()

            reg.registrar_evidencia(
                etapa_id='SC-E4-PILOTO',
                criterio_id='C_CONCILIACAO_35_LANCAMENTOS',
                comando='python3 -m unittest tests.test_piloto_conciliacao',
                exit_code=0,
                saida=(
                    f"Processados 35 lançamentos: 29 exatos, 1 folha 1:N (6 itens), "
                    f"1 divergência NF-4490, 4 pendências. Hash: {rel['integridade']['hash_resultado'][:12]}"
                ),
                versao_entrega='head-e4'
            )

            reg.registrar_evidencia(
                etapa_id='SC-E4-PILOTO',
                criterio_id='C_RETOMADA_INTERRUPCAO_Q46',
                comando='python3 -m unittest tests.test_piloto_conciliacao.TestePilotoConciliacao.test_interrupcao_e_retomada_controlada_q46',
                exit_code=0,
                saida='Interrupção no 18º lançamento e retomada confirmada: hash determinístico idêntico.',
                versao_entrega='head-e4'
            )

            # Finaliza tarefas
            reg.atualizar_tarefa('SC-E4-PILOTO', 'T-E4-01', 'concluida')
            reg.atualizar_tarefa('SC-E4-PILOTO', 'T-E4-02', 'concluida')

            # Verifica se os critérios foram atendidos
            est = reg.estado()
            etapa = est['etapa_atual']
            self.assertTrue(etapa['criterios']['C_CONCILIACAO_35_LANCAMENTOS']['atendido'])
            self.assertTrue(etapa['criterios']['C_RETOMADA_INTERRUPCAO_Q46']['atendido'])
            self.assertEqual(etapa['tarefas']['T-E4-01']['estado'], 'concluida')
            self.assertEqual(etapa['tarefas']['T-E4-02']['estado'], 'concluida')
