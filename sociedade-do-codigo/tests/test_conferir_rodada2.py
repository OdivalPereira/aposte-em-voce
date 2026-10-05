#!/usr/bin/env python3
"""Testes dirigidos para os achados K2, K3 e K4 (Rodada 2 de d1b-robustez).

Cobre:
- K2: Cauda de governança pós-atestado (Q149, Q178).
  `atestado_aprovado` e `commit_existe` avaliam o último commit de produto quando commits
  posteriores tocam exclusivamente arquivos em sociedade/. Se houver alteração fora de
  sociedade/ após o atestado, continua reprovando.
- K3: Identidade estrita de conversa e worktree (Q181, A01).
  Remoção de common_git como pasta válida. Conversas na pasta principal sem vínculo
  estruturado com o worktree não contam (retornam 'não verificado'). Conversas legítimas
  no worktree são resolvidas com sucesso.
- K4: Múltiplas rodadas do Gandalf (Q180).
  Suporte a múltiplas passagens para Gandalf; cada passagem liga a primeira conversa aberta
  após a respectiva passagem no worktree por campo estruturado.
  `delegacoes` totaliza as delegações de todas as rodadas da etapa.
  `conversa_nova` valida cada conversa de cada rodada.
  Ambiguidade só é reportada para conversas conflitantes dentro da mesma rodada.
"""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO  # noqa: E402

