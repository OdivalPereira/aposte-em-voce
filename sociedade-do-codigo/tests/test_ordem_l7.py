#!/usr/bin/env python3
"""Teste para gravação da ordem na pasta sociedade do worktree da etapa (L7).

sc.py ordem --etapa <ID>
Grava a ordem na sociedade/ do worktree da etapa quando ele existir.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, carregar, rodar  # noqa: E402

SCRIPT_SC = NUCLEO / 'scripts' / 'sc.py'


class TesteOrdemL7(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

        # Pasta canônica
        self.canonico = self.raiz / 'canonico'
        self.canonico.mkdir()
        self.soc_canonico = self.canonico / 'sociedade'
        self.soc_canonico.mkdir()

        # Worktree da etapa
        self.wt = self.raiz / 'worktree-e7'
        self.wt.mkdir()
        self.soc_wt = self.wt / 'sociedade'
        self.soc_wt.mkdir()

    def test_ordem_grava_no_worktree_da_etapa_quando_especificado(self):
        r = rodar(
            SCRIPT_SC, 'ordem',
            '--etapa', 'e7',
            '--pasta-sociedade', str(self.soc_wt)
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        ordem_wt = self.soc_wt / 'ordens' / 'e7.md'
        ordem_canonico = self.soc_canonico / 'ordens' / 'e7.md'

        self.assertTrue(ordem_wt.is_file(), f"Ordem não foi criada em {ordem_wt}")
        self.assertFalse(ordem_canonico.exists(), f"Ordem não deveria ter sido criada na canônica: {ordem_canonico}")
        self.assertIn('e7', ordem_wt.read_text(encoding='utf-8'))

    def test_ordem_recusa_se_ja_existir(self):
        ordem_wt = self.soc_wt / 'ordens' / 'e7.md'
        ordem_wt.parent.mkdir(parents=True, exist_ok=True)
        ordem_wt.write_text('ordem existente', encoding='utf-8')

        r = rodar(
            SCRIPT_SC, 'ordem',
            '--etapa', 'e7',
            '--pasta-sociedade', str(self.soc_wt)
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('a ordem já existe', r.stderr)


if __name__ == '__main__':
    unittest.main()
