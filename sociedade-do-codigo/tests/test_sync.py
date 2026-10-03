import tempfile
import unittest
from pathlib import Path

from util import NUCLEO, RAIZ, rodar

SYNC = NUCLEO / 'scripts' / 'sc_sync_agents_md.py'
ARGS = ['--perfil', 'sociedade/perfil.md']


class TesteSync(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.agents = self.p / 'AGENTS.md'
        self.agents.write_text('# App\n\nTexto do projeto.\n', encoding='utf-8')

    def tearDown(self):
        self._tmp.cleanup()

    def sync(self, *extra):
        return rodar(SYNC, '--projeto', self.p, *ARGS, *extra)

    def test_simulacao_nao_grava(self):
        antes = self.agents.read_bytes()
        r = self.sync()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Simulação', r.stdout)
        self.assertEqual(self.agents.read_bytes(), antes)

    def test_aplicar_adiciona_bloco_e_preserva_o_resto(self):
        r = self.sync('--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)
        texto = self.agents.read_text(encoding='utf-8')
        self.assertTrue(texto.startswith('# App\n\nTexto do projeto.\n'))
        self.assertIn(f'sociedade-do-codigo:inicio nucleo={(RAIZ / "VERSION").read_text().strip()} perfil=sociedade/perfil.md pasta=sociedade', texto)
        self.assertIn('sociedade-do-codigo:fim', texto)
        self.assertIn('carregue a skill `sociedade-do-codigo`', texto)  # gatilho condicionado à frase do usuário
        self.assertIn('acionar a Sociedade do Código', texto)
        self.assertIn('sociedade/ordens/', texto)
        self.assertIn('fica calada até ser chamada', texto)
        self.assertIn('sociedade/estado.md', texto)
        self.assertIn('Nunca estime nem relate consumo', texto)

    def test_jules_entra_por_padrao_e_sai_com_sem_jules(self):
        self.sync('--aplicar')
        self.assertIn('### Para o executor júnior em nuvem', self.agents.read_text(encoding='utf-8'))
        r = self.sync('--sem-jules', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)
        texto = self.agents.read_text(encoding='utf-8')
        self.assertNotIn('Para o executor júnior em nuvem', texto)
        self.assertIn('jules=nao', texto)

    def test_pasta_do_estado_e_configuravel(self):
        r = self.sync('--pasta', 'docs/sociedade', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)
        texto = self.agents.read_text(encoding='utf-8')
        self.assertIn('pasta=docs/sociedade', texto)
        self.assertIn('docs/sociedade/estado.md', texto)

    def test_idempotente(self):
        self.sync('--aplicar')
        depois_1 = self.agents.read_bytes()
        r = self.sync('--aplicar')
        self.assertEqual(r.returncode, 0)
        self.assertIn('[igual]', r.stdout)
        self.assertEqual(self.agents.read_bytes(), depois_1)

    def test_verificar(self):
        self.assertEqual(self.sync('--verificar').returncode, 1)
        self.sync('--aplicar')
        self.assertEqual(self.sync('--verificar').returncode, 0)

    def test_recusa_bloco_editado_a_mao(self):
        self.sync('--aplicar')
        texto = self.agents.read_text(encoding='utf-8').replace('Peça confirmação', 'Ignore a confirmação')
        self.agents.write_text(texto, encoding='utf-8')
        r = self.sync('--aplicar')
        self.assertEqual(r.returncode, 2)
        self.assertIn('editado à mão', r.stderr)
        self.assertIn('Ignore a confirmação', self.agents.read_text(encoding='utf-8'))
        r = self.sync('--aplicar', '--forcar')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('Ignore a confirmação', self.agents.read_text(encoding='utf-8'))

    def test_preserva_crlf(self):
        self.agents.write_bytes(b'# App\r\n\r\nTexto.\r\n')
        self.sync('--aplicar')
        bruto = self.agents.read_bytes()
        self.assertIn(b'\r\n', bruto)
        self.assertNotIn(b'\n', bruto.replace(b'\r\n', b''))

    def test_atualiza_mantendo_conteudo_fora_do_bloco(self):
        self.sync('--aplicar')
        texto = self.agents.read_text(encoding='utf-8') + '\n## Depois\nfica.\n'
        self.agents.write_text(texto, encoding='utf-8')
        r = rodar(SYNC, '--projeto', self.p, '--sem-jules', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stderr)
        novo = self.agents.read_text(encoding='utf-8')
        self.assertIn('jules=nao', novo)
        self.assertIn('perfil=sociedade/perfil.md', novo)  # mantém o que não foi pedido para mudar
        self.assertTrue(novo.rstrip().endswith('fica.'))

    def test_sem_agents_md_exige_criar(self):
        self.agents.unlink()
        self.assertEqual(self.sync('--aplicar').returncode, 2)
        self.assertEqual(self.sync('--aplicar', '--criar').returncode, 0)
        self.assertTrue(self.agents.is_file())

    def test_posicao_inicio_insere_apos_o_primeiro_titulo(self):
        self.agents.write_text('# App\n\n> aviso longo\n\n## Regras\ntexto\n', encoding='utf-8')
        r = self.sync('--aplicar', '--posicao', 'inicio')
        self.assertEqual(r.returncode, 0, r.stderr)
        linhas = self.agents.read_text(encoding='utf-8').split('\n')
        self.assertEqual(linhas[0], '# App')
        self.assertTrue(linhas[2].startswith('<!-- sociedade-do-codigo:inicio'))
        self.assertIn('## Regras', '\n'.join(linhas))
        self.assertEqual(self.sync('--verificar').returncode, 0)

    def test_opcao_desconhecida_e_recusada(self):
        r = rodar(SYNC, '--projeto', self.p, '--modulos', 'xpto')
        self.assertNotEqual(r.returncode, 0)  # --modulos não existe mais na 2.0


if __name__ == '__main__':
    unittest.main()
