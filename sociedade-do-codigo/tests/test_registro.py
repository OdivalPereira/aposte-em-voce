import json
import os
import tempfile
import unittest
from pathlib import Path

from util import NUCLEO, carregar

MOD_REGISTRO = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REGISTRO.Registro
ErroRegistroCorrompido = MOD_REGISTRO.ErroRegistroCorrompido
ErroConcorrenciaRegistro = MOD_REGISTRO.ErroConcorrenciaRegistro
ErroValidacaoRegistro = MOD_REGISTRO.ErroValidacaoRegistro


class TesteRegistro(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.reg = Registro.inicializar(self.pasta_sociedade, 'projeto-teste', str(self.p))

    # ==================== C01: Unicidade e Contagem ====================

    def test_c01_unicidade_etapa_e_contagem(self):
        # 1. Abre etapa
        self.reg.abrir_etapa(
            etapa_id='SC-E1',
            objetivo='Testar unicidade',
            plano_ref='plano.md#E1',
            autorizacao_ref='A-SC-E1-001',
            base_efetiva='90e5a95',
            criterios=['C01', 'C02'],
        )
        est = self.reg.estado()
        self.assertIsNotNone(est['etapa_atual'])
        self.assertEqual(est['etapa_atual']['id'], 'SC-E1')
        self.assertEqual(est['contagem_concluidas'], 0)

        # 2. Segunda abertura da mesma etapa é idempotente (mantém identidade)
        self.reg.abrir_etapa(
            etapa_id='SC-E1',
            objetivo='Segunda abertura mesma etapa',
            plano_ref='plano.md#E1',
            autorizacao_ref='A-SC-E1-001',
            base_efetiva='90e5a95',
            criterios=['C01', 'C02'],
        )
        est2 = self.reg.estado()
        self.assertEqual(est2['etapa_atual']['id'], 'SC-E1')
        self.assertEqual(est2['contagem_concluidas'], 0)

        # 3. Tentar abrir OUTRA etapa com uma já ativa falha (REV-014: uma rodada por vez)
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.abrir_etapa('SC-E2', 'Outra etapa', 'plano', 'aut', 'base', ['C1'])

        # 4. Adiciona tarefas
        self.reg.registrar_tarefa('SC-E1', 'T1', 'Elrond', 'Tarefa local')
        self.reg.registrar_tarefa('SC-E1', 'T2', 'Jules', 'Tarefa remota', ferramenta='jules', job_id_remoto='job_123')
        self.reg.passar_bastao('SC-E1', 'Galadriel', autor='Gandalf')
        self.reg.atualizar_tarefa('SC-E1', 'T1', 'concluida')
        self.reg.atualizar_tarefa('SC-E1', 'T2', 'concluida')

        est3 = self.reg.estado()
        self.assertEqual(len(est3['etapa_atual']['tarefas']), 2)
        self.assertEqual(est3['contagem_concluidas'], 0)

    def test_c01_segregacao_simulacao_e_etapa_concluida(self):
        # Abre etapa simulada
        self.reg.abrir_etapa(
            etapa_id='SC-SIM',
            objetivo='Simulação',
            plano_ref='ref',
            autorizacao_ref='aut',
            base_efetiva='base',
            criterios=['C1'],
            origem='simulacao',
        )
        self.reg.registrar_evidencia('SC-SIM', 'C1', 'cmd', 0, 'ok')
        self.reg.registrar_parecer('SC-SIM', 'PAR-01', 'Claude', 'Anthropic', [{'agente': 'Gandalf', 'fornecedor': 'Google'}],
                                   'base', 'aceitar', {'C1': True})
        self.reg.encerrar_etapa('SC-SIM', 'Fechamento simulado')
        est = self.reg.estado()
        # Não conta em concluídas reais
        self.assertEqual(est['contagem_concluidas'], 0)
        self.assertIn('SC-SIM', est['etapas_simuladas'])

    # ==================== C02: Atomicidade, Concorrência e Corrupção ====================

    def test_c02_concorrencia_optimistic_lock(self):
        rev_atual = self.reg.revisao
        self.reg.abrir_etapa('E-01', 'Meta', 'ref', 'aut', 'base', ['C1'])
        self.assertEqual(self.reg.revisao, rev_atual + 1)

        # Tentativa de mutação passando revisão defasada deve falhar
        with self.assertRaises(ErroConcorrenciaRegistro):
            self.reg.aplicar_mutacao(
                lambda dados: [{'tipo': 'tarefa_criada', 'dados': {'etapa_id': 'E-01', 'tarefa_id': 'TX'}}],
                autor='Concorrente',
                revisao_esperada=rev_atual,
            )

    def test_c02_recusa_registro_corrompido_sem_sobrescrever(self):
        reg_file, _ = MOD_REGISTRO.caminhos_registro(self.pasta_sociedade)
        lixo = '{"versao_formato": "2.1.0", "corrompido: [incompleto'
        reg_file.write_text(lixo, encoding='utf-8')

        with self.assertRaises(ErroRegistroCorrompido):
            Registro(self.pasta_sociedade)

        # Tentativa de inicializar sobre base corrompida recusa sobrescrita
        with self.assertRaises(ErroRegistroCorrompido):
            Registro.inicializar(self.pasta_sociedade, 'projeto-teste', str(self.p))

        self.assertEqual(reg_file.read_text(encoding='utf-8'), lixo)

    def test_c02_validacao_sob_trava_impede_encerramento_invalido(self):
        # Processo A abre etapa
        self.reg.abrir_etapa('SC-E1', 'Meta', 'ref', 'aut', 'base', ['C1'])
        self.reg.registrar_evidencia('SC-E1', 'C1', 'cmd', 0, 'ok')
        self.reg.registrar_parecer('SC-E1', 'PAR-01', 'Claude', 'Anthropic', [{'agente': 'Gandalf', 'fornecedor': 'Google'}],
                                   'base', 'aceitar', {'C1': True})

        # Processo B grava bloqueador aberto no disco
        reg_b = Registro(self.pasta_sociedade)
        reg_b.registrar_achado('SC-E1', 'ACH-BLOQ', 'bloqueador', 'src/x.py', 'Falha crítica', autor='Revisor')

        # Processo A tenta encerrar usando sua instância; deve revalidar snapshot do disco e bloquear (REV-009)
        with self.assertRaises(ErroValidacaoRegistro) as cm:
            self.reg.encerrar_etapa('SC-E1', 'Concluir')
        self.assertIn('ACH-BLOQ está aberto', str(cm.exception))

    # ==================== C03: Projeções e Preservação Autoral ====================

    def test_c03_preserva_texto_autoral_e_sincronia(self):
        andamento_md = self.pasta_sociedade / 'andamento.md'
        texto_autoral = (
            "# Estado de continuidade — Sociedade do Código\n\n"
            "Texto autoral escrito por Odival e Astra em 21/09/2026.\n\n"
            "## Decisões Prévias\n"
            "- Não apagar este texto.\n\n"
            "<!-- bloco_gandalf_inicio: SC-E1 -->\n"
            "Texto antigo gerenciado a ser substituído.\n"
            "<!-- bloco_gandalf_fim: SC-E1 -->\n\n"
            "## Outra Seção Posterior\n"
            "Texto autoral posterior intacto.\n"
        )
        andamento_md.write_text(texto_autoral, encoding='utf-8')

        self.reg.abrir_etapa('SC-E1', 'Objetivo novo', 'ref', 'aut', 'base', ['C1'])
        novo_bloco = "## Retorno de Gandalf — SC-E1\n\nNovo retorno gerenciado."
        self.reg.projetar_andamento(andamento_md, bloco_conteudo_gandalf=novo_bloco)

        conteudo_final = andamento_md.read_text(encoding='utf-8')
        self.assertIn("Texto autoral escrito por Odival e Astra em 21/09/2026.", conteudo_final)
        self.assertIn("Não apagar este texto.", conteudo_final)
        self.assertIn("Outra Seção Posterior", conteudo_final)
        self.assertIn("Texto autoral posterior intacto.", conteudo_final)
        self.assertNotIn("Texto antigo gerenciado a ser substituído.", conteudo_final)
        self.assertIn("Novo retorno gerenciado.", conteudo_final)

        # Checa sincronia da projeção
        em_sync, rev_md, rev_reg = MOD_REGISTRO.verificar_sincronia_projecao(andamento_md, self.reg)
        self.assertTrue(em_sync)
        self.assertEqual(rev_md, self.reg.revisao)

    def test_c03_projetar_historico_idempotente(self):
        hist_md = self.pasta_sociedade / 'historico.md'
        entrada = "## DOC-009 · 21/09/2026 · Marco importante\nResultado do marco."
        self.reg.projetar_historico(hist_md, entrada)
        self.reg.projetar_historico(hist_md, entrada)

        texto = hist_md.read_text(encoding='utf-8')
        self.assertEqual(texto.count("## DOC-009"), 1)

    # ==================== C04: Validade da Evidência ====================

    def test_c04_rejeicao_evidencia_invalida(self):
        self.reg.abrir_etapa('SC-E1', 'Obj', 'ref', 'aut', 'base', ['C04'])

        # 1. Comando vazio levanta erro formal
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_evidencia('SC-E1', 'C04', '', 0, 'saida')

        # 2. Saída vazia
        self.reg.registrar_evidencia('SC-E1', 'C04', 'cmd', 0, '   ')
        est = self.reg.estado()
        self.assertFalse(est['etapa_atual']['criterios']['C04']['atendido'])

        # 3. Saída None não quebra com AttributeError (REV-012)
        self.reg.registrar_evidencia('SC-E1', 'C04', 'cmd', 0, None)
        est = self.reg.estado()
        self.assertFalse(est['etapa_atual']['criterios']['C04']['atendido'])

        # 4. Placeholder semântico rejeitado
        self.reg.registrar_evidencia('SC-E1', 'C04', 'cmd', 0, '<preencher com a saida>')
        est = self.reg.estado()
        self.assertFalse(est['etapa_atual']['criterios']['C04']['atendido'])

        # 5. Representações legítimas contendo caracteres angulares são aceitas (REV-012)
        self.reg.registrar_evidencia('SC-E1', 'C04', 'cmd', 0, "<class 'core.App'> - List<Item> 100% OK")
        est = self.reg.estado()
        self.assertTrue(est['etapa_atual']['criterios']['C04']['atendido'])

        # 6. Rejeição de variantes de não executado
        self.reg.registrar_evidencia('SC-E1', 'C04', 'cmd', 0, 'não executado: sem ambiente python')
        est = self.reg.estado()
        # O critério deixa de ser atendido após a evidência falha (REV-012)
        self.assertFalse(est['etapa_atual']['criterios']['C04']['atendido'])

        # 7. Evidência com critério inexistente é rejeitada (REV-012)
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_evidencia('SC-E1', 'CRITERIO_INEXISTENTE', 'cmd', 0, 'ok')

    # ==================== C05: Bloqueadores e Achados ====================

    def test_c05_bloqueador_aberto_ou_contestado_impede_encerramento(self):
        self.reg.abrir_etapa('SC-E1', 'Obj', 'ref', 'aut', '90e5a95', ['C1'])
        self.reg.registrar_evidencia('SC-E1', 'C1', 'cmd', 0, 'Ran 10 tests OK')
        self.reg.registrar_parecer('SC-E1', 'PAR-01', 'Claude Code', 'Anthropic', [{'agente': 'Gandalf', 'fornecedor': 'Google'}],
                                   '90e5a95', 'aceitar', {'C1': 'executada'})

        self.reg.registrar_achado('SC-E1', 'ACH-01', 'bloqueador', 'modulo.py:10', 'Falha crítica', autor='Revisor')

        # Reuso de ID de achado é rejeitado (REV-004)
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_achado('SC-E1', 'ACH-01', 'opcional', 'modulo.py:10', 'Tentativa de rebaixar', autor='Gandalf')

        ok, bloqueios = self.reg.verificar_condicoes_encerramento('SC-E1')
        self.assertFalse(ok)
        self.assertTrue(any('ACH-01 está aberto' in b for b in bloqueios))

        # Transição para excepcionado sem exceção estruturada falha (REV-004)
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.atualizar_achado('SC-E1', 'ACH-01', 'excepcionado')

        # Transição para contestado continua bloqueando
        self.reg.atualizar_achado('SC-E1', 'ACH-01', 'contestado', justificativa='Discordo')
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('SC-E1')
        self.assertFalse(ok)

        # Corrigido libera o bloqueio
        self.reg.atualizar_achado('SC-E1', 'ACH-01', 'corrigido', justificativa='Ajustado')
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('SC-E1')
        self.assertTrue(ok)

    # ==================== C06: Segregação e Independência do Revisor ====================

    def test_c06_segregacao_e_independencia_revisor(self):
        self.reg.abrir_etapa('SC-E1', 'Obj', 'ref', 'aut', '90e5a95', ['C1'])
        self.reg.registrar_evidencia('SC-E1', 'C1', 'cmd', 0, 'Ran 10 tests OK')

        # Lista de implementadores vazia é rejeitada (REV-005)
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_parecer('SC-E1', 'PAR-00', 'Revisor', 'Anthropic', [], '90e5a95', 'aceitar', {'C1': True})

        # Mesmo fornecedor rejeitado (Google revisando Google) (REV-005)
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_parecer(
                etapa_id='SC-E1',
                parecer_id='PAR-01',
                revisor='Gemini Revisor',
                fornecedor_revisor='Google',
                implementadores=[{'agente': 'Gandalf', 'fornecedor': 'Google'}],
                versao_examinada='90e5a95',
                veredito='aceitar',
                criterios_verificados={'C1': True},
            )

        # Fornecedor independente aceito (Anthropic revisando Google)
        self.reg.registrar_parecer(
            etapa_id='SC-E1',
            parecer_id='PAR-02',
            revisor='Claude Sonnet',
            fornecedor_revisor='Anthropic',
            implementadores=[{'agente': 'Gandalf', 'fornecedor': 'Google'}],
            versao_examinada='90e5a95',
            veredito='aceitar',
            criterios_verificados={'C1': True},
        )
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('SC-E1')
        self.assertTrue(ok)

    # ==================== C07: Impacto de Correções ====================

    def test_c07_impacto_correcoes(self):
        self.reg.abrir_etapa('SC-E1', 'Obj', 'ref', 'aut', '90e5a95', ['C1'])
        self.reg.registrar_evidencia('SC-E1', 'C1', 'cmd', 0, 'Ran 10 tests OK')
        self.reg.registrar_parecer('SC-E1', 'PAR-01', 'Claude Sonnet', 'Anthropic', [{'agente': 'Elrond', 'fornecedor': 'Google'}],
                                   '90e5a95', 'aceitar', {'C1': True})

        # Código é alterado após parecer com impacto desconhecido
        self.reg.registrar_versao('SC-E1', 'commit_novo_123', impacto='desconhecido')
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('SC-E1')
        self.assertFalse(ok)
        self.assertTrue(any('impacto desconhecido' in b for b in bloqueios))

        # Correção com alto impacto exige nova revisão
        self.reg.registrar_versao('SC-E1', 'commit_novo_123', impacto='alto')
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('SC-E1')
        self.assertFalse(ok)
        self.assertTrue(any('alto impacto' in b for b in bloqueios))

        # Correção posterior sem_alto NÃO apaga alto impacto anterior (N3)
        self.reg.registrar_versao('SC-E1', 'commit_novo_123', impacto='sem_alto')
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('SC-E1')
        self.assertFalse(ok)
        self.assertTrue(any('alto impacto' in b for b in bloqueios))

        # Nova revisão examinando a nova versão libera o encerramento
        self.reg.registrar_parecer('SC-E1', 'PAR-02', 'Claude Sonnet', 'Anthropic', [{'agente': 'Elrond', 'fornecedor': 'Google'}],
                                   'commit_novo_123', 'aceitar', {'C1': True})
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('SC-E1')
        self.assertTrue(ok)

    # ==================== C08: Exceção Rastreável (sem forcar isolado) ====================

    def test_c08_excecao_rastreavel(self):
        self.reg.abrir_etapa('SC-E1', 'Obj', 'ref', 'aut', '90e5a95', ['C_MOBILE'])
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('SC-E1')
        self.assertFalse(ok)

        # Motivo curto ou sem referência humana explícita falha (REV-003, C08)
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_excecao('SC-E1', 'EXC-01', 'criterio:C_MOBILE', 'curto', 'A-001')
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_excecao('SC-E1', 'EXC-01', 'criterio:C_MOBILE', 'motivo longo o bastante', 'autorizacao_cli')

        # Exceção com motivo substantivo e autorização humana de Odival
        self.reg.registrar_excecao(
            'SC-E1', 'EXC-01', 'criterio:C_MOBILE',
            motivo='Sem navegador mobile no ambiente CLI local',
            referencia_humana='A-SC-E1-001',
        )
        self.reg.registrar_parecer('SC-E1', 'PAR-01', 'Claude Sonnet', 'Anthropic', [{'agente': 'Elrond', 'fornecedor': 'Google'}],
                                   '90e5a95', 'aceitar', {'C_MOBILE': False})

        # Encerra por exceção: fecha a etapa, mas NÃO é elegível para publicação (REV-007, REV-010)
        self.reg.encerrar_etapa('SC-E1', 'Encerrada com critério mobile excepcionado')
        est = self.reg.estado()
        self.assertIn('SC-E1', est['etapas_excepcionadas'])
        self.assertEqual(est['contagem_concluidas'], 0)

    # ==================== C09: Preservação no Encerramento ====================

    def test_c09_encerramento_preserva_historico_e_nao_duplica(self):
        self.reg.abrir_etapa('SC-E1', 'Obj', 'ref', 'aut', '90e5a95', ['C1'])
        self.reg.registrar_evidencia('SC-E1', 'C1', 'cmd', 0, '10 ok')
        self.reg.registrar_parecer('SC-E1', 'PAR-01', 'Claude Sonnet', 'Anthropic', [{'agente': 'Elrond', 'fornecedor': 'Google'}],
                                   '90e5a95', 'aceitar', {'C1': True})

        self.reg.encerrar_etapa('SC-E1', 'Tudo concluído com êxito')
        est = self.reg.estado()
        self.assertEqual(est['contagem_concluidas'], 1)
        self.assertIn('SC-E1', est['etapas_concluidas'])

        # Etapa encerrada não aceita novas tarefas ou evidências (REV-014)
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_tarefa('SC-E1', 'T_NOVA', 'Gandalf', 'Tarefa pós-encerramento')

    # ==================== C10: Agregação Idempotente entre Projetos ====================

    def test_c10_agregacao_idempotente_entre_projetos(self):
        # Auto-importação do mesmo projeto é recusada (REV-007)
        resumo_proprio = {
            'projeto_origem_id': 'projeto-teste',
            'etapa_id': 'SC-E1',
            'revisao_origem': 1,
            'concluida': True,
            'simulacao': False,
            'resumo_hash': 'hash1',
        }
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.importar_resumo_projeto(resumo_proprio)

        resumo_p1 = {
            'projeto_origem_id': 'proj_ficticio_1',
            'etapa_id': 'ET-01',
            'revisao_origem': 5,
            'concluida': True,
            'simulacao': False,
        }
        resumo_p1['resumo_hash'] = MOD_REGISTRO.calcular_hash_conteudo(
            json.dumps({k: v for k, v in resumo_p1.items() if k not in ('timestamp_exportacao', 'resumo_hash')}, sort_keys=True)
        )
        self.assertTrue(self.reg.importar_resumo_projeto(resumo_p1))
        self.assertEqual(self.reg.estado()['contagem_agregada_total'], 1)

        # Reimportar exatamente o mesmo resumo é idempotente (no-op)
        self.assertFalse(self.reg.importar_resumo_projeto(resumo_p1))
        self.assertEqual(self.reg.estado()['contagem_agregada_total'], 1)

        # Mesma revisão com dados conflitantes gera erro formal
        resumo_p1_conflito = dict(resumo_p1)
        resumo_p1_conflito['concluida'] = False
        resumo_p1_conflito['resumo_hash'] = MOD_REGISTRO.calcular_hash_conteudo(
            json.dumps({k: v for k, v in resumo_p1_conflito.items() if k not in ('timestamp_exportacao', 'resumo_hash')}, sort_keys=True)
        )
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.importar_resumo_projeto(resumo_p1_conflito)

    # ==================== C11: Aviso de Cota Manual e Migração Legada ====================

    def test_c11_aviso_cota_manual_e_migracao_legada(self):
        self.reg.registrar_aviso_cota(autor='Odival', percentual=25.0, janela='semanal', data='21/09/2026')
        est = self.reg.estado()
        self.assertIsNotNone(est['aviso_cota_recente'])
        self.assertEqual(est['aviso_cota_recente']['autor'], 'Odival')

        # Migração legada
        rodada_legada_md = self.pasta_sociedade / 'rodada_legada.md'
        rodada_legada_md.write_text(
            "# Rodada NT-02 — Melhoria de conciliação\n\n"
            "nivel: 2\n"
            "## Fatias\n"
            "1. Primeira fatia — fechada · prova: ok\n"
            "2. Segunda fatia — pendente\n",
            encoding='utf-8',
        )
        legado = MOD_REGISTRO.migrar_legado_para_registro(self.reg, rodada_legada_md)
        self.assertIsNotNone(legado)

        # Prova textual antiga NÃO satisfaz critério (REV-006, C11)
        est_migrado = self.reg.estado()
        etapa_migrada = est_migrado['etapa_atual']
        self.assertFalse(etapa_migrada['criterios']['FATIA-1']['atendido'])

        # Migração repetida é idempotente
        legado2 = MOD_REGISTRO.migrar_legado_para_registro(self.reg, rodada_legada_md)
        self.assertEqual(legado2['id'], legado['id'])

    # ==================== C12: Continuidade por Contexto Curto ====================

    def test_c12_continuidade_contexto_curto_processo_novo(self):
        self.reg.abrir_etapa('SC-E1', 'Meta de continuidade', 'plano.md#E1', 'A-SC-E1-001', '90e5a95', ['C01', 'C02'])
        self.reg.registrar_tarefa('SC-E1', 'T_JULES', 'Jules', 'Tarefa remota delegada', ferramenta='jules', job_id_remoto='job_jules_999')
        self.reg.registrar_achado('SC-E1', 'ACH-01', 'relevante', 'arquivo.py:5', 'Aviso pendente', autor='Revisor')
        self.reg.passar_bastao('SC-E1', 'Elrond (Gemini)', autor='Gandalf', nota='Avançar com persistência')

        andamento_md = self.pasta_sociedade / 'andamento.md'
        self.reg.projetar_andamento(andamento_md)

        # Novo processo recupera estado completo
        reg_novo_processo = Registro(self.pasta_sociedade)
        est_novo = reg_novo_processo.estado()
        etapa_recuperada = est_novo['etapa_atual']

        self.assertIsNotNone(etapa_recuperada)
        self.assertEqual(etapa_recuperada['id'], 'SC-E1')
        self.assertEqual(etapa_recuperada['responsavel'], 'Elrond (Gemini)')
        self.assertIn('T_JULES', etapa_recuperada['tarefas'])
        self.assertIn('ACH-01', etapa_recuperada['achados'])

    # ==================== C13: Simulação sem Efeitos Colaterais ====================

    def test_c13_simulacao_nao_grava_em_disco(self):
        reg_file, _ = MOD_REGISTRO.caminhos_registro(self.pasta_sociedade)
        conteudo_antes = reg_file.read_text(encoding='utf-8')
        self.reg.abrir_etapa('E-SIM', 'Simulação', 'ref', 'aut', 'base', ['C1'], aplicar=False)
        self.assertEqual(reg_file.read_text(encoding='utf-8'), conteudo_antes)

    def test_sonda_a_zero_io_pasta_virgem(self):
        # S-A: simulação em pasta virgem não cria pasta, lock, nem registro
        with tempfile.TemporaryDirectory() as tmpdir:
            raiz_virgem = Path(tmpdir) / 'novo_projeto'
            pasta_soc = raiz_virgem / 'sociedade'
            reg_sim = Registro.inicializar(pasta_soc, 'proj-sim', str(raiz_virgem), aplicar=False)
            reg_sim.abrir_etapa('SC-E1', 'Objetivo sim', 'ref', 'aut', 'base', ['C01'], aplicar=False)
            self.assertFalse(raiz_virgem.exists())
            self.assertFalse(pasta_soc.exists())

    def test_sonda_c_preservacao_projecao_e_multiplas_etapas(self):
        # S-C: preservação de prefácio autoral, retorno antigo e notas posteriores
        andamento_md = self.pasta_sociedade / 'andamento.md'
        texto_inicial = (
            "# Prefácio Autoral\n\n"
            "Texto importante do autor.\n\n"
            "<!-- bloco_gandalf_inicio: SC-E0 -->\n"
            "## Retorno de Gandalf — SC-E0\n"
            "Retorno da etapa anterior que não pode sumir.\n"
            "<!-- bloco_gandalf_fim: SC-E0 -->\n\n"
            "## Nota Autoral Posterior\n"
            "Esta nota nunca pode ser truncada ou destruída.\n"
        )
        andamento_md.write_text(texto_inicial, encoding='utf-8')

        self.reg.abrir_etapa('SC-E1', 'Objetivo E1', 'ref', 'aut', '90e5a95', ['C01'])
        self.reg.projetar_andamento(andamento_md)

        conteudo = andamento_md.read_text(encoding='utf-8')
        self.assertIn("# Prefácio Autoral", conteudo)
        self.assertIn("<!-- bloco_gandalf_inicio: SC-E0 -->", conteudo)
        self.assertIn("Retorno da etapa anterior que não pode sumir.", conteudo)
        self.assertIn("## Nota Autoral Posterior", conteudo)
        self.assertIn("Esta nota nunca pode ser truncada ou destruída.", conteudo)
        self.assertIn("<!-- bloco_gandalf_inicio: SC-E1 -->", conteudo)
        self.assertIn("## Retorno de Gandalf — SC-E1", conteudo)

    def test_cadeia_hash_adulteracao_campo_lanca_erro_registro_corrompido(self):
        # A02: evento com hash gravado, campo adulterado no arquivo, recarregamento falha com ErroRegistroCorrompido
        self.reg.abrir_etapa('SC-E1', 'Objetivo E1', 'ref', 'aut', '90e5a95', ['C01'])
        self.reg.passar_bastao('SC-E1', 'Legolas', autor='Gandalf', nota='motivo original')

        reg_path = self.pasta_sociedade / 'registro.json'
        dados = json.loads(reg_path.read_text(encoding='utf-8'))
        eventos = dados['eventos']
        self.assertGreaterEqual(len(eventos), 2)
        # Confere que os eventos possuem hash e prev_hash
        self.assertEqual(eventos[0]['prev_hash'], '')
        self.assertTrue(eventos[0]['hash'])
        self.assertEqual(eventos[1]['prev_hash'], eventos[0]['hash'])
        self.assertTrue(eventos[1]['hash'])

        # Adultera um campo no arquivo de registro (ex.: nota/motivo)
        eventos[1]['dados']['nota'] = 'motivo adulterado maliciosamente'
        reg_path.write_text(json.dumps(dados, indent=2), encoding='utf-8')

        # Recarregamento via Registro falha com ErroRegistroCorrompido
        with self.assertRaises(ErroRegistroCorrompido):
            Registro(self.pasta_sociedade)

    def test_cadeia_hash_rompimento_prev_hash_lanca_erro(self):
        # A02: adulteração do prev_hash rompe a cadeia e lança ErroRegistroCorrompido
        self.reg.abrir_etapa('SC-E1', 'Objetivo E1', 'ref', 'aut', '90e5a95', ['C01'])
        self.reg.passar_bastao('SC-E1', 'Legolas', autor='Gandalf', nota='motivo original')

        reg_path = self.pasta_sociedade / 'registro.json'
        dados = json.loads(reg_path.read_text(encoding='utf-8'))
        dados['eventos'][1]['prev_hash'] = '0' * 64
        # Recalcula o hash do evento 1 com prev_hash falso para testar exclusivamente a verificação de prev_hash
        dados['eventos'][1]['hash'] = MOD_REGISTRO.calcular_hash_evento(dados['eventos'][1])
        reg_path.write_text(json.dumps(dados, indent=2), encoding='utf-8')

        with self.assertRaises(ErroRegistroCorrompido):
            Registro(self.pasta_sociedade)


if __name__ == '__main__':
    unittest.main()
