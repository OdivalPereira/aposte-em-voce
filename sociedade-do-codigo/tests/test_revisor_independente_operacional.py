"""Testes das diretrizes operacionais, invariantes, governança e conformidade do Revisor Independente."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import RAIZ, SKILLS, rodar

LINT_PARECER = SKILLS / 'sc-revisao' / 'scripts' / 'lint_parecer.py'
MODELO_PARECER = SKILLS / 'sc-revisao' / 'assets' / 'parecer-modelo.md'


class TesteRevisorIndependente(unittest.TestCase):
    """Revisão independente na 3.0.0: comportamento do linter e limites técnicos dos agentes revisores.
    As frases dos antigos documentos de papel passaram a checagens estruturais do validador (Q102)."""

    def test_agente_claude_revisor_sem_ferramentas_de_edicao(self):
        texto = (RAIZ / 'adapters' / 'claude' / 'agents' / 'barbarvore.md').read_text(encoding='utf-8')
        cabecalho = texto.split('---')[1]
        self.assertIn('name: barbarvore', cabecalho)
        linha_tools = next(l for l in cabecalho.splitlines() if l.startswith('tools:'))
        for proibida in ('Edit', 'Write', 'NotebookEdit'):
            self.assertNotIn(proibida, linha_tools)

    def test_antigravity_nao_tem_revisor_independente(self):
        # D-RT-001: revisão por outro modelo Google é interna, nunca independente.
        agentes = {a.stem for a in (RAIZ / 'adapters' / 'antigravity' / 'agents').glob('*.md')}
        self.assertFalse({'revisor-independente', 'barbarvore'} & agentes)

    def test_skill_revisao_aponta_para_protocolo_existente(self):
        skill = (SKILLS / 'sc-revisao' / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('references/protocolo-revisao.md', skill)
        self.assertTrue((SKILLS / 'sc-revisao' / 'references' / 'protocolo-revisao.md').is_file())

    def test_linter_parecer_valida_coerencia_logica(self):
        def avaliar_parecer(texto):
            with tempfile.TemporaryDirectory() as tmpdir:
                p = Path(tmpdir) / 'parecer.md'
                p.write_text(texto, encoding='utf-8')
                return rodar(LINT_PARECER, p)

        base_valida = """## Parecer do Revisor Independente
- rodada: SC-E5
- fatia ou fechamento: fechamento
- entrega: branch etapa/sc-e5
- commit: 9318354
- base..head: 8f3ae32..9318354
- revisor: Claude Code · fornecedor: Anthropic · sessão: sess_test_001
- veredito: aceitar
- data: 23/09/2026 09:30

### Independência
Não implementei nem corrigi nada desta entrega, e não vou corrigir. Implementação do fornecedor Google; revisão de fornecedor diferente.

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| Suíte de testes 100% verde | `python3 -m unittest discover tests` passou 279 testes | executada |
| Empacotamento válido | `python3 scripts/validar_pacote.py` retornou pacote válido | executada |

### Achados
- [opcional] refinar documentação de exemplos em fase futura

### O que não verifiquei
- Não foram testados cenários em máquinas Windows ou macOS.
"""
        # Parecer plenamente válido deve passar
        res = avaliar_parecer(base_valida)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

        # Inconsistência 1: veredito aceitar com critério 'não verificada'
        texto_invalido_1 = base_valida.replace(
            "| `python3 scripts/validar_pacote.py` retornou pacote válido | executada |",
            "| não exercitado | não verificada |"
        )
        res1 = avaliar_parecer(texto_invalido_1)
        self.assertEqual(res1.returncode, 1)
        self.assertIn('não combina', res1.stdout)

        # Inconsistência 2: achado bloqueador com veredito aceitar
        texto_invalido_2 = base_valida.replace("[opcional]", "[bloqueador]")
        res2 = avaliar_parecer(texto_invalido_2)
        self.assertEqual(res2.returncode, 1)
        self.assertIn('bloqueador', res2.stdout)

        # Inconsistência 3: omissão da seção 'O que não verifiquei'
        i = base_valida.index("### O que não verifiquei")
        texto_invalido_3 = base_valida[:i]
        res3 = avaliar_parecer(texto_invalido_3)
        self.assertEqual(res3.returncode, 1)
        self.assertIn('O que não verifiquei', res3.stdout)


if __name__ == '__main__':
    unittest.main()
