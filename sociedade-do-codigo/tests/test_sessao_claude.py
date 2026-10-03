"""B03: delegação e conversa nova conferidas pelo log do Claude Code (sessão + subagentes). Transcrições inventadas."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
import sc_conferir  # noqa: E402
import sc_sessao  # noqa: E402

PROJ = '-tmp-projeto-sintetico'


def jsonl(caminho, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text('\n'.join(json.dumps(x) for x in linhas) + '\n', encoding='utf-8')


def ordem(texto='faça a fatia'):
    return {'type': 'user', 'message': {'role': 'user', 'content': texto}}


def chamada(id_, nome='Agent'):
    return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': id_, 'name': nome, 'input': {'prompt': 'x'}}]}}


def resultado(id_):
    return {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': id_, 'content': 'ok'}]}}


def passo():
    return {'type': 'assistant', 'isSidechain': True, 'message': {'content': [{'type': 'text', 'text': 'feito'}]}}


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.projetos = Path(self._tmp.name) / 'projetos'
        self.pasta = self.projetos / PROJ

    def sessao(self, sid, linhas):
        jsonl(self.pasta / f'{sid}.jsonl', linhas)

    def agente(self, sid, aid, linhas, tipo='gandalf'):
        jsonl(self.pasta / sid / 'subagents' / f'agent-{aid}.jsonl', linhas)
        (self.pasta / sid / 'subagents' / f'agent-{aid}.meta.json').write_text(json.dumps({'agentType': tipo}), encoding='utf-8')

    def monta_sessao_com_dois_agentes(self):
        self.sessao('s1', [ordem(), chamada('t1'), resultado('t1'), chamada('t2'), resultado('t2')])
        self.agente('s1', 'aaa', [ordem('ordem do gandalf'), passo(), resultado('x'), passo()])
        self.agente('s1', 'bbb', [ordem('ordem do elrond'), passo()], tipo='elrond')


class TestMedirClaude(Base):
    def test_le_os_subagentes_da_sessao(self):
        self.monta_sessao_com_dois_agentes()
        m = sc_sessao.medir('claude', sessao='s1', projetos=str(self.projetos))
        self.assertEqual(m['delegacoes_chamadas'], 2)
        self.assertEqual(m['delegacoes_total'], 2)
        self.assertEqual({a['agente'] for a in m['subagentes']}, {'aaa', 'bbb'})
        self.assertEqual({a['tipo'] for a in m['subagentes']}, {'gandalf', 'elrond'})
        self.assertTrue(all(a['conversa_nova'] for a in m['subagentes']))
        self.assertTrue(m['conversa_nova'])

    def test_projetos_por_variavel_de_ambiente(self):
        self.monta_sessao_com_dois_agentes()
        with mock.patch.dict(os.environ, {'SC_CLAUDE_PROJETOS': str(self.projetos)}):
            self.assertEqual(sc_sessao.medir('claude', sessao='s1')['delegacoes_total'], 2)

    def test_chamada_sem_log_de_subagente_nao_conta(self):
        # delegação simulada: houve a chamada, mas nenhum subagente executou
        self.sessao('s2', [ordem(), chamada('t1'), chamada('t2'), chamada('t3')])
        self.agente('s2', 'aaa', [ordem(), passo()])
        m = sc_sessao.medir('claude', sessao='s2', projetos=str(self.projetos))
        self.assertEqual((m['delegacoes_chamadas'], m['delegacoes_total']), (3, 1))

    def test_log_de_subagente_sem_chamada_nao_conta(self):
        self.sessao('s3', [ordem()])
        self.agente('s3', 'aaa', [ordem(), passo()])
        self.assertEqual(sc_sessao.medir('claude', sessao='s3', projetos=str(self.projetos))['delegacoes_total'], 0)

    def test_subagente_sem_nenhum_passo_nao_e_execucao(self):
        self.sessao('s4', [ordem(), chamada('t1')])
        self.agente('s4', 'aaa', [ordem()])
        self.assertEqual(sc_sessao.medir('claude', sessao='s4', projetos=str(self.projetos))['delegacoes_total'], 0)

    def test_tarefa_tambem_e_delegacao(self):
        self.sessao('s5', [ordem(), chamada('t1', nome='Task')])
        self.agente('s5', 'aaa', [ordem(), passo()])
        self.assertEqual(sc_sessao.medir('claude', sessao='s5', projetos=str(self.projetos))['delegacoes_total'], 1)

    def test_ordens_de_sistema_e_resultados_nao_contam(self):
        self.sessao('s6', [ordem(), {'type': 'user', 'isMeta': True, 'message': {'content': 'lembrete'}}, resultado('x'),
                           {'type': 'user', 'message': {'content': [{'type': 'text', 'text': 'segunda ordem'}]}}])
        m = sc_sessao.medir('claude', sessao='s6', projetos=str(self.projetos))
        self.assertEqual(m['ordens_na_conversa'], 2)
        self.assertFalse(m['conversa_nova'])

    def test_sessao_mais_recente_por_pasta_usa_projetos(self):
        self.sessao('s7', [ordem()])
        slug_pasta = Path(self._tmp.name) / 'p'
        slug_pasta.mkdir()
        import re
        base = self.projetos / re.sub(r'[^A-Za-z0-9]', '-', str(slug_pasta.resolve()))
        jsonl(base / 'abc.jsonl', [ordem()])
        m = sc_sessao.medir('claude', pasta=str(slug_pasta), projetos=str(self.projetos))
        self.assertEqual(m['sessao'], 'abc')


class TestFalhaFechada(Base):
    def test_sessao_inexistente(self):
        self.pasta.mkdir(parents=True)
        with self.assertRaises(sc_sessao.ErroSessao):
            sc_sessao.medir('claude', sessao='nao-existe', projetos=str(self.projetos))

    def test_pasta_de_projetos_inexistente(self):
        with self.assertRaises(sc_sessao.ErroSessao):
            sc_sessao.medir('claude', sessao='s1', projetos=str(self.projetos / 'nada'))

    def test_log_ilegivel(self):
        (self.pasta).mkdir(parents=True)
        (self.pasta / 'ruim.jsonl').write_bytes(b'\xff\xfe\x00 nao e json\n{quebrado')
        with self.assertRaises(sc_sessao.ErroSessao):
            sc_sessao.medir('claude', sessao='ruim', projetos=str(self.projetos))

    def test_log_vazio(self):
        self.pasta.mkdir(parents=True)
        (self.pasta / 'vazio.jsonl').write_text('', encoding='utf-8')
        with self.assertRaises(sc_sessao.ErroSessao):
            sc_sessao.medir('claude', log=str(self.pasta / 'vazio.jsonl'))

    def test_log_informado_que_nao_existe(self):
        with self.assertRaises(sc_sessao.ErroSessao):
            sc_sessao.medir('claude', log=str(self.pasta / 'fantasma.jsonl'))

    def test_log_de_subagente_ilegivel_reprova_a_sessao(self):
        self.sessao('s8', [ordem(), chamada('t1')])
        self.agente('s8', 'aaa', [ordem(), passo()])
        (self.pasta / 's8' / 'subagents' / 'agent-bbb.jsonl').write_text('lixo\n', encoding='utf-8')
        with self.assertRaises(sc_sessao.ErroSessao):
            sc_sessao.medir('claude', sessao='s8', projetos=str(self.projetos))

    def test_identificador_com_caminho_e_recusado(self):
        for ruim in ('../x', 'a/b', '', '.oculto'):
            with self.assertRaises(sc_sessao.ErroSessao, msg=repr(ruim)):
                sc_sessao.localizar_claude(ruim, str(self.projetos))

    def test_cli_log_ausente_sai_com_erro(self):
        r = rodar(NUCLEO / 'scripts' / 'sc_sessao.py', 'claude', '--sessao', 'x', '--projetos', str(self.projetos))
        self.assertEqual(r.returncode, 1)
        self.assertIn('erro:', r.stderr)

    def test_cli_json(self):
        self.monta_sessao_com_dois_agentes()
        r = rodar(NUCLEO / 'scripts' / 'sc_sessao.py', 'claude', '--sessao', 's1', '--projetos', str(self.projetos), '--json')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['delegacoes_total'], 2)
        r = rodar(NUCLEO / 'scripts' / 'sc_sessao.py', 'claude', '--sessao', 's1', '--projetos', str(self.projetos))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('subagentes:', r.stdout)


class TestConferirClaude(Base):
    def conferir(self, tipo, *args):
        with mock.patch.dict(os.environ, {'SC_CLAUDE_PROJETOS': str(self.projetos)}):
            return sc_conferir.conferir_item({'id': 'E', 'tipo': tipo, 'args': list(args)}, Path(self._tmp.name))

    def test_delegacoes_claude_feito_e_minimo(self):
        self.monta_sessao_com_dois_agentes()
        self.assertEqual(self.conferir('delegacoes', 'claude', 's1', '2')[0], sc_conferir.FEITO)
        estado, detalhe = self.conferir('delegacoes', 'claude', 's1', '3')
        self.assertEqual(estado, sc_conferir.NAO_FEITO)
        self.assertIn('mínimo 3', detalhe)

    def test_delegacoes_claude_sem_minimo_exige_uma(self):
        self.sessao('s9', [ordem()])
        self.assertEqual(self.conferir('delegacoes', 'claude', 's9')[0], sc_conferir.NAO_FEITO)

    def test_conversa_nova_de_agente_por_id(self):
        self.monta_sessao_com_dois_agentes()
        self.agente('s1', 'ccc', [ordem('primeira'), passo(), ordem('segunda'), passo()])
        self.assertEqual(self.conferir('conversa_nova', 'claude', 'aaa')[0], sc_conferir.FEITO)
        self.assertEqual(self.conferir('conversa_nova', 'claude', 'agent-bbb')[0], sc_conferir.FEITO)
        estado, detalhe = self.conferir('conversa_nova', 'claude', 'ccc')
        self.assertEqual(estado, sc_conferir.NAO_FEITO)
        self.assertIn('2 ordens', detalhe)

    def test_conversa_nova_de_sessao(self):
        self.monta_sessao_com_dois_agentes()
        self.assertEqual(self.conferir('conversa_nova', 'claude', 's1')[0], sc_conferir.FEITO)

    def test_log_ausente_reprova_as_duas_entregas(self):
        for tipo, args in (('delegacoes', ('claude', 'fantasma', '1')), ('conversa_nova', ('claude', 'fantasma'))):
            estado, detalhe = self.conferir(tipo, *args)
            self.assertEqual(estado, sc_conferir.NAO_FEITO, tipo)
            self.assertIn('não encontrado', detalhe)

    def test_log_ilegivel_reprova(self):
        self.pasta.mkdir(parents=True)
        (self.pasta / 'ruim.jsonl').write_text('{nao e json\n', encoding='utf-8')
        self.assertEqual(self.conferir('conversa_nova', 'claude', 'ruim')[0], sc_conferir.NAO_FEITO)

    def test_delegacoes_com_id_de_agente_nao_e_feito(self):
        self.monta_sessao_com_dois_agentes()
        self.assertEqual(self.conferir('delegacoes', 'claude', 'aaa', '1')[0], sc_conferir.NAO_FEITO)

    def test_aplicativo_desconhecido_e_nao_preenchido(self):
        self.assertEqual(self.conferir('delegacoes', 'outro', 's1', '1')[0], sc_conferir.NAO_PREENCHIDO)

    def test_marcador_nao_preenchido(self):
        self.assertEqual(self.conferir('delegacoes', 'claude', '<sessão do Círdan>', '5')[0], sc_conferir.NAO_PREENCHIDO)

    def test_ordem_completa_com_entregas_claude(self):
        self.monta_sessao_com_dois_agentes()
        ordem_md = Path(self._tmp.name) / 'ordem-x.md'
        ordem_md.write_text('```entregas\nE6 | delegacoes | claude | s1 | 2\nE7 | conversa_nova | claude | aaa\n```\n', encoding='utf-8')
        with mock.patch.dict(os.environ, {'SC_CLAUDE_PROJETOS': str(self.projetos)}):
            rel = sc_conferir.conferir(ordem_md, raiz=self._tmp.name)
        self.assertEqual((rel['feitos'], rel['total']), (2, 2))

    def test_antigravity_continua_como_antes(self):
        estado, _ = sc_conferir.conferir_item({'id': 'E', 'tipo': 'conversa_nova', 'args': ['antigravity']}, Path(self._tmp.name))
        self.assertEqual(estado, sc_conferir.NAO_PREENCHIDO)


if __name__ == '__main__':
    unittest.main()
