"""Testes unitários para Fatia F2: Worktrees e sociedade/ canônica (Q60).

Cobre:
1. Script executado dentro de um worktree grava na pasta sociedade/ do repositório principal.
2. Localização canônica via Git common dir com fallback robusto fora de repositórios Git.
3. Criação de worktree recusa destino/etapa já existente.
4. Remoção de worktree recusa diretório com alterações pendentes sem commit (a menos que forçado).
5. Portão pré-devolução (sc_pre_devolucao.py) reprova candidato que altere arquivos em sociedade/.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, carregar, rodar

MOD_REG = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
localizar_sociedade_canonica = MOD_REG.localizar_sociedade_canonica
Registro = MOD_REG.Registro

MOD_WT = carregar(NUCLEO / 'scripts' / 'sc_worktree.py', 'sc_worktree')
criar_worktree = MOD_WT.criar_worktree
listar_worktrees = MOD_WT.listar_worktrees
remover_worktree = MOD_WT.remover_worktree
obter_caminho_worktree = MOD_WT.obter_caminho_worktree
ErroWorktree = MOD_WT.ErroWorktree

MOD_PRE = carregar(NUCLEO / 'scripts' / 'sc_pre_devolucao.py', 'sc_pre_devolucao')
VerificadorPreDevolucao = MOD_PRE.VerificadorPreDevolucao

SCRIPT_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'
SCRIPT_WT = NUCLEO / 'scripts' / 'sc_worktree.py'
SCRIPT_PRE = NUCLEO / 'scripts' / 'sc_pre_devolucao.py'


def inicializar_repo_git_teste(caminho: Path):
    """Cria um repositório Git de teste com commit inicial e pasta sociedade/."""
    caminho.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'init', '-b', 'main'], cwd=caminho, capture_output=True, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Testador'], cwd=caminho, capture_output=True, check=True)
    subprocess.run(['git', 'config', 'user.email', 'teste@sociedade.local'], cwd=caminho, capture_output=True, check=True)

    # Cria README inicial e commit
    (caminho / 'README.md').write_text('# Projeto Teste\n', encoding='utf-8')
    subprocess.run(['git', 'add', 'README.md'], cwd=caminho, capture_output=True, check=True)
    subprocess.run(['git', 'commit', '-m', 'feat: commit inicial'], cwd=caminho, capture_output=True, check=True)

    # Cria sociedade/ com registro virgem
    pasta_soc = caminho / 'sociedade'
    pasta_soc.mkdir(parents=True, exist_ok=True)
    dados_reg = {
        'versao_formato': '2.1.0',
        'revisao': 0,
        'criado_em': '2026-09-24T00:00:00Z',
        'atualizado_em': '2026-09-24T00:00:00Z',
        'projeto_id': 'teste-f2',
        'eventos': []
    }
    (pasta_soc / 'registro.json').write_text(json.dumps(dados_reg, indent=2), encoding='utf-8')
    (pasta_soc / 'historico.md').write_text('# Histórico\n', encoding='utf-8')


class TesteWorktreeSociedadeCanonica(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.repo_main = self.tmp_path / 'repo_principal'
        inicializar_repo_git_teste(self.repo_main)
        self.raiz_trabalho = self.tmp_path / 'trabalho'
        self.raiz_trabalho.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_localizar_sociedade_canonica_em_repo_e_em_worktree(self):
        """Verifica que a sociedade/ canônica aponta para o repositório principal a partir de qualquer worktree."""
        # 1. No repositório principal
        soc_main = localizar_sociedade_canonica(self.repo_main)
        self.assertEqual(soc_main, self.repo_main / 'sociedade')

        # 2. Em um subdiretório do repo principal
        subdir = self.repo_main / 'src' / 'modulo'
        subdir.mkdir(parents=True, exist_ok=True)
        soc_sub = localizar_sociedade_canonica(subdir)
        self.assertEqual(soc_sub, self.repo_main / 'sociedade')

        # 3. Criação de worktree
        res_wt = criar_worktree(
            etapa='f2-teste',
            pasta_base=self.repo_main,
            pasta_raiz=self.raiz_trabalho
        )
        caminho_wt = Path(res_wt['caminho'])
        self.assertTrue(caminho_wt.is_dir())

        # 4. A partir de dentro do worktree, deve localizar repo_main / sociedade
        soc_wt = localizar_sociedade_canonica(caminho_wt)
        self.assertEqual(soc_wt, self.repo_main / 'sociedade')

        # 5. Fallback fora do git
        pasta_nao_git = self.tmp_path / 'fora_do_git'
        pasta_nao_git.mkdir(parents=True, exist_ok=True)
        soc_fora = localizar_sociedade_canonica(pasta_nao_git)
        self.assertEqual(soc_fora, pasta_nao_git / 'sociedade')

    def test_script_no_worktree_grava_na_sociedade_canonica(self):
        """Comandos executados dentro do worktree gravam na pasta sociedade/ do repo principal."""
        res_wt = criar_worktree(
            etapa='etapa-exec',
            pasta_base=self.repo_main,
            pasta_raiz=self.raiz_trabalho
        )
        caminho_wt = Path(res_wt['caminho'])

        # Executa sc_rodada.py abrir a partir do worktree, sem passar --pasta
        res = rodar(
            SCRIPT_RODADA,
            'abrir',
            '--id', 'ETP-WT',
            '--meta', 'Meta executada no worktree',
            '--aplicar',
            cwd=str(caminho_wt)
        )
        self.assertEqual(res.returncode, 0, f'Falha ao abrir rodada: {res.stderr}')

        # Verifica se o evento foi gravado na sociedade/ do repositório principal
        reg_main = self.repo_main / 'sociedade' / 'registro.json'
        dados = json.loads(reg_main.read_text(encoding='utf-8'))
        eventos = dados['eventos']
        self.assertTrue(any(e.get('dados', {}).get('etapa_id') == 'ETP-WT' for e in eventos))

        # Garante que NENHUMA pasta sociedade/ foi criada dentro do worktree
        self.assertFalse((caminho_wt / 'sociedade').exists(), 'Candidato não deve conter pasta sociedade/!')

    def test_worktree_criar_recusa_nome_existente(self):
        """Tentativa de criar worktree em pasta já existente deve falhar com erro claro."""
        res1 = criar_worktree(
            etapa='etapa-duplicada',
            pasta_base=self.repo_main,
            pasta_raiz=self.raiz_trabalho
        )
        self.assertTrue(Path(res1['caminho']).is_dir())

        # Segunda tentativa com o mesmo nome deve disparar ErroWorktree
        with self.assertRaises(ErroWorktree) as ctx:
            criar_worktree(
                etapa='etapa-duplicada',
                pasta_base=self.repo_main,
                pasta_raiz=self.raiz_trabalho
            )
        self.assertIn('já existe', str(ctx.exception).lower())

        # Teste via CLI
        cli_res = rodar(
            SCRIPT_WT,
            '--raiz', str(self.raiz_trabalho),
            '--pasta-base', str(self.repo_main),
            'criar',
            '--etapa', 'etapa-duplicada'
        )
        self.assertEqual(cli_res.returncode, 1)
        self.assertIn('já existe', cli_res.stderr.lower())

    def test_worktree_listar(self):
        """Lista worktrees do projeto corretamente."""
        criar_worktree(etapa='etp-1', pasta_base=self.repo_main, pasta_raiz=self.raiz_trabalho)
        criar_worktree(etapa='etp-2', pasta_base=self.repo_main, pasta_raiz=self.raiz_trabalho)

        wts = listar_worktrees(pasta_base=self.repo_main, pasta_raiz=self.raiz_trabalho)
        etapas_encontradas = [w['etapa'] for w in wts]
        self.assertIn('etp-1', etapas_encontradas)
        self.assertIn('etp-2', etapas_encontradas)

        cli_res = rodar(
            SCRIPT_RODADA,
            'worktree',
            'listar',
            '--raiz', str(self.raiz_trabalho),
            '--pasta-base', str(self.repo_main)
        )
        self.assertEqual(cli_res.returncode, 0)
        self.assertIn('etp-1', cli_res.stdout)
        self.assertIn('etp-2', cli_res.stdout)

    def test_worktree_remover_recusa_alteracoes_sem_commit_e_permite_com_forcar(self):
        """Remoção de worktree deve recusar se houver alterações não commitadas (sem --forcar)."""
        res_wt = criar_worktree(
            etapa='etapa-suja',
            pasta_base=self.repo_main,
            pasta_raiz=self.raiz_trabalho
        )
        caminho_wt = Path(res_wt['caminho'])

        # Cria alteração não commitada no worktree
        arquivo_sujo = caminho_wt / 'codigo_novo.py'
        arquivo_sujo.write_text('print("alteracao pendente")\n', encoding='utf-8')

        # Tentativa de remover sem forçar deve falhar
        with self.assertRaises(ErroWorktree) as ctx:
            remover_worktree(
                etapa='etapa-suja',
                forcar=False,
                pasta_base=self.repo_main,
                pasta_raiz=self.raiz_trabalho
            )
        self.assertIn('alterações não commitadas', str(ctx.exception).lower())
        self.assertTrue(caminho_wt.is_dir(), 'Diretório não deveria ter sido removido')

        # Teste via CLI sem forçar
        cli_falha = rodar(
            SCRIPT_RODADA,
            'worktree',
            'remover',
            '--etapa', 'etapa-suja',
            '--raiz', str(self.raiz_trabalho),
            '--pasta-base', str(self.repo_main)
        )
        self.assertEqual(cli_falha.returncode, 1)
        self.assertIn('alterações não commitadas', cli_falha.stderr.lower())

        # Remoção com --forcar deve suceder
        cli_ok = rodar(
            SCRIPT_RODADA,
            'worktree',
            'remover',
            '--etapa', 'etapa-suja',
            '--forcar',
            '--raiz', str(self.raiz_trabalho),
            '--pasta-base', str(self.repo_main)
        )
        self.assertEqual(cli_ok.returncode, 0)
        self.assertFalse(caminho_wt.exists(), 'Worktree deveria ter sido removido com sucesso')

    def test_portao_reprova_alteracao_em_sociedade(self):
        """sc_pre_devolucao deve REPROVAR categoricamente qualquer alteração em arquivos de sociedade/."""
        verificador = VerificadorPreDevolucao(
            pasta_projeto=self.repo_main,
            pasta_sociedade=self.repo_main / 'sociedade'
        )

        # 1. Candidato tenta alterar arquivo dentro de sociedade/
        atestado_reprovado = verificador.executar(
            papel='Gandalf',
            etapa_id='ETP-01',
            fatia_id='F1',
            ignorar_testes=True,
            motivo_ignorar='teste isolamento governanca',
            arquivos_alvo=['sociedade/registro.json']
        )
        self.assertEqual(atestado_reprovado['status'], 'REPROVADO')
        self.assertFalse(atestado_reprovado['verificacoes']['higiene_pastas']['ok'])
        self.assertTrue(any('sociedade' in e.lower() for e in atestado_reprovado['erros']))

        # 2. Candidato altera código do produto limpo
        (self.repo_main / 'main.py').write_text('print("produto ok")\n', encoding='utf-8')
        atestado_aprovado = verificador.executar(
            papel='Gandalf',
            etapa_id='ETP-01',
            fatia_id='F1',
            ignorar_testes=True,
            motivo_ignorar='teste produto limpo',
            arquivos_alvo=['main.py']
        )
        self.assertEqual(atestado_aprovado['status'], 'APROVADO')
        self.assertTrue(atestado_aprovado['verificacoes']['higiene_pastas']['ok'])


class TesteWorktreeCaminhosSeguros(unittest.TestCase):
    """D02 do diagnóstico de 25/09/2026: 'remover --forcar' com '../' apagava pasta que não era worktree,
    e 'criar' aceitava destino fora da raiz de trabalho."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.repo_main = self.tmp_path / 'repo_principal'
        inicializar_repo_git_teste(self.repo_main)
        self.raiz = self.tmp_path / 'trabalho'
        (self.raiz / 'proj').mkdir(parents=True)
        self.vitima = self.tmp_path / 'vitima'
        self.vitima.mkdir()
        (self.vitima / 'dado.txt').write_text('importante\n', encoding='utf-8')

    def tearDown(self):
        self._tmp.cleanup()

    def test_remover_com_barra_ou_pontos_e_recusado_e_nada_e_apagado(self):
        for etapa in ('../../vitima', '../vitima', 'a/b', '..'):
            with self.assertRaises(ErroWorktree):
                remover_worktree(etapa=etapa, forcar=True, projeto='proj',
                                 pasta_base=self.repo_main, pasta_raiz=self.raiz)
        self.assertTrue((self.vitima / 'dado.txt').is_file())

    def test_remover_pasta_que_nao_e_worktree_e_recusado_mesmo_com_forcar(self):
        comum = self.raiz / 'proj' / 'pasta-comum'
        comum.mkdir()
        (comum / 'x.txt').write_text('x\n', encoding='utf-8')
        with self.assertRaises(ErroWorktree):
            remover_worktree(etapa='pasta-comum', forcar=True, projeto='proj',
                             pasta_base=self.repo_main, pasta_raiz=self.raiz)
        self.assertTrue((comum / 'x.txt').is_file())

    def test_criar_fora_da_raiz_e_recusado(self):
        with self.assertRaises(ErroWorktree):
            criar_worktree(etapa='../../fora', projeto='proj', pasta_base=self.repo_main, pasta_raiz=self.raiz)
        self.assertFalse((self.tmp_path / 'fora').exists())

    def test_cli_remover_com_pontos_retorna_erro(self):
        r = rodar(SCRIPT_WT, '--pasta-base', str(self.repo_main), '--raiz', str(self.raiz), '--projeto', 'proj',
                  'remover', '--etapa', '../../vitima', '--forcar')
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue((self.vitima / 'dado.txt').is_file())


if __name__ == '__main__':
    unittest.main()
