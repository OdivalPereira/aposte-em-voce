import tempfile
import unittest
from pathlib import Path

from util import NUCLEO, carregar, rodar

DISJ = NUCLEO / 'scripts' / 'verificar_disjuncao.py'


class TesteDisjuncao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = carregar(DISJ, 'verificar_disjuncao')

    def test_normalizar(self):
        for bruto, esperado in (('./src/a.ts', 'src/a.ts'), ('src//b.ts', 'src/b.ts'),
                                ('`src/c.ts`', 'src/c.ts'), ('src/d/', 'src/d'),
                                ('  src\\e.ts  ', 'src/e.ts')):
            self.assertEqual(self.mod.normalizar(bruto), esperado, bruto)

    def test_conflito_por_igualdade_e_containment(self):
        self.assertIsNotNone(self.mod.conflito('src/a.ts', 'src/a.ts'))
        self.assertIsNotNone(self.mod.conflito('src/db', 'src/db/schema.sql'))
        self.assertIsNotNone(self.mod.conflito('src/db/schema.sql', 'src/db'))
        self.assertIsNone(self.mod.conflito('src/a.ts', 'src/b.ts'))
        self.assertIsNone(self.mod.conflito('src/db', 'src/dbx/y.sql'))  # prefixo não é pasta

    def test_conflito_por_curinga(self):
        self.assertIsNotNone(self.mod.conflito('src/*.sql', 'src/x.sql'))
        self.assertIsNone(self.mod.conflito('src/*.sql', 'src/x.ts'))

    def test_ler_pares_ignora_cabecalho(self):
        pares = self.mod.ler_pares('# Despacho\n\n- Elrond: a.ts, b.ts\n- Legolas: c.tsx\n')
        self.assertEqual(pares, [('Elrond', ['a.ts', 'b.ts']), ('Legolas', ['c.tsx'])])

    def test_cli_aprova_listas_disjuntas(self):
        r = rodar(DISJ, '--par', 'Elrond: src/db/schema.sql', '--par', 'Legolas: src/ui/Rodape.tsx')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('disjunto', r.stdout)

    def test_cli_recusa_cruzamento(self):
        r = rodar(DISJ, '--par', 'Elrond: src/db', '--par', 'Jules T-01: src/db/schema.sql')
        self.assertEqual(r.returncode, 1)
        self.assertIn('conflito', r.stdout)
        self.assertIn('sequenciais', r.stdout)

    def test_cli_le_arquivo(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        arq = Path(d.name) / 'despacho.md'
        arq.write_text('## Fatia 2\n- Aragorn: docs/fontes.md\n- Galadriel: docs/fontes.md\n', encoding='utf-8')
        r = rodar(DISJ, str(arq))
        self.assertEqual(r.returncode, 1)
        self.assertIn('Aragorn e Galadriel', r.stdout)

    def test_cli_le_entrada_padrao(self):
        r = rodar(DISJ, '-', entrada='- A: x.ts\n- B: y.ts\n')
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_um_executor_so_passa(self):
        r = rodar(DISJ, '--par', 'Elrond: a, b')
        self.assertEqual(r.returncode, 0)
        self.assertIn('nada a cruzar', r.stdout)

    def test_repetido_na_propria_lista(self):
        r = rodar(DISJ, '--par', 'Elrond: a.ts, ./a.ts', '--par', 'Legolas: b.ts')
        self.assertEqual(r.returncode, 1)
        self.assertIn('repetido', r.stdout)

    def test_entrada_vazia_e_erro_de_uso(self):
        r = rodar(DISJ, '-', entrada='\n')
        self.assertEqual(r.returncode, 2)


if __name__ == '__main__':
    unittest.main()
