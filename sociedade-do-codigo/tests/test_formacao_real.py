#!/usr/bin/env python3
"""Teste de ponta a ponta da transição para formação real (fim da emulação).

Reproduz a transição da abertura:
- Perfil sintético inicial com todo mundo na Anthropic em modo emulação.
- Rodada de trocas:
    - Arquiteto (Claude Code / Anthropic / Claude Opus 5.5)
    - Revisor (Codex / OpenAI / GPT-6 Sol)
    - Execução (Antigravity / Google / Gemini 3.8 Flash)
    - Jules (espera)
    - Executores locais (espera)
  todas com o motivo 'formação real: fim da emulação em nuvem'.
- Desligamento da emulação via:
  sc_rodada.py papel emulacao desligar --motivo "formação real estabelecida" --autor Odival --aplicar
- Asserções:
    - --emulacao dá "não"
    - papel status não exibe aviso de emulação
    - nenhuma linha do perfil traz o prefixo "emulação:"
    - eventos gravados na cadeia de custódia do registro.json
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, carregar, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
MOD_PERFIL = carregar(NUCLEO / 'scripts' / 'sc_perfil.py', 'sc_perfil')
MOD_REGISTRO = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REGISTRO.Registro
SCRIPT_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'

PERFIL_INICIAL = """# Perfil sintético inicial (emulação)

## Missão
Projeto sintético para teste de formação real.

## Autoridades
- **Decide escopo, prioridade e publicação:** Odival

## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | Claude Code | Anthropic | Claude 3.5 Sonnet | high | ativo | 2026-10-01 | emulação: inicial |
| Revisor Independente | Barbárvore | Claude Code | Anthropic | Claude 3.5 Sonnet | high | ativo | 2026-10-01 | emulação: inicial |
| Coordenador | Gandalf | Claude Code | Anthropic | Claude 3.5 Sonnet | high | ativo | 2026-10-01 | emulação: inicial |
| Dados e persistência | Elrond | Claude Code | Anthropic | Claude 3.5 Sonnet | high | ativo | 2026-10-01 | emulação: inicial |
| Especialista visual | Galadriel | Claude Code | Anthropic | Claude 3.5 Sonnet | high | ativo | 2026-10-01 | emulação: inicial |
| Lógica e testes | Aragorn | Claude Code | Anthropic | Claude 3.5 Sonnet | high | ativo | 2026-10-01 | emulação: inicial |
| Integração e CI/CD | Legolas | Claude Code | Anthropic | Claude 3.5 Sonnet | high | ativo | 2026-10-01 | emulação: inicial |
| Executor em nuvem | Jules | Claude Code | Anthropic | Claude 3.5 Sonnet | high | ativo | 2026-10-01 | emulação: inicial |
| Executores locais | Celebrimbor, Radagast, Faramir, Bilbo | Claude Code | Anthropic | Claude 3.5 Sonnet | high | ativo | 2026-10-01 | emulação: inicial |

