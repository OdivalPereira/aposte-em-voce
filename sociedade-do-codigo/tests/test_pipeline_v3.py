"""Ferramentas do pipeline 3.0.0: medição de sessão, conferência da ordem, estado, sc.py e validador."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, RAIZ, carregar, rodar  # noqa: E402

SESSAO = carregar(NUCLEO / 'scripts' / 'sc_sessao.py', 'sc_sessao')
CONFERIR = carregar(NUCLEO / 'scripts' / 'sc_conferir.py', 'sc_conferir')
RESUMO = carregar(NUCLEO / 'scripts' / 'sc_resumo.py', 'sc_resumo')
REGISTRO = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
SC = NUCLEO / 'scripts' / 'sc.py'
SYNC = NUCLEO / 'scripts' / 'sc_sync_agents_md.py'
VALIDAR = carregar(RAIZ / 'scripts' / 'validar_pacote.py', 'validar_pacote_v3')


def git(pasta, *args):
    return subprocess.run(['git', '-C', str(pasta), *args], capture_output=True, text=True, check=True).stdout.strip()


def commit(pasta, msg):
    git(pasta, 'add', '-A')
    git(pasta, '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', msg)
    return git(pasta, 'rev-parse', 'HEAD')


def escrever_jsonl(caminho, linhas):
    caminho.write_text('\n'.join(json.dumps(l, ensure_ascii=False) for l in linhas) + '\n', encoding='utf-8')


class TestMedicaoDeSessao(unittest.TestCase):
    """Q141: contagens objetivas pelo log; nada de conteúdo."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_antigravity_conta_ordens_delegacoes_e_releituras(self):
        log = self.p / 'transcript.jsonl'
        escrever_jsonl(log, [
            {'type': 'USER_INPUT', 'created_at': '2026-09-25T10:00:00Z', 'content': 'segredo da ordem'},
            {'type': 'PLANNER_RESPONSE', 'created_at': '2026-09-25T10:01:00Z', 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {}},
                {'name': 'view_file', 'args': {'AbsolutePath': '"/x/grande.py"'}},
                {'name': 'view_file', 'args': {'AbsolutePath': '"/x/grande.py"'}},
                {'name': 'run_command', 'args': {'CommandLine': '"python3 -m unittest discover"'}}]},
            {'type': 'USER_INPUT', 'created_at': '2026-09-25T10:30:00Z', 'content': 'segunda ordem'},
        ])
        m = SESSAO.medir('antigravity', log=str(log))
        self.assertEqual(m['ordens_na_conversa'], 2)
        self.assertFalse(m['conversa_nova'])
        self.assertEqual(m['delegacoes_por_ordem'], [1, 0])
        self.assertEqual(m['execucoes_de_teste'], 1)
        self.assertEqual(m['arquivos_relidos'], {'/x/grande.py': 2})
        self.assertEqual(m['duracao_min'], 30)
        self.assertNotIn('segredo', json.dumps(m, ensure_ascii=False))

    def test_codex_detecta_sessao_reaproveitada_memoria_e_leitura_fora(self):
        permitida = str(self.p / 'copia')
        log = self.p / 'rollout.jsonl'
        escrever_jsonl(log, [
            {'type': 'turn_context', 'timestamp': '2026-09-25T10:00:00Z', 'payload': {'model': 'gpt-6-sol', 'effort': 'xhigh', 'cwd': '/home/u/projeto'}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'text': 'primeira'}]}},
            {'type': 'response_item', 'payload': {'type': 'function_call', 'arguments': 'cat /home/u/.codex/memories/MEMORY.md'}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'text': 'segunda'}]}},
        ])
        m = SESSAO.medir('codex', log=str(log), pasta=permitida)
        self.assertFalse(m['conversa_nova'])
        self.assertFalse(m['pasta_da_sessao_e_a_permitida'])
        self.assertEqual(m['memoria_lida_por_comando'], 1)
        self.assertIn('gpt-6-sol / xhigh', m['modelos_esforcos'])

    def test_claude_conta_mensagens_humanas_delegacoes_e_modelo(self):
        log = self.p / 'sessao.jsonl'
        escrever_jsonl(log, [
            {'type': 'user', 'turnOrigin': 'human', 'timestamp': '2026-09-25T10:00:00Z', 'message': {'content': 'pedido'}},
            {'type': 'assistant', 'effort': 'high', 'timestamp': '2026-09-25T10:05:00Z', 'message': {'model': 'claude-x', 'content': [
                {'type': 'tool_use', 'name': 'Agent', 'input': {}},
                {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': '/p/a.py'}},
                {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': '/p/a.py'}},
                {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'python3 -B -m unittest discover -s tests'}}]}},
            {'type': 'assistant', 'isSidechain': True, 'message': {'content': [{'type': 'tool_use', 'name': 'Read', 'input': {}}]}},
        ])
        m = SESSAO.medir('claude', log=str(log))
        self.assertEqual(m['mensagens_do_usuario'], 1)
        self.assertEqual(m['delegacoes_por_subagente'], 1)
        self.assertEqual(m['modelos'], {'claude-x': 1})
        self.assertEqual(m['execucoes_de_teste'], 1)
        self.assertEqual(m['ferramentas_dos_subagentes'], {'Read': 1})


    def test_leituras_pelo_terminal_entram_na_releitura(self):
        casos = {
            'cat sociedade/andamento.md': ['sociedade/andamento.md'],
            'sed -n 1,40p sociedade/planejamento.md | head': ['sociedade/planejamento.md'],
            'head -5 docs/a.md && tail -n 3 docs/b.md': ['docs/a.md', 'docs/b.md'],
            'git status': [],
        }
        for comando, esperado in casos.items():
            self.assertEqual(SESSAO.leituras_por_comando(comando), esperado, comando)
        log = self.p / 'terminal.jsonl'
        escrever_jsonl(log, [{'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'cat sociedade/grande.md'}},
            {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'sed -n 1,9p sociedade/grande.md'}}]}}])
        self.assertEqual(SESSAO.medir('claude', log=str(log))['arquivos_relidos'], {'sociedade/grande.md': 2})

