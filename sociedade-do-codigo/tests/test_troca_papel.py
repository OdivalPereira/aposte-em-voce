#!/usr/bin/env python3
"""Testes de unidade para a Fatia F4 (Troca de papel: M2; R1–R3).

Critérios de aceite observáveis de F4:
- Comandos 'papel status' e 'papel trocar' funcionais;
- Recusa R1: arquiteto e revisor na mesma plataforma ao mesmo tempo;
- Recusa R2: revisor do mesmo fornecedor de implementador da etapa aberta;
- Recusa R3: execução fora do Google sem decisão registrada;
- Estado 'espera' aceito para o revisor (Q14);
- Simulação por padrão: nenhuma escrita em disco (critério de N5);
- Com --aplicar: evento 'papel_trocado' gravado no registro.json e perfil.md atualizado;
- Mensagem de passagem impressa com papel, modelo, esforço, motivo e data (Q40).
"""
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, rodar, carregar

MOD_REGISTRO = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REGISTRO.Registro

MOD_PERFIL = carregar(NUCLEO / 'scripts' / 'sc_perfil.py', 'sc_perfil')
carregar_perfil = MOD_PERFIL.carregar_perfil

SCRIPT_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'

PERFIL_INICIAL = """# Perfil de Teste de Troca

## Missão
Projeto para teste de troca de papel.

## Autoridades
- **Decide escopo, prioridade e publicação:** Odival
- **Decide gasto adicional:** Odival
- **Arquiteto (planeja a rodada, avalia e arbitra):** Círdan

## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | Claude Code | Anthropic | Claude Opus 5.5 | high | ativo | 2026-09-24 | planejamento |
| Revisor Independente | Barbárvore | Codex CLI | OpenAI | GPT-6 Sol | high | ativo | 2026-09-24 | revisão independente |
| Coordenador | Gandalf | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-09-24 | coordenação geral |
| Coleta e procedência | Aragorn | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-09-24 | especialidade de coleta |
| Dados e persistência | Elrond | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-09-24 | especialidade de dados |
| Métodos e qualidade | Galadriel | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-09-24 | especialidade de métodos |
| Interface e acessibilidade | Legolas | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-09-24 | especialidade de interface |
| Executor júnior em nuvem | Jules | Jules | Google | Jules Agent | padrão | reserva | 2026-09-24 | tarefas isoladas |
| Executores locais | Celebrimbor | máquina local | Local | local | padrão | espera | 2026-09-24 | tarefas offline |

## Equipe ativa
- **Papéis ativos:** Círdan, Barbárvore, Gandalf, Aragorn, Elrond, Galadriel, Legolas

## Conectores por papel
| Papel | Conectores autorizados | Ambiente |
|---|---|---|
| Arquiteto | nenhum conector de dados | isolado |
| Revisor Independente | nenhum conector de dados | isolado |
| Coordenador | git push autorizado | desenvolvimento |
"""