## Modo emulação (Q147)
- **Emulação:** sim. Modo emulação temporário de abertura.
"""


class TesteFormacaoRealPontaAPonta(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.pasta = self.raiz / 'sociedade'
        self.pasta.mkdir(parents=True)
        self.arq_perfil = self.pasta / 'perfil.md'
        self.arq_perfil.write_text(PERFIL_INICIAL, encoding='utf-8')
        self.reg = Registro.inicializar(self.pasta, projeto_id='teste-formacao-real', caminho_canonico=str(self.raiz), aplicar=True)

    def eventos(self, tipo=None):
        reg = Registro(self.pasta)
        evs = reg.dados.get('eventos', [])
        if tipo:
            evs = [e for e in evs if e.get('tipo') == tipo]
        return evs

    def test_transicao_para_formacao_real(self):
        motivo_troca = 'formação real: fim da emulação em nuvem'

        # 1. Troca do Arquiteto: Claude Code / Anthropic / Claude Opus 5.5
        r_arq = rodar(
            SCRIPT_RODADA, 'papel', 'trocar',
            '--papel', 'arquiteto',
            '--para', 'Claude Code',
            '--fornecedor', 'Anthropic',
            '--modelo', 'Claude Opus 5.5',
            '--esforco', 'high',
            '--motivo', motivo_troca,
            '--autor', 'Odival',
            '--pasta', str(self.pasta),
            '--aplicar'
        )
        self.assertEqual(r_arq.returncode, 0, r_arq.stdout + r_arq.stderr)

        # 2. Troca do Revisor: Codex / OpenAI / GPT-6 Sol
        r_rev = rodar(
            SCRIPT_RODADA, 'papel', 'trocar',
            '--papel', 'revisor',
            '--para', 'Codex',
            '--fornecedor', 'OpenAI',
            '--modelo', 'GPT-6 Sol',
            '--esforco', 'high',
            '--motivo', motivo_troca,
            '--autor', 'Odival',
            '--pasta', str(self.pasta),
            '--aplicar'
        )
        self.assertEqual(r_rev.returncode, 0, r_rev.stdout + r_rev.stderr)

        # 3. Troca de toda a Execução: Antigravity / Google / Gemini 3.8 Flash
        r_exec = rodar(
            SCRIPT_RODADA, 'papel', 'trocar',
            '--papel', 'execucao',
            '--para', 'Antigravity',
            '--fornecedor', 'Google',
            '--modelo', 'Gemini 3.8 Flash',
            '--esforco', 'high',
            '--motivo', motivo_troca,
            '--autor', 'Odival',
            '--pasta', str(self.pasta),
            '--aplicar'
        )
        self.assertEqual(r_exec.returncode, 0, r_exec.stdout + r_exec.stderr)

        # 4. Troca de Jules para espera
        r_jules = rodar(
            SCRIPT_RODADA, 'papel', 'trocar',
            '--papel', 'jules',
            '--estado', 'espera',
            '--motivo', motivo_troca,
            '--autor', 'Odival',
            '--pasta', str(self.pasta),
            '--aplicar'
        )
        self.assertEqual(r_jules.returncode, 0, r_jules.stdout + r_jules.stderr)

        # 5. Troca de executores_locais para espera
        r_locais = rodar(
            SCRIPT_RODADA, 'papel', 'trocar',
            '--papel', 'executores_locais',
            '--estado', 'espera',
            '--motivo', motivo_troca,
            '--autor', 'Odival',
            '--pasta', str(self.pasta),
            '--aplicar'
        )
        self.assertEqual(r_locais.returncode, 0, r_locais.stdout + r_locais.stderr)

        # 6. Desligar emulação
        r_desligar = rodar(
            SCRIPT_RODADA, 'papel', 'emulacao', 'desligar',
            '--motivo', 'formação real estabelecida',
            '--autor', 'Odival',
            '--pasta', str(self.pasta),
            '--aplicar'
        )
        self.assertEqual(r_desligar.returncode, 0, r_desligar.stdout + r_desligar.stderr)
        self.assertIn("alterado para 'desligar' com sucesso", r_desligar.stdout)

        # 7. Conferir --emulacao dá "não"
        r_emul = rodar(SCRIPT_RODADA, 'papel', 'status', '--emulacao', '--pasta', str(self.pasta))
        self.assertEqual(r_emul.returncode, 0)
        self.assertEqual(r_emul.stdout.strip(), 'não')

        # 8. Conferir papel status completo não exibe aviso
        r_status = rodar(SCRIPT_RODADA, 'papel', 'status', '--pasta', str(self.pasta))
        self.assertEqual(r_status.returncode, 0)
        self.assertIn('Modo emulação: desligado', r_status.stdout)
        self.assertNotIn('AVISO', r_status.stdout)

        # 9. Conferir que nenhuma linha do perfil traz o prefixo "emulação:"
        conteudo_perfil = self.arq_perfil.read_text(encoding='utf-8')
        self.assertNotIn('emulação:', conteudo_perfil)
        self.assertIn('- **Emulação:** não. formação real estabelecida', conteudo_perfil)

        # 10. Conferir eventos registrados na cadeia
        eventos_emul = self.eventos('emulacao_alterada')
        self.assertEqual(len(eventos_emul), 1)
        self.assertEqual(eventos_emul[0]['dados']['estado'], 'desligado')
        self.assertEqual(eventos_emul[0]['dados']['autor'], 'Odival')

        eventos_troca = self.eventos('papel_trocado')
        # Houve troca de arquiteto, revisor, execucao (5 papéis), jules, executores_locais
        self.assertGreaterEqual(len(eventos_troca), 5)


if __name__ == '__main__':
    unittest.main()
