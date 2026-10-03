#!/usr/bin/env python3
"""Testes de unidade para a Fatia F3 (Perfil do projeto: Q61, Q95, Q109; A2-P01, A2-P08).

Critérios de aceite observáveis de F3:
- Perfil ausente ou malformado gera erro claro, sem inventar fornecedor;
- Nível A é recusado se algum implementador continuar com fornecedor desconhecido (A2-P01);
- Auto-revisão comparada por identificador de agente (A2-P08);
- Testes com perfil fictício;
- Leitor único do perfil e integração com registro.
"""
import tempfile
import unittest
from pathlib import Path

from util import NUCLEO, rodar, carregar

MOD_REGISTRO = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REGISTRO.Registro
ErroValidacaoRegistro = MOD_REGISTRO.ErroValidacaoRegistro

MOD_PERFIL = carregar(NUCLEO / 'scripts' / 'sc_perfil.py', 'sc_perfil')
PerfilProjeto = MOD_PERFIL.PerfilProjeto
ErroPerfil = MOD_PERFIL.ErroPerfil
carregar_perfil = MOD_PERFIL.carregar_perfil
localizar_perfil = MOD_PERFIL.localizar_perfil
sao_mesmo_agente = MOD_PERFIL.sao_mesmo_agente
extrair_base_agente = MOD_PERFIL.extrair_base_agente

SCRIPT_PERFIL = NUCLEO / 'scripts' / 'sc_perfil.py'

PERFIL_FICTICIO = """# Perfil de Teste Fictício

## Missão
Projeto fictício para validação de regras de perfil.

## Autoridades
- **Decide escopo, prioridade e publicação:** Odival
- **Decide gasto adicional:** Odival
- **Arquiteto (planeja a rodada, avalia e arbitra):** Círdan

## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | Claude Code | Anthropic | Claude Opus 5.5 | high | ativo | 2026-09-24 | planejamento |
| Revisor Independente | Barbárvore | Claude Code | Anthropic | Claude Sonnet 5 | high | ativo | 2026-09-24 | revisão independente |
| Coordenador | Gandalf | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-09-24 | coordenação geral |
| Coleta e procedência | Aragorn | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-09-24 | especialidade de coleta |
| Dados e persistência | Elrond | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-09-24 | especialidade de dados |
| Métodos e qualidade | Galadriel | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-09-24 | especialidade de métodos |
| Interface e acessibilidade | Legolas | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-09-24 | especialidade de interface |
| Executor júnior em nuvem | Jules | Jules | Google | Jules Agent | padrão | reserva | 2026-09-24 | tarefas isoladas |
| Executores locais | Celebrimbor | máquina local | Local | local | padrão | espera | 2026-09-24 | tarefas offline |

## Equipe ativa
- **Papéis ativos:** Círdan, Barbárvore, Gandalf, Aragorn, Elrond, Galadriel, Legolas
- **Papéis em reserva:** Jules
- **Papéis em espera:** Celebrimbor

## Identificadores de agente
| Identificador | Papel | Nome | Variantes reconhecidas |
|---|---|---|---|
| cirdan | Arquiteto | Círdan | cirdan, cirdan-arquiteto, cirdan_architect |
| barbarvore | Revisor Independente | Barbárvore | barbarvore, barbarvore_reviewer, barbarvore2, barbarvore-revisor |
| gandalf | Coordenador | Gandalf | gandalf, gandalf_reviewer, gandalf2, gandalfrevisor, gandalf_coord |
| aragorn | Coleta e procedência | Aragorn | aragorn, aragorn_dev |
| elrond | Dados e persistência | Elrond | elrond, elrond_dev |
| galadriel | Métodos e qualidade | Galadriel | galadriel, galadriel_qa |
| legolas | Interface e acessibilidade | Legolas | legolas, legolas_ui |
| jules | Executor júnior em nuvem | Jules | jules, jules_agent |

## Conectores por papel
| Papel | Conectores autorizados | Ambiente |
|---|---|---|
| Arquiteto | nenhum conector de dados | isolado |
| Revisor Independente | nenhum conector de dados | isolado |
| Coordenador | git push autorizado | desenvolvimento |
| Especialistas | ambiente local | desenvolvimento |
"""


