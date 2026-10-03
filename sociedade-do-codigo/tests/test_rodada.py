import sys
import tempfile
import unittest
from pathlib import Path

from util import NUCLEO, rodar

sys.path.insert(0, str(NUCLEO / 'scripts'))
from adversarial._cenario import parecer_texto  # noqa: E402
from sc_registro import Registro  # noqa: E402

RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'
MODELO = NUCLEO / 'assets' / 'rodada-modelo.md'


class TesteRodada(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.p = Path(self._tmp.name)
        self.arq = self.p / 'sociedade' / 'rodada.md'
        self.hist = self.p / 'sociedade' / 'historico.md'
        (self.p / 'sociedade').mkdir()  # B15: o fornecedor do implementador vem do perfil, não de argumento
        (self.p / 'sociedade' / 'perfil.md').write_text(
            '# Perfil sintético\n\n## Papel × ferramenta\n'
            '| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |\n'
            '|---|---|---|---|---|---|---|---|---|\n'
            '| Coordenador | Gandalf | Antigravity | Google | Modelo G | high | ativo | 2026-10-03 | teste |\n', encoding='utf-8')

    def sc(self, *args, aplicar=True):
        extra = ['--aplicar'] if aplicar else []
        return rodar(RODADA, *args, '--pasta', str(self.p / 'sociedade'), *extra)

    def abrir(self, **kw):
        args = ['abrir', '--id', kw.get('id', 'R-01'), '--meta', kw.get('meta', 'fazer X'),
                '--nivel', kw.get('nivel', '2'), '--base', 'main@a1b2c3d',
                '--bastao', 'Gandalf (Antigravity)', '--limites', 'não tocar em migrações',
                '--aceite', 'X existe e passa no teste']
        for f in kw.get('fatias', ['primeira', 'segunda']):
            args += ['--fatia', f]
        return self.sc(*args)

    def texto(self):
        return self.arq.read_text(encoding='utf-8')

    def parecer(self, veredito='aceitar', etapa='R-01', nivel='Nível A (fornecedor diferente)', *args):
        """B15: o parecer vem de um arquivo (com lint); revisor, fornecedor e veredito saem dele."""
        arq = self.p / 'parecer-sintetico.md'
        arq.write_text(parecer_texto('a1b2c3d', 'a1b2c3d', veredito=veredito, nivel=nivel, etapa=etapa,
                                     revisor='Claude (revisor externo)', fornecedor='Anthropic'), encoding='utf-8')
        return self.sc('parecer', '--arquivo', str(arq), '--versao', 'main@a1b2c3d', *args)

    def decidir(self, etapa='R-01'):
        """B15: o `encerrar` exige o evento da decisão de uma pessoa; aqui o registro a grava (sem passar pelo `sc.py decidir`)."""
        Registro(self.p / 'sociedade').registrar_decisao(etapa, f'DEC-{etapa}-1', 'Odival Sintético', 'teste', 'aceitar',
                                                         autor='Odival Sintético')

    # ---------- abertura ----------

    def test_simulacao_nao_grava(self):
        r = self.sc('abrir', '--id', 'R-01', '--meta', 'fazer X', '--nivel', '2', aplicar=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('simulação', r.stdout)
        self.assertFalse(self.arq.exists())

    def test_abre_e_registra_no_historico(self):
        r = self.abrir()
        self.assertEqual(r.returncode, 0, r.stderr)
        t = self.texto()
        self.assertTrue(t.startswith('# Rodada R-01 — fazer X'))
        self.assertIn('nivel: 2', t)
        self.assertIn('base: main@a1b2c3d', t)
        self.assertIn('1. primeira — pendente', t)
        self.assertIn('rodada R-01 · abertura', self.hist.read_text(encoding='utf-8'))

    def test_uma_rodada_por_vez(self):
        self.abrir()
        r = self.sc('abrir', '--id', 'R-02', '--meta', 'outra', '--nivel', '1')
        self.assertEqual(r.returncode, 1)
        self.assertIn('uma rodada por vez', r.stderr)

    def test_nivel_0_nao_abre_rodada(self):
        r = self.sc('abrir', '--id', 'R-01', '--meta', 'x', '--nivel', '0')
        self.assertEqual(r.returncode, 1)
        self.assertIn('nível inválido', r.stderr)

    def test_abrir_sem_nivel_usa_padrao_2(self):
        r = self.sc('abrir', '--id', 'R-SEM-NIVEL', '--meta', 'teste padrao')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('nivel: 2', self.texto())

    def test_abrir_nivel_adaptativo(self):
        r = self.sc('abrir', '--id', 'R-ADAPT', '--meta', 'teste adaptativo', '--nivel', 'adaptativo')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('nivel: adaptativo', self.texto())

    # ---------- fatias ----------

    def test_fatia_so_fecha_com_prova(self):
        self.abrir()
        r = self.sc('fatia', '1', '--fechar')
        self.assertEqual(r.returncode, 1)
        self.assertIn('prova', r.stderr)
        r = self.sc('fatia', '1', '--fechar', '--prova', 'pytest -q → 12 ok')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('1. primeira — fechada · prova: pytest -q → 12 ok', self.texto())

    def test_fatia_nao_pula_a_anterior(self):
        self.abrir()
        r = self.sc('fatia', '2', '--fechar', '--prova', 'x')
        self.assertEqual(r.returncode, 1)
        self.assertIn('não fecharam', r.stderr)
        r = self.sc('fatia', '2')
        self.assertEqual(r.returncode, 1)

    def test_forcar_permite_pular_com_motivo(self):
        self.abrir()
        r = self.sc('fatia', '2', '--fechar', '--prova', 'x', '--forcar')
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_acrescentar_fatia(self):
        self.abrir()
        self.sc('fatia', '--add', 'terceira')
        self.assertIn('3. terceira — pendente', self.texto())

    # ---------- bastão ----------

    def test_bastao_troca_e_preenche_o_bloco(self):
        self.abrir()
        r = self.sc('bastao', '--para', 'Revisor (Claude Code)', '--leia', 'src/a.ts',
                    '--faca', 'revisar a fatia 1', '--nao-faca', 'corrigir o código',
                    '--devolva', 'neste arquivo')
        self.assertEqual(r.returncode, 0, r.stderr)
        t = self.texto()
        self.assertIn('bastao: Revisor (Claude Code)', t)
        self.assertIn('- src/a.ts', t)
        self.assertIn('devolva: neste arquivo', t)
        self.assertIn('passou o bastão para Revisor', self.hist.read_text(encoding='utf-8'))

    def test_leia_so_tem_teto(self):
        self.abrir()
        r = self.sc('bastao', '--para', 'X', *sum([['--leia', f'a{i}.ts'] for i in range(6)], []))
        self.assertEqual(r.returncode, 1)
        self.assertIn('no máximo 5', r.stderr)

    def test_leia_so_com_justificativa_permite_expansao(self):
        self.abrir()
        r = self.sc('bastao', '--para', 'X',
                    '--justificativa-expansao', 'necessidade de verificar 7 schemas relacionados',
                    *sum([['--leia', f'schema_{i}.json'] for i in range(7)], []))
        self.assertEqual(r.returncode, 0, r.stderr)
        t = self.texto()
        self.assertIn('expansão justificada: necessidade de verificar 7 schemas relacionados', t)
        self.assertIn('- schema_6.json', t)
        # Lint não deve falhar
        r_lint = self.sc('lint')
        self.assertEqual(r_lint.returncode, 0, r_lint.stderr)

    # ---------- autorização e achados ----------

    def test_autorizacao_fica_escrita_com_data(self):
        self.abrir()
        self.sc('autorizar', 'integrar quando a revisão fechar', '--quem', 'Odival')
        t = self.texto()
        self.assertIn('integrar quando a revisão fechar (Odival,', t)
        self.assertNotIn('nenhuma ainda', t)

    def test_achado_bloqueador_impede_encerrar(self):
        self.abrir(fatias=['unica'])
        self.sc('fatia', '1', '--fechar', '--prova', 'ok')
        self.sc('achado', '--severidade', 'bloqueador', '--onde', 'src/a.ts:1', '--texto', 'quebra no mobile')
        self.parecer()
        r = self.sc('encerrar')
        self.assertEqual(r.returncode, 1)
        self.assertIn('bloqueador', r.stderr)
        self.sc('achado', '--fechar', 'REV-001', '--estado', 'corrigido')
        self.decidir()
        r = self.sc('encerrar', '--resumo', 'pronto')
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_severidade_invalida(self):
        self.abrir()
        r = self.sc('achado', '--severidade', 'gravissimo', '--texto', 'x')
        self.assertEqual(r.returncode, 1)

    # ---------- encerramento ----------

    def test_encerrar_limpa_o_estado_e_abre_avaliacao(self):
        self.abrir(fatias=['unica'])
        self.sc('fatia', '1', '--fechar', '--prova', 'ok')
        self.parecer()
        self.decidir()
        r = self.sc('encerrar', '--resumo', 'entregue')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.arq.exists())
        aval = (self.p / 'sociedade' / 'avaliacao.md').read_text(encoding='utf-8')
        self.assertIn('deu certo', aval)
        self.assertIn('cota usada (preenchido pelo usuário)', aval)  # medição é manual, nunca do agente
        self.assertIn('encerramento', self.hist.read_text(encoding='utf-8'))

    def test_fatia_aberta_impede_encerrar(self):
        self.abrir()
        r = self.sc('encerrar')
        self.assertEqual(r.returncode, 1)
        self.assertIn('não fechadas', r.stderr)

    # ---------- lint ----------

    def test_lint_sem_rodada_e_valido(self):
        r = self.sc('lint')
        self.assertEqual(r.returncode, 0)
        self.assertIn('calada', r.stdout)

    def test_lint_aprova_rodada_recem_aberta(self):
        self.abrir()
        r = self.sc('lint')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_lint_pega_teto_estourado(self):
        self.abrir()
        self.arq.write_text(self.texto() + '\n' + 'x' * 7000, encoding='utf-8')
        r = self.sc('lint')
        self.assertEqual(r.returncode, 1)
        self.assertIn('acima do teto', r.stdout)

    def test_lint_pega_medicao_de_consumo(self):
        self.abrir()
        self.arq.write_text(self.texto() + '\n- nota: gastei bastante da cota aqui\n', encoding='utf-8')
        r = self.sc('lint')
        self.assertEqual(r.returncode, 1)
        self.assertIn('medição de consumo', r.stdout)

    def test_lint_pega_fatia_fechada_sem_prova(self):
        self.abrir()
        self.arq.write_text(self.texto().replace('1. primeira — pendente', '1. primeira — fechada'),
                            encoding='utf-8')
        r = self.sc('lint')
        self.assertEqual(r.returncode, 1)
        self.assertIn('sem prova', r.stdout)

    def test_lint_pega_secao_ausente(self):
        self.abrir()
        t = self.texto()
        self.arq.write_text(t[:t.index('## Achados abertos')], encoding='utf-8')
        r = self.sc('lint')
        self.assertEqual(r.returncode, 1)
        self.assertIn('Achados abertos', r.stdout)

    # ---------- colar ----------

    def test_colar_gera_bloco_curto_e_completo(self):
        self.abrir()
        self.sc('fatia', '1', '--fechar', '--prova', 'pytest → ok')
        self.sc('bastao', '--para', 'Arquiteto (ChatGPT)', '--leia', 'src/a.ts', '--faca', 'avaliar o marco')
        r = self.sc('colar', aplicar=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('[Sociedade do Código] Rodada R-01', r.stdout)
        self.assertIn('já fechado: 1. primeira', r.stdout)
        self.assertIn('avaliar o marco', r.stdout)
        self.assertLess(len(r.stdout.encode('utf-8')), 2000)  # cabe em qualquer chat sem custar caro

    # ---------- histórico ----------

    def test_rotacionar_arquiva_sem_apagar(self):
        self.abrir()
        antigas = ('## 15/08/2026 10:00 · Gandalf · rodada W · abertura\nfez: antigo\n'
                   '\n## 03/07/2026 09:00 · Gandalf · rodada V · abertura\nfez: mais antigo\n')
        self.hist.write_text(self.hist.read_text(encoding='utf-8') + '\n' + antigas, encoding='utf-8')
        r = self.sc('rotacionar')
        self.assertEqual(r.returncode, 0, r.stderr)
        pasta = self.p / 'sociedade' / 'historico'
        arquivados = sorted(a.name for a in pasta.iterdir())
        self.assertEqual(arquivados, ['2026-07.md', '2026-08.md'])
        self.assertIn('fez: antigo', (pasta / '2026-08.md').read_text(encoding='utf-8'))
        self.assertNotIn('fez: antigo', self.hist.read_text(encoding='utf-8'))
        self.assertIn('rodada R-01 · abertura', self.hist.read_text(encoding='utf-8'))

    # ---------- modelo ----------

    def test_modelo_bate_com_o_que_o_script_gera(self):
        modelo = MODELO.read_text(encoding='utf-8')
        for secao in ('## Aceite', '## Fatias', '## Para quem pega o bastão agora', '## Achados abertos'):
            self.assertIn(secao, modelo)
        self.abrir()
        for secao in ('## Aceite', '## Fatias', '## Para quem pega o bastão agora', '## Achados abertos'):
            self.assertIn(secao, self.texto())
        self.assertRegex(modelo, r'(?m)^- nivel: ')

    def test_comandos_aceitam_flags_antes_e_depois_do_subcomando(self):
        pasta = str(self.p / 'sociedade')
        r = rodar(RODADA, '--pasta', pasta, '--aplicar', 'abrir', '--id', 'R-09', '--meta', 'y', '--nivel', '1')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.arq.is_file())

    # ---------- integração com registro e governança (REV-001..REV-015) ----------

    def test_cli_recusa_registro_corrompido(self):
        self.abrir()
        reg_path = self.p / 'sociedade' / 'registro.json'
        self.assertTrue(reg_path.is_file())
        reg_path.write_text('{ json quebrado: ', encoding='utf-8')
        r = self.sc('fatia', '1')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('corrompido', r.stderr)

    def test_cli_grava_registro_antes_do_markdown(self):
        self.abrir()
        # Fatia 1 fecha, mas fatia 2 fica pendente
        self.sc('fatia', '1', '--fechar', '--prova', 'pytest -> ok')
        # Tentar encerrar sem fechar fatia 2
        r = self.sc('encerrar', '--resumo', 'teste falho')
        self.assertEqual(r.returncode, 1)
        # rodada.md não pode ser apagado se o encerramento falha
        self.assertTrue(self.arq.is_file())
        # historico.md não pode conter encerramento da rodada
        hist_text = self.hist.read_text(encoding='utf-8')
        self.assertNotIn('rodada R-01 · encerramento', hist_text)
        # avaliacao.md não pode ser criada
        self.assertFalse((self.p / 'sociedade' / 'avaliacao.md').exists())

    def test_cli_forcar_sem_parametros_falha(self):
        self.abrir()
        # Sem motivo nem decisao-ref
        r = self.sc('encerrar', '--forcar')
        self.assertEqual(r.returncode, 1)
        self.assertIn('exige --motivo substantivo', r.stderr)
        self.assertIn('--decisao-ref', r.stderr)

        # Motivo curto demais (< 10 caracteres)
        r = self.sc('encerrar', '--forcar', '--motivo', 'curto', '--decisao-ref', 'DEC-01')
        self.assertEqual(r.returncode, 1)
        self.assertIn('mínimo 10 caracteres', r.stderr)

        # Decisao ref inválida ('autorizacao_cli')
        r = self.sc('encerrar', '--forcar', '--motivo', 'motivo substantivo longo', '--decisao-ref', 'autorizacao_cli')
        self.assertEqual(r.returncode, 1)
        self.assertIn('exige --motivo substantivo', r.stderr)
        self.assertIn('--decisao-ref', r.stderr)

        # Registra exceção para revisão independente antes de forçar encerramento
        self.sc('excecao', '--etapa', 'R-01', '--regra', 'revisao_independente',
                '--motivo', 'dispensa temporaria de revisao em teste', '--decisao-ref', 'DEC-ODIVAL-001')
        # Com parâmetros válidos humanos e a decisão registrada, o encerramento forçado via exceção passa
        self.decidir()
        r = self.sc('encerrar', '--forcar', '--regra', 'fatias_pendentes',
                    '--motivo', 'excecao aprovada pelo usuario em teste', '--decisao-ref', 'DEC-ODIVAL-999')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.arq.exists())

    def test_cli_forcar_abrir_exige_motivo_e_decisao(self):
        self.abrir()
        r = self.sc('abrir', '--id', 'R-02', '--meta', 'outra', '--nivel', '1', '--forcar')
        self.assertEqual(r.returncode, 1)
        self.assertIn('exige --motivo substantivo', r.stderr)

    def test_cli_linter_rejeita_relato_de_gasto_disfarcado(self):
        self.abrir()
        t = self.texto()
        # Simula agente relatando consumo disfarcado
        self.arq.write_text(t + '\n- observacao: gastou 3500 tokens no prompt\n', encoding='utf-8')
        r = self.sc('lint')
        self.assertEqual(r.returncode, 1)
        self.assertIn('medição de consumo', r.stdout)

        # Frases com tentativas de contornar linter com palavras-chave de isenção são rejeitadas (REV-013, N11)
        self.arq.write_text(t + '\n- nota: gastei 90000 tokens hoje, informado por mim\n', encoding='utf-8')
        r = self.sc('lint')
        self.assertEqual(r.returncode, 1)

        self.arq.write_text(t + '\n- nota: gastei 40 mil tokens (nenhum agente estima)\n', encoding='utf-8')
        r = self.sc('lint')
        self.assertEqual(r.returncode, 1)

        # Simula alerta manual legítimo de Odival
        self.arq.write_text(t + '\n<!-- odival: cota usada atingida na conta institucional -->\n', encoding='utf-8')
        r = self.sc('lint')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_cli_subcomando_evidencia(self):
        self.abrir()
        r = self.sc('evidencia', '--etapa', 'R-01', '--criterio', 'fatia_1',
                    '--comando', f'{sys.executable} -c "print(\'15 passed in 0.2s\')"')  # B15: o comando roda e o código é o medido
        self.assertEqual(r.returncode, 0, r.stderr)
        import json
        reg = json.loads((self.p / 'sociedade' / 'registro.json').read_text(encoding='utf-8'))
        eventos_ev = [e for e in reg['eventos'] if e['tipo'] == 'evidencia_registrada']
        self.assertEqual(len(eventos_ev), 1)
        self.assertEqual(eventos_ev[0]['dados']['criterio_id'], 'fatia_1')
        self.assertEqual(eventos_ev[0]['dados']['exit_code'], 0)

    def test_cli_subcomando_parecer_e_excecao(self):
        self.abrir()
        r = self.parecer('não aceitar', 'R-01', 'Nível A (fornecedor diferente)',
                         '--etapa', 'R-01', '--achado', 'REV-001:bloqueador:falha de isolamento')
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.sc('excecao', '--etapa', 'R-01', '--regra', 'achados_bloqueadores',
                    '--motivo', 'motivo substantivo de excecao', '--decisao-ref', 'DEC-123')
        self.assertEqual(r.returncode, 0, r.stderr)
        import json
        reg = json.loads((self.p / 'sociedade' / 'registro.json').read_text(encoding='utf-8'))
        tipos = [e['tipo'] for e in reg['eventos']]
        self.assertIn('parecer_registrado', tipos)
        self.assertIn('excecao_registrada', tipos)

    def test_cli_subcomando_resumo(self):
        self.abrir(fatias=['unica'])
        self.sc('fatia', '1', '--fechar', '--prova', 'ok')
        self.parecer()
        self.decidir()
        self.sc('encerrar', '--resumo', 'concluido com sucesso')
        r = self.sc('resumo', '--exportar', 'R-01', aplicar=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('resumo_hash', r.stdout)
        self.assertIn('concluido com sucesso', r.stdout)

    def test_sonda_b_revisao_obrigatoria_por_padrao_na_cli(self):
        # S-B: abrir sem --sem-revisao exige revisão independente antes de encerrar
        self.abrir(fatias=['unica'])
        self.sc('fatia', '1', '--fechar', '--prova', 'python3 -m unittest -> OK')
        self.decidir()  # com a decisão registrada, o que barra o encerramento é a falta do parecer
        r = self.sc('encerrar', '--resumo', 'tentativa sem parecer')
        self.assertEqual(r.returncode, 1)
        self.assertIn('Revisão independente obrigatória', r.stderr)

    def test_cli_subcomando_projetar_e_sincronizar(self):
        self.abrir(fatias=['unica'])
        andamento_md = self.p / 'sociedade' / 'andamento.md'
        andamento_md.write_text('# Andamento do Projeto\n', encoding='utf-8')
        r = self.sc('projetar')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('## Retorno de Gandalf — R-01', andamento_md.read_text(encoding='utf-8'))

        # Sincronia deve acusar sincronizado
        r = self.sc('sincronizar')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('sincronizado', r.stdout)


if __name__ == '__main__':
    unittest.main()

