#!/usr/bin/env python3
"""Testes para o Pacote 4: Acabamento, Sincronização e Onboarding (§9, §10 e §11c).

Cobre:
  - §9 / P9: Fatias paralelas seguras com cláusula de disjunção e fechamento independente.
  - §10 / P10: Hash SHA-256 de integridade de sincronia na projeção Markdown e detecção de adulteração.
  - §11c / P11: Script de Onboarding sc_init.py (perfil.md válido, AGENTS.md, registro.json virgem).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL_DIR = RAIZ / 'plugins' / 'sociedade-do-codigo' / 'skills' / 'sociedade-do-codigo'
SCRIPTS_DIR = SKILL_DIR / 'scripts'

sys.path.insert(0, str(SCRIPTS_DIR))
from sc_registro import (
    Registro,
    calcular_hash_conteudo,
    verificar_sincronia_projecao,
)
from validar_perfil import validar as validar_perfil
from sc_init import inicializar_projeto


class TestPacote4FatiasParalelas(unittest.TestCase):
    """Testes de fatias paralelas seguras (§9 / P9)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='sc_teste_p4_fatias_')
        self.p_dir = Path(self.temp_dir)
        self.pasta_soc = self.p_dir / 'sociedade'
        self.py = sys.executable

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_rodada(self, *args):
        cmd = [self.py, str(SCRIPTS_DIR / 'sc_rodada.py'), '--pasta', str(self.pasta_soc)] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', cwd=str(self.p_dir))

    def test_fatia_sequencial_bloqueia_pulo(self):
        # Abre rodada com 3 fatias
        r = self.run_rodada('abrir', '--id', 'R-01', '--meta', 'Meta P4', '--nivel', '2',
                            '--fatia', 'Fatia 1', '--fatia', 'Fatia 2', '--fatia', 'Fatia 3', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        # Tentar iniciar fatia 2 sem --paralelo deve falhar
        r = self.run_rodada('fatia', '2', '--aplicar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('comece pela fatia 1', r.stderr)

    def test_fatia_paralela_exige_arquivos(self):
        r = self.run_rodada('abrir', '--id', 'R-01', '--meta', 'Meta P4', '--nivel', '2',
                            '--fatia', 'Fatia 1', '--fatia', 'Fatia 2', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        # Iniciar com --paralelo sem --arquivos deve falhar
        r = self.run_rodada('fatia', '2', '--paralelo', '--aplicar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('--paralelo exige --arquivos', r.stderr)

    def test_fatia_paralela_rejeitada_nivel_3_sem_forcar(self):
        r = self.run_rodada('abrir', '--id', 'R-01', '--meta', 'Meta N3', '--nivel', '3',
                            '--fatia', 'Fatia 1', '--fatia', 'Fatia 2', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        # No nível 3, paralelo é proibido por padrão
        r = self.run_rodada('fatia', '2', '--paralelo', '--arquivos', 'src/f2.py', '--aplicar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('não são permitidas no nível 3', r.stderr)

    def test_fatias_paralelas_disjuntas_sucesso_e_bloqueio_sobreposicao(self):
        r = self.run_rodada('abrir', '--id', 'R-01', '--meta', 'Meta P4', '--nivel', '2',
                            '--fatia', 'Fatia 1', '--fatia', 'Fatia 2', '--fatia', 'Fatia 3', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        # Inicia fatia 1 com arquivos declarados
        r = self.run_rodada('fatia', '1', '--paralelo', '--arquivos', 'src/auth.py', 'src/models.py', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        # Tenta iniciar fatia 2 com sobreposição em src/models.py -> deve ser bloqueada fail-closed
        r = self.run_rodada('fatia', '2', '--paralelo', '--arquivos', 'src/models.py', 'src/views.py', '--aplicar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('sobreposição de arquivos detectada', r.stderr)
        self.assertIn('conflita com', r.stderr)

        # Tenta iniciar fatia 2 com sobreposição de diretório pai (src/) -> deve bloquear
        r = self.run_rodada('fatia', '2', '--paralelo', '--arquivos', 'src', '--aplicar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('sobreposição de arquivos detectada', r.stderr)

        # Inicia fatia 2 com arquivos 100% disjuntos -> deve ter sucesso
        r = self.run_rodada('fatia', '2', '--paralelo', '--arquivos', 'docs/api.md', 'tests/test_api.py', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        # Verifica rodada.md
        rodada_md = (self.pasta_soc / 'rodada.md').read_text(encoding='utf-8')
        self.assertIn('1. Fatia 1 — em andamento (paralela: src/auth.py, src/models.py)', rodada_md)
        self.assertIn('2. Fatia 2 — em andamento (paralela: docs/api.md, tests/test_api.py)', rodada_md)

        # Verifica registro.json: arquivos persistidos nas tarefas
        reg = Registro(self.pasta_soc)
        tarefas = reg.estado()['etapa_atual']['tarefas']
        self.assertEqual(tarefas['fatia_1']['arquivos'], ['src/auth.py', 'src/models.py'])
        self.assertEqual(tarefas['fatia_2']['arquivos'], ['docs/api.md', 'tests/test_api.py'])

        # Fechar fatia 2 antes da fatia 1 (fechamento independente com prova válida)
        r = self.run_rodada('fatia', '2', '--fechar', '--prova', 'test_api: 5 passed in 0.12s', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        rodada_md_pos = (self.pasta_soc / 'rodada.md').read_text(encoding='utf-8')
        self.assertIn('2. Fatia 2 — fechada · prova: test_api: 5 passed in 0.12s', rodada_md_pos)
        self.assertIn('1. Fatia 1 — em andamento', rodada_md_pos)


class TestPacote4HashSincronia(unittest.TestCase):
    """Testes de hash de integridade de sincronia na projeção Markdown (§10 / P10)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='sc_teste_p4_hash_')
        self.p_dir = Path(self.temp_dir)
        self.pasta_soc = self.p_dir / 'sociedade'
        self.py = sys.executable

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_rodada(self, *args):
        cmd = [self.py, str(SCRIPTS_DIR / 'sc_rodada.py'), '--pasta', str(self.pasta_soc)] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', cwd=str(self.p_dir))

    def test_marcador_sincronia_gravado_e_verificado_com_sucesso(self):
        r = self.run_rodada('abrir', '--id', 'R-01', '--meta', 'Meta Hash', '--nivel', '2',
                            '--fatia', 'Unica', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        # Projeta andamento.md
        andamento_md = self.pasta_soc / 'andamento.md'
        andamento_md.write_text('# Andamento\n', encoding='utf-8')
        r = self.run_rodada('projetar', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        conteudo_andamento = andamento_md.read_text(encoding='utf-8')
        self.assertIn('<!-- registro_revisao:', conteudo_andamento)
        self.assertIn('<!-- registro_sincronia: rev=', conteudo_andamento)
        self.assertIn('sha=', conteudo_andamento)

        conteudo_rodada = (self.pasta_soc / 'rodada.md').read_text(encoding='utf-8')
        self.assertIn('<!-- registro_sincronia: rev=', conteudo_rodada)

        # Comando sincronizar deve retornar sucesso
        r = self.run_rodada('sincronizar')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('sincronizado', r.stdout)

    def test_sincronizar_detecta_adulteracao_manual(self):
        r = self.run_rodada('abrir', '--id', 'R-01', '--meta', 'Meta Hash', '--nivel', '2',
                            '--fatia', 'Unica', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        andamento_md = self.pasta_soc / 'andamento.md'
        andamento_md.write_text('# Andamento\n', encoding='utf-8')
        r = self.run_rodada('projetar', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)

        # Adultera o hash no andamento.md
        conteudo = andamento_md.read_text(encoding='utf-8')
        adulterado = conteudo.replace('sha=', 'sha=deadbeefcafebabe')
        andamento_md.write_text(adulterado, encoding='utf-8')

        # Sincronizar deve acusar desatualizado/adulterado
        r = self.run_rodada('sincronizar')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('desatualizado', r.stdout)


class TestPacote4OnboardingInit(unittest.TestCase):
    """Testes do script de onboarding sc_init.py (§11c / P11)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='sc_teste_p4_init_')
        self.p_dir = Path(self.temp_dir)
        self.py = sys.executable

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_dry_run_nao_cria_arquivos(self):
        relatorio = inicializar_projeto(
            destino=str(self.p_dir),
            nome='Projeto DryRun',
            missao='Testar simulação sem escrita',
            aplicar=False,
        )
        self.assertIn('SIMULAÇÃO', relatorio)
        self.assertFalse((self.p_dir / 'sociedade' / 'perfil.md').exists())
        self.assertFalse((self.p_dir / 'sociedade' / 'registro.json').exists())

    def test_init_completo_cria_e_valida_todos_os_artefatos(self):
        relatorio = inicializar_projeto(
            destino=str(self.p_dir),
            nome='Minha App Core',
            missao='Processamento de dados seguro',
            autoridade='Odival',
            stack='Python 3.12, sqlite3',
            comando_build='make build',
            comando_teste='pytest -q',
            comando_lint='flake8',
            com_jules=True,
            aplicar=True,
        )
        self.assertIn('[VALIDADO] Perfil aprovado', relatorio)
        self.assertIn('[OK] sociedade/registro.json inicializado', relatorio)

        # 1. Verifica perfil.md
        perfil_path = self.p_dir / 'sociedade' / 'perfil.md'
        self.assertTrue(perfil_path.is_file())
        faltam, avisos = validar_perfil(str(perfil_path))
        self.assertEqual(len(faltam), 0, f'Perfil com campos faltantes: {faltam}')

        texto_perfil = perfil_path.read_text(encoding='utf-8')
        self.assertIn('# Perfil de Minha App Core', texto_perfil)
        self.assertIn('## Missão\nProcessamento de dados seguro', texto_perfil)
        self.assertIn('Decide escopo, prioridade e publicação:** Odival', texto_perfil)
        self.assertIn('make build', texto_perfil)
        self.assertIn('pytest -q', texto_perfil)
        self.assertNotIn('<', texto_perfil)  # Zero marcadores residuais

        # 2. Verifica AGENTS.md
        agents_path = self.p_dir / 'AGENTS.md'
        self.assertTrue(agents_path.is_file())
        texto_agents = agents_path.read_text(encoding='utf-8')
        self.assertIn('<!-- sociedade-do-codigo:inicio', texto_agents)
        self.assertIn('<!-- sociedade-do-codigo:fim -->', texto_agents)

        # 3. Verifica sociedade/registro.json
        reg_path = self.p_dir / 'sociedade' / 'registro.json'
        self.assertTrue(reg_path.is_file())
        reg = Registro(self.p_dir / 'sociedade')
        self.assertEqual(reg.revisao, 1)
        self.assertEqual(reg._dados['projeto_id'], 'minha-app-core')

        # 4. Verifica sociedade/historico.md
        hist_path = self.p_dir / 'sociedade' / 'historico.md'
        self.assertTrue(hist_path.is_file())
        texto_hist = hist_path.read_text(encoding='utf-8')
        self.assertIn('adoção da Sociedade do Código', texto_hist)

    def test_init_cli_wrapper(self):
        cmd = [
            self.py,
            str(RAIZ / 'scripts' / 'sc_init.py'),
            '--destino', str(self.p_dir),
            '--nome', 'Projeto CLI',
            '--missao', 'Teste via entry point raiz',
            '--aplicar',
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.p_dir))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.p_dir / 'sociedade' / 'perfil.md').is_file())
        self.assertTrue((self.p_dir / 'sociedade' / 'registro.json').is_file())


if __name__ == '__main__':
    unittest.main()