sys.path.insert(0, str((NUCLEO / 'scripts').resolve()))
import sc_conferir as MOD_CONFERIR
import sc_registro as MOD_REGISTRO
import sc_sessao as MOD_SESSAO
import sc_status as MOD_STATUS

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
## Modo emulação (Q147)
- **Emulação:** não.
"""

AMBIENTE_GIT = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}


def _git(raiz, *args):
    return subprocess.run(
        ['git', '-C', str(raiz), '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', *args],
        capture_output=True, text=True, check=True, env=AMBIENTE_GIT
    ).stdout.strip()


def _commit(raiz, msg):
    _git(raiz, 'add', '-A')
    _git(raiz, 'commit', '-q', '-m', msg)
    return _git(raiz, 'rev-parse', 'HEAD')


class TestK2CaudaGovernanca(unittest.TestCase):
    """Cenários do achado K2: Cauda de governança pós-atestado (Q149 / Q178)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        _git(self.raiz, 'init', '-q')

        self.soc = self.raiz / 'sociedade'
        self.soc.mkdir()
        self.pareceres = self.soc / 'pareceres'
        self.pareceres.mkdir()
        (self.raiz / 'pacote').mkdir()

        self.perfil = self.soc / 'perfil.md'
        self.perfil.write_text(PERFIL_TESTE, encoding='utf-8')
        (self.raiz / 'pacote' / 'app.py').write_text('X = 1\n', encoding='utf-8')
        self.commit_produto = _commit(self.raiz, 'feat(pacote): produto inicial')

    def _gerar_atestado(self, commit_sha, status='APROVADO'):
        perfil_hash = hashlib.sha256(self.perfil.read_bytes()).hexdigest()
        arq_hash = hashlib.sha256((self.raiz / 'pacote' / 'app.py').read_bytes()).hexdigest()
        hashes = {'pacote/app.py': arq_hash}
        dados = {
            'status': status,
            'commit': commit_sha,
            'perfil_hash': perfil_hash,
            'total_arquivos_inspecionados': 1,
            'arquivos_inspecionados': ['pacote/app.py'],
            'hashes_artefatos': hashes,
            'data_hora': '2026-10-05T12:00:00Z',
            'areas': {'pacote': {'status': 'APROVADO'}},
            'portao': {
                'modo': 'por_area',
                'commit': commit_sha,
                'areas': [{'area': 'pacote', 'ok': True}],
                'areas_tocadas': ['pacote'],
                'cobertura_completa': True,
                'perfil_sha256': perfil_hash,
            },
            'erros': [],
        }
        at_hash = MOD_STATUS.hash_do_atestado(dados)
        dados['atestado_hash'] = at_hash
        at_path = self.pareceres / 'atestado-teste.json'
        at_path.write_text(json.dumps(dados, indent=2), encoding='utf-8')
        return at_path

    def test_atestado_aprovado_com_cauda_de_governanca_pura_passa(self):
        """K2: atestado_aprovado confere com HEAD mesmo quando commits posteriores tocam só sociedade/."""
        at_file = self._gerar_atestado(self.commit_produto)

        # Commits de governança pura posteriores ao atestado (ex: c0c316f e f0ade5b)
        (self.soc / 'regras.md').write_text('# Regras\n', encoding='utf-8')
        _commit(self.raiz, 'sociedade: atualiza regras (Q149)')
        (self.soc / 'estado.md').write_text('# Estado\n', encoding='utf-8')
        head_gov = _commit(self.raiz, 'sociedade: atualiza estado')

        self.assertNotEqual(head_gov, self.commit_produto)

        item = {'tipo': 'atestado_aprovado', 'args': [str(at_file.relative_to(self.raiz)), 'HEAD']}
        st, obs = MOD_CONFERIR.conferir_item(item, self.raiz)
        self.assertEqual(st, FEITO)
        self.assertIn('APROVADO', obs)
        self.assertIn(self.commit_produto[:12], obs)

    def test_atestado_aprovado_com_alteracao_fora_de_sociedade_reprova(self):
        """K2: Se houver commit com alteração de produto após o atestado, continua reprovando."""
        at_file = self._gerar_atestado(self.commit_produto)

        # Commit posterior alterando produto fora de sociedade/
        (self.raiz / 'pacote' / 'extra.py').write_text('Y = 2\n', encoding='utf-8')
        _commit(self.raiz, 'feat(pacote): alteracao de produto pos atestado')

        item = {'tipo': 'atestado_aprovado', 'args': [str(at_file.relative_to(self.raiz)), 'HEAD']}
        st, obs = MOD_CONFERIR.conferir_item(item, self.raiz)
        self.assertEqual(st, NAO_FEITO)
        self.assertIn('esperado', obs)

    def test_commit_existe_avalia_ultimo_commit_produto_na_cauda(self):
        """K2: commit_existe avalia o último commit de produto quando HEAD tem cauda de governança."""
        # Cria commits posteriores puramente em sociedade/
        (self.soc / 'regras.md').write_text('# Regras\n', encoding='utf-8')
        _commit(self.raiz, 'sociedade: atualiza regras')
        (self.soc / 'nota.md').write_text('# Nota\n', encoding='utf-8')
        head_gov = _commit(self.raiz, 'sociedade: cauda final')

        # 1 argumento: commit_existe | HEAD
        item1 = {'tipo': 'commit_existe', 'args': ['HEAD']}
        st1, obs1 = MOD_CONFERIR.conferir_item(item1, self.raiz)
        self.assertEqual(st1, FEITO)
        self.assertEqual(obs1, self.commit_produto[:12])

        # 2 argumentos: commit_existe | HEAD | <commit_produto>
        item2 = {'tipo': 'commit_existe', 'args': ['HEAD', self.commit_produto]}
        st2, obs2 = MOD_CONFERIR.conferir_item(item2, self.raiz)
        self.assertEqual(st2, FEITO)
        self.assertEqual(obs2, self.commit_produto[:12])

    def test_commit_existe_com_produto_divergente_reprova(self):
        """K2: commit_existe reprova se houve alteração fora de sociedade/ após o esperado."""
        (self.raiz / 'pacote' / 'novo.py').write_text('Z = 3\n', encoding='utf-8')
        _commit(self.raiz, 'feat: novo produto')

        item = {'tipo': 'commit_existe', 'args': ['HEAD', self.commit_produto]}
        st, obs = MOD_CONFERIR.conferir_item(item, self.raiz)
        self.assertEqual(st, NAO_FEITO)
        self.assertIn('esperado', obs)


