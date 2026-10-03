"""Consumo por agente e modelo pelo log do Claude Code (`sc.py sessao claude`, `--desde`, `decidir`).

Transcrições inventadas em `tempfile`; os valores esperados foram somados à mão, à parte do código.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, RAIZ, carregar, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
import sc_metricas  # noqa: E402
import sc_sessao  # noqa: E402
from test_ciclo import SC, Base  # noqa: E402

PROJ = '-tmp-projeto-sintetico'
OPUS, SONETO = 'modelo-a', 'modelo-b'


def jsonl(caminho, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text('\n'.join(json.dumps(x) for x in linhas) + '\n', encoding='utf-8')


def msg(id_, modelo, ent, esc, lido, saida, ts='2026-10-03T12:00:00.000Z', **extra):
    return {'type': 'assistant', 'timestamp': ts,
            'message': {'id': id_, 'model': modelo, 'content': [{'type': 'text', 'text': 'x'}],
                        'usage': {'input_tokens': ent, 'cache_creation_input_tokens': esc,
                                  'cache_read_input_tokens': lido, 'output_tokens': saida}}, **extra}


def pedido(texto):
    return {'type': 'user', 'timestamp': '2026-10-03T11:59:00.000Z', 'message': {'role': 'user', 'content': texto}}


def linha(rel, agente, modelo):
    achadas = [x for x in rel['consumo']['por_agente_e_modelo'] if x['agente'] == agente and x['modelo'] == modelo]
    assert len(achadas) == 1, (agente, modelo, rel['consumo'])
    return achadas[0]


class Base_(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.projetos = Path(self._t.name)
        self.sessao = self.projetos / PROJ / 's1.jsonl'
        self.subs = self.projetos / PROJ / 's1' / 'subagents'


class TestSoma(Base_):
    def test_soma_por_agente_e_modelo_com_oraculo_a_mao(self):
        jsonl(self.sessao, [
            pedido('abra a etapa'),
            msg('m1', OPUS, 10, 100, 1000, 5),
            msg('m2', OPUS, 20, 200, 2000, 7),
            msg('m3', SONETO, 1, 2, 3, 4),
        ])
        jsonl(self.subs / 'agent-a1.jsonl', [pedido('Para: Gandalf (coordenador) · faça'), msg('g1', OPUS, 100, 0, 5000, 50)])
        (self.subs / 'agent-a1.meta.json').write_text(json.dumps({'agentType': 'gandalf', 'description': 'x'}), encoding='utf-8')
        jsonl(self.subs / 'agent-a2.jsonl', [pedido('Para: Elrond · fatia'), msg('e1', SONETO, 7, 8, 9, 10), msg('e2', SONETO, 1, 1, 1, 1)])
        r = sc_sessao.medir('claude', sessao='s1', projetos=str(self.projetos))
        c = r['consumo']
        self.assertEqual({k: linha(r, 'principal', OPUS)[k] for k in ('entrada', 'cache_escrito', 'cache_lido', 'saida')},
                         {'entrada': 30, 'cache_escrito': 300, 'cache_lido': 3000, 'saida': 12})
        self.assertEqual(linha(r, 'principal', SONETO)['cache_lido'], 3)
        self.assertEqual(linha(r, 'gandalf', OPUS)['cache_lido'], 5000)
        self.assertEqual(linha(r, 'elrond', SONETO)['entrada'], 8)
        self.assertEqual(linha(r, 'elrond', SONETO)['mensagens'], 2)
        self.assertEqual(c['total'], {'mensagens': 6, 'entrada': 139, 'cache_escrito': 311, 'cache_lido': 8013, 'saida': 77})
        self.assertEqual(sum(x['cache_lido'] for x in c['por_agente_e_modelo']), c['total']['cache_lido'])

    def test_ignora_sintetico_e_registro_sem_uso(self):
        jsonl(self.sessao, [
            msg('m1', OPUS, 1, 1, 1, 1),
            msg('m2', '<synthetic>', 99, 99, 99, 99),
            {'type': 'assistant', 'message': {'id': 'm3', 'model': OPUS, 'content': []}},
            {'type': 'user', 'message': {'usage': {'input_tokens': 500}}},
        ])
        t = sc_sessao.medir('claude', log=str(self.sessao))['consumo']['total']
        self.assertEqual((t['mensagens'], t['entrada'], t['saida']), (1, 1, 1))

    def test_nome_do_agente_pelo_pedido_sem_meta_e_sem_nada(self):
        jsonl(self.sessao, [msg('m0', OPUS, 1, 0, 0, 1)])
        jsonl(self.subs / 'agent-b1.jsonl', [pedido('Para: Galadriel (métodos) · revise'), msg('b1', OPUS, 2, 0, 0, 2)])
        jsonl(self.subs / 'agent-b2.jsonl', [pedido('só uma conversa solta'), msg('b2', OPUS, 3, 0, 0, 3)])
        r = sc_sessao.medir('claude', log=str(self.sessao))
        self.assertEqual(linha(r, 'galadriel', OPUS)['entrada'], 2)
        self.assertEqual(linha(r, 'agent-b2', OPUS)['entrada'], 3)

    def test_meta_vence_o_pedido_e_agentes_do_mesmo_tipo_somam(self):
        jsonl(self.sessao, [msg('m0', OPUS, 1, 0, 0, 1)])
        jsonl(self.subs / 'agent-c1.jsonl', [pedido('Para: Elrond · x'), msg('c1', OPUS, 5, 0, 0, 1)])
        (self.subs / 'agent-c1.meta.json').write_text(json.dumps({'agentType': 'Gandalf'}), encoding='utf-8')
        jsonl(self.subs / 'agent-c2.jsonl', [pedido('Para: Gandalf · y'), msg('c2', OPUS, 6, 0, 0, 1)])
        r = sc_sessao.medir('claude', log=str(self.sessao))
        self.assertEqual(linha(r, 'gandalf', OPUS)['entrada'], 11)
        self.assertEqual(linha(r, 'gandalf', OPUS)['mensagens'], 2)

    def test_agente_novo_continua_separado_de_modelo_diferente_no_mesmo_agente(self):
        jsonl(self.sessao, [msg('m1', OPUS, 1, 0, 0, 1), msg('m2', SONETO, 2, 0, 0, 1)])
        r = sc_sessao.medir('claude', log=str(self.sessao))
        self.assertEqual(len(r['consumo']['por_agente_e_modelo']), 2)


class TestDeduplicacao(Base_):
    def test_mesmo_id_em_varios_blocos_conta_uma_vez(self):
        jsonl(self.sessao, [msg('m1', OPUS, 10, 20, 30, 40), msg('m1', OPUS, 10, 20, 30, 40), msg('m1', OPUS, 10, 20, 30, 40)])
        t = sc_sessao.medir('claude', log=str(self.sessao))['consumo']['total']
        self.assertEqual(t, {'mensagens': 1, 'entrada': 10, 'cache_escrito': 20, 'cache_lido': 30, 'saida': 40})

    def test_valores_divergentes_ficam_com_a_maior_saida(self):
        jsonl(self.sessao, [msg('m1', OPUS, 10, 20, 30, 5), msg('m1', OPUS, 11, 21, 31, 90), msg('m1', OPUS, 12, 22, 32, 40)])
        t = sc_sessao.medir('claude', log=str(self.sessao))['consumo']['total']
        self.assertEqual((t['entrada'], t['cache_lido'], t['saida']), (11, 31, 90))

    def test_mesmo_id_no_principal_e_no_subagente_conta_uma_vez(self):
        jsonl(self.sessao, [msg('dup', OPUS, 1, 1, 1, 10), msg('m2', OPUS, 2, 2, 2, 2)])
        jsonl(self.subs / 'agent-d1.jsonl', [pedido('Para: Elrond · x'), msg('dup', OPUS, 1, 1, 1, 10)])
        r = sc_sessao.medir('claude', log=str(self.sessao))
        self.assertEqual(r['consumo']['total']['mensagens'], 2)
        self.assertEqual(r['consumo']['total']['entrada'], 3)

    def test_mensagens_sem_id_nao_se_fundem(self):
        sem_id = msg(None, OPUS, 1, 0, 0, 1)
        sem_id['message'].pop('id')
        jsonl(self.sessao, [sem_id, sem_id])
        self.assertEqual(sc_sessao.medir('claude', log=str(self.sessao))['consumo']['total']['mensagens'], 2)


class TestDesde(Base_):
    def setUp(self):
        super().setUp()
        jsonl(self.sessao, [
            msg('a', OPUS, 1, 0, 100, 1, ts='2026-10-03T10:00:00.000Z'),
            msg('b', OPUS, 2, 0, 200, 1, ts='2026-10-03T12:00:00.000Z'),
            msg('c', OPUS, 4, 0, 400, 1, ts='2026-10-03T14:00:00.000Z'),
        ])
        jsonl(self.subs / 'agent-e1.jsonl', [pedido('Para: Elrond · x'), msg('d', OPUS, 8, 0, 800, 1, ts='2026-10-03T09:00:00.000Z'),
                                             msg('e', OPUS, 16, 0, 1600, 1, ts='2026-10-03T13:00:00.000Z')])

    def lido(self, desde):
        return sc_sessao.medir('claude', log=str(self.sessao), desde=desde)['consumo']['total']['cache_lido']

    def test_sem_desde_soma_tudo(self):
        self.assertEqual(self.lido(None), 100 + 200 + 400 + 800 + 1600)

    def test_desde_com_z_descarta_o_anterior_e_inclui_o_igual(self):
        self.assertEqual(self.lido('2026-10-03T12:00:00Z'), 200 + 400 + 1600)

    def test_desde_com_offset(self):
        # 10:00-03:00 = 13:00Z: ficam c (14h) e e (13h)
        self.assertEqual(self.lido('2026-10-03T10:00:00-03:00'), 400 + 1600)

    def test_desde_sem_fuso_vale_utc(self):
        self.assertEqual(self.lido('2026-10-03T13:30:00'), 400)

    def test_desde_depois_de_tudo_zera(self):
        r = sc_sessao.medir('claude', log=str(self.sessao), desde='2027-01-01T00:00:00Z')
        self.assertEqual(r['consumo']['total']['mensagens'], 0)

    def test_desde_invalido_e_erro_claro(self):
        with self.assertRaisesRegex(sc_sessao.ErroSessao, '--desde inválido'):
            self.lido('ontem')

    def test_desde_pela_linha_de_comando(self):
        r = rodar(SC, 'sessao', 'claude', '--log', self.sessao, '--desde', '2026-10-03T13:00:00Z', '--json')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['consumo']['total']['cache_lido'], 400 + 1600)
        ruim = rodar(SC, 'sessao', 'claude', '--log', self.sessao, '--desde', 'ontem')
        self.assertEqual(ruim.returncode, 1)
        self.assertIn('--desde inválido', ruim.stderr)

    def test_desde_so_vale_para_claude(self):
        r = rodar(SC, 'sessao', 'codex', '--pasta', self._t.name, '--desde', '2026-10-03T13:00:00Z')
        self.assertEqual(r.returncode, 1)
        self.assertIn('só vale para o Claude Code', r.stderr)


class TestSaida(Base_):
    def test_tabela_curta_com_total(self):
        jsonl(self.sessao, [msg('m1', OPUS, 1500, 2, 3000000, 4)])
        r = rodar(SC, 'sessao', 'claude', '--log', self.sessao)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('consumo:', r.stdout)
        self.assertIn('principal', r.stdout)
        self.assertIn('3.000.000', r.stdout)
        self.assertRegex(r.stdout, r'total\s+1\.500\s+2\s+3\.000\.000\s+4')

    def test_log_ausente_e_erro_claro_e_nao_zero(self):
        r = rodar(SC, 'sessao', 'claude', '--log', self.projetos / 'nao-existe.jsonl')
        self.assertEqual(r.returncode, 1)
        self.assertIn('Log ausente ou ilegível', r.stderr)
        self.assertNotIn('consumo', r.stdout)


class TestMetricasEEvolucao(Base_):
    def test_consumo_tolerante_sem_log_ou_ilegivel_e_none(self):
        self.assertIsNone(sc_sessao.consumo_tolerante([]))
        self.assertIsNone(sc_sessao.consumo_tolerante([self.projetos / 'fantasma.jsonl']))
        ruim = self.projetos / 'ruim.jsonl'
        ruim.write_text('isto não é json\n', encoding='utf-8')
        self.assertIsNone(sc_sessao.consumo_tolerante([ruim]))
        sem_uso = self.projetos / 'sem-uso.jsonl'
        jsonl(sem_uso, [pedido('oi')])
        self.assertIsNone(sc_sessao.consumo_tolerante([sem_uso]))

    def test_coluna_nova_antes_da_meta_e_inteiro_puro(self):
        cols = sc_metricas.COLUNAS
        self.assertEqual(cols[-2:], ('Consumo (cache lido)', 'Dentro da meta?'))
        jsonl(self.sessao, [msg('m1', OPUS, 1, 1, 1234567, 1)])
        reg = _registro_com_etapa(self._t.name)
        m = sc_metricas.medir_etapa(reg.dados, 'etapa-x', [self.sessao], versao_metodo='3.0.0')
        self.assertEqual(m['valores']['Consumo (cache lido)'], 1234567)
        self.assertEqual(sc_metricas.linha_evolucao(m).split('|')[-3].strip(), '1234567')
        sem = sc_metricas.medir_etapa(reg.dados, 'etapa-x', [], versao_metodo='3.0.0')
        self.assertEqual(sc_metricas.linha_evolucao(sem).split('|')[-3].strip(), 'n/d')

    def test_migra_evolucao_antiga_e_acrescenta_na_tabela(self):
        cols = sc_metricas.COLUNAS
        antigas = [c for c in cols if c != 'Consumo (cache lido)']
        md = self.projetos / 'evolucao.md'
        md.write_text('# Evolução\n\n| ' + ' | '.join(antigas) + ' |\n|' + '---|' * len(antigas) + '\n'
                      + '| a1 | 3.0.0 | ' + ' | '.join(['0'] * (len(antigas) - 3)) + ' | não |\n\n## Notas\ntexto livre\n', encoding='utf-8')
        nova = '| b2 | 3.0.0 | ' + ' | '.join(['1'] * (len(cols) - 4)) + ' | 77 | sim |'
        sc_metricas.acrescentar_linha(md, nova)
        linhas = md.read_text(encoding='utf-8').splitlines()
        tabela = [l for l in linhas if l.startswith('|')]
        self.assertEqual(len(tabela), 4)
        self.assertEqual({len(l.strip('|').split('|')) for l in tabela}, {len(cols)})
        self.assertIn('Consumo (cache lido) | Dentro da meta?', tabela[0])
        self.assertEqual(tabela[1], '|' + '---|' * len(cols))
        self.assertTrue(tabela[2].endswith('| n/d | não |'), tabela[2])
        self.assertEqual(tabela[3], nova)
        self.assertLess(linhas.index(nova), linhas.index('## Notas'))  # entra na tabela, não no fim do arquivo
        self.assertEqual(linhas[-1], 'texto livre')

    def test_migracao_nao_repete_em_tabela_ja_nova(self):
        cols = sc_metricas.COLUNAS
        md = self.projetos / 'evolucao.md'
        md.write_text('| ' + ' | '.join(cols) + ' |\n|' + '---|' * len(cols) + '\n', encoding='utf-8')
        sc_metricas.acrescentar_linha(md, '| a | ' + ' | '.join(['0'] * (len(cols) - 1)) + ' |')
        self.assertEqual(md.read_text(encoding='utf-8').count('Consumo (cache lido)'), 1)


class TestValidadorDeMedicao(unittest.TestCase):
    """O validador do pacote aceita medir pelo log e continua recusando estimar."""

    @classmethod
    def setUpClass(cls):
        cls.v = carregar(RAIZ / 'scripts' / 'validar_pacote.py', 'validar_pacote_medicao')

    def test_medir_pelo_log_passa(self):
        for frase in ('Medir o consumo pelo log do aplicativo.', 'Medir tokens a partir dos logs é permitido.',
                      'O script mede o gasto na transcrição.'):
            self.assertFalse(self.v.instrucao_de_medir(frase), frase)

    def test_estimar_continua_recusado_mesmo_com_log(self):
        for frase in ('Estime o consumo de tokens.', 'Estime o consumo pelo log.', 'Calcule o custo a partir do log.',
                      'Relate o gasto em tokens do log.', 'Medir os tokens da sessão.'):
            self.assertTrue(self.v.instrucao_de_medir(frase), frase)

    def test_proibicao_na_mesma_linha_continua_valendo(self):
        self.assertFalse(self.v.instrucao_de_medir('Nunca estime o consumo.'))
        self.assertFalse(self.v.instrucao_de_medir('Medir o consumo pelo log é permitido; estimar é proibido.'))

    def test_pacote_atual_passa(self):
        r = rodar(RAIZ / 'scripts' / 'validar_pacote.py')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


def _registro_com_etapa(tmp):
    from sc_registro import Registro
    reg = Registro.inicializar(Path(tmp) / 'sociedade', 'projeto-teste', tmp)
    reg.abrir_etapa('etapa-x', 'objetivo', 'plano', 'aut', 'abc1234', ['C1'])
    return reg


class TestDecidirGravaConsumo(Base):
    def projetos_com_log(self):
        projetos = Path(self._tmp.name) / 'projetos'
        log = projetos / PROJ / 'sess.jsonl'
        jsonl(log, [msg('m1', OPUS, 10, 20, 300, 4, ts='2026-10-03T10:00:00Z'),
                    msg('m2', OPUS, 1, 2, 30, 4, ts='2026-10-03T15:00:00Z')])
        jsonl(projetos / PROJ / 'sess' / 'subagents' / 'agent-x1.jsonl', [pedido('Para: Elrond · x'), msg('m3', SONETO, 5, 6, 70, 8, ts='2026-10-03T16:00:00Z')])
        return log

    def aceitar_com(self, *extra):
        self.ok(self.p.abrir())
        self.ok(self.p.entregar())
        self.ok(self.p.revisar(self.parecer()))
        return self.ok(self.p.decidir('aceitar', '--por', 'Odival Sintético', *extra))

    def test_aceitar_grava_consumo_no_evento_e_na_evolucao(self):
        log = self.projetos_com_log()
        self.aceitar_com('--log', log)
        decisao = [d for d in self.p.eventos('decisao_registrada') if d['acao'] == 'aceitar'][0]
        c = decisao['consumo']
        self.assertEqual(c['total'], {'mensagens': 3, 'entrada': 16, 'cache_escrito': 28, 'cache_lido': 400, 'saida': 16})
        self.assertEqual(c['logs'], 1)
        self.assertIsNone(c['desde'])
        self.assertEqual({(x['agente'], x['modelo']) for x in c['por_agente_e_modelo']},
                         {('principal', OPUS), ('elrond', SONETO)})
        linha = [l for l in (self.p.soc / 'evolucao.md').read_text(encoding='utf-8').splitlines() if l.startswith('| soma |')][0]
        self.assertEqual(linha.split('|')[-3].strip(), '400')

    def test_desde_do_decidir_vai_para_o_evento_e_a_coluna(self):
        log = self.projetos_com_log()
        self.aceitar_com('--log', log, '--desde', '2026-10-03T14:00:00Z')
        c = [d for d in self.p.eventos('decisao_registrada') if d['acao'] == 'aceitar'][0]['consumo']
        self.assertEqual(c['total']['cache_lido'], 100)
        self.assertEqual(c['desde'], '2026-10-03T14:00:00+00:00')

    def test_sem_log_a_coluna_e_nd_e_nao_quebra(self):
        self.aceitar_com()
        decisao = [d for d in self.p.eventos('decisao_registrada') if d['acao'] == 'aceitar'][0]
        self.assertNotIn('consumo', decisao)
        linha = [l for l in (self.p.soc / 'evolucao.md').read_text(encoding='utf-8').splitlines() if l.startswith('| soma |')][0]
        self.assertEqual(linha.split('|')[-3].strip(), 'n/d')

    def test_desde_invalido_recusa_antes_de_decidir(self):
        self.ok(self.p.abrir())
        self.ok(self.p.entregar())
        self.ok(self.p.revisar(self.parecer()))
        r = self.p.decidir('aceitar', '--por', 'Odival Sintético', '--desde', 'ontem')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('--desde inválido', r.stderr)
        self.assertEqual([d for d in self.p.eventos('decisao_registrada') if d['acao'] == 'aceitar'], [])


if __name__ == '__main__':
    unittest.main()
