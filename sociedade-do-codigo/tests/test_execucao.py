import json
import re
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from util import PLUGIN, RAIZ, SKILLS, carregar, rodar

EXEC = SKILLS / 'sc-execucao'
DIR_PAPEIS = SKILLS / 'sc-papeis'
INV = EXEC / 'scripts' / 'inventario_local.py'
MODULO = RAIZ / 'modulos' / 'executores-locais'
PAPEIS = ('Círdan', 'Barbárvore', 'Gandalf', 'Aragorn', 'Elrond', 'Galadriel', 'Legolas', 'Jules')
_PAPEIS_ANTIGOS = ('Gandalf', 'Aragorn', 'Elrond', 'Galadriel', 'Legolas', 'Jules', 'Revisor Independente',
          'Celebrimbor', 'Radagast', 'Faramir', 'Bilbo')
LOCAIS = ('celebrimbor', 'radagast', 'faramir', 'bilbo')

MEMINFO = 'MemTotal:       16384000 kB\nMemFree:         1000000 kB\nMemAvailable:    8192000 kB\n'


class Fake(BaseHTTPRequestHandler):
    """Ollama de mentira: só responde os três GET de leitura que o inventário usa."""
    caminhos = []

    def do_GET(self):
        Fake.caminhos.append(self.path)
        corpos = {
            '/api/version': {'version': '0.9.9'},
            '/api/tags': {'models': [{'name': 'modelo-pequeno:3b', 'size': 2 * 1024 ** 3,
                                      'details': {'parameter_size': '3B', 'quantization_level': 'Q4_K_M'}}]},
            '/api/ps': {'models': []},
        }
        if self.path not in corpos:
            self.send_response(404)
            self.end_headers()
            return
        dados = json.dumps(corpos[self.path]).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(dados)

    def log_message(self, *a):
        pass


class TesteInventario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = carregar(INV, 'inventario_local')

    def test_meminfo(self):
        total, disp = self.mod.parse_meminfo(MEMINFO)
        self.assertEqual(total, 16384000 * 1024)
        self.assertEqual(disp, 8192000 * 1024)
        self.assertEqual(self.mod.parse_meminfo('nada'), (None, None))

    def test_formatacao_brasileira(self):
        self.assertEqual(self.mod.formatar_gib(3 * 1024 ** 3 + 512 * 1024 ** 2), '3,5 GiB')
        self.assertEqual(self.mod.formatar_gib(None), 'não informado')
        self.assertEqual(self.mod.formatar_tamanho(300 * 1024 ** 2), '300 MiB')

    def test_so_enderecos_locais(self):
        for ok in ('http://127.0.0.1:11434', 'http://localhost:11434', 'http://[::1]:11434'):
            self.assertTrue(self.mod.host_local(ok), ok)
        for ruim in ('http://exemplo.com:11434', 'https://127.0.0.1:11434', 'http://192.168.0.5:11434',
                     'http://127.0.0.1.exemplo.com:11434', 'ftp://localhost'):
            self.assertFalse(self.mod.host_local(ruim), ruim)

    def test_endereco_externo_nem_e_consultado(self):
        info = self.mod.coletar_ollama('http://exemplo.com:11434')
        self.assertIn('não consultado', info['servidor'])
        self.assertEqual(info['modelos'], [])

    def test_ollama_falso_modelos_e_versao(self):
        Fake.caminhos = []
        srv = HTTPServer(('127.0.0.1', 0), Fake)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        info = self.mod.coletar_ollama(f'http://127.0.0.1:{srv.server_address[1]}')
        self.assertEqual(info['servidor'], 'respondendo')
        self.assertEqual(info['versao'], '0.9.9')
        self.assertEqual(info['modelos'][0]['nome'], 'modelo-pequeno:3b')
        self.assertEqual(info['modelos'][0]['quantizacao'], 'Q4_K_M')
        self.assertEqual(sorted(set(Fake.caminhos)), ['/api/ps', '/api/tags', '/api/version'])  # só leitura, só estes
        inv = {'ollama': info}
        self.assertEqual(self.mod.avaliar_exigencias(['servidor', 'modelo:MODELO-pequeno', 'modelo:outro'], inv), ['modelo:outro'])

    def test_exigencias(self):
        inv = {'ollama': {'binario': None, 'servidor': 'sem resposta', 'modelos': []}}
        falta = self.mod.avaliar_exigencias(['ollama', 'servidor', 'py:json', 'py:modulo_que_nao_existe_xyz', 'coisa'], inv)
        self.assertEqual(falta, ['ollama', 'servidor', 'py:modulo_que_nao_existe_xyz', 'coisa (item desconhecido)'])

    def test_biblioteca_e_procurada_sem_importar(self):
        self.assertTrue(self.mod.biblioteca('json', 'json')['presente'])
        self.assertFalse(self.mod.biblioteca('modulo_que_nao_existe_xyz', 'x')['presente'])

    def test_cli_json_e_codigos_de_saida(self):
        r = rodar(INV, '--json', '--caminho', str(RAIZ), '--caminho', '/nao/existe/mesmo', '--comando', 'python3')
        self.assertEqual(r.returncode, 0, r.stderr)
        inv = json.loads(r.stdout)
        for chave in ('maquina', 'ollama', 'bibliotecas', 'playwright_navegadores', 'caminhos', 'comandos', 'faltando'):
            self.assertIn(chave, inv)
        self.assertEqual(inv['caminhos'][str(RAIZ)], 'pasta')
        self.assertEqual(inv['caminhos']['/nao/existe/mesmo'], 'não existe')
        self.assertEqual(set(inv['bibliotecas']), set(self.mod.GRUPOS))
        self.assertEqual(rodar(INV, '--exigir', 'py:modulo_que_nao_existe_xyz').returncode, 1)
        r = rodar(INV, '--ollama-url', 'http://exemplo.com:11434')
        self.assertEqual(r.returncode, 2)

    def test_texto_em_portugues_sem_ponto_decimal(self):
        r = rodar(INV)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('somente leitura', r.stdout)
        self.assertIn('Nada foi instalado, baixado, executado nem alterado', r.stdout)
        self.assertRegex(r.stdout, r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}')  # data e hora no padrão brasileiro

    def test_script_nao_escreve_nem_instala_nada(self):
        fonte = INV.read_text(encoding='utf-8')
        for proibido in ('pip install', "'pip'", 'ollama pull', 'ollama run', '/api/generate', '/api/pull', 'os.remove',
                         'shutil.rmtree', 'write_text', 'POST'):
            self.assertTrue(proibido not in fonte, proibido)
        self.assertIsNone(re.search(r'(?<![\w.])open\(', fonte))  # open( sozinho; urlopen( de leitura é permitido