class TestPerfilProjeto(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.p = Path(self.temp_dir.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.pasta_sociedade.mkdir(parents=True)
        self.arquivo_perfil = self.pasta_sociedade / 'perfil.md'
        self.arquivo_perfil.write_text(PERFIL_FICTICIO, encoding='utf-8')

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_perfil_carregamento_e_estrutura(self):
        perfil = carregar_perfil(self.arquivo_perfil)
        self.assertEqual(len(perfil.papeis), 9)
        self.assertEqual(len(perfil.equipe_ativa()), 7)

        # Q95: equipe ativa filtra papéis reserva e espera
        nomes_ativos = [p['nome'] for p in perfil.equipe_ativa()]
        self.assertIn('Gandalf', nomes_ativos)
        self.assertIn('Círdan', nomes_ativos)
        self.assertNotIn('Jules', nomes_ativos)  # reserva
        self.assertNotIn('Celebrimbor', nomes_ativos)  # espera

        # Q109: conectores declarados
        con = perfil.obter_conectores('Arquiteto')
        self.assertIsNotNone(con)
        self.assertIn('nenhum conector', con['conectores'])

    def test_perfil_ausente_gera_erro_claro(self):
        pasta_vazia = self.p / 'vazia'
        pasta_vazia.mkdir()
        with self.assertRaises(ErroPerfil) as ctx:
            carregar_perfil(pasta_vazia)
        self.assertIn('não encontrado', str(ctx.exception).lower())

    def test_perfil_malformado_gera_erro_claro(self):
        arq_malformado = self.p / 'malformado.md'
        arq_malformado.write_text('# Incompleto\n\nTexto sem tabelas.', encoding='utf-8')
        with self.assertRaises(ErroPerfil) as ctx:
            carregar_perfil(arq_malformado)
        self.assertIn('malformado', str(ctx.exception).lower())

        # Linha com colunas incompatíveis
        arq_linhas_erradas = self.p / 'colunas_erradas.md'
        arq_linhas_erradas.write_text(
            "| Papel | Fornecedor |\n|---|---|\n| Gandalf | Google | Extra |\n",
            encoding='utf-8'
        )
        with self.assertRaises(ErroPerfil) as ctx:
            carregar_perfil(arq_linhas_erradas)
        self.assertIn('colunas', str(ctx.exception).lower())

    def test_sem_inventar_fornecedor(self):
        perfil = carregar_perfil(self.arquivo_perfil)
        # Agente cadastrado retorna o fornecedor real
        self.assertEqual(perfil.obter_fornecedor('Gandalf'), 'Google')
        self.assertEqual(perfil.obter_fornecedor('Círdan'), 'Anthropic')

        # Agente desconhecido retorna None e NUNCA inventa fornecedor padrão
        self.assertIsNone(perfil.obter_fornecedor('AgenteInexistente'))
        self.assertIsNone(perfil.obter_fornecedor('Desconhecido'))

    def test_auto_revisao_com_identificadores_de_agente_a2_p08(self):
        perfil = carregar_perfil(self.arquivo_perfil)

        # Variantes mapeadas explicitamente ou por sufixo
        self.assertTrue(perfil.sao_mesmo_agente('Gandalf', 'Gandalf'))
        self.assertTrue(perfil.sao_mesmo_agente('Gandalf_reviewer', 'Gandalf'))
        self.assertTrue(perfil.sao_mesmo_agente('Gandalf2', 'Gandalf'))
        self.assertTrue(perfil.sao_mesmo_agente('GandalfRevisor', 'Gandalf'))
        self.assertTrue(perfil.sao_mesmo_agente('gandalf-reviewer', 'gandalf'))

        # Agentes sabidamente distintos
        self.assertFalse(perfil.sao_mesmo_agente('Barbárvore', 'Gandalf'))
        self.assertFalse(perfil.sao_mesmo_agente('Círdan', 'Gandalf'))
        self.assertFalse(perfil.sao_mesmo_agente('Claude', 'Gandalf'))

    def test_registro_preenche_fornecedor_pelo_perfil(self):
        reg = Registro.inicializar(self.pasta_sociedade, 'teste', str(self.p), versao_inicial='commit1')
        reg.abrir_etapa('E1', 'Obj', 'ref', 'aut', 'commit1', ['C1'])

        # Implementador sem fornecedor declarado (apenas string 'Gandalf')
        # Registro deve preencher automaticamente como 'Google' pelo perfil.md!
        reg.registrar_parecer(
            etapa_id='E1',
            parecer_id='PAR-01',
            revisor='Barbárvore',
            fornecedor_revisor='Anthropic',
            implementadores=['Gandalf'],  # sem fornecedor explícito
            versao_examinada='commit1',
            veredito='aceitar',
            criterios_verificados={'C1': True},
            nivel_independencia='A'
        )

        dados = reg.dados
        evt_parecer = [e for e in dados['eventos'] if e['tipo'] == 'parecer_registrado'][0]
        impls = evt_parecer['dados']['implementadores']
        self.assertEqual(len(impls), 1)
        self.assertEqual(impls[0]['agente'], 'Gandalf')
        self.assertEqual(impls[0]['fornecedor'], 'Google')

    def test_nivel_a_recusado_se_fornecedor_continuar_desconhecido_a2_p01(self):
        reg = Registro.inicializar(self.pasta_sociedade, 'teste', str(self.p), versao_inicial='commit1')
        reg.abrir_etapa('E1', 'Obj', 'ref', 'aut', 'commit1', ['C1'])

        # Agente NãoCadastrado não existe no perfil -> fornecedor continua desconhecido
        with self.assertRaises(ErroValidacaoRegistro) as ctx:
            reg.registrar_parecer(
                etapa_id='E1',
                parecer_id='PAR-01',
                revisor='Barbárvore',
                fornecedor_revisor='Anthropic',
                implementadores=['AgenteDesconhecido'],
                versao_examinada='commit1',
                veredito='aceitar',
                criterios_verificados={'C1': True},
                nivel_independencia='A'
            )
        self.assertIn('fornecedor desconhecido', str(ctx.exception).lower())
        self.assertIn('A2-P01', str(ctx.exception))

    def test_auto_revisao_rejeitada_no_registro_com_variantes_a2_p08(self):
        reg = Registro.inicializar(self.pasta_sociedade, 'teste', str(self.p), versao_inicial='commit1')
        reg.abrir_etapa('E1', 'Obj', 'ref', 'aut', 'commit1', ['C1'])

        # Tentativa de auto-revisão com variante Gandalf_reviewer vs Gandalf
        with self.assertRaises(ErroValidacaoRegistro) as ctx:
            reg.registrar_parecer(
                etapa_id='E1',
                parecer_id='PAR-AUTO',
                revisor='Gandalf_reviewer',
                fornecedor_revisor='Google',
                implementadores=['Gandalf'],
                versao_examinada='commit1',
                veredito='aceitar',
                criterios_verificados={'C1': True},
                nivel_independencia='B',
                justificativa_independencia='Tentativa com variante'
            )
        self.assertIn('auto-revisão rejeitada', str(ctx.exception).lower())

    def test_cli_sc_perfil(self):
        # Validação do perfil fictício
        r = rodar(SCRIPT_PERFIL, str(self.arquivo_perfil), '--validar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('Perfil válido', r.stdout)

        # Consulta de equipe ativa
        r_eq = rodar(SCRIPT_PERFIL, str(self.arquivo_perfil), '--equipe-ativa')
        self.assertEqual(r_eq.returncode, 0)
        self.assertIn('Gandalf', r_eq.stdout)

        # Consulta de fornecedor
        r_forn = rodar(SCRIPT_PERFIL, str(self.arquivo_perfil), '--fornecedor', 'Gandalf')
        self.assertEqual(r_forn.returncode, 0)
        self.assertEqual(r_forn.stdout.strip(), 'Google')

        # Teste de mesmo agente via CLI
        r_mesmo = rodar(SCRIPT_PERFIL, str(self.arquivo_perfil), '--mesmo-agente', 'Gandalf2', 'Gandalf')
        self.assertEqual(r_mesmo.returncode, 0)
        self.assertIn('MESMO AGENTE', r_mesmo.stdout)


class TestCorrecoesDiagnostico(unittest.TestCase):
    """D08 e D09 do diagnóstico de 25/09/2026."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.pasta_sociedade.mkdir()
        (self.pasta_sociedade / 'perfil.md').write_text(PERFIL_FICTICIO, encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_parecer_nao_pode_omitir_implementador_registrado(self):
        # D08: a lista de implementadores era só a declarada por quem registrava o parecer.
        reg = Registro.inicializar(self.pasta_sociedade, 'teste', str(self.p), versao_inicial='commit1')
        reg.abrir_etapa('E1', 'Obj', 'ref', 'aut', 'commit1', ['C1'], responsavel='Gandalf')
        with self.assertRaises(ErroValidacaoRegistro) as ctx:
            reg.registrar_parecer(
                etapa_id='E1', parecer_id='PAR-01', revisor='Revisor Gemini', fornecedor_revisor='Google',
                implementadores=['Celebrimbor:Local'], versao_examinada='commit1', veredito='aceitar',
                criterios_verificados={'C1': True}, nivel_independencia='A')
        self.assertIn('Independência violada', str(ctx.exception))

    def test_tabela_alheia_malformada_nao_derruba_perfil(self):
        # D09: qualquer tabela com colunas desiguais tornava o perfil inteiro ilegível.
        extra = "\n## Notas\n| A | B |\n|---|---|\n| 1 | 2 | 3 |\n"
        perfil = carregar_perfil(conteudo=PERFIL_FICTICIO + extra)
        self.assertEqual(len(perfil.listar_papeis()), 9)

    def test_tabela_de_papeis_malformada_gera_erro_claro(self):
        quebrado = PERFIL_FICTICIO.replace('| Coordenador | Gandalf | Antigravity | Google |', '| Coordenador | Gandalf | Antigravity |', 1)
        with self.assertRaises(ErroPerfil) as ctx:
            carregar_perfil(conteudo=quebrado)
        self.assertIn('malformado', str(ctx.exception))

    def test_papel_nao_casa_por_pedaco_de_texto(self):
        perfil = carregar_perfil(conteudo=PERFIL_FICTICIO)
        self.assertIsNone(perfil.obter_papel('e'))
        self.assertEqual(perfil.obter_papel('revisor')['nome'], 'Barbárvore')
        self.assertEqual(perfil.obter_papel('coordenador')['nome'], 'Gandalf')


if __name__ == '__main__':
    unittest.main()
