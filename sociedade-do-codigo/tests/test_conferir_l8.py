#!/usr/bin/env python3
"""Teste para resolução de @etapa em delegacoes e conversa_nova do conferir_atestado (L8).

sc_conferir:
- Resolve @etapa para Antigravity buscando a conversa aberta na pasta do worktree após
  o evento 'passagem' para Gandalf.
- Na ausência ou ambiguidade, devolve 'não feito' com motivo explicativo sem quebrar.
- Quando unívoco, resolve para o identificador da conversa e afere a medição.
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, carregar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
MOD_CONFERIR = carregar(NUCLEO / 'scripts' / 'sc_conferir.py', 'sc_conferir')
MOD_REGISTRO = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REGISTRO.Registro
FEITO = MOD_CONFERIR.FEITO
NAO_FEITO = MOD_CONFERIR.NAO_FEITO


class TesteConferirL8(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

        # Worktree da etapa
        self.wt = self.raiz / 'worktree-e8'
        self.wt.mkdir()
        self.soc_wt = self.wt / 'sociedade'
        self.soc_wt.mkdir()

        # Brain e summaries_db simulados
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

        self.reg = Registro.inicializar(self.soc_wt, projeto_id='proj-l8', caminho_canonico=str(self.wt), aplicar=True)

    def _registrar_passagem(self, etapa='e8', data_hora='2026-10-03T12:00:00Z'):
        def gerador(dados):
            return [{
                'tipo': 'passagem',
                'dados': {
                    'etapa': etapa,
                    'para': 'gandalf',
                    'papel': 'coordenador',
                    'ferramenta': 'Antigravity',
                    'modelo': 'Gemini 3.8 Flash',
                    'esforco': 'high',
                    'pasta': str(self.wt.resolve()),
                    'linha': f'Para: Gandalf. Execute sociedade/ordens/{etapa}.md.',
                    'data_hora': data_hora,
                }
            }]
        self.reg.aplicar_mutacao(gerador, autor='Círdan', aplicar=True)

    def _inserir_conversa_db(self, cid, tempo, uris):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO conversation_summaries VALUES (?, ?, ?, ?)",
            (cid, tempo, tempo, uris)
        )
        conn.commit()
        conn.close()

    def test_sem_evento_passagem_retorna_none_com_motivo(self):
        cid, motivo = MOD_CONFERIR.resolver_conversa_etapa(
            'e8', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path
        )
        self.assertIsNone(cid)
        self.assertIn('nenhum evento de passagem', motivo)

    def test_nenhuma_conversa_apos_passagem_retorna_none_com_motivo(self):
        self._registrar_passagem()
        ev = self.reg.dados['eventos'][-1]
        t_passagem = ev.get('timestamp') or '2026-10-04T00:00:00Z'
        from datetime import datetime, timedelta, timezone
        dt = datetime.fromisoformat(str(t_passagem).replace('Z', '+00:00'))
        tempo_anterior = (dt - timedelta(minutes=10)).isoformat()

        # Conversa anterior ao timestamp de passagem
        self._inserir_conversa_db('cid-antiga', tempo_anterior, str(self.wt.resolve()))

        cid, motivo = MOD_CONFERIR.resolver_conversa_etapa(
            'e8', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path
        )
        self.assertIsNone(cid)
        self.assertIn('nenhuma conversa do Antigravity encontrada', motivo)

    def test_ambiguidade_mais_de_uma_conversa_retorna_none_com_motivo(self):
        self._registrar_passagem()
        ev = self.reg.dados['eventos'][-1]
        t_passagem = ev.get('timestamp') or '2026-10-04T00:00:00Z'
        from datetime import datetime, timedelta, timezone
        dt = datetime.fromisoformat(str(t_passagem).replace('Z', '+00:00'))
        t1 = (dt + timedelta(minutes=5)).isoformat()
        t2 = (dt + timedelta(minutes=10)).isoformat()

        self._inserir_conversa_db('cid-1', t1, str(self.wt.resolve()))
        self._inserir_conversa_db('cid-2', t2, str(self.wt.resolve()))

        cid, motivo = MOD_CONFERIR.resolver_conversa_etapa(
            'e8', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path
        )
        self.assertIsNone(cid)
        self.assertIn('ambiguidade:', motivo)
        self.assertIn('2 conversas', motivo)

    def test_conversa_unica_resolve_corretamente(self):
        self._registrar_passagem()
        ev = self.reg.dados['eventos'][-1]
        t_passagem = ev.get('timestamp') or '2026-10-04T00:00:00Z'
        from datetime import datetime, timedelta, timezone
        dt = datetime.fromisoformat(str(t_passagem).replace('Z', '+00:00'))
        t1 = (dt + timedelta(minutes=5)).isoformat()

        self._inserir_conversa_db('cid-unica', t1, str(self.wt.resolve()))

        cid, motivo = MOD_CONFERIR.resolver_conversa_etapa(
            'e8', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path
        )
        self.assertEqual(cid, 'cid-unica')
        self.assertIsNone(motivo)

    def test_conferir_item_com_arroba_ausente_devolve_nao_feito(self):
        self._registrar_passagem()
        item = {'tipo': 'conversa_nova', 'args': ['antigravity', '@e8']}
        status, obs = MOD_CONFERIR.conferir_item(item, self.wt)
        # Sem conversa registrada no local padrão do Antigravity, retorna NAO_FEITO sem quebrar
        self.assertEqual(status, NAO_FEITO)
        self.assertTrue(len(obs) > 0)

    def test_negativo_pasta_errada_recusa(self):
        self._registrar_passagem()
        ev = self.reg.dados['eventos'][-1]
        t_passagem = ev.get('timestamp') or '2026-10-04T00:00:00Z'
        from datetime import datetime, timedelta
        dt = datetime.fromisoformat(str(t_passagem).replace('Z', '+00:00'))
        t1 = (dt + timedelta(minutes=5)).isoformat()

        pasta_errada = self.raiz / 'outro-worktree'
        pasta_errada.mkdir()
        self._inserir_conversa_db('cid-errada', t1, str(pasta_errada.resolve()))

        cid, motivo = MOD_CONFERIR.resolver_conversa_etapa(
            'e8', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path
        )
        self.assertIsNone(cid)
        self.assertIn('nenhuma conversa do Antigravity encontrada', motivo)

    def test_negativo_prefixo_pasta_recusa(self):
        self._registrar_passagem()
        ev = self.reg.dados['eventos'][-1]
        t_passagem = ev.get('timestamp') or '2026-10-04T00:00:00Z'
        from datetime import datetime, timedelta
        dt = datetime.fromisoformat(str(t_passagem).replace('Z', '+00:00'))
        t1 = (dt + timedelta(minutes=5)).isoformat()

        # Pasta cujo caminho começa com o worktree (prefixo), ex: worktree-e8-outro
        pasta_prefixo = str(self.wt.resolve()) + '-outro'
        self._inserir_conversa_db('cid-prefixo', t1, pasta_prefixo)

        cid, motivo = MOD_CONFERIR.resolver_conversa_etapa(
            'e8', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path
        )
        self.assertIsNone(cid)
        self.assertIn('nenhuma conversa do Antigravity encontrada', motivo)

    def test_negativo_ausencia_timestamp_recusa(self):
        self._registrar_passagem()
        # Sem timestamp no DB (None ou vazio)
        self._inserir_conversa_db('cid-sem-tempo', None, str(self.wt.resolve()))

        cid, motivo = MOD_CONFERIR.resolver_conversa_etapa(
            'e8', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path
        )
        self.assertIsNone(cid)
        self.assertIn('nenhuma conversa do Antigravity encontrada', motivo)

    def test_negativo_timestamp_anterior_passagem_recusa(self):
        self._registrar_passagem()
        ev = self.reg.dados['eventos'][-1]
        t_passagem = ev.get('timestamp') or '2026-10-04T00:00:00Z'
        from datetime import datetime, timedelta
        dt = datetime.fromisoformat(str(t_passagem).replace('Z', '+00:00'))
        t_anterior = (dt - timedelta(seconds=1)).isoformat()

        self._inserir_conversa_db('cid-anterior', t_anterior, str(self.wt.resolve()))

        cid, motivo = MOD_CONFERIR.resolver_conversa_etapa(
            'e8', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path
        )
        self.assertIsNone(cid)
        self.assertIn('nenhuma conversa do Antigravity encontrada', motivo)

    def test_negativo_transcript_pasta_diferente_mesmo_citando_ordem_recusa(self):
        self._registrar_passagem()
        ev = self.reg.dados['eventos'][-1]
        t_passagem = ev.get('timestamp') or '2026-10-04T00:00:00Z'
        from datetime import datetime, timedelta
        dt = datetime.fromisoformat(str(t_passagem).replace('Z', '+00:00'))
        t1 = (dt + timedelta(minutes=5)).isoformat()

        # Transcript em brain que cita ordens/e8.md mas pertence a outra pasta
        cid_dir = self.brain / 'cid-ordem-outra-pasta' / '.system_generated' / 'logs'
        cid_dir.mkdir(parents=True)
        t_file = cid_dir / 'transcript.jsonl'
        primeiro_passo = {
            'step_index': 0,
            'created_at': t1,
            'content': f'Para: Gandalf. Execute sociedade/ordens/e8.md na pasta /tmp/outra-pasta-totalmente-diferente.',
            'workspace': '/tmp/outra-pasta-totalmente-diferente'
        }
        t_file.write_text(json.dumps(primeiro_passo) + '\n', encoding='utf-8')

        cid, motivo = MOD_CONFERIR.resolver_conversa_etapa(
            'e8', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path
        )
        self.assertIsNone(cid)
        self.assertIn('nenhuma conversa do Antigravity encontrada', motivo)


if __name__ == '__main__':
    unittest.main()
