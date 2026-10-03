"""Testes unitários dedicados para sc_init.py pós-teste operacional.

Cobre:
1. Captura automática do commit Git inicial no registro.json (versao_inicial).
2. Preservação da versão inicial sem dependência de flags manuais.
3. Abertura subsequente de rodada herdando versao_inicial em vez de <preencher>.
4. Execução do sc_init via CLI com validação determinística dos artefatos.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, carregar, rodar

MOD_INIT = carregar(NUCLEO / 'scripts' / 'sc_init.py', 'sc_init')
inicializar_projeto = MOD_INIT.inicializar_projeto
obter_commit_git_head = MOD_INIT.obter_commit_git_head

MOD_REG = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REG.Registro

SCRIPT_INIT = NUCLEO / 'scripts' / 'sc_init.py'
SCRIPT_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'


class TesteScInitEvolucoes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)

        # Inicializa repositório Git no diretório de teste
        subprocess.run(['git', 'init'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'tester@sociedade.org'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Tester'], cwd=self.p, capture_output=True, check=True)
        (self.p / 'README.md').write_text('# Projeto Inicializado\n', encoding='utf-8')
        subprocess.run(['git', 'add', 'README.md'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'commit inicial de teste'], cwd=self.p, capture_output=True, check=True)
        r = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.p, capture_output=True, text=True, check=True)
        self.commit_inicial = r.stdout.strip()

    def tearDown(self):
        self._tmp.cleanup()

    def test_captura_commit_git_inicial(self):
        commit = obter_commit_git_head(self.p)
        self.assertEqual(commit, self.commit_inicial)

    def test_inicializar_projeto_grava_versao_inicial_no_registro(self):
        relatorio = inicializar_projeto(
            destino=str(self.p),
            nome='Projeto Teste Init',
            missao='Testar captura de versao git',
            aplicar=True
        )
        self.assertIn('registro.json inicializado com sucesso', relatorio)
        self.assertIn(self.commit_inicial[:7], relatorio)

        p_reg = self.p / 'sociedade' / 'registro.json'
        self.assertTrue(p_reg.is_file())
        dados = json.loads(p_reg.read_text(encoding='utf-8'))
        self.assertEqual(dados.get('versao_inicial'), self.commit_inicial)

    def test_rodada_aberta_apos_init_usa_versao_inicial(self):
        # 1. Executa init
        inicializar_projeto(
            destino=str(self.p),
            nome='Projeto Auto Versao',
            aplicar=True
        )

        # 2. Abre rodada sem informar --base
        res_abrir = rodar(
            SCRIPT_RODADA, 'abrir',
            '--pasta', str(self.p / 'sociedade'),
            '--id', 'SC-E1',
            '--meta', 'Primeira entrega após init',
            '--aceite', 'C01',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(res_abrir.returncode, 0, res_abrir.stderr)

        # 3. Verifica que a rodada e o registro não ficaram com '<preencher>'
        p_rod = self.p / 'sociedade' / 'rodada.md'
        txt = p_rod.read_text(encoding='utf-8')
        self.assertIn(f'- base: {self.commit_inicial}', txt)
        self.assertNotIn('- base: <preencher>', txt)

        reg = Registro(self.p / 'sociedade')
        est = reg.estado()
        self.assertEqual(est['etapa_atual']['base_efetiva'], self.commit_inicial)

    def test_cli_sc_init_sucesso(self):
        res = rodar(
            SCRIPT_INIT,
            '--destino', str(self.p),
            '--nome', 'CLI Init Test',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((self.p / 'sociedade' / 'perfil.md').is_file())
        self.assertTrue((self.p / 'sociedade' / 'registro.json').is_file())

    def test_inicializar_projeto_simulacao_nao_escreve_arquivos(self):
        relatorio = inicializar_projeto(
            destino=str(self.p),
            nome='Projeto Simulacao Init',
            aplicar=False
        )
        self.assertIn('[SIMULAÇÃO]', relatorio)
        self.assertIn('[VALIDADO] Perfil aprovado', relatorio)
        self.assertNotIn('[OK]', relatorio)
        self.assertFalse((self.p / 'sociedade' / 'perfil.md').exists())
        self.assertFalse((self.p / 'sociedade' / 'registro.json').exists())
        self.assertFalse((self.p / 'sociedade' / 'historico.md').exists())


if __name__ == '__main__':
    unittest.main()
