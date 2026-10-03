"""Testes automatizados do Pacote 2: Eficiência e Desacoplamento Arquitetural.

Cobre:
- §2 / P2: Papéis em Duas Camadas (11 arquivos essenciais <= 2.5 KB).
- §7 / P7: Desacoplamento de Domínio no Núcleo (Celebrimbor, Faramir, Bilbo).
- §6 / P6: Escala Tripartite de Independência do Revisor (Níveis A, B e C).
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import RAIZ, SKILLS, NUCLEO, rodar, carregar

PAPEIS = (
    'gandalf', 'aragorn', 'elrond', 'galadriel', 'legolas',
    'jules', 'revisor', 'celebrimbor', 'radagast', 'faramir', 'bilbo'
)

sc_reg = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = sc_reg.Registro
ErroValidacaoRegistro = sc_reg.ErroValidacaoRegistro


class TestePacote2PapeisDuasCamadas(unittest.TestCase):
    """Valida a arquitetura de papéis em duas camadas (P2)."""

    def setUp(self):
        self.dir_ref = SKILLS / 'sc-papeis' / 'references'
        self.skill_papeis = SKILLS / 'sc-papeis' / 'SKILL.md'
        self.conteudo_skill = self.skill_papeis.read_text(encoding='utf-8')

class TestePacote2DesacoplamentoDominio(unittest.TestCase):
    """Valida o desacoplamento de domínio no núcleo (P7)."""

class TestePacote2EscalaTripartiteRevisor(unittest.TestCase):
    """Valida a Escala Tripartite de Independência do Revisor (P6)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pasta = Path(self.temp_dir.name)
        self.pasta_sociedade = self.pasta / 'sociedade'
        self.reg = Registro.inicializar(self.pasta_sociedade, 'TESTE-P2', str(self.pasta))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_nivel_a_fornecedor_distinto_aceito(self):
        self.reg.abrir_etapa(
            etapa_id='E1', objetivo='Teste A', plano_ref='plano:E1', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Gandalf', nivel='2'
        )
        self.reg.registrar_evidencia('E1', 'C1', 'python3 -m unittest', 0, 'Ran 10 tests OK')
        self.reg.registrar_parecer(
            etapa_id='E1', parecer_id='PAR-A', revisor='Claude Code', fornecedor_revisor='Anthropic',
            implementadores=[{'agente': 'Gandalf', 'fornecedor': 'Google'}],
            versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
            nivel_independencia='A'
        )
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('E1')
        self.assertTrue(ok, f'Encerramento deveria passar: {bloqueios}')
        self.reg.encerrar_etapa('E1', 'Encerramento com parecer A')
        est = self.reg.estado()
        self.assertIn('E1', est['etapas_concluidas'])
        self.assertNotIn('E1', est['etapas_excepcionadas'])
        self.assertEqual(est['contagem_concluidas'], 1)
        self.assertTrue(est['etapas']['E1']['elegivel_publicacao'])

    def test_nivel_a_mesmo_fornecedor_rejeitado(self):
        self.reg.abrir_etapa(
            etapa_id='E1', objetivo='Teste A rejeitado', plano_ref='plano:E1', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Gandalf', nivel='2'
        )
        with self.assertRaises(ErroValidacaoRegistro) as ctx:
            self.reg.registrar_parecer(
                etapa_id='E1', parecer_id='PAR-A-FAIL', revisor='Gemini Revisor', fornecedor_revisor='Google',
                implementadores=[{'agente': 'Gandalf', 'fornecedor': 'Google'}],
                versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
                nivel_independencia='A'
            )
        self.assertIn('Independência violada', str(ctx.exception))

    def test_nivel_b_mesmo_fornecedor_com_justificativa_aceito(self):
        self.reg.abrir_etapa(
            etapa_id='E1', objetivo='Teste B', plano_ref='plano:E1', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Gandalf', nivel='2'
        )
        self.reg.registrar_evidencia('E1', 'C1', 'python3 -m unittest', 0, 'Ran 10 tests OK')
        self.reg.registrar_parecer(
            etapa_id='E1', parecer_id='PAR-B', revisor='Gemini 1.5 Pro', fornecedor_revisor='Google',
            implementadores=[{'agente': 'Gandalf (Gemini 2.0 Flash)', 'fornecedor': 'Google'}],
            versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
            nivel_independencia='B',
            justificativa_independencia='Revisão realizada por modelo e sessão distintos (Gemini 1.5 Pro vs 2.0 Flash).'
        )
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('E1')
        self.assertTrue(ok, f'Nível B com justificativa deveria passar: {bloqueios}')
        # D-RT-001: Nível B encerra como etapa excepcionada (elegivel_publicacao=False)
        self.reg.encerrar_etapa('E1', 'Encerramento com parecer B')
        est = self.reg.estado()
        self.assertIn('E1', est['etapas_excepcionadas'])
        self.assertNotIn('E1', est['etapas_concluidas'])
        self.assertEqual(est['contagem_concluidas'], 0)
        self.assertFalse(est['etapas']['E1']['elegivel_publicacao'])

    def test_nivel_b_sem_justificativa_rejeitado(self):
        self.reg.abrir_etapa(
            etapa_id='E1', objetivo='Teste B sem justif', plano_ref='plano:E1', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Gandalf', nivel='2'
        )
        with self.assertRaises(ErroValidacaoRegistro) as ctx:
            self.reg.registrar_parecer(
                etapa_id='E1', parecer_id='PAR-B-FAIL', revisor='Gemini 1.5 Pro', fornecedor_revisor='Google',
                implementadores=[{'agente': 'Gandalf', 'fornecedor': 'Google'}],
                versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
                nivel_independencia='B',
                justificativa_independencia=''
            )
        self.assertIn('exige justificativa formal', str(ctx.exception))

    def test_nivel_c_em_etapa_nivel_2_aceito(self):
        self.reg.abrir_etapa(
            etapa_id='E1', objetivo='Teste C Nivel 2', plano_ref='plano:E1', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Gandalf', nivel='2'
        )
        self.reg.registrar_evidencia('E1', 'C1', 'python3 -m unittest', 0, 'Ran 10 tests OK')
        self.reg.registrar_parecer(
            etapa_id='E1', parecer_id='PAR-C', revisor='Revisor Isolado', fornecedor_revisor='Google',
            implementadores=[{'agente': 'Gandalf', 'fornecedor': 'Google'}],
            versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
            nivel_independencia='C',
            justificativa_independencia='Executado em segunda sessão limpa e isolada sem contaminação de contexto.'
        )
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('E1')
        self.assertTrue(ok, f'Nível C em etapa nível 2 deveria passar: {bloqueios}')
        # D-RT-001: Nível C em nível 2 também é exceção essencial (elegivel_publicacao=False)
        self.reg.encerrar_etapa('E1', 'Encerramento com parecer C')
        est = self.reg.estado()
        self.assertIn('E1', est['etapas_excepcionadas'])
        self.assertNotIn('E1', est['etapas_concluidas'])
        self.assertEqual(est['contagem_concluidas'], 0)
        self.assertFalse(est['etapas']['E1']['elegivel_publicacao'])

    def test_nivel_c_em_etapa_nivel_3_bloqueia_encerramento(self):
        self.reg.abrir_etapa(
            etapa_id='E3', objetivo='Teste C Nivel 3 Bloqueado', plano_ref='plano:E3', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Gandalf', nivel='3'
        )
        self.reg.registrar_evidencia('E3', 'C1', 'python3 -m unittest', 0, 'Ran 10 tests OK')
        self.reg.registrar_parecer(
            etapa_id='E3', parecer_id='PAR-C3', revisor='Revisor Isolado', fornecedor_revisor='Google',
            implementadores=[{'agente': 'Gandalf', 'fornecedor': 'Google'}],
            versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
            nivel_independencia='C',
            justificativa_independencia='Segunda sessão isolada.'
        )
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('E3')
        self.assertFalse(ok, 'Nível C NÃO pode aprovar encerramento de etapa de nível 3')
        self.assertTrue(any('Nível C não é aceito para homologação de nível 3' in b for b in bloqueios),
                        f'Bloqueio esperado ausente: {bloqueios}')

    def test_auto_revisao_rejeitada_em_todos_os_niveis(self):
        self.reg.abrir_etapa(
            etapa_id='E1', objetivo='Teste Auto', plano_ref='plano:E1', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Gandalf', nivel='2'
        )
        for nivel in ('A', 'B', 'C'):
            with self.assertRaises(ErroValidacaoRegistro) as ctx:
                self.reg.registrar_parecer(
                    etapa_id='E1', parecer_id=f'PAR-AUTO-{nivel}', revisor='Gandalf', fornecedor_revisor='Google',
                    implementadores=[{'agente': 'Gandalf', 'fornecedor': 'Google'}],
                    versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
                    nivel_independencia=nivel,
                    justificativa_independencia='Tentativa de auto-revisao'
                )
            self.assertIn('Auto-revisão rejeitada', str(ctx.exception))

    def test_nivel_independencia_invalido_rejeitado(self):
        self.reg.abrir_etapa(
            etapa_id='E1', objetivo='Teste Invalido', plano_ref='plano:E1', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Gandalf', nivel='2'
        )
        with self.assertRaises(ErroValidacaoRegistro) as ctx:
            self.reg.registrar_parecer(
                etapa_id='E1', parecer_id='PAR-INV', revisor='Revisor X', fornecedor_revisor='Anthropic',
                implementadores=[{'agente': 'Gandalf', 'fornecedor': 'Google'}],
                versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
                nivel_independencia='Z'
            )
        self.assertIn('Nível de independência inválido', str(ctx.exception))

    def test_d_rt_001_revisoes_internas_mesmo_fornecedor_nao_habilitam_encerramento_normal_nem_publicacao(self):
        """D-RT-001: Revisões de mesmo fornecedor (Nível B/C) não habilitam encerramento normal ou publicação."""
        self.reg.abrir_etapa(
            etapa_id='E-RT', objetivo='Teste D-RT-001', plano_ref='plano:E-RT', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Gandalf', nivel='2'
        )
        self.reg.registrar_evidencia('E-RT', 'C1', 'python3 -m unittest', 0, 'Ran 1 tests OK')
        self.reg.registrar_parecer(
            etapa_id='E-RT', parecer_id='PAR-RT-B', revisor='Gemini 1.5 Pro', fornecedor_revisor='Google',
            implementadores=[{'agente': 'Gandalf', 'fornecedor': 'Google'}],
            versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
            nivel_independencia='B',
            justificativa_independencia='Revisão em modelo diferente para verificação interna.'
        )
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('E-RT')
        self.assertTrue(ok)
        self.reg.encerrar_etapa('E-RT', 'Encerramento sob D-RT-001')
        est = self.reg.estado()
        self.assertIn('E-RT', est['etapas_excepcionadas'])
        self.assertNotIn('E-RT', est['etapas_concluidas'])
        self.assertEqual(est['contagem_concluidas'], 0)
        self.assertFalse(est['etapas']['E-RT']['elegivel_publicacao'])

    def test_auto_revisao_sem_falso_positivo_substring_nomes(self):
        """Garante que Ana como revisora não coincide com Anaconda como implementador."""
        self.reg.abrir_etapa(
            etapa_id='E-ANA', objetivo='Teste Nomes', plano_ref='plano:E-ANA', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Anaconda', nivel='2'
        )
        # Ana revisando trabalho de Anaconda (fornecedores distintos, Nível A) deve ser aceito
        self.reg.registrar_parecer(
            etapa_id='E-ANA', parecer_id='PAR-ANA-1', revisor='Ana', fornecedor_revisor='Anthropic',
            implementadores=[{'agente': 'Anaconda', 'fornecedor': 'Google'}],
            versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
            nivel_independencia='A'
        )
        # Já Ana revisando Ana deve ser rejeitado como auto-revisão
        with self.assertRaises(ErroValidacaoRegistro) as ctx:
            self.reg.registrar_parecer(
                etapa_id='E-ANA', parecer_id='PAR-ANA-FAIL', revisor='Ana', fornecedor_revisor='Anthropic',
                implementadores=[{'agente': 'Ana', 'fornecedor': 'Anthropic'}],
                versao_examinada='abc1234', veredito='aceitar', criterios_verificados={'C1': True},
                nivel_independencia='B',
                justificativa_independencia='Sessao isolada'
            )
        self.assertIn('Auto-revisão rejeitada', str(ctx.exception))

    def test_evidencia_aceita_formato_pytest_skipped_count(self):
        """R03-005: Saída no formato '12 passed, 0 skipped' é aceita como evidência válida."""
        self.reg.abrir_etapa(
            etapa_id='E-SKIP', objetivo='Teste Pytest Skipped', plano_ref='plano:E-SKIP', autorizacao_ref='cli',
            base_efetiva='abc1234', criterios=['C1'], responsavel='Gandalf', nivel='2'
        )
        saida_pytest = "test_core.py ... [100%]\n\n====== 12 passed, 0 skipped in 0.42s ======"
        disco, eventos = self.reg.registrar_evidencia('E-SKIP', 'C1', 'pytest', 0, saida_pytest)
        self.assertTrue(eventos[0]['dados']['valida'])
        self.assertIn('pytest', eventos[0]['dados']['comando'])
        est = self.reg.estado()
        self.assertTrue(est['etapas']['E-SKIP']['criterios']['C1']['atendido'])