class TesteExecucaoLocal(unittest.TestCase):
    def test_todos_os_papeis_estao_listados_em_sc_papeis(self):
        texto = (SKILLS / 'sc-papeis' / 'SKILL.md').read_text(encoding='utf-8')
        for papel in PAPEIS:
            self.assertRegex(texto, rf'\|\s*{papel}\s*\|', f'{papel} falta na tabela de sc-papeis')
        leia = (MODULO / 'LEIA-ME.md').read_text(encoding='utf-8')
        for nome in LOCAIS:
            self.assertIn(nome.capitalize(), leia)

    def test_cada_executor_local_tem_referencia_e_agente(self):
        for nome in LOCAIS:
            ref = MODULO / f'papel-{nome}.md'
            self.assertTrue(ref.is_file(), ref)
            self.assertIn(f'papel-{nome}.md', (MODULO / 'LEIA-ME.md').read_text(encoding='utf-8'))
            agente = MODULO / 'agents' / f'{nome}.md'
            self.assertTrue(agente.is_file(), agente)
            self.assertRegex(agente.read_text(encoding='utf-8'), rf'(?m)^name: {nome}$')

    def test_executores_locais_nao_escrevem_em_sistema_real(self):
        for nome in ('faramir', 'bilbo', 'radagast', 'celebrimbor'):
            texto = (MODULO / f'papel-{nome}.md').read_text(encoding='utf-8')
            self.assertIn('## Não faz', texto, nome)
            self.assertTrue(re.search(r'(?i)(nuvem|banco|produção)', texto), nome)

    def test_perfil_modelo_tem_secao_executores_locais(self):
        texto = (SKILLS / 'sociedade-do-codigo' / 'assets' / 'perfil-modelo.md').read_text(encoding='utf-8')
        self.assertIn('## Executores locais', texto)
        for nome in ('Celebrimbor', 'Radagast', 'Faramir', 'Bilbo'):
            self.assertIn(f'| {nome} |', texto)

    def test_modelo_de_execucao_tem_os_campos_de_evidencia(self):
        texto = (MODULO / 'execucao-local.md').read_text(encoding='utf-8')
        for campo in ('comando:', 'modelo local:', 'entrada:', 'saída:', 'camadas executadas:', 'resultado:'):
            self.assertIn(campo, texto)
        self.assertIn('não executado', texto)

    def test_skill_local_sem_termos_de_projeto(self):
        proibidos = re.compile(r'palandir|nosso tim|supabase|alterdata|domínio sistemas|bitrix|vercel', re.I)
        for arq in EXEC.rglob('*'):
            if arq.is_file() and arq.suffix in ('.md', '.py'):
                self.assertIsNone(proibidos.search(arq.read_text(encoding='utf-8')), arq.name)


if __name__ == '__main__':
    unittest.main()
