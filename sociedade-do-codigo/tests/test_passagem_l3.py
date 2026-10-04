#!/usr/bin/env python3
"""Teste do comando sc.py passar (L3 / Q175).

sc.py passar --etapa <ID> --para gandalf|barbarvore
Produz a mensagem de passagem do bastão para a próxima ferramenta/papel da cadeia,
imprimindo exatamente 3 linhas na saída padrão:
- Linha 1: Ferramenta, modelo e esforço com indicação expressa de 'conversa nova'.
- Linha 2: Caminho absoluto da pasta de trabalho.
- Linha 3: Frase exata a colar na nova conversa.
Grava evento 'passagem' no registro.json com carimbo de data/hora.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, carregar, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
MOD_REGISTRO = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REGISTRO.Registro
SCRIPT_SC = NUCLEO / 'scripts' / 'sc.py'

PERFIL = """# Perfil de teste
## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | Claude Code | Anthropic | Claude Opus 5.5 | high | ativo | 2026-10-03 | formação real |
| Revisor Independente | Barbárvore | Codex | OpenAI | GPT-6 Sol | xhigh | ativo | 2026-10-03 | formação real |
| Coordenador | Gandalf | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-10-03 | formação real |
| Dados e persistência | Elrond | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-10-03 | formação real |

## Modo emulação (Q147)
- **Emulação:** não.
"""


class TestePassagemL3(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

        # Worktree da etapa
        self.wt = self.raiz / 'worktree-e1'
        self.wt.mkdir(parents=True)
        self.soc_wt = self.wt / 'sociedade'
        self.soc_wt.mkdir(parents=True)
        (self.soc_wt / 'perfil.md').write_text(PERFIL, encoding='utf-8')
        (self.soc_wt / 'ordens').mkdir(parents=True)
        (self.soc_wt / 'ordens' / 'e1.md').write_text('# Ordem e1\nRevisão independente: conferir testes unitários.\n', encoding='utf-8')

        # Cópia de revisão
        self.rev = self.raiz / 'revisao-e1'
        self.rev.mkdir(parents=True)

        self.reg = Registro.inicializar(self.soc_wt, projeto_id='proj-l3', caminho_canonico=str(self.wt), aplicar=True)

    def test_passar_para_gandalf(self):
        r = rodar(
            SCRIPT_SC, 'passar',
            '--etapa', 'e1',
            '--para', 'gandalf',
            '--pasta-sociedade', str(self.soc_wt)
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        linhas = [l for l in r.stdout.splitlines() if l.strip()]
        self.assertEqual(len(linhas), 3, f"Esperado exatamente 3 linhas, obtido: {linhas}")

        # Linha 1: Ferramenta, modelo, esforço com (conversa nova)
        self.assertIn('Antigravity', linhas[0])
        self.assertIn('Gemini 3.8 Flash', linhas[0])
        self.assertIn('high', linhas[0])
        self.assertIn('(conversa nova)', linhas[0])

        # Linha 2: Caminho absoluto do worktree
        self.assertEqual(linhas[1], str(self.wt.resolve()))

        # Linha 3: Frase exata a colar apontando para ordem
        self.assertIn('Para: Gandalf', linhas[2])
        self.assertIn('sociedade/ordens/e1.md', linhas[2])

        # Confere evento 'passagem' no registro
        reg = Registro(self.soc_wt)
        evs = [e for e in reg.dados.get('eventos', []) if e.get('tipo') == 'passagem']
        self.assertEqual(len(evs), 1)
        d = evs[0]['dados']
        self.assertEqual(d['etapa'], 'e1')
        self.assertEqual(d['para'], 'gandalf')
        self.assertEqual(d['papel'], 'coordenador')
        self.assertEqual(d['ferramenta'], 'Antigravity')
        self.assertEqual(d['pasta'], str(self.wt.resolve()))
        self.assertIn('data_hora', d)

    def test_passar_para_barbarvore(self):
        r = rodar(
            SCRIPT_SC, 'passar',
            '--etapa', 'e1',
            '--para', 'barbarvore',
            '--pasta-sociedade', str(self.soc_wt)
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        linhas = [l for l in r.stdout.splitlines() if l.strip()]
        self.assertEqual(len(linhas), 3, f"Esperado exatamente 3 linhas, obtido: {linhas}")

        # Linha 1: Ferramenta, modelo, esforço com (conversa nova)
        self.assertIn('Codex', linhas[0])
        self.assertIn('GPT-6 Sol', linhas[0])
        self.assertIn('xhigh', linhas[0])
        self.assertIn('(conversa nova)', linhas[0])

        # Linha 2: Caminho absoluto da cópia de revisão
        self.assertEqual(linhas[1], str(self.rev.resolve()))

        # Linha 3: Frase exata a colar apontando para parecer
        self.assertIn('Para: Barbárvore', linhas[2])
        self.assertIn('parecer.md', linhas[2])

        # Confere evento 'passagem' no registro
        reg = Registro(self.soc_wt)
        evs = [e for e in reg.dados.get('eventos', []) if e.get('tipo') == 'passagem']
        self.assertEqual(len(evs), 1)
        d = evs[0]['dados']
        self.assertEqual(d['etapa'], 'e1')
        self.assertEqual(d['para'], 'barbarvore')
        self.assertEqual(d['papel'], 'revisor')
        self.assertEqual(d['ferramenta'], 'Codex')
        self.assertEqual(d['pasta'], str(self.rev.resolve()))


if __name__ == '__main__':
    unittest.main()
