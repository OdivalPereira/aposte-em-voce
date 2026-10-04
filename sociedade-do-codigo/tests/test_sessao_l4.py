#!/usr/bin/env python3
"""Teste de medição de sessão e consumo de tokens para Codex e Antigravity (L4).

- sc.py sessao codex: soma tokens de input, cache read e output dos logs de sessão.
- sc.py sessao antigravity: lê as sessões; se não expuser tokens de consumo,
  exibe 'n/d' com o motivo e até 3 hipóteses técnicas sem quebrar.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, carregar, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
MOD_SESSAO = carregar(NUCLEO / 'scripts' / 'sc_sessao.py', 'sc_sessao')
SCRIPT_SC = NUCLEO / 'scripts' / 'sc.py'


class TesteSessaoL4(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

    def test_codex_soma_tokens_de_input_cache_e_output(self):
        log_codex = self.raiz / 'rollout-teste.jsonl'
        # Monta eventos com medições de uso
        eventos = [
            {'type': 'turn_context', 'payload': {'cwd': str(self.raiz)}},
            {'type': 'event', 'payload': {'type': 'user_message', 'content': [{'type': 'text', 'text': 'olá'}]}},
            {
                'type': 'event',
                'payload': {
                    'type': 'assistant_message',
                    'model': 'gpt-6-sol',
                    'usage': {
                        'input_tokens': 1500,
                        'cached_input_tokens': 500,
                        'cache_write_input_tokens': 200,
                        'output_tokens': 300,
                    }
                }
            },
            {
                'type': 'event',
                'payload': {
                    'type': 'assistant_message',
                    'model': 'gpt-6-sol',
                    'usage': {
                        'input_tokens': 2000,
                        'cached_input_tokens': 1200,
                        'cache_write_input_tokens': 100,
                        'output_tokens': 450,
                    }
                }
            }
        ]
        with open(log_codex, 'w', encoding='utf-8') as f:
            for ev in eventos:
                f.write(json.dumps(ev) + '\n')

        # Teste direto da função consumo_codex
        consumo = MOD_SESSAO.consumo_codex(log_codex)
        self.assertIn('total', consumo)
        tot = consumo['total']
        self.assertEqual(tot['entrada'], 3500)
        self.assertEqual(tot['cache_lido'], 1700)
        self.assertEqual(tot['cache_escrito'], 300)
        self.assertEqual(tot['saida'], 750)
        self.assertEqual(tot['mensagens'], 2)

        # Teste via CLI sc.py sessao codex --json
        r_json = rodar(SCRIPT_SC, 'sessao', 'codex', '--log', str(log_codex), '--json')
        self.assertEqual(r_json.returncode, 0, r_json.stdout + r_json.stderr)
        dados = json.loads(r_json.stdout)
        self.assertIn('consumo', dados)
        self.assertEqual(dados['consumo']['total']['entrada'], 3500)
        self.assertEqual(dados['consumo']['total']['cache_lido'], 1700)
        self.assertEqual(dados['consumo']['total']['saida'], 750)

        # Teste via CLI textual
        r_txt = rodar(SCRIPT_SC, 'sessao', 'codex', '--log', str(log_codex))
        self.assertEqual(r_txt.returncode, 0, r_txt.stdout + r_txt.stderr)
        self.assertIn('consumo:', r_txt.stdout)
        self.assertIn('gpt-6-sol', r_txt.stdout)
        self.assertIn('3.500', r_txt.stdout)
        self.assertIn('1.700', r_txt.stdout)
        self.assertIn('750', r_txt.stdout)

    def test_antigravity_tokens_nd_com_hipoteses_sem_quebrar(self):
        # Monta transcript do Antigravity
        log_ag = self.raiz / 'transcript.jsonl'
        passos = [
            {'type': 'USER_INPUT', 'content': 'iniciar tarefa', 'created_at': '2026-10-03T10:00:00Z'},
            {
                'type': 'PLANNER_RESPONSE',
                'tool_calls': [
                    {'name': 'view_file', 'args': {'AbsolutePath': '/tmp/teste.txt'}},
                    {'name': 'run_command', 'args': {'CommandLine': 'pytest tests/'}}
                ],
                'created_at': '2026-10-03T10:05:00Z'
            }
        ]
        with open(log_ag, 'w', encoding='utf-8') as f:
            for p in passos:
                f.write(json.dumps(p) + '\n')

        # Teste direto da inspeção de base do Antigravity
        info = MOD_SESSAO.inspecionar_base_antigravity('conversa-inexistente')
        self.assertEqual(info['consumo'], 'n/d')
        self.assertIn('Tokens não expostos', info['motivo'])
        self.assertIsInstance(info['hipoteses'], list)
        self.assertLessEqual(len(info['hipoteses']), 3)
        self.assertGreaterEqual(len(info['hipoteses']), 1)

        # Teste via CLI sc.py sessao antigravity --json
        r_json = rodar(SCRIPT_SC, 'sessao', 'antigravity', '--log', str(log_ag), '--json')
        self.assertEqual(r_json.returncode, 0, r_json.stdout + r_json.stderr)
        dados = json.loads(r_json.stdout)
        self.assertIn('consumo', dados)
        self.assertEqual(dados['consumo'], 'n/d')
        self.assertEqual(len(dados['hipoteses_consumo']), 3)

        # Teste via CLI textual
        r_txt = rodar(SCRIPT_SC, 'sessao', 'antigravity', '--log', str(log_ag))
        self.assertIn('consumo: n/d', r_txt.stdout)
        self.assertIn('hipóteses para ausência de tokens expostos', r_txt.stdout)


if __name__ == '__main__':
    unittest.main()
