#!/usr/bin/env python3
"""Testes de identidade da conversa (@etapa) e delegações restritas (F3 / A01 / Q182).

Cobre:
- @etapa resolve a pasta apenas por campo estruturado do log do Antigravity (workspace_uris no SQLite ou metadados estruturados).
- Menção incidental no texto/corpo da conversa de outra pasta não é promovida a identidade do workspace (A01).
- Declaração divergente de pasta é recusada.
- Sem campo estruturado de workspace, o resultado é 'não verificado', nunca 'feito'.
- Só contam conversas iniciadas após a última passagem para Gandalf.
- Só contam delegações com TypeName de especialista ativo do perfil; self não conta (Q182).
- Os testes passam por conferir_item e pela medição de sessão.
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO  # noqa: E402

sys.path.insert(0, str((NUCLEO / 'scripts').resolve()))
import sc_conferir as MOD_CONFERIR
import sc_registro as MOD_REGISTRO
import sc_sessao as MOD_SESSAO
Registro = MOD_REGISTRO.Registro
FEITO = MOD_CONFERIR.FEITO
NAO_FEITO = MOD_CONFERIR.NAO_FEITO
NAO_VERIFICADO = MOD_CONFERIR.NAO_VERIFICADO

PERFIL_TESTE = """# Perfil de teste
## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | Claude Code | Anthropic | Modelo A | high | ativo | 2026-10-01 | inicial |
| Revisor Independente | Barbárvore | Codex | OpenAI | Modelo R | high | ativo | 2026-10-01 | inicial |
| Coordenador | Gandalf | Antigravity | Google | Modelo G | high | ativo | 2026-10-01 | inicial |
| Dados e persistência | Elrond | Antigravity | Google | Modelo G | high | ativo | 2026-10-01 | inicial |
| Métodos e qualidade | Galadriel | Antigravity | Google | Modelo G | high | ativo | 2026-10-01 | inicial |
| Executor júnior em nuvem | Jules | Jules | Google | a definir | padrão | espera | 2026-10-01 | inicial |
## Modo emulação (Q147)
- **Emulação:** não.
"""


class TesteConferirIdentidade(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

        # Worktree da etapa
        self.wt = self.raiz / 'worktree-f3'
        self.wt.mkdir()
        self.soc_wt = self.wt / 'sociedade'
        self.soc_wt.mkdir()
        (self.soc_wt / 'perfil.md').write_text(PERFIL_TESTE, encoding='utf-8')

        # Brain e summaries_db
        self.brain = self.raiz / 'brain'
        self.brain.mkdir()
        self.db_path = self.raiz / 'conversation_summaries.db'

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE conversation_summaries (
                conversation_id TEXT PRIMARY KEY,
                last_user_input_time TEXT,
                last_modified_time TEXT,
                workspace_uris TEXT
            )
        """)
        conn.commit()
        conn.close()

        self.reg = Registro.inicializar(self.soc_wt, projeto_id='proj-f3', caminho_canonico=str(self.wt), aplicar=True)

    def _registrar_passagem(self, etapa='f3', ts='2026-10-05T12:00:00+00:00'):
        def gerador(_dados):
            return [{
                'tipo': 'passagem',
                'timestamp': ts,
                'dados': {
                    'etapa': etapa,
                    'para': 'gandalf',
                    'papel': 'coordenador',
                    'ferramenta': 'Antigravity',
                    'pasta': str(self.wt.resolve()),
                    'data_hora': ts,
                }
            }]
        self.reg.aplicar_mutacao(gerador, autor='Círdan', aplicar=True)

    def _criar_transcript(self, cid, passos):
        cid_dir = self.brain / cid / '.system_generated' / 'logs'
        cid_dir.mkdir(parents=True, exist_ok=True)
        t_file = cid_dir / 'transcript.jsonl'
        linhas = [json.dumps(p) for p in passos]
        t_file.write_text('\n'.join(linhas) + '\n', encoding='utf-8')
        return t_file

    def _inserir_db(self, cid, tempo, uris):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO conversation_summaries VALUES (?, ?, ?, ?)",
            (cid, tempo, tempo, uris)
        )
        conn.commit()
        conn.close()

    def test_resolucao_por_campo_estruturado_sqlite(self):
        """Conversa resolvida via workspace_uris no SQLite passa pelo conferir_item e medição."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('f3', ts)
        t1 = '2026-10-05T12:05:00+00:00'
        self._inserir_db('cid-db-ok', t1, str(self.wt.resolve()))

        self._criar_transcript('cid-db-ok', [
            {'type': 'USER_INPUT', 'content': 'Para: Gandalf. Execute sociedade/ordens/f3.md.', 'created_at': t1},
            {'type': 'ASSISTANT', 'created_at': t1, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'elrond'}]}}
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            conv_id, motivo = MOD_CONFERIR.resolver_conversa_etapa('f3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
            self.assertEqual(conv_id, 'cid-db-ok')
            self.assertIsNone(motivo)

            real_resolver = MOD_CONFERIR.resolver_conversa_etapa
            def resolver(etapa, pasta_sociedade=None):
                return real_resolver(etapa, pasta_sociedade=pasta_sociedade, brain_dir=self.brain, summaries_db=self.db_path)

            with patch.object(MOD_CONFERIR, 'resolver_conversa_etapa', side_effect=resolver):
                st_del, obs_del = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@f3', '1']}, self.wt)
                self.assertEqual(st_del, FEITO)
                self.assertIn('1 delegações', obs_del)

                st_cn, obs_cn = MOD_CONFERIR.conferir_item({'tipo': 'conversa_nova', 'args': ['antigravity', '@f3']}, self.wt)
                self.assertEqual(st_cn, FEITO)

    def test_mencao_incidental_no_corpo_nao_promove_conversa_a01(self):
        """Achado A01: mensagem do assistente citando o caminho da etapa não promove conversa de outra pasta."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('f3', ts)
        t1 = '2026-10-05T12:05:00+00:00'

        outra_pasta = self.raiz / 'worktree-outra'
        outra_pasta.mkdir()

        # Transcript pertence a outra pasta, mas assistente cita o caminho do worktree como referência
        self._criar_transcript('cid-corpo-incidental', [
            {'type': 'USER_INPUT', 'content': f'Para: Gandalf. Execute sociedade/ordens/f3.md. Pasta: {outra_pasta}', 'created_at': t1},
            {'type': 'ASSISTANT', 'content': f'Outro caminho citado como referência: {self.wt}', 'created_at': t1},
            {'type': 'ASSISTANT', 'created_at': t1, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'elrond'}] * 5}}
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            conv_id, motivo = MOD_CONFERIR.resolver_conversa_etapa('f3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
            self.assertIsNone(conv_id)
            self.assertIn('nenhuma conversa do Antigravity encontrada', motivo)

            real_resolver = MOD_CONFERIR.resolver_conversa_etapa
            def resolver(etapa, pasta_sociedade=None):
                return real_resolver(etapa, pasta_sociedade=pasta_sociedade, brain_dir=self.brain, summaries_db=self.db_path)

            with patch.object(MOD_CONFERIR, 'resolver_conversa_etapa', side_effect=resolver):
                st, _ = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@f3', '5']}, self.wt)
                self.assertEqual(st, NAO_FEITO)

    def test_declaracao_divergente_recusada(self):
        """Conversa declarando explicitamente pasta divergente no primeiro passo é recusada."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('f3', ts)
        t1 = '2026-10-05T12:05:00+00:00'

        pasta_errada = self.raiz / 'worktree-errada'
        self._criar_transcript('cid-divergente', [
            {'type': 'USER_INPUT', 'workspace': str(pasta_errada), 'content': f'Pasta: {pasta_errada}', 'created_at': t1}
        ])

        conv_id, motivo = MOD_CONFERIR.resolver_conversa_etapa('f3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
        self.assertIsNone(conv_id)
        self.assertIn('nenhuma conversa do Antigravity encontrada', motivo)

    def test_sem_campo_estruturado_resultado_nao_verificado(self):
        """Conversa sem campo estruturado de workspace resulta em 'não verificado', nunca 'feito'."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('f3', ts)
        t1 = '2026-10-05T12:05:00+00:00'

        # Cita ordens/f3.md em texto, mas não tem campo de workspace nem declaração estruturada Pasta:
        self._criar_transcript('cid-sem-estrutura', [
            {'type': 'USER_INPUT', 'content': 'Por favor continue a execucao de ordens/f3.md no ambiente.', 'created_at': t1},
            {'type': 'ASSISTANT', 'created_at': t1, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'elrond'}]}}
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            conv_id, motivo = MOD_CONFERIR.resolver_conversa_etapa('f3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
            self.assertIsNone(conv_id)
            self.assertIn('sem campo estruturado de workspace', motivo)

            real_resolver = MOD_CONFERIR.resolver_conversa_etapa
            def resolver(etapa, pasta_sociedade=None):
                return real_resolver(etapa, pasta_sociedade=pasta_sociedade, brain_dir=self.brain, summaries_db=self.db_path)

            with patch.object(MOD_CONFERIR, 'resolver_conversa_etapa', side_effect=resolver):
                st, obs = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@f3', '1']}, self.wt)
                self.assertEqual(st, NAO_VERIFICADO)
                self.assertNotEqual(st, FEITO)
                self.assertIn('sem campo estruturado', obs)

    def test_conversas_anteriores_a_passagem_descartadas(self):
        """Conversas iniciadas antes da passagem para Gandalf não são aceitas."""
        t_passagem = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('f3', t_passagem)
        t_antiga = '2026-10-05T11:50:00+00:00'

        self._inserir_db('cid-antiga', t_antiga, str(self.wt.resolve()))
        self._criar_transcript('cid-antiga', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt), 'content': 'Início antigo', 'created_at': t_antiga}
        ])

        conv_id, motivo = MOD_CONFERIR.resolver_conversa_etapa('f3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
        self.assertIsNone(conv_id)
        self.assertIn('nenhuma conversa do Antigravity encontrada', motivo)

    def test_delegacoes_self_nao_contam_q182(self):
        """Delegações com TypeName 'self' não contam (Q182), apenas especialistas ativos do perfil."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('f3', ts)
        t1 = '2026-10-05T12:05:00+00:00'
        self._inserir_db('cid-self', t1, str(self.wt.resolve()))

        # 3 chamadas a invoke_subagent: 2 para 'self' e 1 para 'elrond' (especialista ativo)
        self._criar_transcript('cid-self', [
            {'type': 'USER_INPUT', 'content': f'Para: Gandalf. Execute sociedade/ordens/f3.md. Pasta: {self.wt}', 'created_at': t1},
            {'type': 'ASSISTANT', 'created_at': t1, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'self'}]}},
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'self'}]}},
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'elrond'}]}}
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            real_resolver = MOD_CONFERIR.resolver_conversa_etapa
            def resolver(etapa, pasta_sociedade=None):
                return real_resolver(etapa, pasta_sociedade=pasta_sociedade, brain_dir=self.brain, summaries_db=self.db_path)

            with patch.object(MOD_CONFERIR, 'resolver_conversa_etapa', side_effect=resolver):
                # Pedindo 2 delegações: como 'self' não conta, só há 1 válida (elrond) -> NAO_FEITO
                st, obs = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@f3', '2']}, self.wt)
                self.assertEqual(st, NAO_FEITO)
                self.assertIn('1 delegações, mínimo 2', obs)

                # Pedindo 1 delegação: a chamada para 'elrond' satisfaz
                st_ok, obs_ok = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@f3', '1']}, self.wt)
                self.assertEqual(st_ok, FEITO)
                self.assertIn('1 delegações', obs_ok)

    def test_delegacoes_nao_especialistas_ou_inativos_descartadas(self):
        """Delegações para coordenador (gandalf) ou especialista inativo (jules em espera) não contam."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('f3', ts)
        t1 = '2026-10-05T12:05:00+00:00'
        self._inserir_db('cid-inativo', t1, str(self.wt.resolve()))

        self._criar_transcript('cid-inativo', [
            {'type': 'USER_INPUT', 'content': f'Para: Gandalf. Execute sociedade/ordens/f3.md. Pasta: {self.wt}', 'created_at': t1},
            {'type': 'ASSISTANT', 'created_at': t1, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'gandalf'}]}},  # Coordenador, não especialista
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'jules'}]}},    # Especialista, mas em 'espera' no perfil
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'galadriel'}]}} # Especialista ativo no perfil
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            real_resolver = MOD_CONFERIR.resolver_conversa_etapa
            def resolver(etapa, pasta_sociedade=None):
                return real_resolver(etapa, pasta_sociedade=pasta_sociedade, brain_dir=self.brain, summaries_db=self.db_path)

            with patch.object(MOD_CONFERIR, 'resolver_conversa_etapa', side_effect=resolver):
                # Apenas galadriel conta como especialista ativo: total = 1
                st, obs = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@f3', '2']}, self.wt)
                self.assertEqual(st, NAO_FEITO)
                self.assertIn('1 delegações, mínimo 2', obs)

                st_ok, obs_ok = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@f3', '1']}, self.wt)
                self.assertEqual(st_ok, FEITO)
                self.assertIn('1 delegações', obs_ok)

    def test_resolucao_por_campo_estruturado_json_transcript(self):
        """Conversa resolvida via campo estruturado 'workspace' no transcript sem depender de summaries_db."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('f3', ts)
        t1 = '2026-10-05T12:05:00+00:00'

        self._criar_transcript('cid-json-workspace', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()), 'content': 'Execute ordens/f3.md', 'created_at': t1},
            {'type': 'ASSISTANT', 'created_at': t1, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'elrond'}]}}
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            conv_id, motivo = MOD_CONFERIR.resolver_conversa_etapa('f3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
            self.assertEqual(conv_id, 'cid-json-workspace')
            self.assertIsNone(motivo)

    def test_segunda_passagem_invalida_conversa_anterior(self):
        """Só contam conversas iniciadas após a ÚLTIMA passagem para Gandalf."""
        t1 = '2026-10-05T10:00:00+00:00'
        self._registrar_passagem('f3', t1)
        t_conv1 = '2026-10-05T10:10:00+00:00'
        self._inserir_db('cid-rodada1', t_conv1, str(self.wt.resolve()))
        self._criar_transcript('cid-rodada1', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()), 'content': 'Rodada 1', 'created_at': t_conv1}
        ])

        # Segunda passagem mais recente
        t2 = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('f3', t2)

        # Sem nova conversa após t2: deve recusar a antiga
        conv_id, motivo = MOD_CONFERIR.resolver_conversa_etapa('f3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
        self.assertIsNone(conv_id)
        self.assertIn('nenhuma conversa do Antigravity encontrada', motivo)

        # Agora cria conversa após t2
        t_conv2 = '2026-10-05T12:05:00+00:00'
        self._inserir_db('cid-rodada2', t_conv2, str(self.wt.resolve()))
        self._criar_transcript('cid-rodada2', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()), 'content': 'Rodada 2', 'created_at': t_conv2}
        ])

        conv_id2, motivo2 = MOD_CONFERIR.resolver_conversa_etapa('f3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
        self.assertEqual(conv_id2, 'cid-rodada2')
        self.assertIsNone(motivo2)

    def test_delegacoes_subagents_serializados_em_string(self):
        """Suporta Subagents como string JSON com validação de especialistas e exclusão de self."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('f3', ts)
        t1 = '2026-10-05T12:05:00+00:00'
        self._inserir_db('cid-str-json', t1, str(self.wt.resolve()))

        subs_json = json.dumps([
            {'TypeName': 'self'},
            {'TypeName': 'elrond'},
            {'TypeName': 'galadriel'}
        ])
        self._criar_transcript('cid-str-json', [
            {'type': 'USER_INPUT', 'content': f'Para: Gandalf. Execute sociedade/ordens/f3.md. Pasta: {self.wt}', 'created_at': t1},
            {'type': 'ASSISTANT', 'created_at': t1, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': subs_json}}
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            real_resolver = MOD_CONFERIR.resolver_conversa_etapa
            def resolver(etapa, pasta_sociedade=None):
                return real_resolver(etapa, pasta_sociedade=pasta_sociedade, brain_dir=self.brain, summaries_db=self.db_path)

            with patch.object(MOD_CONFERIR, 'resolver_conversa_etapa', side_effect=resolver):
                # 3 subagentes na string: self é descartado, elrond e galadriel contam -> total 2
                st, obs = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@f3', '2']}, self.wt)
                self.assertEqual(st, FEITO)
                self.assertIn('2 delegações', obs)

                st3, obs3 = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@f3', '3']}, self.wt)
                self.assertEqual(st3, NAO_FEITO)
                self.assertIn('2 delegações, mínimo 3', obs3)


if __name__ == '__main__':
    unittest.main()