class TestConferenciaDaOrdem(unittest.TestCase):
    """Q119: cada entrega marcada como feita ou não feita, por critério objetivo."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / 'repo'
        (self.repo / 'pacote').mkdir(parents=True)
        (self.repo / 'sociedade' / 'pareceres').mkdir(parents=True)
        (self.repo / 'pacote' / 'a.py').write_text('x = 1\n', encoding='utf-8')
        git(self.repo, 'init', '-q')
        self.base = commit(self.repo, 'base')
        (self.repo / 'pacote' / 'a.py').write_text('x = 2\n', encoding='utf-8')
        self.head = commit(self.repo, 'candidato')

    def tearDown(self):
        self.tmp.cleanup()

    def ordem(self, linhas):
        arq = self.repo / 'sociedade' / 'ordens' / 'E1.md'
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text('# Ordem E1\n\n```entregas\n' + '\n'.join(linhas) + '\n```\n', encoding='utf-8')
        return arq

    def test_marca_feito_nao_feito_e_nao_preenchido(self):
        at = self.repo / 'sociedade' / 'pareceres' / 'atestado-E1.json'
        perfil = 'perfil sintético\n'
        (self.repo / 'sociedade' / 'perfil.md').write_text(perfil, encoding='utf-8')
        dados = {'status': 'APROVADO', 'commit': self.head, 'base': self.base, 'papel': 'Coordenador', 'etapa_id': 'E1',
                 'fatia_id': 'N/A', 'verificacoes': {}, 'erros': [], 'hashes_artefatos': {'pacote/a.py': 'a' * 64},
                 'arquivos_inspecionados': ['pacote/a.py'], 'total_arquivos_inspecionados': 1,
                 'portao': {'modo': 'por_area', 'commit': self.head, 'areas_tocadas': ['p'], 'cobertura_completa': True,
                            'perfil_sha256': hashlib.sha256(perfil.encode('utf-8')).hexdigest(), 'areas': [{'area': 'p', 'ok': True}]}}
        dados['atestado_hash'] = hashlib.sha256(json.dumps({k: dados.get(k) for k in (
            'commit', 'base', 'papel', 'etapa_id', 'fatia_id', 'status', 'verificacoes', 'hashes_artefatos', 'portao', 'erros')},
            sort_keys=True).encode('utf-8')).hexdigest()  # B15: atestado do `entregar`: forma 1.3.0 e hash conferidos
        at.write_text(json.dumps(dados), encoding='utf-8')
        vazio = self.repo / 'sociedade' / 'pareceres' / 'atestado-vazio.json'
        vazio.write_text(json.dumps({'status': 'APROVADO', 'commit': self.head, 'total_arquivos_inspecionados': 0}), encoding='utf-8')
        arq = self.ordem([
            f'E1 | commit_existe | {self.head[:7]}',
            f'E2 | arquivos_em | {self.base[:7]}..{self.head[:7]} | pacote/',
            f'E3 | arquivos_em | {self.base[:7]}..{self.head[:7]} | docs/',
            f'E4 | atestado_aprovado | sociedade/pareceres/atestado-E1.json | {self.head[:7]}',
            f'E5 | atestado_aprovado | sociedade/pareceres/atestado-vazio.json | {self.head[:7]}',
            'E6 | hash_confere | pacote/a.py | 0000',
            'E7 | commit_existe | <commit final>',
        ])
        rel = CONFERIR.conferir(arq, self.repo)
        estados = {i['id']: i['estado'] for i in rel['itens']}
        self.assertEqual(estados, {'E1': 'feito', 'E2': 'feito', 'E3': 'não feito', 'E4': 'feito',
                                   'E5': 'não feito', 'E6': 'não feito', 'E7': 'não preenchido'})
        self.assertEqual((rel['feitos'], rel['total']), (3, 7))

    def test_registrar_grava_evento_e_estado_mostra_pendencia(self):
        soc = self.repo / 'sociedade'
        REGISTRO.Registro.inicializar(soc, 'teste', str(self.repo), versao_inicial=self.base[:7])
        arq = self.ordem([f'E1 | commit_existe | {self.head[:7]}', 'E2 | arquivo_existe | nao/existe.md'])
        rel = CONFERIR.conferir(arq, self.repo)
        CONFERIR.registrar(rel, soc)
        eventos = json.loads((soc / 'registro.json').read_text(encoding='utf-8'))['eventos']
        self.assertEqual(eventos[-1]['tipo'], 'conferencia_registrada')
        dados = RESUMO.coletar(soc)
        self.assertTrue(any('não feita' in p for p in RESUMO.pendencias(dados)))

    def test_ordem_sem_bloco_de_entregas_e_erro(self):
        arq = self.repo / 'sociedade' / 'ordens' / 'E9.md'
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text('# sem bloco\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            CONFERIR.conferir(arq, self.repo)


class TestComandosDoPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / 'repo'
        (self.repo / 'sociedade').mkdir(parents=True)
        (self.repo / 'x.py').write_text('x = 1\n', encoding='utf-8')
        git(self.repo, 'init', '-q')
        self.base = commit(self.repo, 'base')

    def tearDown(self):
        self.tmp.cleanup()

    def test_ordem_cria_do_modelo_e_recusa_duplicada(self):
        soc = str(self.repo / 'sociedade')
        r = rodar(SC, 'ordem', '--etapa', 'E1', '--pasta-sociedade', soc)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        texto = (self.repo / 'sociedade' / 'ordens' / 'E1.md').read_text(encoding='utf-8')
        self.assertIn('# Ordem E1', texto)
        self.assertIn('```entregas', texto)
        self.assertNotEqual(rodar(SC, 'ordem', '--etapa', 'E1', '--pasta-sociedade', soc).returncode, 0)
        self.assertNotEqual(rodar(SC, 'ordem', '--etapa', '../fora', '--pasta-sociedade', soc).returncode, 0)

    def test_revisar_monta_copia_com_dois_commits(self):
        (self.repo / 'x.py').write_text('x = 2\n', encoding='utf-8')
        head = commit(self.repo, 'candidato')
        destino = Path(self.tmp.name) / 'revisao'
        r = rodar(SC, 'revisar', '--etapa', 'E1', '--base', self.base, '--head', head,
                  '--destino', str(destino), '--pasta-sociedade', str(self.repo / 'sociedade'))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        log = git(destino, 'log', '--format=%s')
        self.assertEqual(log.splitlines(), [f'candidato ({head[:7]})', f'base ({self.base[:7]})'])
        self.assertTrue((destino / 'PROTOCOLO-REVISAO.md').is_file())
        self.assertEqual(git(destino, 'status', '--porcelain'), '')

    def test_estado_gera_md_e_html(self):
        soc = self.repo / 'sociedade'
        r = rodar(SC, 'estado', '--pasta-sociedade', str(soc))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        md = (soc / 'estado.md').read_text(encoding='utf-8')
        self.assertIn('## Precisa de atenção', md)
        self.assertLessEqual(len(md.encode('utf-8')), 5 * 1024)
        self.assertIn('<title>Estado da Sociedade</title>', (soc / 'estado.html').read_text(encoding='utf-8'))
        # caminho relativo também identifica o projeto pelo nome da pasta
        import os
        antes = os.getcwd()
        try:
            os.chdir(self.repo)
            self.assertEqual(RESUMO.coletar('sociedade')['projeto'], 'repo')
        finally:
            os.chdir(antes)

    def test_estado_em_fragmento_para_pagina(self):
        soc = self.repo / 'sociedade'
        frag = Path(self.tmp.name) / 'painel.html'
        r = rodar(SC, 'estado', '--pasta-sociedade', str(soc), '--sem-html')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = rodar(SC, 'estado', '--pasta-sociedade', str(soc), '--sem-html', '--artefato', str(frag))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        texto = frag.read_text(encoding='utf-8')
        self.assertTrue(texto.startswith('<title>Estado da Sociedade</title>'))
        import re
        for proibido in (r'<html[\s>]', r'<body[\s>]', r'<head[\s>]', r'<!doctype'):
            self.assertIsNone(re.search(proibido, texto, re.I), proibido)
        self.assertIn(':root:not([data-theme="light"])', texto)
        self.assertIn(':root[data-theme="dark"]', texto)

    def test_ponteiros_criam_claude_e_gemini_sem_sobrescrever(self):
        (self.repo / 'GEMINI.md').write_text('texto meu\n', encoding='utf-8')
        r = rodar(SYNC, '--projeto', str(self.repo), '--criar', '--ponteiros', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.repo / 'CLAUDE.md').read_text(encoding='utf-8'), '@AGENTS.md\n')
        self.assertEqual((self.repo / 'GEMINI.md').read_text(encoding='utf-8'), 'texto meu\n')
        self.assertIn('não aponta para o AGENTS.md', r.stdout)


class TestValidadorEstrutural(unittest.TestCase):
    """Q102: o que os testes de redação conferiam virou checagem estrutural do validador."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        self.plugin = self.raiz / 'plugins' / 'p'
        (self.plugin / 'skills' / 'sc-papeis' / 'references').mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_detecta_papel_grande_sem_secoes_caminho_absoluto_link_quebrado_e_termo_revogado(self):
        ref = self.plugin / 'skills' / 'sc-papeis' / 'references'
        (ref / 'papel-x.md').write_text('# Papel X\n' + 'texto longo ' * 300, encoding='utf-8')
        (ref / 'papel-y.md').write_text('# Y\n## Faz\n## Não faz\n## Entrega\nVeja [a](file:///home/u/a.md) e [b](nao-existe.md).\n'
                                        'Adote a Escala Tripartite.\n', encoding='utf-8')
        erros = VALIDAR.checagens_estruturais(self.raiz, self.plugin)
        texto = '\n'.join(erros)
        self.assertIn('papel com', texto)
        self.assertIn('sem a seção "## Faz"', texto)
        self.assertIn('caminho absoluto', texto)
        self.assertIn('link quebrado', texto)
        self.assertIn('escala tripartite', texto)

    def test_pacote_real_passa(self):
        self.assertEqual(VALIDAR.checagens_estruturais(RAIZ, RAIZ / 'plugins' / 'sociedade-do-codigo'), [])


if __name__ == '__main__':
    unittest.main()