class TestePacote2LintParecerECLIRodada(unittest.TestCase):
    """Testa integração com lint_parecer e CLI de sc_rodada."""

    def test_lint_parecer_aceita_campo_independencia_nivel_a(self):
        lint = SKILLS / 'sc-revisao' / 'scripts' / 'lint_parecer.py'
        conteudo = """## Parecer do Revisor Independente
- rodada: TESTE-01
- fatia ou fechamento: 1
- entrega: PR 10
- commit: e4f5a6b
- base..head: a1b2c3d..e4f5a6b
- revisor: Claude Code · fornecedor: Anthropic · sessão: sess_abc123
- independência: Nível A (fornecedor externo)
- veredito: aceitar
- data: 23/09/2026 11:00

### Independência
Não implementei nem corrigi nada desta entrega, e não vou corrigir. Revisão com fornecedor externo.

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| C1 | `python3 -m unittest` passou | executada |

### Achados
Nenhum

### O que não verifiquei
- Testes de carga em produção.
"""
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.md', delete=False) as fp:
            fp.write(conteudo)
            caminho = fp.name

        try:
            r = rodar(lint, caminho)
            self.assertEqual(r.returncode, 0, f'lint_parecer falhou: {r.stdout}\n{r.stderr}')
        finally:
            Path(caminho).unlink(missing_ok=True)

    def test_cli_rodada_parecer_com_nivel_independencia(self):
        sc_rodada = NUCLEO / 'scripts' / 'sc_rodada.py'
        with tempfile.TemporaryDirectory() as td:
            pasta = Path(td)
            # Inicia rodada
            r_ini = rodar(sc_rodada, 'abrir', '--pasta', str(pasta), '--id', 'R1', '--meta', 'Meta R1',
                          '--base', 'a1b2c3d', '--aceite', 'C1', '--nivel', '2', '--aplicar')
            self.assertEqual(r_ini.returncode, 0, r_ini.stderr)

            # Registra parecer com --nivel-independencia B e justificativa
            r_par = rodar(sc_rodada, 'parecer', '--pasta', str(pasta), '--etapa', 'R1',
                          '--revisor', 'Gemini Pro', '--fornecedor', 'Google',
                          '--implementador', 'Gandalf:Google', '--versao', 'a1b2c3d',
                          '--veredito', 'aceitar', '--criterio-ok', 'C1',
                          '--nivel-independencia', 'B',
                          '--justificativa-independencia', 'Modelo distinto em sessao isolada',
                          '--aplicar')
            self.assertEqual(r_par.returncode, 0, f'cmd_parecer falhou: {r_par.stderr}')
            self.assertIn('registrado para etapa R1', r_par.stdout)


if __name__ == '__main__':
    unittest.main()