class TestTrocaPapel(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.p = Path(self.temp_dir.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.pasta_sociedade.mkdir(parents=True)
        self.arquivo_perfil = self.pasta_sociedade / 'perfil.md'
        self.arquivo_perfil.write_text(PERFIL_INICIAL, encoding='utf-8')

        # Inicializa registro.json
        self.reg = Registro.inicializar(self.pasta_sociedade, 'teste-troca', str(self.p), versao_inicial='v1.0.0')

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_papel_status(self):
        r = rodar(SCRIPT_RODADA, 'papel', 'status', '--pasta', str(self.pasta_sociedade))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('MATRIZ DE PAPÉIS DO PROJETO', r.stdout)
        self.assertIn('Arquiteto', r.stdout)
        self.assertIn('Barbárvore', r.stdout)
        self.assertIn('EQUIPE ATIVA (Q95)', r.stdout)

    def trocar(self, *args):
        return rodar(SCRIPT_RODADA, 'papel', 'trocar', '--pasta', str(self.pasta_sociedade),
                     '--autor', 'Odival', *args)

    def test_recusa_r1_arquiteto_e_revisor_na_mesma_plataforma(self):
        # Arquiteto está em 'Claude Code' (Anthropic): revisor para lá viola R1.
        r = self.trocar('--papel', 'revisor', '--para', 'Claude Code', '--motivo', 'viola R1')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Violação de R1', r.stderr)
        # Revisor está em 'Codex CLI' (OpenAI): arquiteto para lá viola R1.
        r2 = self.trocar('--papel', 'arquiteto', '--para', 'Codex CLI', '--motivo', 'viola R1')
        self.assertNotEqual(r2.returncode, 0)
        self.assertIn('Violação de R1', r2.stderr)

    def test_recusa_r2_revisor_mesmo_fornecedor_implementador_etapa_aberta(self):
        self.reg.abrir_etapa('E1', 'Meta 1', 'ref', 'aut', 'v1.0.0', ['C1'], responsavel='Gandalf')
        self.reg.registrar_tarefa('E1', 'T1', especialista='Gandalf', descricao='tarefa', fornecedor='Google')
        r = self.trocar('--papel', 'revisor', '--para', 'Antigravity', '--modelo', 'Gemini 3.1 Pro', '--motivo', 'viola R2')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Violação de R2', r.stderr)
        self.assertIn('Google', r.stderr)

    def test_r2_recusa_quando_implementador_sem_fornecedor_conhecido(self):
        # D03: responsável que não casa com o perfil deixava a lista vazia e a R2 passava.
        self.reg.abrir_etapa('E1', 'Meta', 'ref', 'aut', 'v1.0.0', ['C1'], responsavel='Equipe Misteriosa')
        r = self.trocar('--papel', 'revisor', '--para', 'Antigravity', '--modelo', 'Gemini 3.1 Pro', '--motivo', 'teste D03')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('fornecedor desconhecido', r.stderr)

    def test_recusa_r3_execucao_fora_do_google_sem_decisao(self):
        r = self.trocar('--papel', 'execucao', '--para', 'Claude Code', '--modelo', 'Claude Sonnet 5', '--motivo', 'viola R3')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Violação de R3', r.stderr)

    def test_r3_exige_decisao_registrada_especifica(self):
        # D04: qualquer decisão antiga que citasse Odival liberava a execução fora do Google.
        self.reg.abrir_etapa('E1', 'Meta', 'ref', 'aut', 'v1.0.0', ['C1'])
        self.reg.registrar_decisao('E1', 'DEC-RODAPE', 'Odival', 'conversa', 'aprovar o texto do rodapé')
        args = ('--papel', 'execucao', '--para', 'Claude Code', '--modelo', 'Claude Sonnet 5', '--motivo', 'Google sem cota (Q13)')
        self.assertNotEqual(self.trocar(*args).returncode, 0)
        r_outra = self.trocar(*args, '--decisao-ref', 'DEC-RODAPE')
        self.assertNotEqual(r_outra.returncode, 0)
        self.assertIn('não trata de execução', r_outra.stderr)
        self.assertNotEqual(self.trocar(*args, '--decisao-ref', 'DEC-INEXISTENTE').returncode, 0)
        self.reg = Registro(self.pasta_sociedade)
        self.reg.registrar_decisao('E1', 'DEC-ODIVAL-001', 'Odival', 'conversa 25/09',
                                   'autorizar execução fora do Google enquanto a cota não volta')
        r_ok = self.trocar(*args, '--decisao-ref', 'DEC-ODIVAL-001')
        self.assertEqual(r_ok.returncode, 0, r_ok.stdout + r_ok.stderr)
        self.assertIn('SIMULAÇÃO DE TROCA DE PAPEL', r_ok.stdout)

    def test_plataforma_desconhecida_exige_fornecedor_sem_adivinhar(self):
        # D05: 'console' virava OpenAI porque contém 'sol'; 'astra' virava GPT-6 Sol.
        for para in ('console do servidor', 'astra', 'Google'):
            r = self.trocar('--papel', 'revisor', '--para', para, '--motivo', 'teste D05')
            self.assertNotEqual(r.returncode, 0, para)
            self.assertIn('não está no perfil', r.stderr)
        r_ok = self.trocar('--papel', 'revisor', '--para', 'Codex CLI', '--motivo', 'mesma plataforma declarada')
        self.assertEqual(r_ok.returncode, 0, r_ok.stdout + r_ok.stderr)
        self.assertIn('- Fornecedor: OpenAI', r_ok.stdout)

    def test_fornecedor_novo_exige_modelo(self):
        r = self.trocar('--papel', 'arquiteto', '--para', 'Antigravity', '--motivo', 'sem modelo')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('--modelo', r.stderr)

    def test_autor_obrigatorio_e_registrado(self):
        # D06: toda troca ficava registrada como feita pelo Gandalf.
        r_sem = rodar(SCRIPT_RODADA, 'papel', 'trocar', '--pasta', str(self.pasta_sociedade),
                      '--papel', 'revisor', '--estado', 'espera', '--motivo', 'sem autor')
        self.assertNotEqual(r_sem.returncode, 0)
        r = self.trocar('--papel', 'revisor', '--estado', 'espera', '--motivo', 'OpenAI sem cota', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        evts = [e for e in Registro(self.pasta_sociedade).dados['eventos'] if e.get('tipo') == 'papel_trocado']
        self.assertEqual(evts[-1]['autor'], 'Odival')

    def test_troca_altera_so_a_linha_do_papel(self):
        # D07: trocar "revisor" também alterava a linha "Revisor sênior".
        texto = self.arquivo_perfil.read_text(encoding='utf-8').replace(
            '| Coordenador | Gandalf |',
            '| Revisor sênior | Outro | Claude Code | Anthropic | Claude Sonnet 5 | high | reserva | 2026-09-24 | fechamento |\n| Coordenador | Gandalf |')
        self.arquivo_perfil.write_text(texto, encoding='utf-8')
        r = self.trocar('--papel', 'revisor', '--estado', 'espera', '--motivo', 'OpenAI sem cota', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        perfil = carregar_perfil(self.arquivo_perfil)
        estados = {p['papel']: p['estado'] for p in perfil.listar_papeis()}
        self.assertEqual(estados['Revisor Independente'], 'espera')
        self.assertEqual(estados['Revisor sênior'], 'reserva')

    def test_estado_espera_aceito_para_revisor_q14(self):
        r = self.trocar('--papel', 'revisor', '--estado', 'espera', '--motivo', 'OpenAI sem cota de modelo (Q14)')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('Estado: espera', r.stdout)

    def test_simulacao_por_padrao_zero_io_disco(self):
        mtime_perfil_antes = self.arquivo_perfil.stat().st_mtime_ns
        conteudo_perfil_antes = self.arquivo_perfil.read_text(encoding='utf-8')
        eventos_antes = list(self.reg.dados['eventos'])
        arquivos_antes = sorted(x.name for x in self.pasta_sociedade.iterdir())
        r = self.trocar('--papel', 'arquiteto', '--para', 'Antigravity', '--modelo', 'Gemini 3.1 Pro',
                        '--motivo', 'Claude sem cota, contingência Gemini (B4)')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('SIMULAÇÃO DE TROCA DE PAPEL', r.stdout)
        self.assertIn('Nenhuma alteração foi gravada em disco', r.stdout)
        self.assertEqual(self.arquivo_perfil.stat().st_mtime_ns, mtime_perfil_antes)
        self.assertEqual(self.arquivo_perfil.read_text(encoding='utf-8'), conteudo_perfil_antes)
        self.assertEqual(sorted(x.name for x in self.pasta_sociedade.iterdir()), arquivos_antes)
        self.assertEqual(len(Registro(self.pasta_sociedade).dados['eventos']), len(eventos_antes))

    def test_aplicar_grava_em_disco_e_gera_evento(self):
        r = self.trocar('--papel', 'arquiteto', '--para', 'Antigravity', '--modelo', 'Gemini 3.1 Pro',
                        '--motivo', 'Claude sem cota, contingência Gemini (B4)', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('atualizado com sucesso', r.stdout)
        self.assertIn('MENSAGEM DE PASSAGEM', r.stdout)
        arq = carregar_perfil(self.arquivo_perfil).obter_papel('arquiteto')
        self.assertEqual(arq['fornecedor'], 'Google')
        self.assertEqual(arq['plataforma'], 'Antigravity')
        self.assertEqual(arq['modelo'], 'Gemini 3.1 Pro')
        self.assertIn('contingência Gemini', arq['motivo'])
        evts = [e for e in Registro(self.pasta_sociedade).dados['eventos'] if e.get('tipo') == 'papel_trocado']
        self.assertEqual(len(evts), 1)
        self.assertEqual(evts[0]['dados']['papel'], 'arquiteto')
        self.assertEqual(evts[0]['dados']['fornecedor'], 'Google')
        self.assertEqual(evts[0]['dados']['estado'], 'ativo')

    def test_mensagem_de_passagem_formatada(self):
        r = self.trocar('--papel', 'arquiteto', '--para', 'Antigravity', '--modelo', 'Gemini Pro', '--motivo', 'Claude sem cota (B4)')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('MENSAGEM DE PASSAGEM — TROCA DE PAPEL (M2, Q40)', r.stdout)
        self.assertIn('- Papel: Arquiteto', r.stdout)
        self.assertIn('- Fornecedor: Google', r.stdout)
        self.assertIn('- Modelo: Gemini Pro', r.stdout)
        self.assertIn('- Esforço: high', r.stdout)
        self.assertIn('- Motivo: Claude sem cota (B4)', r.stdout)
        self.assertIn('Instruções para o próximo agente:', r.stdout)

    def test_papel_execucao_altera_todos_especialistas_ativos(self):
        # --papel execucao altera coordenador e todos os especialistas ativos (Aragorn, Elrond, Galadriel, Legolas)
        r = self.trocar('--papel', 'execucao', '--para', 'Antigravity', '--modelo', 'Gemini 3.9 Flash',
                        '--esforco', 'high', '--motivo', 'atualização modelo execução', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        perfil = carregar_perfil(self.arquivo_perfil)
        papeis = {p['papel']: p for p in perfil.listar_papeis()}
        for papel_nome in ('Coordenador', 'Coleta e procedência', 'Dados e persistência', 'Métodos e qualidade', 'Interface e acessibilidade'):
            self.assertEqual(papeis[papel_nome]['modelo'], 'Gemini 3.9 Flash', papel_nome)
            self.assertEqual(papeis[papel_nome]['fornecedor'], 'Google', papel_nome)
        # Arquiteto e revisor permanecem inalterados
        self.assertEqual(papeis['Arquiteto']['fornecedor'], 'Anthropic')
        self.assertEqual(papeis['Revisor Independente']['fornecedor'], 'OpenAI')

    def test_alcancar_jules_e_executores_locais_em_espera(self):
        r1 = self.trocar('--papel', 'jules', '--estado', 'espera', '--motivo', 'sem tarefas na nuvem', '--aplicar')
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        r2 = self.trocar('--papel', 'executores_locais', '--estado', 'espera', '--motivo', 'sem tarefas offline', '--aplicar')
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        perfil = carregar_perfil(self.arquivo_perfil)
        papeis = {p['papel']: p for p in perfil.listar_papeis()}
        self.assertEqual(papeis['Executor júnior em nuvem']['estado'], 'espera')
        self.assertEqual(papeis['Executores locais']['estado'], 'espera')

    def test_troca_sem_alterar_nenhuma_linha_falha_sem_evento(self):
        # Tenta trocar arquiteto para os mesmos dados atuais
        contagem_antes = len(Registro(self.pasta_sociedade).dados['eventos'])
        r = self.trocar('--papel', 'arquiteto', '--para', 'Claude Code', '--modelo', 'Claude Opus 5.5',
                        '--esforco', 'high', '--estado', 'ativo', '--motivo', 'planejamento', '--aplicar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('nenhuma linha do perfil foi alterada', r.stderr)
        self.assertEqual(len(Registro(self.pasta_sociedade).dados['eventos']), contagem_antes)

    def test_recusa_r3_para_especialista_ativo_fora_do_google(self):
        # Tenta trocar Elrond para fornecedor fora do Google sem decisão registrada
        r = self.trocar('--papel', 'elrond', '--para', 'Claude Code', '--modelo', 'Claude Sonnet 5',
                        '--fornecedor', 'Anthropic', '--motivo', 'teste R3 especialista')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Violação de R3', r.stderr)


if __name__ == '__main__':
    unittest.main()
