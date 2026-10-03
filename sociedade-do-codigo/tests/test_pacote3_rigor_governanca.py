"""Testes automatizados do Pacote 3: Rigor Empírico e Governança do Jules (§4 e §8).

Cobre:
- §4 / P4: Calibração empírica do gatilho de rigor (sc_calibrar_gatilho.py e sc_rodada.py calibrar);
- §8 / P8: Portão de Ferro de auditoria física de Draft PRs do Jules em 6 passos (sc_jules_portao.py);
- §8 / P8: Trava de contrapressão de fila (>= 8 PRs abertos) em sc_passagem.py despachar-jules;
- §8 / P8: Subcomando sc_passagem.py auditar-jules.

Somente biblioteca padrão do Python.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from util import NUCLEO, carregar, rodar

CALIBRAR_SCRIPT = NUCLEO / 'scripts' / 'sc_calibrar_gatilho.py'
PORTAO_SCRIPT = NUCLEO / 'scripts' / 'sc_jules_portao.py'
RODADA_SCRIPT = NUCLEO / 'scripts' / 'sc_rodada.py'
PASSAGEM_SCRIPT = NUCLEO / 'scripts' / 'sc_passagem.py'


class TesteCalibracaoGatilhoRigor(unittest.TestCase):
    """Testa o motor de calibração empírica dos 5 fatores de rigor (Q22)."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp_dir.name)
        self.mod_calibrar = carregar(CALIBRAR_SCRIPT, 'sc_calibrar_gatilho')

    def tearDown(self):
        self.tmp_dir.cleanup()

    def criar_registro_sintetico(self):
        """Cria registro.json contendo 4 etapas modeladas: 1 VP, 1 FP, 1 FN e 1 VN."""
        p_reg = self.pasta / 'registro.json'
        conteudo = {
            'versao_formato': '2.1.0',
            'projeto_id': 'teste-calibracao',
            'revisao': 1,
            'eventos': [
                # Etapa 1: VP (Nível 3, múltiplos fatores, achado bloqueador real)
                {
                    'id': 'EV-001', 'seq': 1, 'tipo': 'etapa_aberta', 'timestamp': '2026-09-23T10:00:00Z',
                    'dados': {
                        'etapa_id': 'E-VP',
                        'nivel': '3',
                        'objetivo': 'Novo contrato de api com persistencia em banco e algoritmo de complexidade',
                        'criterios': ['C1'],
                        'responsavel': 'Gandalf'
                    }
                },
                {
                    'id': 'EV-002', 'seq': 2, 'tipo': 'achado_registrado', 'timestamp': '2026-09-23T10:05:00Z',
                    'dados': {
                        'etapa_id': 'E-VP',
                        'achado_id': 'ACH-01',
                        'severidade': 'bloqueador',
                        'onde': 'api.py',
                        'descricao': 'Quebra de contrato'
                    }
                },
                {
                    'id': 'EV-003', 'seq': 3, 'tipo': 'etapa_encerrada', 'timestamp': '2026-09-23T10:09:00Z',
                    'dados': {
                        'etapa_id': 'E-VP',
                        'resumo': 'Encerrada',
                        'elegivel_publicacao': True
                    }
                },
                # Etapa 2: FP (Nível 3, múltiplos fatores, mas transcorreu trivial sem achados)
                {
                    'id': 'EV-004', 'seq': 4, 'tipo': 'etapa_aberta', 'timestamp': '2026-09-23T10:10:00Z',
                    'dados': {
                        'etapa_id': 'E-FP',
                        'nivel': '3',
                        'objetivo': 'Revisão de contrato e persistencia de estado',
                        'criterios': ['C1'],
                        'responsavel': 'Gandalf'
                    }
                },
                {
                    'id': 'EV-005', 'seq': 5, 'tipo': 'parecer_registrado', 'timestamp': '2026-09-23T10:15:00Z',
                    'dados': {
                        'etapa_id': 'E-FP',
                        'parecer_id': 'PAR-01',
                        'revisor': 'Claude',
                        'fornecedor_revisor': 'Anthropic',
                        'veredito': 'aceitar',
                        'versao_examinada': 'HEAD'
                    }
                },
                {
                    'id': 'EV-006', 'seq': 6, 'tipo': 'etapa_encerrada', 'timestamp': '2026-09-23T10:19:00Z',
                    'dados': {
                        'etapa_id': 'E-FP',
                        'resumo': 'Encerrada',
                        'elegivel_publicacao': True
                    }
                },
                # Etapa 3: FN (Nível 1, objetivo simples sem fatores, mas sofreu defeito bloqueador)
                {
                    'id': 'EV-007', 'seq': 7, 'tipo': 'etapa_aberta', 'timestamp': '2026-09-23T10:20:00Z',
                    'dados': {
                        'etapa_id': 'E-FN',
                        'nivel': '1',
                        'objetivo': 'Ajuste cosmético em texto',
                        'criterios': ['C1'],
                        'responsavel': 'Gandalf'
                    }
                },
                {
                    'id': 'EV-008', 'seq': 8, 'tipo': 'achado_registrado', 'timestamp': '2026-09-23T10:25:00Z',
                    'dados': {
                        'etapa_id': 'E-FN',
                        'achado_id': 'ACH-02',
                        'severidade': 'bloqueador',
                        'onde': 'texto.md',
                        'descricao': 'Erro grave inesperado'
                    }
                },
                {
                    'id': 'EV-009', 'seq': 9, 'tipo': 'etapa_encerrada', 'timestamp': '2026-09-23T10:29:00Z',
                    'dados': {
                        'etapa_id': 'E-FN',
                        'resumo': 'Encerrada',
                        'elegivel_publicacao': True
                    }
                },
                # Etapa 4: VN (Nível 1, sem fatores e sem achados)
                {
                    'id': 'EV-010', 'seq': 10, 'tipo': 'etapa_aberta', 'timestamp': '2026-09-23T10:30:00Z',
                    'dados': {
                        'etapa_id': 'E-VN',
                        'nivel': '1',
                        'objetivo': 'Correção de typo simples',
                        'criterios': ['C1'],
                        'responsavel': 'Gandalf'
                    }
                },
                {
                    'id': 'EV-011', 'seq': 11, 'tipo': 'parecer_registrado', 'timestamp': '2026-09-23T10:35:00Z',
                    'dados': {
                        'etapa_id': 'E-VN',
                        'parecer_id': 'PAR-02',
                        'revisor': 'Claude',
                        'fornecedor_revisor': 'Anthropic',
                        'veredito': 'aceitar',
                        'versao_examinada': 'HEAD'
                    }
                },
                {
                    'id': 'EV-012', 'seq': 12, 'tipo': 'etapa_encerrada', 'timestamp': '2026-09-23T10:39:00Z',
                    'dados': {
                        'etapa_id': 'E-VN',
                        'resumo': 'Encerrada',
                        'elegivel_publicacao': True
                    }
                }
            ]
        }
        p_reg.write_text(json.dumps(conteudo, indent=2), encoding='utf-8')
        return p_reg

    def test_extracao_fatores_e_desfecho(self):
        """Testa heurística determinística de fatores e classificação de desfecho."""
        etapa_simples = {
            'objetivo': 'Ajustar layout e schema de novos contratos',
            'tarefas': {
                'T1': {'descricao': 'persistencia em sqlite e banco de dados'}
            },
            'criterios': {},
            'achados': {
                'A1': {'severidade': 'bloqueador'}
            },
            'pareceres': []
        }
        fatores = self.mod_calibrar.extrair_fatores_etapa(etapa_simples)
        self.assertTrue(fatores['novos_contratos'])
        self.assertTrue(fatores['persistencia'])

        desfecho = self.mod_calibrar.avaliar_desfecho_etapa(etapa_simples)
        self.assertTrue(desfecho['necessitou_rigor'])
        self.assertEqual(desfecho['total_bloqueadores'], 1)

    def test_matriz_confusao_e_metricas(self):
        """Valida cálculo exato da matriz de confusão e taxas analíticas."""
        p_reg = self.criar_registro_sintetico()
        dados = json.loads(p_reg.read_text(encoding='utf-8'))

        resultado = self.mod_calibrar.calibrar_gatilho_rigor(dados, limiar_fatores=2)
        self.assertTrue(resultado['sucesso'])
        self.assertEqual(resultado['total_etapas'], 4)

        mc = resultado['matriz_confusao']
        self.assertEqual(mc['verdadeiros_positivos'], 1, 'E-VP deve ser VP')
        self.assertEqual(mc['falsos_positivos'], 1, 'E-FP deve ser FP')
        self.assertEqual(mc['falsos_negativos'], 1, 'E-FN deve ser FN')
        self.assertEqual(mc['verdadeiros_negativos'], 1, 'E-VN deve ser VN')

        met = resultado['metricas']
        self.assertEqual(met['sensibilidade'], 0.5)
        self.assertEqual(met['especificidade'], 0.5)
        self.assertEqual(met['precisao'], 0.5)
        self.assertEqual(met['acuracia'], 0.5)
        self.assertEqual(met['taxa_sobrecarga_cerimonial'], 0.5)
        self.assertEqual(met['taxa_risco_residual'], 0.5)

    def test_cli_sc_calibrar_gatilho(self):
        """Testa execução pela CLI de sc_calibrar_gatilho.py em formatos texto e json."""
        p_reg = self.criar_registro_sintetico()

        # Saída em JSON
        res_json = rodar(CALIBRAR_SCRIPT, '--registro', p_reg, '--formato', 'json')
        self.assertEqual(res_json.returncode, 0)
        dados_saida = json.loads(res_json.stdout)
        self.assertTrue(dados_saida['sucesso'])
        self.assertEqual(dados_saida['matriz_confusao']['verdadeiros_positivos'], 1)

        # Saída em Texto
        res_txt = rodar(CALIBRAR_SCRIPT, '--registro', p_reg, '--formato', 'texto')
        self.assertEqual(res_txt.returncode, 0)
        self.assertIn('CALIBRAÇÃO EMPÍRICA DO GATILHO DE RIGOR', res_txt.stdout)
        self.assertIn('[VP] Rigor elevado necessário', res_txt.stdout)

    def test_cli_sc_rodada_calibrar(self):
        """Testa integração do subcomando sc_rodada.py calibrar."""
        self.criar_registro_sintetico()
        res = rodar(RODADA_SCRIPT, '--pasta', self.pasta, 'calibrar', '--formato', 'json')
        self.assertEqual(res.returncode, 0)
        dados = json.loads(res.stdout)
        self.assertTrue(dados['sucesso'])
        self.assertEqual(dados['total_etapas'], 4)


