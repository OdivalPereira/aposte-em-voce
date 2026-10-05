#!/usr/bin/env python3
"""Testes unitários e de integração para a trava comum de perfil e registro (A03, F2).

Critérios de aceite observáveis de F2:
- Leitura, validação e gravação de perfil e registro ficam sob uma trava comum,
  em `papel trocar` e em `papel emulacao`.
- Uma troca intercalada é recusada ou deixa estado final válido (nunca emulação
  desligada com violações de R1-R3 no perfil).
- O teste exercita a janela, a partir de estado válido.
- Rollback em falha preserva perfil e registro sob a trava.
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
import sc_perfil  # noqa: E402
import sc_registro  # noqa: E402
import sc_rodada  # noqa: E402

Registro = sc_registro.Registro
carregar_perfil = sc_perfil.carregar_perfil
emulacao_ligada = sc_perfil.emulacao_ligada
SCRIPT_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'
trava_perfil_registro = sc_rodada.trava_perfil_registro
ErroTravaPerfil = sc_rodada.ErroTravaPerfil
conferir_regras_estritas_equipe = sc_rodada.conferir_regras_estritas_equipe

PERFIL_VALIDO_EMULACAO = """# Perfil de Teste da Trava
## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | Claude Code | Anthropic | Modelo A | high | ativo | 2026-10-01 | inicial |
| Revisor Independente | Barbárvore | Codex | OpenAI | Modelo R | high | ativo | 2026-10-01 | inicial |
| Coordenador | Gandalf | Antigravity | Google | Modelo G | high | ativo | 2026-10-01 | inicial |
| Dados e persistência | Elrond | Antigravity | Google | Modelo G | high | ativo | 2026-10-01 | inicial |

