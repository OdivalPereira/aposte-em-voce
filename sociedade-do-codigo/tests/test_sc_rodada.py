"""Testes unitários dedicados para sc_rodada.py pós-teste operacional.

Cobre:
1. sc_rodada.py abrir com Git HEAD automático (--sincronizar-git ou resolução de placeholder).
2. sc_rodada.py sincronizar-versao (atualização de versão no registro e na rodada).
3. sc_rodada.py parecer e encerrar com --sincronizar-git.
4. sc_rodada.py achado com sinônimos de status (resolvido, fechado, atendido -> corrigido; abrir, novo -> aberto) e uso de --id.
5. sc_rodada.py achado reabrindo achado já corrigido.
6. sc_rodada.py parsing e encerramento com fatias marcadas como "concluida" e "em_andamento".
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, carregar, rodar

MOD_REG = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REG.Registro

MOD_ROD = carregar(NUCLEO / 'scripts' / 'sc_rodada.py', 'sc_rodada')
fatias_de = MOD_ROD.fatias_de
partir = MOD_ROD.partir

SCRIPT_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'


class TesteScRodadaEvolucoes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'

        # Inicializa repositório Git no diretório do teste
        subprocess.run(['git', 'init'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'tester@sociedade.org'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Tester'], cwd=self.p, capture_output=True, check=True)
        (self.p / 'README.md').write_text('# Repositório de Teste\n', encoding='utf-8')
        subprocess.run(['git', 'add', 'README.md'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'commit base'], cwd=self.p, capture_output=True, check=True)
        r = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.p, capture_output=True, text=True, check=True)
        self.commit_inicial = r.stdout.strip()

    def tearDown(self):
        self._tmp.cleanup()

    def test_abrir_com_sincronizar_git_captura_head(self):
        res = rodar(
            SCRIPT_RODADA, 'abrir',
            '--pasta', str(self.pasta_sociedade),
            '--id', 'SC-E1',
            '--meta', 'Meta com Git',
            '--aceite', 'C01',
            '--fatia', 'Fatia inicial',
            '--sincronizar-git',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        p_rod = self.pasta_sociedade / 'rodada.md'
        self.assertTrue(p_rod.is_file())
        conteudo = p_rod.read_text(encoding='utf-8')
        self.assertIn(f'- base: {self.commit_inicial}', conteudo)

        reg = Registro(self.pasta_sociedade)
        est = reg.estado()
        self.assertEqual(est['etapa_atual']['base_efetiva'], self.commit_inicial)

    def test_sincronizar_versao_atualiza_registro_e_rodada(self):
        # Abre rodada com base manual
        rodar(
            SCRIPT_RODADA, 'abrir',
            '--pasta', str(self.pasta_sociedade),
            '--id', 'SC-E1',
            '--meta', 'Meta Teste',
            '--aceite', 'C01',
            '--base', '<preencher>',
            '--aplicar',
            cwd=self.p
        )
        novo_hash = 'abcdef1234567890'
        res_sync = rodar(
            SCRIPT_RODADA, 'sincronizar-versao',
            '--pasta', str(self.pasta_sociedade),
            '--versao', novo_hash,
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(res_sync.returncode, 0, res_sync.stderr)

        p_rod = self.pasta_sociedade / 'rodada.md'
        self.assertIn(f'- base: {novo_hash}', p_rod.read_text(encoding='utf-8'))

        reg = Registro(self.pasta_sociedade)
        est = reg.estado()
        self.assertEqual(est['etapa_atual']['versao_atual'], novo_hash)

    def test_parecer_e_encerrar_com_sincronizar_git(self):
        # 1. Abre rodada com <preencher>
        rodar(
            SCRIPT_RODADA, 'abrir',
            '--pasta', str(self.pasta_sociedade),
            '--id', 'SC-E1',
            '--meta', 'Etapa para Parecer',
            '--aceite', 'C01',
            '--fatia', 'Fatia 1',
            '--base', '<preencher>',
            '--aplicar',
            cwd=self.p
        )
        # Fecha a fatia 1
        rodar(
            SCRIPT_RODADA, 'fatia', '1',
            '--pasta', str(self.pasta_sociedade),
            '--fechar',
            '--prova', 'testes passaram',
            '--aplicar',
            cwd=self.p
        )
        # Registra evidência para C01
        rodar(
            SCRIPT_RODADA, 'evidencia',
            '--pasta', str(self.pasta_sociedade),
            '--criterio', 'C01',
            '--comando', 'pytest',
            '--saida', '1 passed',
            '--verificador', 'Gandalf',
            '--aplicar',
            cwd=self.p
        )

        # 2. Parecer com --sincronizar-git
        res_par = rodar(
            SCRIPT_RODADA, 'parecer',
            '--pasta', str(self.pasta_sociedade),
            '--revisor', 'Claude',
            '--fornecedor', 'Anthropic',
            '--implementador', 'Legolas:OpenAI',
            '--veredito', 'aceitar',
            '--criterio-ok', 'C01',
            '--sincronizar-git',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(res_par.returncode, 0, res_par.stderr)

        # 3. Encerrar com --sincronizar-git
        res_enc = rodar(
            SCRIPT_RODADA, 'encerrar',
            '--pasta', str(self.pasta_sociedade),
            '--sincronizar-git',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(res_enc.returncode, 0, res_enc.stderr)

    def test_achados_sinonimos_resolvido_fechado_atendido(self):
        rodar(
            SCRIPT_RODADA, 'abrir',
            '--pasta', str(self.pasta_sociedade),
            '--id', 'SC-E1',
            '--meta', 'Meta Achados',
            '--aceite', 'C01',
            '--aplicar',
            cwd=self.p
        )
        # Registra 3 achados
        rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
              '--id', 'REV-001', '--severidade', 'relevante', '--onde', 'a.py:1', '--texto', 'A1', '--aplicar', cwd=self.p)
        rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
              '--id', 'REV-002', '--severidade', 'opcional', '--onde', 'b.py:2', '--texto', 'A2', '--aplicar', cwd=self.p)
        rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
              '--id', 'REV-003', '--severidade', 'relevante', '--onde', 'c.py:3', '--texto', 'A3', '--aplicar', cwd=self.p)

        # Atualiza com resolvido
        r1 = rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
                   '--id', 'REV-001', '--status', 'resolvido', '--aplicar', cwd=self.p)
        self.assertEqual(r1.returncode, 0, r1.stderr)

        # Atualiza com fechado
        r2 = rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
                   '--fechar', 'REV-002', '--status', 'fechado', '--aplicar', cwd=self.p)
        self.assertEqual(r2.returncode, 0, r2.stderr)

        # Atualiza com atendido
        r3 = rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
                   '--id', 'REV-003', '--status', 'atendido', '--aplicar', cwd=self.p)
        self.assertEqual(r3.returncode, 0, r3.stderr)

        p_rod = self.pasta_sociedade / 'rodada.md'
        txt = p_rod.read_text(encoding='utf-8')
        self.assertIn('REV-001 · relevante · a.py:1 · A1 · corrigido', txt)
        self.assertIn('REV-002 · opcional · b.py:2 · A2 · corrigido', txt)
        self.assertIn('REV-003 · relevante · c.py:3 · A3 · corrigido', txt)

    def test_achado_reabertura_de_corrigido_para_aberto(self):
        rodar(
            SCRIPT_RODADA, 'abrir',
            '--pasta', str(self.pasta_sociedade),
            '--id', 'SC-E1',
            '--meta', 'Meta Reabertura',
            '--aceite', 'C01',
            '--aplicar',
            cwd=self.p
        )
        rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
              '--id', 'REV-001', '--severidade', 'relevante', '--onde', 'a.py:1', '--texto', 'A1', '--aplicar', cwd=self.p)

        # Fecha primeiro
        rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
              '--id', 'REV-001', '--status', 'corrigido', '--aplicar', cwd=self.p)
        txt_fechado = (self.pasta_sociedade / 'rodada.md').read_text(encoding='utf-8')
        self.assertIn('REV-001 · relevante · a.py:1 · A1 · corrigido', txt_fechado)

        # Reabre usando --status abrir
        r_reabrir = rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
                          '--id', 'REV-001', '--status', 'abrir', '--aplicar', cwd=self.p)
        self.assertEqual(r_reabrir.returncode, 0, r_reabrir.stderr)
        txt_reaberto = (self.pasta_sociedade / 'rodada.md').read_text(encoding='utf-8')
        self.assertIn('REV-001 · relevante · a.py:1 · A1 · aberto', txt_reaberto)

    def test_parsing_fatias_concluida_e_em_andamento(self):
        secoes = {
            'Fatias': [
                '1. Primeira fatia — concluida · prova: ok',
                '2. Segunda fatia — em_andamento',
                '3. Terceira fatia — em andamento',
                '4. Quarta fatia — pendente',
            ]
        }
        fs = fatias_de(secoes)
        self.assertEqual(len(fs), 4)
        self.assertEqual(fs[0]['estado'], 'fechada')
        self.assertEqual(fs[1]['estado'], 'em andamento')
        self.assertEqual(fs[2]['estado'], 'em andamento')
        self.assertEqual(fs[3]['estado'], 'pendente')

    def test_encerrar_com_fatia_marcada_concluida(self):
        rodar(
            SCRIPT_RODADA, 'abrir',
            '--pasta', str(self.pasta_sociedade),
            '--id', 'SC-E1',
            '--meta', 'Meta Concluida',
            '--fatia', 'Fatia Concluida',
            '--aceite', 'C01',
            '--aplicar',
            cwd=self.p
        )
        p_rod = self.pasta_sociedade / 'rodada.md'
        txt = p_rod.read_text(encoding='utf-8')
        # Simula escrita com o sufixo "— concluida"
        txt_concluida = txt.replace('1. Fatia Concluida — pendente', '1. Fatia Concluida — concluida · prova: ok')
        p_rod.write_text(txt_concluida, encoding='utf-8')

        reg = Registro(self.pasta_sociedade)
        reg.atualizar_tarefa('SC-E1', 'fatia_1', 'concluida')
        reg.registrar_evidencia('SC-E1', 'fatia_1', 'python3 -m py_compile x.py', 0, 'ok')
        reg.registrar_evidencia('SC-E1', 'C01', 'pytest', 0, 'ok')
        reg.registrar_parecer(
            etapa_id='SC-E1',
            parecer_id='PAR-001',
            revisor='Claude',
            fornecedor_revisor='Anthropic',
            implementadores=[{'agente': 'Legolas', 'fornecedor': 'OpenAI'}],
            versao_examinada=self.commit_inicial,
            veredito='aceitar',
            criterios_verificados={'C01': True, 'fatia_1': True}
        )

        res_enc = rodar(
            SCRIPT_RODADA, 'encerrar',
            '--pasta', str(self.pasta_sociedade),
            '--sincronizar-git',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(res_enc.returncode, 0, res_enc.stderr)


if __name__ == '__main__':
    unittest.main()