class TestK3IdentidadeWorktree(unittest.TestCase):
    """Cenários do achado K3: Identidade estrita de conversa e worktree (Q181 / A01)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

        # Repositório principal (raiz do projeto Git)
        self.repo_principal = self.raiz / 'repo-principal'
        self.repo_principal.mkdir()
        _git(self.repo_principal, 'init', '-q')
        (self.repo_principal / 'README.md').write_text('repo\n', encoding='utf-8')
        _commit(self.repo_principal, 'init')

        # Worktree da etapa
        self.wt = self.raiz / 'worktree-k3'
        _git(self.repo_principal, 'worktree', 'add', '-b', 'etapa/k3', str(self.wt))

        self.soc_wt = self.wt / 'sociedade'
        self.soc_wt.mkdir(exist_ok=True)
        (self.soc_wt / 'perfil.md').write_text(PERFIL_TESTE, encoding='utf-8')

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

        self.reg = Registro.inicializar(self.soc_wt, projeto_id='proj-k3', caminho_canonico=str(self.wt), aplicar=True)

    def _registrar_passagem(self, etapa='k3', ts='2026-10-05T12:00:00+00:00'):
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

    def _inserir_db(self, cid, tempo, uris):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO conversation_summaries VALUES (?, ?, ?, ?)",
            (cid, tempo, tempo, uris)
        )
        conn.commit()
        conn.close()

    def _criar_transcript(self, cid, passos):
        cid_dir = self.brain / cid / '.system_generated' / 'logs'
        cid_dir.mkdir(parents=True, exist_ok=True)
        t_file = cid_dir / 'transcript.jsonl'
        linhas = [json.dumps(p) for p in passos]
        t_file.write_text('\n'.join(linhas) + '\n', encoding='utf-8')
        return t_file

    def test_raiz_principal_common_git_nao_conta_sem_vinculo_estruturado(self):
        """K3: Conversa aberta na raiz principal do repositório (common_git) resulta em não verificado."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('k3', ts)
        t_conv = '2026-10-05T12:05:00+00:00'

        # Conversa aponta para a pasta do repositório principal (não para o worktree)
        self._inserir_db('cid-repo-principal', t_conv, str(self.repo_principal.resolve()))
        self._criar_transcript('cid-repo-principal', [
            {'type': 'USER_INPUT', 'workspace': str(self.repo_principal.resolve()),
             'content': 'Para: Gandalf. Execute sociedade/ordens/k3.md no ambiente.', 'created_at': t_conv},
            {'type': 'ASSISTANT', 'created_at': t_conv, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'elrond'}]}}
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            conv_id, motivo = MOD_CONFERIR.resolver_conversa_etapa('k3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
            self.assertIsNone(conv_id)
            self.assertIn('sem campo estruturado de workspace', motivo)

            real_resolver = MOD_CONFERIR.resolver_conversa_etapa
            def resolver(etapa, pasta_sociedade=None):
                return real_resolver(etapa, pasta_sociedade=pasta_sociedade, brain_dir=self.brain, summaries_db=self.db_path)

            with patch.object(MOD_CONFERIR, 'resolver_conversa_etapa', side_effect=resolver):
                st, obs = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@k3', '1']}, self.wt)
                self.assertEqual(st, NAO_VERIFICADO)
                self.assertIn('sem campo estruturado', obs)

    def test_conversa_legitima_no_worktree_com_campo_estruturado_aceita(self):
        """K3: Conversa aberta legitimamente no worktree da etapa é resolvida com sucesso."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('k3', ts)
        t_conv = '2026-10-05T12:05:00+00:00'

        self._inserir_db('cid-wt-ok', t_conv, str(self.wt.resolve()))
        self._criar_transcript('cid-wt-ok', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()),
             'content': 'Para: Gandalf. Execute sociedade/ordens/k3.md.', 'created_at': t_conv},
            {'type': 'ASSISTANT', 'created_at': t_conv, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'elrond'}]}}
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            conv_id, motivo = MOD_CONFERIR.resolver_conversa_etapa('k3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
            self.assertEqual(conv_id, 'cid-wt-ok')
            self.assertIsNone(motivo)

    def test_convivencia_repo_principal_e_worktree_apenas_worktree_escolhido(self):
        """K3: Quando existem conversa na pasta principal e conversa no worktree, apenas a do worktree conta."""
        ts = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('k3', ts)

        # Conversa espúria na pasta principal
        t_esp = '2026-10-05T12:02:00+00:00'
        self._inserir_db('cid-espuria-repo', t_esp, str(self.repo_principal.resolve()))
        self._criar_transcript('cid-espuria-repo', [
            {'type': 'USER_INPUT', 'workspace': str(self.repo_principal.resolve()), 'content': 'Teste na raiz', 'created_at': t_esp}
        ])

        # Conversa legítima no worktree
        t_leg = '2026-10-05T12:05:00+00:00'
        self._inserir_db('cid-legitima-wt', t_leg, str(self.wt.resolve()))
        self._criar_transcript('cid-legitima-wt', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()),
             'content': 'Para: Gandalf. Execute ordens/k3.md', 'created_at': t_leg},
            {'type': 'ASSISTANT', 'created_at': t_leg, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'elrond'}]}}
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            conv_id, motivo = MOD_CONFERIR.resolver_conversa_etapa('k3', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
            self.assertEqual(conv_id, 'cid-legitima-wt')
            self.assertIsNone(motivo)


class TestK4MultiplasRodadas(unittest.TestCase):
    """Cenários do achado K4: Múltiplas rodadas do Gandalf (Q180)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

        self.wt = self.raiz / 'worktree-k4'
        self.wt.mkdir()
        self.soc_wt = self.wt / 'sociedade'
        self.soc_wt.mkdir()
        (self.soc_wt / 'perfil.md').write_text(PERFIL_TESTE, encoding='utf-8')

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

        self.reg = Registro.inicializar(self.soc_wt, projeto_id='proj-k4', caminho_canonico=str(self.wt), aplicar=True)

    def _registrar_passagem(self, etapa='k4', ts='2026-10-05T10:00:00+00:00'):
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

    def _inserir_db(self, cid, tempo, uris):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO conversation_summaries VALUES (?, ?, ?, ?)",
            (cid, tempo, tempo, uris)
        )
        conn.commit()
        conn.close()

    def _criar_transcript(self, cid, passos):
        cid_dir = self.brain / cid / '.system_generated' / 'logs'
        cid_dir.mkdir(parents=True, exist_ok=True)
        t_file = cid_dir / 'transcript.jsonl'
        linhas = [json.dumps(p) for p in passos]
        t_file.write_text('\n'.join(linhas) + '\n', encoding='utf-8')
        return t_file

    def test_duas_rodadas_delegacoes_somadas_e_conversa_nova(self):
        """K4: Duas rodadas somam delegações no @etapa e validam uma ordem por conversa em cada."""
        # Rodada 1
        t_passagem1 = '2026-10-05T10:00:00+00:00'
        self._registrar_passagem('k4', t_passagem1)
        t_conv1 = '2026-10-05T10:05:00+00:00'
        self._inserir_db('cid-r1', t_conv1, str(self.wt.resolve()))
        self._criar_transcript('cid-r1', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()),
             'content': 'Para: Gandalf. Execute sociedade/ordens/k4.md (rodada 1)', 'created_at': t_conv1},
            {'type': 'ASSISTANT', 'created_at': t_conv1, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'elrond'}, {'TypeName': 'galadriel'}]}}
            ]}
        ])

        # Rodada 2
        t_passagem2 = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('k4', t_passagem2)
        t_conv2 = '2026-10-05T12:05:00+00:00'
        self._inserir_db('cid-r2', t_conv2, str(self.wt.resolve()))
        self._criar_transcript('cid-r2', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()),
             'content': 'Para: Gandalf. Execute sociedade/ordens/k4.md (rodada 2)', 'created_at': t_conv2},
            {'type': 'ASSISTANT', 'created_at': t_conv2, 'tool_calls': [
                {'name': 'invoke_subagent', 'args': {'Subagents': [{'TypeName': 'elrond'}]}}
            ]}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            convs, motivo = MOD_CONFERIR.resolver_conversas_etapa('k4', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
            self.assertEqual(convs, ['cid-r1', 'cid-r2'])
            self.assertIsNone(motivo)

            real_resolver = MOD_CONFERIR.resolver_conversa_etapa
            def resolver(etapa, pasta_sociedade=None):
                return real_resolver(etapa, pasta_sociedade=pasta_sociedade, brain_dir=self.brain, summaries_db=self.db_path)

            with patch.object(MOD_CONFERIR, 'resolver_conversa_etapa', side_effect=resolver):
                # Total somado das rodadas: 2 da rodada 1 + 1 da rodada 2 = 3 delegações
                st_del3, obs_del3 = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@k4', '3']}, self.wt)
                self.assertEqual(st_del3, FEITO)
                self.assertIn('3 delegações', obs_del3)

                st_del4, obs_del4 = MOD_CONFERIR.conferir_item({'tipo': 'delegacoes', 'args': ['antigravity', '@k4', '4']}, self.wt)
                self.assertEqual(st_del4, NAO_FEITO)
                self.assertIn('3 delegações, mínimo 4', obs_del4)

                # conversa_nova valida que cada rodada tem 1 ordem por conversa
                st_cn, obs_cn = MOD_CONFERIR.conferir_item({'tipo': 'conversa_nova', 'args': ['antigravity', '@k4']}, self.wt)
                self.assertEqual(st_cn, FEITO)

    def test_conversa_nova_reprova_se_uma_rodada_tiver_multiplas_ordens(self):
        """K4: Se qualquer conversa de qualquer rodada tiver mais de uma ordem, conversa_nova reprova."""
        t1 = '2026-10-05T10:00:00+00:00'
        self._registrar_passagem('k4', t1)
        t_c1 = '2026-10-05T10:05:00+00:00'
        self._inserir_db('cid-ok-r1', t_c1, str(self.wt.resolve()))
        self._criar_transcript('cid-ok-r1', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()), 'content': 'Ordem 1', 'created_at': t_c1}
        ])

        t2 = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('k4', t2)
        t_c2 = '2026-10-05T12:05:00+00:00'
        # Segunda conversa recebe 2 ordens
        self._inserir_db('cid-reusa-r2', t_c2, str(self.wt.resolve()))
        self._criar_transcript('cid-reusa-r2', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()), 'content': 'Ordem A em r2', 'created_at': t_c2},
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()), 'content': 'Ordem B na mesma conversa', 'created_at': '2026-10-05T12:10:00+00:00'}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            real_resolver = MOD_CONFERIR.resolver_conversa_etapa
            def resolver(etapa, pasta_sociedade=None):
                return real_resolver(etapa, pasta_sociedade=pasta_sociedade, brain_dir=self.brain, summaries_db=self.db_path)

            with patch.object(MOD_CONFERIR, 'resolver_conversa_etapa', side_effect=resolver):
                st_cn, obs_cn = MOD_CONFERIR.conferir_item({'tipo': 'conversa_nova', 'args': ['antigravity', '@k4']}, self.wt)
                self.assertEqual(st_cn, NAO_FEITO)
                self.assertIn('ordens na mesma conversa', obs_cn)

    def test_multiplas_conversas_em_rodadas_distintas_nao_causam_ambiguidade(self):
        """K4: Múltiplas conversas em rodadas distintas não causam ambiguidade (cada rodada tem a sua)."""
        t1 = '2026-10-05T10:00:00+00:00'
        self._registrar_passagem('k4', t1)
        t_a = '2026-10-05T10:05:00+00:00'
        self._inserir_db('cid-r1-ok', t_a, str(self.wt.resolve()))
        self._criar_transcript('cid-r1-ok', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()), 'content': 'Para: Gandalf. Ordem k4 rodada 1', 'created_at': t_a}
        ])

        t2 = '2026-10-05T12:00:00+00:00'
        self._registrar_passagem('k4', t2)
        t_b = '2026-10-05T12:05:00+00:00'
        self._inserir_db('cid-r2-ok', t_b, str(self.wt.resolve()))
        self._criar_transcript('cid-r2-ok', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()), 'content': 'Para: Gandalf. Ordem k4 rodada 2', 'created_at': t_b}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            convs, motivo = MOD_CONFERIR.resolver_conversas_etapa('k4', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
            self.assertEqual(convs, ['cid-r1-ok', 'cid-r2-ok'])
            self.assertIsNone(motivo)

    def test_ambiguidade_reportada_com_multiplas_conversas_na_mesma_rodada(self):
        """K4: Ambiguidade reportada quando múltiplas conversas conflitantes são abertas na mesma rodada."""
        t1 = '2026-10-05T10:00:00+00:00'
        self._registrar_passagem('k4', t1)

        t_conflito1 = '2026-10-05T10:05:00+00:00'
        self._inserir_db('cid-conflito-1', t_conflito1, str(self.wt.resolve()))
        self._criar_transcript('cid-conflito-1', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()), 'content': 'Para: Gandalf. Ordem k4 tentativa 1', 'created_at': t_conflito1}
        ])
        t_conflito2 = '2026-10-05T10:15:00+00:00'
        self._inserir_db('cid-conflito-2', t_conflito2, str(self.wt.resolve()))
        self._criar_transcript('cid-conflito-2', [
            {'type': 'USER_INPUT', 'workspace': str(self.wt.resolve()), 'content': 'Para: Gandalf. Ordem k4 tentativa 2', 'created_at': t_conflito2}
        ])

        with patch.object(MOD_SESSAO, 'AG_BRAIN', self.brain), \
             patch.object(MOD_SESSAO, 'inspecionar_base_antigravity', return_value={'consumo': 'n/d', 'motivo': 'mock', 'hipoteses': []}):
            convs, motivo = MOD_CONFERIR.resolver_conversas_etapa('k4', pasta_sociedade=self.soc_wt, brain_dir=self.brain, summaries_db=self.db_path)
            self.assertEqual(convs, [])
            self.assertIn('ambiguidade', motivo)


if __name__ == '__main__':
    unittest.main()