## Modo emulação (Q147)
- **Emulação:** sim.
"""


class TestTravaPerfilRegistro(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.pasta_sociedade = self.raiz / 'sociedade'
        self.pasta_sociedade.mkdir(parents=True)
        self.arq_perfil = self.pasta_sociedade / 'perfil.md'
        self.arq_perfil.write_text(PERFIL_VALIDO_EMULACAO, encoding='utf-8')
        self.reg = Registro.inicializar(self.pasta_sociedade, 'teste-trava', str(self.raiz), aplicar=True)

    def fontes(self):
        return (
            self.arq_perfil.read_bytes(),
            (self.pasta_sociedade / 'registro.json').read_bytes()
        )

    def cli(self, args):
        stream = io.StringIO()
        err_stream = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(err_stream):
            try:
                code = sc_rodada.main(args)
            except SystemExit as e:
                code = e.code
            except Exception as e:
                code = type(e).__name__ + ': ' + str(e)
        return code, stream.getvalue(), err_stream.getvalue()

    def trocar(self, *args):
        return self.cli(['papel', 'trocar', '--pasta', str(self.pasta_sociedade),
                         '--autor', 'Tester', *args])

    def emulacao(self, *args):
        return self.cli(['papel', 'emulacao', *args, '--pasta', str(self.pasta_sociedade),
                         '--autor', 'Tester'])

    def test_trava_exclusiva_bloqueia_concorrencia_direta(self):
        """Testa diretamente que duas aquisições concorrentes não-bloqueantes da trava colidem."""
        with trava_perfil_registro(self.pasta_sociedade):
            with self.assertRaises(ErroTravaPerfil):
                with trava_perfil_registro(self.pasta_sociedade):
                    pass

    def test_trava_liberada_permite_nova_aquisicao(self):
        """Testa que após a liberação da trava uma nova operação consegue adquiri-la."""
        with trava_perfil_registro(self.pasta_sociedade):
            pass
        # Segunda aquisição sucede sem erro
        with trava_perfil_registro(self.pasta_sociedade):
            pass

    def test_trava_liberada_apos_excecao(self):
        """Testa que mesmo em falha a trava é liberada no finally."""
        try:
            with trava_perfil_registro(self.pasta_sociedade):
                raise ValueError("falha simulada")
        except ValueError:
            pass

        # Trava deve estar livre
        with trava_perfil_registro(self.pasta_sociedade):
            pass

    def test_janela_entre_validacoes_a_partir_de_estado_valido(self):
        """A03: Intercalação entre validações detecta violação de R3 e recusa desligamento.

        Estado inicial é válido (emulação ligada).
        A troca para execução fora do Google se intercala antes da revalidação sob a trava.
        A revalidação detecta a violação e recusa desligar a emulação.
        """
        exchanged = []

        def change():
            code, out, err = self.trocar('--papel', 'execucao', '--para', 'Claude Code',
                                         '--fornecedor', 'Anthropic', '--modelo', 'Modelo Z',
                                         '--motivo', 'troca intercalada', '--aplicar')
            exchanged.append(code)

        chamadas = [0]
        actual_val = sc_rodada.conferir_regras_estritas_equipe

        def hook_regras(perfil, reg, decisao_ref=None):
            res = actual_val(perfil, reg, decisao_ref=decisao_ref)
            chamadas[0] += 1
            if chamadas[0] == 1:
                change()
            return res

        with patch.object(sc_rodada, 'conferir_regras_estritas_equipe', side_effect=hook_regras):
            code, out, err = self.emulacao('desligar', '--motivo', 'formacao real', '--aplicar')

        # Desligamento foi recusado devido à violação detectada na revalidação
        self.assertNotEqual(code, 0)
        self.assertIn('recusado por violação de regra invariante', str(code) + err)
        self.assertEqual(exchanged, [0])

        # Estado final permanece válido: emulação continua ligada
        perfil_final = carregar_perfil(self.arq_perfil)
        self.assertTrue(emulacao_ligada(perfil_final))

    def test_janela_apos_ultima_validacao_recusa_troca_concorrente(self):
        """A03: Intercalação após última validação é recusada pela trava ativa.

        Estado inicial é válido.
        Durante a atualização do perfil em desligar, uma troca tenta se intercalar.
        A trava comum recusa a troca concorrente.
        Desligamento conclui e estado final fica válido (sem violações no perfil).
        """
        exchanged = []

        def change():
            code, out, err = self.trocar('--papel', 'execucao', '--para', 'Claude Code',
                                         '--fornecedor', 'Anthropic', '--modelo', 'Modelo Z',
                                         '--motivo', 'troca na janela', '--aplicar')
            exchanged.append(code)

        actual_emul = sc_perfil.atualizar_emulacao

        def hook_emulacao(caminho, ligar, motivo=''):
            change()
            return actual_emul(caminho, ligar=ligar, motivo=motivo)

        with patch.object(sc_perfil, 'atualizar_emulacao', side_effect=hook_emulacao):
            code, out, err = self.emulacao('desligar', '--motivo', 'formacao real', '--aplicar')

        self.assertEqual(code, 0)
        # Troca concorrente foi recusada pela trava
        self.assertEqual(len(exchanged), 1)
        self.assertNotEqual(exchanged[0], 0)

        # Estado final: emulação desligada e NENHUMA violação de regra invariante
        perfil_final = carregar_perfil(self.arq_perfil)
        self.assertFalse(emulacao_ligada(perfil_final))
        violacoes = conferir_regras_estritas_equipe(perfil_final, Registro(self.pasta_sociedade))
        self.assertEqual(violacoes, [])

    def test_trocar_segura_trava_e_recusa_emulacao_concorrente(self):
        """Trava comum protege também o caminho inverso: papel trocar bloqueia papel emulacao."""
        emul_result = []

        def tentar_desligar():
            code, out, err = self.emulacao('desligar', '--motivo', 'desligar concorrente', '--aplicar')
            emul_result.append(code)

        actual_registrar = sc_registro.Registro.registrar_troca_papel

        def hook_registrar(*args, **kwargs):
            tentar_desligar()
            return actual_registrar(self.reg, *args, **kwargs)

        with patch.object(sc_registro.Registro, 'registrar_troca_papel', side_effect=hook_registrar):
            code, out, err = self.trocar('--papel', 'coordenador', '--modelo', 'Gemini 3.9 Flash',
                                         '--motivo', 'atualizacao normal', '--aplicar')

        self.assertEqual(code, 0)
        self.assertEqual(len(emul_result), 1)
        # Operação de emulação concorrente foi recusada por trava ativa
        self.assertNotEqual(emul_result[0], 0)

    def test_rollback_emulacao_sob_trava_preserva_fontes(self):
        """A05: Falha na gravação do evento em desligar restaura perfil sob a trava."""
        antes = self.fontes()
        with patch.object(sc_registro.Registro, 'aplicar_mutacao', side_effect=OSError('falha de gravação')):
            code, out, err = self.emulacao('desligar', '--motivo', 'falha simulada', '--aplicar')

        self.assertNotEqual(code, 0)
        self.assertEqual(self.fontes(), antes)

    def test_rollback_troca_sob_trava_preserva_fontes(self):
        """A05: Falha na gravação do evento em trocar restaura perfil sob a trava."""
        antes = self.fontes()
        with patch.object(sc_registro.Registro, 'aplicar_mutacao', side_effect=OSError('falha de gravação')):
            code, out, err = self.trocar('--papel', 'coordenador', '--modelo', 'Gemini Novo',
                                         '--motivo', 'falha simulada', '--aplicar')

        self.assertNotEqual(code, 0)
        self.assertEqual(self.fontes(), antes)

    def test_simulacao_nao_cria_arquivo_de_trava(self):
        """N5: Sem --aplicar, não há criação de arquivo de trava nem escrita em disco."""
        lock_file = self.pasta_sociedade / sc_rodada.NOME_ARQUIVO_TRAVA_PERFIL
        if lock_file.exists():
            lock_file.unlink()

        r1 = rodar(SCRIPT_RODADA, 'papel', 'trocar', '--pasta', str(self.pasta_sociedade),
                   '--autor', 'Tester', '--papel', 'coordenador', '--para', 'Antigravity',
                   '--modelo', 'Gemini Simulado', '--motivo', 'simulacao')
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        self.assertFalse(lock_file.exists())

        r2 = rodar(SCRIPT_RODADA, 'papel', 'emulacao', 'desligar', '--pasta', str(self.pasta_sociedade),
                   '--autor', 'Tester', '--motivo', 'simulacao')
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertFalse(lock_file.exists())

    def test_concorrencia_real_entre_processos(self):
        """Testa concorrência real entre subprocessos do SO via trava."""
        with trava_perfil_registro(self.pasta_sociedade):
            # Enquanto o processo pai segura a trava, subprocesso deve ser recusado
            r = rodar(SCRIPT_RODADA, 'papel', 'trocar', '--pasta', str(self.pasta_sociedade),
                      '--autor', 'Externo', '--papel', 'coordenador', '--modelo', 'Gemini Conc',
                      '--motivo', 'tentativa concorrente', '--aplicar')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('trava ativa', r.stderr)


if __name__ == '__main__':
    unittest.main()
