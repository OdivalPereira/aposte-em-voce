"""B10: métricas por etapa e linha de evolucao.md. Registro e transcrições sintéticos."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
import sc_metricas  # noqa: E402
import sc_sessao  # noqa: E402
from sc_registro import Registro  # noqa: E402

ETAPA = 'etapa-x'
CABECALHO = '| ' + ' | '.join(sc_metricas.COLUNAS) + ' |'


def bash(id_, comando):
    return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': id_, 'name': 'Bash', 'input': {'command': comando}}]}}


def ferramenta(id_, nome, caminho):
    return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': id_, 'name': nome, 'input': {'file_path': caminho}}]}}


def retorno(id_, texto='ok', erro=False):
    b = {'type': 'tool_result', 'tool_use_id': id_, 'content': texto}
    if erro:
        b['is_error'] = True
    return {'type': 'user', 'message': {'content': [b]}}


def jsonl(caminho, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text('\n'.join(json.dumps(x) for x in linhas) + '\n', encoding='utf-8')


class TestMedirLog(unittest.TestCase):
    def test_comandos_do_metodo_erros_e_edicoes(self):
        linhas = [
            bash('1', 'python3 -B sociedade-do-codigo/plugins/x/scripts/sc.py abrir --etapa a'), retorno('1'),
            bash('2', 'python3 sc.py entregar --etapa a'), retorno('2', 'Exit code 1\nfalhou'),
            bash('3', 'git status'), retorno('3'),
            bash('4', 'python3 sc.py revisar --etapa a'), retorno('4', 'falha', erro=True),
            bash('5', 'sc.py estado'), retorno('5', [{'type': 'text', 'text': 'Exit code 0'}]),
            ferramenta('6', 'Edit', '/r/sociedade/registro.json'),
            ferramenta('7', 'Write', '/r/sociedade/estado.md'),
            ferramenta('8', 'Write', '/r/sociedade/pareceres/atestado-a.json'),
            ferramenta('9', 'Edit', '/r/sociedade/ordens/a.md'),
            ferramenta('10', 'Edit', '/r/src/app.py'),
            bash('11', "echo '{}' > sociedade/registro.json"),
            bash('12', "sed -i 's/a/b/' sociedade/rodada.md"),
            bash('13', 'cat sociedade/registro.json > /tmp/copia.json'),
        ]
        m = sc_metricas.medir_log(linhas)
        self.assertEqual(m['comandos'], ['abrir', 'entregar', 'revisar', 'estado'])
        self.assertEqual(m['erros'], ['entregar', 'revisar'])
        self.assertEqual(len(m['edicoes_manuais']), 5, m['edicoes_manuais'])
        self.assertTrue(all('src/app.py' not in e and 'ordens' not in e and '/tmp' not in e for e in m['edicoes_manuais']))

    def test_arquivos_de_controle(self):
        for ok in ('sociedade/registro.json', '/r/sociedade/estado.md', 'sociedade/evolucao.md', 'sociedade/rodada.md',
                   'sociedade/historico.md', 'sociedade/pareceres/atestado-x.json'):
            self.assertTrue(sc_metricas.eh_arquivo_de_controle(ok), ok)
        for nao in ('sociedade/ordens/x.md', 'sociedade/pareceres/parecer-x.md', 'docs/estado.md', 'src/registro.json'):
            self.assertFalse(sc_metricas.eh_arquivo_de_controle(nao), nao)

    def test_log_ausente_ou_ilegivel_falha_fechada(self):
        with tempfile.TemporaryDirectory() as t:
            ruim = Path(t) / 'ruim.jsonl'
            ruim.write_text('{nao', encoding='utf-8')
            for log in (Path(t) / 'fantasma.jsonl', ruim):
                with self.assertRaises(sc_sessao.ErroSessao):
                    sc_metricas.medir_logs([log])

    def test_soma_os_subagentes_da_sessao(self):
        with tempfile.TemporaryDirectory() as t:
            sessao = Path(t) / 's.jsonl'
            jsonl(sessao, [bash('1', 'sc.py abrir'), retorno('1')])
            jsonl(Path(t) / 's' / 'subagents' / 'agent-a.jsonl', [bash('1', 'sc.py entregar'), retorno('1', 'Exit code 2')])
            com = sc_metricas.medir_logs([sessao])
            sem = sc_metricas.medir_logs([sessao], incluir_subagentes=False)
        self.assertEqual((com['comandos'], com['erros']), (['abrir', 'entregar'], ['entregar']))
        self.assertEqual(sem['comandos'], ['abrir'])


class TestRegistro(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pasta = Path(self._tmp.name) / 'sociedade'
        self.reg = Registro.inicializar(self.pasta, 'projeto-teste', self._tmp.name)
        self.reg.abrir_etapa(ETAPA, 'objetivo', 'plano', 'aut', 'abc1234', ['C1'])

    def test_contagens_do_registro(self):
        self.reg.registrar_achado(ETAPA, 'A1', 'bloqueador', 'x.py', 'descricao', 'Revisor')
        self.reg.registrar_achado(ETAPA, 'A2', 'bloqueador', 'y.py', 'descricao', 'Revisor')
        self.reg.registrar_achado(ETAPA, 'A3', 'relevante', 'z.py', 'descricao', 'Revisor')
        self.reg.registrar_troca_papel('Barbárvore', 'claude', 'Anthropic', motivo='emulação')
        self.reg.registrar_aviso_cota('Odival', 80, 'semana', '2026-10-03')
        r = sc_metricas.medir_registro(self.reg.dados, ETAPA)
        self.assertEqual(r, {'revisoes': 0, 'bloqueadores': 2, 'trocas_de_papel': 1, 'eventos_de_cota': 1})

    def test_etapa_inexistente(self):
        with self.assertRaises(ValueError):
            sc_metricas.medir_registro(self.reg.dados, 'nao-existe')

    def test_nao_conta_achado_de_outra_etapa(self):
        dados = json.loads(json.dumps(self.reg.dados))
        dados['eventos'].append({'tipo': 'achado_registrado', 'timestamp': '2999-01-01T00:00:00+00:00',
                                 'dados': {'etapa_id': 'outra', 'severidade': 'bloqueador'}})
        self.assertEqual(sc_metricas.medir_registro(dados, ETAPA)['bloqueadores'], 0)

    def test_linha_completa_no_formato_da_tabela(self):
        self.reg.registrar_achado(ETAPA, 'A1', 'bloqueador', 'x.py', 'descricao', 'Revisor')
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / 's.jsonl'
            jsonl(log, [bash('1', 'sc.py abrir'), retorno('1'), bash('2', 'sc.py decidir'), retorno('2', 'Exit code 1')])
            m = sc_metricas.medir_etapa(self.reg.dados, ETAPA, [log], intervencoes=2, minutos_odival=15,
                                        escaparam_ao_aceite=0, versao_metodo='3.0.0')
        linha = sc_metricas.linha_evolucao(m)
        self.assertEqual(linha, f'| {ETAPA} | 3.0.0 | 0 | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 2 | 15 | n/d | sim |')
        self.assertEqual(len(linha.strip('|').split('|')), len(sc_metricas.COLUNAS))

    def test_sem_parametros_de_odival_vira_nd_e_nao_estima(self):
        m = sc_metricas.medir_etapa(self.reg.dados, ETAPA, [], versao_metodo='3.0.0')
        v = m['valores']
        for c in ('Escaparam ao aceite', 'Comandos', 'Erros', 'Edições manuais', 'Intervenções', 'Minutos de Odival'):
            self.assertIsNone(v[c], c)
        self.assertEqual(v['Dentro da meta?'], 'n/d')
        self.assertTrue(sc_metricas.linha_evolucao(m).endswith('| 0 | 0 | n/d | n/d | n/d | n/d | n/d | n/d | n/d |'))

    def test_meta_estourada(self):
        base = dict(versao_metodo='3.0.0', escaparam_ao_aceite=0)
        casos = {'comandos': dict(minutos_odival=1, intervencoes=1),
                 'minutos': dict(minutos_odival=31, intervencoes=1),
                 'intervencoes': dict(minutos_odival=1, intervencoes=6)}
        with tempfile.TemporaryDirectory() as t:
            ok = Path(t) / 'ok.jsonl'
            jsonl(ok, [bash(str(i), f'sc.py estado{i}') for i in range(13)])  # 13 comandos > 12
            r = sc_metricas.medir_etapa(self.reg.dados, ETAPA, [ok], **base, **casos['comandos'])
            self.assertEqual(r['valores']['Dentro da meta?'], 'não')
            limpo = Path(t) / 'limpo.jsonl'
            jsonl(limpo, [bash('1', 'sc.py abrir')])
            for nome in ('minutos', 'intervencoes'):
                r = sc_metricas.medir_etapa(self.reg.dados, ETAPA, [limpo], **base, **casos[nome])
                self.assertEqual(r['valores']['Dentro da meta?'], 'não', nome)
            jsonl(limpo, [bash('1', 'sc.py abrir'), ferramenta('2', 'Edit', 'sociedade/estado.md')])
            r = sc_metricas.medir_etapa(self.reg.dados, ETAPA, [limpo], **base, minutos_odival=1, intervencoes=1)
            self.assertEqual(r['valores']['Dentro da meta?'], 'não')  # 1 edição manual > 0

    def test_nada_de_consumo_na_linha(self):
        m = sc_metricas.medir_etapa(self.reg.dados, ETAPA, [], versao_metodo='3.0.0')
        texto = json.dumps(m, ensure_ascii=False).lower()
        for proibido in ('token', 'custo', 'cota_percentual', 'us$'):
            self.assertNotIn(proibido, texto.replace('eventos de cota', ''))

    def test_versao_do_metodo_vem_do_manifesto(self):
        self.assertRegex(sc_metricas.versao_do_metodo(), r'^\d+\.\d+\.\d+$')


class TestEvolucaoMd(unittest.TestCase):
    def test_acrescenta_uma_vez_por_etapa(self):
        with tempfile.TemporaryDirectory() as t:
            md = Path(t) / 'evolucao.md'
            md.write_text(f'# Evolução\n\n{CABECALHO}\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n', encoding='utf-8')
            linha = '| etapa-x | 3.0.0 | 1 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 1 | 10 | sim |'
            sc_metricas.acrescentar_linha(md, linha)
            texto = md.read_text(encoding='utf-8')
            self.assertTrue(texto.endswith(linha + '\n'))
            with self.assertRaises(ValueError):
                sc_metricas.acrescentar_linha(md, linha)
            sc_metricas.acrescentar_linha(md, linha.replace('etapa-x', 'etapa-y'))
            self.assertEqual(md.read_text(encoding='utf-8').count('\n| etapa-'), 2)

    def test_cabecalho_igual_ao_da_tabela_do_projeto(self):
        real = Path(__file__).resolve().parents[2] / 'sociedade' / 'evolucao.md'
        if not real.is_file():
            self.skipTest('sem sociedade/evolucao.md do projeto')
        texto = real.read_text(encoding='utf-8')
        if '| Comandos |' not in texto:
            self.skipTest('evolucao.md do projeto ainda no formato anterior à B10')
        antigo = CABECALHO.replace(' Consumo (cache lido) |', '')  # tabela ainda sem a coluna: o próximo `decidir` a migra
        self.assertTrue(CABECALHO in texto or antigo in texto)


class TestCLI(unittest.TestCase):
    def test_imprime_e_grava_a_linha(self):
        with tempfile.TemporaryDirectory() as t:
            pasta = Path(t) / 'sociedade'
            reg = Registro.inicializar(pasta, 'projeto-teste', t)
            reg.abrir_etapa(ETAPA, 'objetivo', 'plano', 'aut', 'abc1234', ['C1'])
            (pasta / 'evolucao.md').write_text(f'{CABECALHO}\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n', encoding='utf-8')
            r = rodar(NUCLEO / 'scripts' / 'sc_metricas.py', '--etapa', ETAPA, '--pasta-sociedade', pasta,
                      '--intervencoes', '1', '--minutos', '5', '--escaparam', '0', '--versao-metodo', '3.0.0', '--gravar')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(f'| {ETAPA} | 3.0.0 |', r.stdout)
            self.assertIn(r.stdout.strip(), (pasta / 'evolucao.md').read_text(encoding='utf-8'))

    def test_etapa_inexistente_sai_com_erro(self):
        with tempfile.TemporaryDirectory() as t:
            pasta = Path(t) / 'sociedade'
            Registro.inicializar(pasta, 'projeto-teste', t)
            r = rodar(NUCLEO / 'scripts' / 'sc_metricas.py', '--etapa', 'nada', '--pasta-sociedade', pasta)
            self.assertEqual(r.returncode, 1)
            self.assertIn('erro:', r.stderr)

    def test_registro_inexistente_sai_com_erro(self):
        with tempfile.TemporaryDirectory() as t:
            r = rodar(NUCLEO / 'scripts' / 'sc_metricas.py', '--etapa', 'nada', '--pasta-sociedade', Path(t))
            self.assertEqual(r.returncode, 1)


if __name__ == '__main__':
    unittest.main()
