import tempfile
import unittest
from pathlib import Path

from util import NUCLEO, rodar

VALIDAR = NUCLEO / 'scripts' / 'validar_perfil.py'
MODELO = NUCLEO / 'assets' / 'perfil-modelo.md'


class TestePerfil(unittest.TestCase):
    def escrever(self, texto):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        arq = Path(d.name) / 'perfil.md'
        arq.write_text(texto, encoding='utf-8')
        return arq

    def test_perfil_minimo_com_titulos(self):
        r = rodar(VALIDAR, self.escrever('## Missão\nA\n## Autoridades\nB\n## Papel × ferramenta\nC\n'))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_perfil_com_rotulos_em_negrito(self):
        r = rodar(VALIDAR, self.escrever('**Missão:** A\n\n**Autoridades:** B\n\n**Papel × ferramenta:** C\n'))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_falta_campo_obrigatorio(self):
        r = rodar(VALIDAR, self.escrever('## Missão\nA\n## Autoridades\nB\n'))
        self.assertEqual(r.returncode, 1)
        self.assertIn('Papel × ferramenta', r.stdout)

    def test_modelo_cru_tem_marcadores_mas_tem_o_minimo(self):
        r = rodar(VALIDAR, MODELO)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('aviso', r.stdout)


if __name__ == '__main__':
    unittest.main()
