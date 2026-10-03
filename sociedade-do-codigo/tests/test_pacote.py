import json
import shutil
import tempfile
import unittest
from pathlib import Path

from util import RAIZ, SKILLS, rodar

VALIDAR = RAIZ / 'scripts' / 'validar_pacote.py'
GEN = RAIZ / 'scripts' / 'gen_manifests.py'


class TestePacote(unittest.TestCase):
    def copia(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        destino = Path(d.name) / 'pk'
        shutil.copytree(RAIZ, destino, ignore=shutil.ignore_patterns('.git', '__pycache__', 'dist'))
        return destino

    def test_pacote_atual_e_valido(self):
        r = rodar(VALIDAR)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_manifestos_em_dia(self):
        self.assertEqual(rodar(GEN, '--verificar').returncode, 0)

    def test_versao_unica_em_todos_os_lugares(self):
        versao = (RAIZ / 'VERSION').read_text(encoding='utf-8').strip()
        for rel in ('plugins/sociedade-do-codigo/plugin.json', 'plugins/sociedade-do-codigo/.claude-plugin/plugin.json',
                    'plugins/sociedade-do-codigo/.codex-plugin/plugin.json'):
            self.assertEqual(json.loads((RAIZ / rel).read_text(encoding='utf-8'))['version'], versao, rel)
        for skill in SKILLS.iterdir():
            self.assertIn(f'versao: "{versao}"', (skill / 'SKILL.md').read_text(encoding='utf-8'), skill.name)

    def test_detecta_termo_de_projeto(self):
        c = self.copia()
        (c / 'plugins/sociedade-do-codigo/skills/sc-papeis/references/papel-aragorn.md').write_text('menciona o Palandir', encoding='utf-8')
        r = rodar(VALIDAR, '--raiz', c)
        self.assertEqual(r.returncode, 1)
        self.assertIn('palandir', r.stdout)

    def test_detecta_nome_de_skill_diferente_da_pasta(self):
        c = self.copia()
        arq = c / 'plugins/sociedade-do-codigo/skills/sc-execucao/SKILL.md'
        arq.write_text(arq.read_text(encoding='utf-8').replace('name: sc-execucao', 'name: outro-nome'), encoding='utf-8')
        r = rodar(VALIDAR, '--raiz', c)
        self.assertEqual(r.returncode, 1)
        self.assertIn('igual ao nome da pasta', r.stdout)

    def test_detecta_arquivo_citado_inexistente(self):
        c = self.copia()
        (c / 'plugins/sociedade-do-codigo/skills/sc-execucao/assets/tarefa-jules.md').unlink()
        r = rodar(VALIDAR, '--raiz', c)
        self.assertEqual(r.returncode, 1)
        self.assertIn('arquivo citado não existe', r.stdout)

    def test_detecta_versao_alterada_sem_regenerar_manifestos(self):
        c = self.copia()
        (c / 'VERSION').write_text('1.0.1\n', encoding='utf-8')
        self.assertEqual(rodar(VALIDAR, '--raiz', c).returncode, 1)

    def test_detecta_segredo(self):
        c = self.copia()
        (c / 'docs').mkdir(exist_ok=True)
        (c / 'docs' / 'x.md').write_text('chave ' + 'AI' + 'zaSyA1234567890abcdefghijklmnopqrstuvwx', encoding='utf-8')
        r = rodar(VALIDAR, '--raiz', c)
        self.assertEqual(r.returncode, 1)
        self.assertIn('segredo', r.stdout)

    def test_skills_respeitam_o_padrao_agent_skills(self):
        import re
        for sk in SKILLS.iterdir():
            texto = (sk / 'SKILL.md').read_text(encoding='utf-8')
            self.assertTrue(texto.startswith('---\n'), sk.name)
            self.assertLess(len(texto.split('\n')), 500, sk.name)
            desc = re.search(r'^description: (.+)$', texto, re.M).group(1)
            self.assertLessEqual(len(desc), 1024, sk.name)


if __name__ == '__main__':
    unittest.main()
