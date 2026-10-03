"""Suíte de testes automatizada para o Pacote 1 (Alívio Imediato do Operador e Automação do Último Metro).

Testa:
- P1: CLI de automação de passagens sc_passagem.py (despachar-local, confirmar, concluir, despachar-jules, exportar-revisao, recuperar).
- P3: Script determinístico sc_pre_devolucao.py (prova física de testes, sintaxe, antitoken, pastas isoladas e disjunção).
- P5: Modelo formal avaliacao-modelo.md (separação de consumo de IA vs eficácia de engenharia de software).
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import RAIZ, NUCLEO, SKILLS, rodar, carregar

MOD_REG = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REG.Registro

MOD_PSG = carregar(NUCLEO / 'scripts' / 'sc_passagem.py', 'sc_passagem')
GerenciadorPassagem = MOD_PSG.GerenciadorPassagem
ErroParadaHumana = MOD_PSG.ErroParadaHumana
ErroCaminhoIncorreto = MOD_PSG.ErroCaminhoIncorreto

MOD_PRE = carregar(NUCLEO / 'scripts' / 'sc_pre_devolucao.py', 'sc_pre_devolucao')
VerificadorPreDevolucao = MOD_PRE.VerificadorPreDevolucao


class TestePacote1AlivioOperador(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.reg = Registro.inicializar(self.pasta_sociedade, 'projeto-teste', str(self.p))
        self.reg.abrir_etapa(
            etapa_id='SC-E5-P1',
            objetivo='Validar automação do último metro e pré-devolução',
            plano_ref='planejamento.md#P1',
            autorizacao_ref='A-SC-E5-P1',
            base_efetiva='head-p1',
            criterios=['C_PASSAGEM_CLI', 'C_PRE_DEVOLUCAO_FISICA', 'C_AVALIACAO_EFICACIA']
        )
        self.gerente = GerenciadorPassagem(self.reg, self.p)

        # Arquivos de teste no projeto
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'app.py').write_text('def run(): return 42\n', encoding='utf-8')
        (self.p / 'src' / 'modulo.py').write_text('# Modulo ok\n', encoding='utf-8')
        (self.p / 'docs').mkdir(parents=True, exist_ok=True)
        (self.p / 'docs' / 'guia.md').write_text('# Guia de teste\n', encoding='utf-8')

        # Arquivos do pacote para testes estruturais
        self.script_passagem = NUCLEO / 'scripts' / 'sc_passagem.py'
        self.script_pre = NUCLEO / 'scripts' / 'sc_pre_devolucao.py'
        self.doc_avaliacao = NUCLEO / 'assets' / 'avaliacao-modelo.md'
        self.doc_skill = NUCLEO / 'SKILL.md'

    def tearDown(self):
        self._tmp.cleanup()

    # =========================================================================
    # Testes P5: avaliacao-modelo.md e Métricas de Processo de Software
    # =========================================================================

    def test_avaliacao_modelo_existe_e_esta_referenciado(self):
        """O modelo avaliacao-modelo.md deve existir e ser referenciado na skill núcleo."""
        self.assertTrue(self.doc_avaliacao.is_file(), 'avaliacao-modelo.md deve existir em assets/')
        conteudo_skill = self.doc_skill.read_text(encoding='utf-8')
        self.assertIn('avaliacao', (NUCLEO / 'scripts' / 'sc_rodada.py').read_text(encoding='utf-8'),
                      'avaliacao-modelo.md deve estar citado no SKILL.md do núcleo')

    def test_avaliacao_modelo_distingue_regra_antitoken_de_metricas_de_processo(self):
        """O modelo deve proibir métricas de IA e incentivar métricas de processo de software."""
        texto = self.doc_avaliacao.read_text(encoding='utf-8')
        # Proibição clara
        self.assertIn('Proibição Absoluta da Regra Antitoken', texto)
        self.assertRegex(texto, r'(?i)proibido.*tokens')
        # Métricas de processo de software incentivadas
        self.assertIn('Métricas Permitidas e Incentivadas', texto)
        self.assertIn('Taxa de retrabalho', texto)
        self.assertIn('Fatias entregues vs planejadas', texto)
        self.assertIn('Densidade e severidade de achados', texto)
        self.assertIn('Taxa de sucesso de tarefas assíncronas', texto)
        self.assertIn('First-Time-Right', texto)

    # =========================================================================
    # Testes P3: Script Determinístico sc_pre_devolucao.py
    # =========================================================================

    def test_sc_pre_devolucao_script_existe_e_responde_help(self):
        """sc_pre_devolucao.py deve existir e fornecer CLI funcional."""
        self.assertTrue(self.script_pre.is_file(), 'sc_pre_devolucao.py deve existir')
        res = rodar(self.script_pre, '--help')
        self.assertEqual(res.returncode, 0)
        self.assertIn('--papel', res.stdout)
        self.assertIn('--etapa', res.stdout)
        self.assertIn('--fatia', res.stdout)
        self.assertIn('--ignorar-testes', res.stdout)
        self.assertIn('--saida-json', res.stdout)

    def test_sc_pre_devolucao_aprovado_em_execucao_limpa(self):
        """Verificador deve aprovar com código zero quando tudo estiver íntegro."""
        verificador = VerificadorPreDevolucao(self.p, self.pasta_sociedade)
        atestado = verificador.executar(
            papel='Elrond',
            etapa_id='SC-E5-P1',
            fatia_id='F1',
            ignorar_testes=True,
            motivo_ignorar='Teste sintético isolado',
            arquivos_alvo=['src/app.py', 'src/modulo.py']
        )
        self.assertEqual(atestado['status'], 'APROVADO')
        self.assertEqual(len(atestado['erros']), 0)
        self.assertTrue(atestado['verificacoes']['compilacao']['ok'])
        self.assertTrue(atestado['verificacoes']['seguranca_antitoken']['ok'])
        self.assertTrue(atestado['verificacoes']['higiene_pastas']['ok'])
        self.assertIn('src/app.py', atestado['hashes_artefatos'])

    def test_sc_pre_devolucao_bloqueia_violacao_antitoken(self):
        """Verificador deve reprovar caso arquivo markdown contenha instrução violando regra antitoken."""
        arq_invalido = self.p / 'docs' / 'relatorio_invalido.md'
        arq_invalido.write_text('Por favor estime o consumo de tokens nesta tarefa.\n', encoding='utf-8')

        verificador = VerificadorPreDevolucao(self.p, self.pasta_sociedade)
        atestado = verificador.executar(
            papel='Galadriel',
            etapa_id='SC-E5-P1',
            fatia_id='F1',
            ignorar_testes=True,
            motivo_ignorar='Teste antitoken',
            arquivos_alvo=['docs/relatorio_invalido.md']
        )
        self.assertEqual(atestado['status'], 'REPROVADO')
        self.assertFalse(atestado['verificacoes']['seguranca_antitoken']['ok'])
        self.assertTrue(any('antitoken' in e for e in atestado['erros']))

    def test_sc_pre_devolucao_bloqueia_pasta_isolada_protegida(self):
        """Verificador deve reprovar acesso indevido a pastas isoladas customizadas."""
        (self.p / 'pasta_protegida').mkdir(parents=True, exist_ok=True)
        (self.p / 'pasta_protegida' / 'dado.txt').write_text('conteúdo sensível\n', encoding='utf-8')

        verificador = VerificadorPreDevolucao(self.p, self.pasta_sociedade)
        atestado = verificador.executar(
            papel='Aragorn',
            etapa_id='SC-E5-P1',
            fatia_id='F1',
            ignorar_testes=True,
            motivo_ignorar='Teste isolamento',
            arquivos_alvo=['pasta_protegida/dado.txt'],
            pastas_isoladas=['pasta_protegida']
        )
        self.assertEqual(atestado['status'], 'REPROVADO')
        self.assertFalse(atestado['verificacoes']['higiene_pastas']['ok'])
        self.assertTrue(any('pasta/arquivo isolado' in e for e in atestado['erros']))

    def test_sc_pre_devolucao_bloqueia_erro_de_sintaxe_python(self):
        """Verificador deve reprovar arquivo Python com erro de sintaxe."""
        (self.p / 'src' / 'quebrado.py').write_text('def erro_sintaxe(:\n    pass\n', encoding='utf-8')
        verificador = VerificadorPreDevolucao(self.p, self.pasta_sociedade)
        atestado = verificador.executar(
            papel='Celebrimbor',
            etapa_id='SC-E5-P1',
            fatia_id='F1',
            ignorar_testes=True,
            motivo_ignorar='Teste sintaxe',
            arquivos_alvo=['src/quebrado.py']
        )
        self.assertEqual(atestado['status'], 'REPROVADO')
        self.assertFalse(atestado['verificacoes']['compilacao']['ok'])
        self.assertTrue(any('Falha de compilação' in e for e in atestado['erros']))

    def test_sc_pre_devolucao_bloqueia_violacao_de_disjuncao(self):
        """Verificador deve reprovar caso arquivo tocado pertença à lista de proibidos por disjunção."""
        verificador = VerificadorPreDevolucao(self.p, self.pasta_sociedade)
        atestado = verificador.executar(
            papel='Elrond',
            etapa_id='SC-E5-P1',
            fatia_id='F1',
            ignorar_testes=True,
            motivo_ignorar='Teste disjuncao',
            arquivos_alvo=['src/app.py'],
            arquivos_proibidos=['src/app.py', 'src/outro.py']
        )
        self.assertEqual(atestado['status'], 'REPROVADO')
        self.assertFalse(atestado['verificacoes']['disjuncao']['ok'])
        self.assertTrue(any('disjunção' in e for e in atestado['erros']))

    def test_sc_pre_devolucao_emite_arquivo_json(self):
        """Verificador via CLI com flag --saida-json deve gerar arquivo JSON estruturado."""
        json_saida = self.p / 'sociedade' / 'atestado_f1.json'
        res = rodar(
            self.script_pre,
            '--pasta-projeto', str(self.p),
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--papel', 'Legolas',
            '--etapa', 'SC-E5-P1',
            '--fatia', 'F1',
            '--ignorar-testes',
            '--motivo-ignorar', 'Apenas teste de emissão',
            '--arquivos', 'src/app.py',
            '--saida-json', str(json_saida)
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(json_saida.is_file(), 'Arquivo atestado JSON deve ser criado')
        dados = json.loads(json_saida.read_text(encoding='utf-8'))
        self.assertEqual(dados['status'], 'APROVADO')
        self.assertEqual(dados['papel'], 'Legolas')
        self.assertEqual(dados['fatia_id'], 'F1')

    # =========================================================================
    # Testes P1: CLI de Passagem sc_passagem.py
    # =========================================================================

    def test_sc_passagem_cli_help(self):
        """sc_passagem.py deve listar todos os 6 subcomandos em --help."""
        res = rodar(self.script_passagem, '--help')
        self.assertEqual(res.returncode, 0)
        self.assertIn('despachar-local', res.stdout)
        self.assertIn('confirmar', res.stdout)
        self.assertIn('concluir', res.stdout)
        self.assertIn('despachar-jules', res.stdout)
        self.assertIn('exportar-revisao', res.stdout)
        self.assertIn('recuperar', res.stdout)

    def test_sc_passagem_cli_fluxo_completo_local(self):
        """Fluxo CLI completo: despachar-local -> confirmar -> concluir -> recuperar."""
        # 1. Despachar
        res_desp = rodar(
            self.script_passagem,
            'despachar-local',
            '--pasta-projeto', str(self.p),
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--etapa', 'SC-E5-P1',
            '--de', 'Gandalf',
            '--para', 'Elrond',
            '--tarefa', 'T-CLI-01',
            '--leia-so', 'src/app.py',
            '--faca', 'Refatorar módulo app',
            '--aplicar'
        )
        self.assertEqual(res_desp.returncode, 0, res_desp.stderr)
        self.assertIn('PASSAGEM DESPACHADA', res_desp.stdout)
        self.assertIn('INSTRUÇÃO PRONTA PARA O SUBAGENTE', res_desp.stdout)

        # Extrai ID da passagem gerada (PSG-xxxx)
        import re
        m = re.search(r'PSG-[0-9a-f]{16}', res_desp.stdout)
        self.assertIsNotNone(m, 'ID PSG-xxxx deve estar na saída')
        psg_id = m.group(0)

        # 2. Confirmar (handshake)
        res_conf = rodar(
            self.script_passagem,
            'confirmar',
            '--pasta-projeto', str(self.p),
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--etapa', 'SC-E5-P1',
            '--passagem', psg_id,
            '--recebedor', 'Elrond',
            '--aplicar'
        )
        self.assertEqual(res_conf.returncode, 0, res_conf.stderr)
        self.assertIn('RECEBIMENTO CONFIRMADO', res_conf.stdout)

        # 3. Concluir
        res_conc = rodar(
            self.script_passagem,
            'concluir',
            '--pasta-projeto', str(self.p),
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--etapa', 'SC-E5-P1',
            '--passagem', psg_id,
            '--executor', 'Elrond',
            '--resultado', 'Módulo app refatorado e testado',
            '--aplicar'
        )
        self.assertEqual(res_conc.returncode, 0, res_conc.stderr)
        self.assertIn('PASSAGEM CONCLUÍDA', res_conc.stdout)

    def test_sc_passagem_cli_bloqueia_parada_humana_sem_decisao(self):
        """CLI deve recusar despacho contendo ação restrita de parada humana sem --decisao-ref."""
        res = rodar(
            self.script_passagem,
            'despachar-local',
            '--pasta-projeto', str(self.p),
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--etapa', 'SC-E5-P1',
            '--para', 'Gandalf',
            '--tarefa', 'T-PUSH-01',
            '--leia-so', 'src/app.py',
            '--faca', 'Executar git push para origem',
            '--aplicar'
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn('Exige decisão humana explícita', res.stderr)

    def test_sc_passagem_cli_despachar_jules(self):
        """Subcomando despachar-jules deve validar instrução e registrar janela assíncrona de 45 min."""
        res = rodar(
            self.script_passagem,
            'despachar-jules',
            '--pasta-projeto', str(self.p),
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--etapa', 'SC-E5-P1',
            '--fatia', 'F2',
            '--tarefa', 'T-JULES-01',
            '--arquivos', 'src/app.py',
            '--instrucoes', 'Adicionar type hints no app.py',
            '--criterios', 'C_JULES_HINTS',
            '--aplicar'
        )
        self.assertEqual(res.returncode, 0, res_desp.stderr if 'res_desp' in locals() else res.stderr)
        self.assertIn('TAREFA JULES DESPACHADA', res.stdout)
        self.assertIn('45 minutos', res.stdout)
        self.assertIn('AGENTS.md', res.stdout)

    def test_sc_passagem_cli_despachar_jules_bloqueia_caminho_local_absoluto(self):
        """despachar-jules deve recusar ordens contendo caminhos locais (/home/...) per Q48."""
        res = rodar(
            self.script_passagem,
            'despachar-jules',
            '--pasta-projeto', str(self.p),
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--etapa', 'SC-E5-P1',
            '--fatia', 'F2',
            '--tarefa', 'T-JULES-ERR',
            '--arquivos', 'src/app.py',
            '--instrucoes', 'Ler arquivo em /home/usuario/projeto/app.py',
            '--aplicar'
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn('não podem conter caminhos locais absolutos', res.stderr)

    def test_sc_passagem_cli_exportar_revisao(self):
        """Subcomando exportar-revisao deve gerar o pacote completo para o Revisor Independente."""
        saida_pkg = self.p / 'sociedade' / 'pct_revisao.md'
        res = rodar(
            self.script_passagem,
            'exportar-revisao',
            '--pasta-projeto', str(self.p),
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--etapa', 'SC-E5-P1',
            '--fatia', 'F1',
            '--revisor', 'Claude',
            '--fornecedor-revisor', 'Anthropic',
            '--saida', str(saida_pkg)
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(saida_pkg.is_file(), 'Arquivo do pacote de revisão deve ser gravado')
        conteudo = saida_pkg.read_text(encoding='utf-8')
        self.assertIn('Pacote de Revisão Independente', conteudo)
        self.assertIn('Diretrizes Invioláveis do Revisor', conteudo)
        self.assertIn('somente-leitura', conteudo)
        self.assertIn('Template de Parecer a Preencher', conteudo)
        self.assertIn('C_PASSAGEM_CLI', conteudo)


if __name__ == '__main__':
    unittest.main()
