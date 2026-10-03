"""B05 (caso B): status `portao` e `aceite` calculados por sc_status, com repositório, atestado e registro sintéticos."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, RAIZ, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
import sc_status  # noqa: E402
from sc_registro import Registro  # noqa: E402

ETAPA = 'etapa-x'
RAMO = f'etapa/{ETAPA}'
ATESTADO = f'sociedade/pareceres/atestado-{ETAPA}.json'


def atestado(commit, **extra):
    base = {'tipo': 'atestado_pre_devolucao', 'status': 'APROVADO', 'etapa_id': ETAPA, 'commit': commit,
            'total_arquivos_inspecionados': 3}
    base.update(extra)
    return base


class Repo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.r = Path(self._tmp.name)
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.invalid')
        self.git('config', 'user.name', 'Teste')
        self.base = self.commit({'README.md': 'base\n'}, 'base')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.r), *args], capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, arquivos, msg):
        for rel, conteudo in arquivos.items():
            alvo = self.r / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(conteudo, encoding='utf-8')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', msg)
        return self.git('rev-parse', 'HEAD')

    def produto(self, nome='src/a.py'):
        return self.commit({nome: 'x = 1\n'}, f'produto {nome}')

    def com_atestado(self, commit, **extra):
        return self.commit({ATESTADO: json.dumps(atestado(commit, **extra))}, 'sociedade: atestado')

    def portao(self, head=None, ramo=RAMO):
        return sc_status.verificar_portao(self.r, ramo, head or self.git('rev-parse', 'HEAD'))


class TestPortao(Repo):
    def test_verde_com_atestado_aprovado_do_commit_ancestral(self):
        p = self.produto()
        head = self.com_atestado(p)
        r = self.portao(head)
        self.assertTrue(r['ok'], r['motivo'])
        self.assertEqual(r['commit'], p)
        esperado = hashlib.sha256((self.r / ATESTADO).read_bytes()).hexdigest()
        self.assertEqual(r['atestado_sha256'], esperado)

    def test_verde_com_cauda_so_de_sociedade(self):
        p = self.produto()
        self.com_atestado(p)
        head = self.commit({'sociedade/pareceres/parecer-x.md': 'parecer\n', 'sociedade/estado.md': 'e\n'}, 'sociedade: parecer')
        self.assertTrue(self.portao(head)['ok'])

    def test_vermelho_sem_atestado(self):
        self.produto()
        r = self.portao()
        self.assertFalse(r['ok'])
        self.assertIn('sem sociedade/pareceres/atestado', r['motivo'])
        self.assertIsNone(r['atestado_sha256'])

    def test_vermelho_atestado_no_ramo_mas_nao_no_head(self):
        p = self.produto()
        self.com_atestado(p)
        outro = self.commit({'sociedade/x.md': 'y\n'}, 'sociedade: depois')
        self.git('rm', '-q', ATESTADO)
        self.git('commit', '-q', '-m', 'sociedade: remove atestado')
        r = self.portao()
        self.assertFalse(r['ok'])
        self.assertNotEqual(outro, self.git('rev-parse', 'HEAD'))

    def test_vermelho_atestado_reprovado(self):
        p = self.produto()
        self.com_atestado(p, status='REPROVADO')
        self.assertIn('REPROVADO', self.portao()['motivo'])
        self.assertFalse(self.portao()['ok'])

    def test_vermelho_atestado_de_outra_etapa(self):
        p = self.produto()
        self.com_atestado(p, etapa_id='outra')
        self.assertFalse(self.portao()['ok'])

    def test_vermelho_atestado_sem_arquivo_inspecionado(self):
        p = self.produto()
        self.com_atestado(p, total_arquivos_inspecionados=0)
        self.assertFalse(self.portao()['ok'])

    def test_vermelho_atestado_sem_commit_ou_commit_inventado(self):
        self.produto()
        for commit in (None, '', 'deadbeefdeadbeef', '--all', 'HEAD'):
            self.com_atestado(commit)
            r = self.portao()
            self.assertFalse(r['ok'], f'commit={commit!r}')
            self.git('rm', '-q', ATESTADO)
            self.git('commit', '-q', '-m', 'limpa')

    def test_vermelho_atestado_nao_json(self):
        self.produto()
        self.commit({ATESTADO: 'isto não é json'}, 'sociedade: lixo')
        r = self.portao()
        self.assertFalse(r['ok'])
        self.assertTrue(r['atestado_sha256'])

    def test_vermelho_commit_de_produto_depois_do_atestado(self):
        p = self.produto()
        self.com_atestado(p)
        head = self.produto('src/b.py')
        r = self.portao(head)
        self.assertFalse(r['ok'])
        self.assertIn('src/b.py', r['motivo'])

    def test_vermelho_commit_misto_depois_do_atestado(self):
        p = self.produto()
        self.com_atestado(p)
        head = self.commit({'sociedade/ok.md': 'a\n', 'src/c.py': 'c\n'}, 'misto')
        self.assertFalse(self.portao(head)['ok'])

    def test_vermelho_produto_escondido_e_revertido_na_cauda(self):
        # o diff final é só de sociedade/, mas um commit intermediário tocou o produto
        p = self.produto()
        self.com_atestado(p)
        self.produto('src/d.py')
        self.git('rm', '-q', 'src/d.py')
        head_rev = self.commit({'sociedade/x.md': 'x\n'}, 'sociedade: reverte')
        self.assertFalse(self.portao(head_rev)['ok'])

    def test_vermelho_rename_de_produto_para_sociedade(self):
        p = self.produto()
        self.com_atestado(p)
        self.git('mv', 'src/a.py', 'sociedade/a.py')
        self.git('commit', '-q', '-m', 'move produto para sociedade')
        r = self.portao()
        self.assertFalse(r['ok'])
        self.assertIn('src/a.py', r['motivo'])

    def test_vermelho_commit_do_atestado_nao_e_ancestral(self):
        self.git('checkout', '-q', '-b', 'lateral')
        lateral = self.produto('src/lateral.py')
        self.git('checkout', '-q', 'main')
        self.produto()
        head = self.com_atestado(lateral)
        r = self.portao(head)
        self.assertFalse(r['ok'])
        self.assertIn('não é ancestral', r['motivo'])

    def test_vermelho_merge_na_cauda(self):
        p = self.produto()
        self.com_atestado(p)
        self.git('checkout', '-q', '-b', 'lateral')
        self.commit({'sociedade/l.md': 'l\n'}, 'sociedade: lateral')
        self.git('checkout', '-q', 'main')
        self.commit({'sociedade/m.md': 'm\n'}, 'sociedade: main')
        self.git('merge', '-q', '--no-ff', 'lateral', '-m', 'merge')
        r = self.portao()
        self.assertFalse(r['ok'])
        self.assertIn('merge', r['motivo'])

    def test_vermelho_ramo_invalido(self):
        p = self.produto()
        head = self.com_atestado(p)
        for ramo in ('main', 'claude/outro', 'etapa/', 'etapa/Maiuscula', 'etapa/../x', 'etapa/a b', f'etapa/{"a" * 41}', '', None):
            r = sc_status.verificar_portao(self.r, ramo, head)
            self.assertFalse(r['ok'], f'ramo={ramo!r}')

    def test_head_invalido(self):
        self.assertFalse(self.portao('naoehsha')['ok'])
        self.assertFalse(self.portao('0' * 40)['ok'])


class TestEtapaDoRamo(unittest.TestCase):
    def test_id(self):
        self.assertEqual(sc_status.etapa_do_ramo('etapa/m0-destravar'), 'm0-destravar')
        self.assertEqual(sc_status.etapa_do_ramo('refs/heads/etapa/a1'), 'a1')
        self.assertIsNone(sc_status.etapa_do_ramo('jules/a1'))
        self.assertIsNone(sc_status.etapa_do_ramo('etapa/-a'))


def decisao(acao='aceitar', commit='ABC', quem='Odival Teste', etapa=ETAPA, **extra):
    d = {'etapa_id': etapa, 'decisao_id': 'DEC-1', 'quem': quem, 'referencia': 'conversa', 'acao': acao,
         'alcance': 'etapa', 'commit': commit}
    d.update(extra)
    return {'tipo': 'decisao_registrada', 'seq': 9, 'id': 'EVT-9', 'timestamp': '2026-01-01T00:00:00+00:00', 'dados': d}


def registro_sintetico(*decisoes):
    return {'eventos': list(decisoes)}


class TestAceite(Repo):
    def setUp(self):
        super().setUp()
        self.p = self.produto()
        self.head = self.com_atestado(self.p)

    def aceite(self, dados, head=None):
        return sc_status.verificar_aceite(self.r, RAMO, head or self.head, registro=dados)

    def test_verde_com_decisao_aceitar_do_sha_revisado(self):
        r = self.aceite(registro_sintetico(decisao(commit=self.p)))
        self.assertTrue(r['ok'], r['motivo'])
        self.assertIn('Odival Teste', r['motivo'])

    def test_verde_com_sha_abreviado(self):
        self.assertTrue(self.aceite(registro_sintetico(decisao(commit=self.p[:10])))['ok'])

    def test_vermelho_sem_decisao(self):
        r = self.aceite(registro_sintetico())
        self.assertFalse(r['ok'])
        self.assertIn('sem decisão', r['motivo'])

    def test_vermelho_decisao_de_outra_etapa(self):
        self.assertFalse(self.aceite(registro_sintetico(decisao(commit=self.p, etapa='outra')))['ok'])

    def test_vermelho_ultima_decisao_nao_e_aceitar(self):
        for acao in ('corrigir', 'rejeitar', 'sem-aceite', 'autorizacao'):
            r = self.aceite(registro_sintetico(decisao(commit=self.p), decisao(acao=acao, commit=self.p)))
            self.assertFalse(r['ok'], acao)

    def test_verde_quando_aceite_vem_depois_de_corrigir(self):
        self.assertTrue(self.aceite(registro_sintetico(decisao('corrigir', self.p), decisao('aceitar', self.p)))['ok'])

    def test_vermelho_sem_quem_ou_sem_commit(self):
        self.assertFalse(self.aceite(registro_sintetico(decisao(commit=self.p, quem='  ')))['ok'])
        self.assertFalse(self.aceite(registro_sintetico(decisao(commit='')))['ok'])

    def test_vermelho_decisao_de_sha_que_nao_e_ancestral(self):
        self.git('checkout', '-q', '-b', 'lateral', self.base)
        lateral = self.produto('src/lateral.py')
        self.git('checkout', '-q', 'main')
        self.assertFalse(self.aceite(registro_sintetico(decisao(commit=lateral)))['ok'])

    def test_vermelho_produto_depois_do_sha_revisado(self):
        head = self.produto('src/novo.py')
        r = self.aceite(registro_sintetico(decisao(commit=self.p)), head=head)
        self.assertFalse(r['ok'])
        self.assertIn('src/novo.py', r['motivo'])

    def test_registro_lido_do_head_do_git(self):
        # registro real, gravado pelo Registro e commitado depois do SHA revisado
        pasta = self.r / 'sociedade'
        reg = Registro.inicializar(pasta, 'projeto-teste', str(self.r))
        reg.abrir_etapa(ETAPA, 'objetivo', 'plano', 'aut', self.base[:7], ['C1'])
        evento = {'tipo': 'decisao_registrada', 'dados': decisao(commit=self.p)['dados']}
        reg.aplicar_mutacao(lambda dados: [evento], autor='Odival Teste')
        head = self.commit({'sociedade/_marca': 'ok\n'}, 'sociedade: registro')
        r = sc_status.verificar_aceite(self.r, RAMO, head)
        self.assertTrue(r['ok'], r['motivo'])

    def test_vermelho_sem_registro_no_head(self):
        r = sc_status.verificar_aceite(self.r, RAMO, self.head)
        self.assertFalse(r['ok'])
        self.assertIn('sem sociedade/registro.json', r['motivo'])

    def test_vermelho_registro_corrompido(self):
        head = self.commit({'sociedade/registro.json': '{nao e json'}, 'sociedade: registro ruim')
        r = sc_status.verificar_aceite(self.r, RAMO, head)
        self.assertFalse(r['ok'])
        self.assertIn('ilegível', r['motivo'])

    def test_vermelho_ramo_invalido(self):
        r = sc_status.verificar_aceite(self.r, 'main', self.head, registro=registro_sintetico(decisao(commit=self.p)))
        self.assertFalse(r['ok'])


class TestCLI(Repo):
    def test_codigo_de_saida_e_hash_impresso(self):
        p = self.produto()
        head = self.com_atestado(p)
        script = NUCLEO / 'scripts' / 'sc_status.py'
        r = rodar(script, 'portao', '--ramo', RAMO, '--head', head, '--raiz', self.r)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('atestado sha256:', r.stdout)
        r = rodar(script, 'aceite', '--ramo', RAMO, '--head', head, '--raiz', self.r)
        self.assertEqual(r.returncode, 1)
        self.assertIn('VERMELHO', r.stdout)

    def test_erro_inesperado_e_vermelho(self):
        r = rodar(NUCLEO / 'scripts' / 'sc_status.py', 'portao', '--ramo', RAMO, '--head', 'a' * 40, '--raiz', self.r / 'nao-existe')
        self.assertEqual(r.returncode, 1)


class TestWorkflow(unittest.TestCase):
    """O workflow só chama o script, tem os jobs com os nomes exatos e pipefail em todo passo `run`."""
    texto = (RAIZ.parent / '.github' / 'workflows' / 'status.yml').read_text(encoding='utf-8') \
        if (RAIZ.parent / '.github' / 'workflows' / 'status.yml').is_file() else None

    def setUp(self):
        if self.texto is None:
            self.skipTest('fora do repositório do projeto (sem .github/workflows/status.yml)')

    def test_jobs_com_os_nomes_exatos(self):
        jobs = re.findall(r'^  ([a-z0-9_-]+):\s*$', self.texto.split('\njobs:\n', 1)[1], re.M)
        self.assertEqual(jobs, ['portao', 'aceite'])

    def test_dispara_no_pull_request_e_nao_toca_o_ci(self):
        self.assertRegex(self.texto, r'(?m)^on:\n  pull_request:')
        self.assertFalse(re.search(r'(?m)^name:\s*ci\s*$', self.texto))

    def test_todo_run_tem_pipefail(self):
        blocos = re.findall(r'(?ms)^(\s+)run:\s*\|\n(.*?)(?=^\s*-\s|\n\S|\Z)', self.texto)
        self.assertGreaterEqual(len(blocos), 4)
        for _, corpo in blocos:
            self.assertIn('pipefail', corpo)
        self.assertEqual(self.texto.count('shell: bash -eo pipefail {0}'), 2)

    def test_chama_o_script_nos_dois_status(self):
        self.assertRegex(self.texto, r'"\$SC_STATUS" portao --ramo "\$RAMO" --head "\$HEAD_SHA"')
        self.assertRegex(self.texto, r'"\$SC_STATUS" aceite --ramo "\$RAMO" --head "\$HEAD_SHA"')

    def test_ramo_vem_por_variavel_de_ambiente_e_nao_inline(self):
        # evita injeção de comando por nome de ramo
        for corpo in re.findall(r'(?ms)run:\s*\|\n(.*?)(?=^\s*-\s|\Z)', self.texto):
            self.assertNotIn('${{', corpo)


if __name__ == '__main__':
    unittest.main()