class TestePortaoDeFerroJules(unittest.TestCase):
    """Testa os 6 passos locais de auditoria física de Draft PRs do Jules."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp_dir.name)
        self.mod_portao = carregar(PORTAO_SCRIPT, 'sc_jules_portao')
        self.portao = self.mod_portao.PortaoDeFerroJules(self.pasta)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_passo1_rejeicao_arquivo_fora_do_escopo(self):
        """Passo 1 rejeita PR com arquivo não autorizado."""
        ok, msg = self.portao.passo1_inspecionar_escopo(
            arquivos_alterados=['src/valido.py', 'src/intruso.py'],
            arquivos_permitidos=['src/valido.py']
        )
        self.assertFalse(ok)
        self.assertIn('Violação de escopo', msg)
        self.assertIn('src/intruso.py', msg)

    def test_passo1_rejeicao_arquivo_sensivel(self):
        """Passo 1 rejeita PR que toque em segredos (.env, chaves)."""
        ok, msg = self.portao.passo1_inspecionar_escopo(
            arquivos_alterados=['.env'],
            arquivos_permitidos=['.env']
        )
        self.assertFalse(ok)
        self.assertIn('Violação de segurança', msg)

    def test_passo2_arquivo_inexistente_no_disco(self):
        """Passo 2 rejeita se o arquivo alterado não existir no disco."""
        ok, msg, _ = self.portao.passo2_verificar_integridade_arquivos(['arquivo_fantasma.py'])
        self.assertFalse(ok)
        self.assertIn('não existe fisicamente no disco', msg)

    def test_passo3_rejeicao_erro_sintaxe_python(self):
        """Passo 3 rejeita código Python com SyntaxError."""
        arq_quebrado = self.pasta / 'quebrado.py'
        arq_quebrado.write_text('def func_com_sintaxe_invalida(:\n  pass', encoding='utf-8')

        ok, msg = self.portao.passo3_compilacao_sintaxe(['quebrado.py'])
        self.assertFalse(ok)
        self.assertIn('Erro de sintaxe/compilação', msg)

    def test_passo4_comando_teste_local(self):
        """Passo 4 executa comando de teste e exige código de saída 0."""
        ok_sucesso, _, code_ok, _ = self.portao.passo4_executar_comando_teste('python3 -c "exit(0)"')
        self.assertTrue(ok_sucesso)
        self.assertEqual(code_ok, 0)

        ok_falha, msg_falha, code_falha, _ = self.portao.passo4_executar_comando_teste('python3 -c "exit(1)"')
        self.assertFalse(ok_falha)
        self.assertEqual(code_falha, 1)
        self.assertIn('falhou com código 1', msg_falha)

    def test_passo6_rejeicao_teste_tautologico(self):
        """Passo 6 rejeita teste contendo 'assert True' ou teste evasivo."""
        arq_teste = self.pasta / 'test_evasivo.py'
        arq_teste.write_text('import unittest\nclass T(unittest.TestCase):\n  def test_a(self):\n    assert True\n', encoding='utf-8')

        ok, msg = self.portao.passo6_auditar_integridade_evidencias(['test_evasivo.py'])
        self.assertFalse(ok)
        self.assertIn('Teste tautológico/evasivo proibido', msg)

    def test_passo6_rejeicao_caminho_local_absoluto(self):
        """Passo 6 rejeita código com caminhos locais absolutos vazados."""
        arq_codigo = self.pasta / 'servico.py'
        arq_codigo.write_text('CAMINHO = "/home/usuario/dados.txt"\n', encoding='utf-8')

        ok, msg = self.portao.passo6_auditar_integridade_evidencias(['servico.py'])
        self.assertFalse(ok)
        self.assertIn('Caminho absoluto local proibido detectado', msg)

    def test_auditoria_completa_aprovada(self):
        """Testa aprovação de PR com todos os 6 passos válidos."""
        arq_codigo = self.pasta / 'valido.py'
        arq_codigo.write_text('def soma(a, b):\n    return a + b\n', encoding='utf-8')

        arq_teste = self.pasta / 'test_valido.py'
        arq_teste.write_text(
            'import unittest\nfrom valido import soma\nclass T(unittest.TestCase):\n  def test_soma(self):\n    self.assertEqual(soma(2, 3), 5)\n',
            encoding='utf-8'
        )

        res = self.portao.auditar_pr(
            arquivos_permitidos=['valido.py', 'test_valido.py'],
            arquivos_alterados=['valido.py', 'test_valido.py'],
            comando_teste='python3 -m unittest test_valido.py',
            tarefa_id='T-JULES-01',
            pr_id='PR-42'
        )
        self.assertEqual(res['status'], 'APROVADO')
        self.assertIsNone(res['passo_falha'])
        self.assertEqual(len(res['passos']), 6)
        self.assertTrue(all(p['aprovado'] for p in res['passos']))

    def test_cli_sc_jules_portao(self):
        """Testa CLI sc_jules_portao.py com saída formatada e código de retorno."""
        arq = self.pasta / 'modulo.py'
        arq.write_text('x = 42\n', encoding='utf-8')

        res = rodar(
            PORTAO_SCRIPT,
            '--pasta-projeto', self.pasta,
            '--arquivos-permitidos', 'modulo.py',
            '--arquivos-alterados', 'modulo.py',
            '--comando-teste', 'python3 -c "import modulo; assert modulo.x == 42"'
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn('PORTÃO DE FERRO DE AUDITORIA FÍSICA', res.stdout)
        self.assertIn('Todos os 6 passos cumpridos com retorno zero', res.stdout)


class TesteGovernancaPassagemJules(unittest.TestCase):
    """Testa a trava de contrapressão de fila e o subcomando auditar-jules em sc_passagem.py."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp_dir.name)
        self.pasta_soc = self.pasta / 'sociedade'
        self.pasta_soc.mkdir(parents=True, exist_ok=True)

        # Inicializa registro.json
        reg_init = {
            'versao_formato': '2.1.0',
            'projeto_id': 'teste-governanca',
            'revisao': 1,
            'eventos': [
                {
                    'id': 'EV-001', 'seq': 1, 'tipo': 'etapa_aberta', 'timestamp': '2026-09-23T10:00:00Z',
                    'dados': {
                        'etapa_id': 'SC-TESTE',
                        'nivel': '2',
                        'objetivo': 'Etapa de teste de contrapressão',
                        'criterios': ['C1'],
                        'responsavel': 'Gandalf'
                    }
                }
            ]
        }
        (self.pasta_soc / 'registro.json').write_text(json.dumps(reg_init, indent=2), encoding='utf-8')

        # Cria arquivo no projeto
        (self.pasta / 'app.py').write_text('print("ok")\n', encoding='utf-8')

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_bloqueio_por_contrapressao_despachar_jules(self):
        """Bloqueia despacho quando a fila de PRs abertos atinge ou supera o teto de 8."""
        res = rodar(
            PASSAGEM_SCRIPT,
            'despachar-jules',
            '--etapa', 'SC-TESTE',
            '--fatia', 'F1',
            '--tarefa', 'T-JULES-01',
            '--arquivos', 'app.py',
            '--instrucoes', 'Adicionar suporte a logging mecânico',
            '--prs-abertos', '8',
            '--max-prs-abertos', '8',
            '--pasta-sociedade', self.pasta_soc,
            '--pasta-projeto', self.pasta
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn('Contrapressão: Jules possui 8 tarefas/PRs abertos', res.stderr)
        self.assertIn('esvazie a fila', res.stderr)

    def test_despacho_autorizado_abaixo_da_contrapressao(self):
        """Permite despacho quando a fila estiver abaixo do teto regulamentar."""
        res = rodar(
            PASSAGEM_SCRIPT,
            'despachar-jules',
            '--etapa', 'SC-TESTE',
            '--fatia', 'F1',
            '--tarefa', 'T-JULES-02',
            '--arquivos', 'app.py',
            '--instrucoes', 'Adicionar documentação mecânica',
            '--prs-abertos', '3',
            '--max-prs-abertos', '8',
            '--pasta-sociedade', self.pasta_soc,
            '--pasta-projeto', self.pasta
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn('TAREFA JULES DESPACHADA', res.stdout)
        self.assertIn('Janela assíncrona mandatória: 45 minutos', res.stdout)

    def test_cli_auditar_jules_em_sc_passagem(self):
        """Testa o subcomando auditar-jules em sc_passagem.py com aprovação."""
        arq_teste = self.pasta / 'test_app.py'
        arq_teste.write_text(
            'import unittest\nclass T(unittest.TestCase):\n  def test_ok(self):\n    self.assertEqual(2+2, 4)\n',
            encoding='utf-8'
        )

        res = rodar(
            PASSAGEM_SCRIPT,
            'auditar-jules',
            '--arquivos-permitidos', 'app.py', 'test_app.py',
            '--arquivos-alterados', 'app.py', 'test_app.py',
            '--comando-teste', 'python3 -m unittest test_app.py',
            '--tarefa', 'T-JULES-03',
            '--pr', 'PR-10',
            '--pasta-sociedade', self.pasta_soc,
            '--pasta-projeto', self.pasta
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn('PORTÃO DE FERRO DE AUDITORIA FÍSICA', res.stdout)
        self.assertIn('Todos os 6 passos cumpridos com retorno zero', res.stdout)


if __name__ == '__main__':
    unittest.main()
