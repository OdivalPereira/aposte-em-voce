#!/usr/bin/env python3
"""Modo emulação (B02, Q147): chave `emulacao` do perfil.

- Chave desligada ou ausente: D-RT-001 e R1-R3 como antes (violação reprova, fornecedor igual reprova).
- Chave ligada: R1-R3 viram AVISO; a troca grava o motivo "emulação" (R4); o parecer do mesmo
  fornecedor vale como "aceite em emulação", marcado no registro e no painel; independência = "não".
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, carregar, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
MOD_PERFIL = carregar(NUCLEO / 'scripts' / 'sc_perfil.py', 'sc_perfil')
MOD_REGISTRO = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
MOD_RODADA = carregar(NUCLEO / 'scripts' / 'sc_rodada.py', 'sc_rodada')
MOD_RESUMO = carregar(NUCLEO / 'scripts' / 'sc_resumo.py', 'sc_resumo')
MOD_VALIDAR = carregar(NUCLEO / 'scripts' / 'validar_perfil.py', 'validar_perfil')
Registro = MOD_REGISTRO.Registro
ErroValidacaoRegistro = MOD_REGISTRO.ErroValidacaoRegistro
SCRIPT_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'

PERFIL = """# Perfil sintético

## Missão
Projeto sintético para o modo emulação.

## Autoridades
- **Decide escopo, prioridade e publicação:** Odival

## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | Claude Code (nuvem) | Anthropic | Modelo A | high | ativo | 2026-10-03 | sessão principal |
| Revisor Independente | Barbárvore | Claude Code (nuvem) | Anthropic | Modelo A | high | ativo | 2026-10-03 | subagente isolado |
| Coordenador | Gandalf | Claude Code (nuvem) | Anthropic | Modelo B | high | ativo | 2026-10-03 | subagente |
| Dados e persistência | Elrond | Claude Code (nuvem) | Anthropic | Modelo B | high | ativo | 2026-10-03 | subagente |

## Modo emulação (Q147)
{CHAVE}
- Adaptador: um agente por papel.
"""
LIGADA = '- **Emulação:** sim. Um só fornecedor ocupa todos os papéis.'
DESLIGADA = '- **Emulação:** não.'


def perfil_com(chave):
    return PERFIL.replace('{CHAVE}', chave)


class Base(unittest.TestCase):
    chave = LIGADA

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.pasta = self.raiz / 'sociedade'
        self.pasta.mkdir()
        self.arq_perfil = self.pasta / 'perfil.md'
        self.arq_perfil.write_text(perfil_com(self.chave), encoding='utf-8')
        self.reg = Registro.inicializar(self.pasta, 'proj-sintetico', str(self.raiz), versao_inicial='v1')

    def abrir_etapa_com_parecer(self, **kw):
        self.reg.abrir_etapa('E1', 'Meta', 'ref', 'aut', 'abc1234', ['C1'], responsavel='Gandalf')
        self.reg.registrar_tarefa('E1', 'T1', especialista='Elrond', descricao='dados', fornecedor='Anthropic')
        self.reg.registrar_evidencia('E1', 'C1', 'cmd', 0, 'Ran 3 tests OK', versao_entrega='abc1234')
        self.reg.atualizar_tarefa('E1', 'T1', 'concluida')
        return self.reg.registrar_parecer('E1', 'PAR-1', 'Barbárvore', 'Anthropic', ['Elrond:Anthropic'],
                                          'abc1234', 'aceitar', {'C1': True}, **kw)

    def eventos(self, tipo):
        return [e for e in Registro(self.pasta).dados['eventos'] if e.get('tipo') == tipo]


class TesteChave(unittest.TestCase):
    def test_lida_da_secao_modo_emulacao(self):
        emul = MOD_PERFIL.emulacao_ligada
        self.assertTrue(emul(perfil_com(LIGADA)))
        self.assertFalse(emul(perfil_com(DESLIGADA)))
        self.assertFalse(emul(perfil_com('- Sem a linha da chave.')))

    def test_falha_fechada_fora_da_secao_ou_valor_estranho(self):
        emul = MOD_PERFIL.emulacao_ligada
        fora = PERFIL.replace('{CHAVE}', '- nada') + '\n## Outra seção\n- **Emulação:** sim\n'
        self.assertFalse(emul(fora))
        em_codigo = PERFIL.replace('{CHAVE}', '```\n- **Emulação:** sim\n```')
        self.assertFalse(emul(em_codigo))
        self.assertFalse(emul(perfil_com('- **Emulação:** talvez')))
        self.assertFalse(emul(perfil_com('- **Emulação:** simulado')))
        self.assertFalse(emul(None))
        self.assertFalse(emul(''))
        self.assertFalse(emul('/caminho/que/nao/existe/perfil.md'))

    def test_f6_so_o_valor_unico_sim_liga(self):
        """F6 (achado 1): a chave falha fechada; só `sim` sozinho liga (ponto final e texto depois dele valem)."""
        emul = MOD_PERFIL.emulacao_ligada
        for ligam in ('- **Emulação:** sim', '- **Emulação:** SIM.', '- **Emulacao:** sim', '* **Emulação**: sim',
                      '- **Emulação:** sim. Um só fornecedor.'):
            with self.subTest(valor=ligam):
                self.assertTrue(emul(perfil_com(ligam)), ligam)
        for nao_ligam in ('- **Emulação:** sim | não', '- **Emulação:** sim ou não', '- **Emulação:** sim/não',
                          '- **Emulação:** sim, não', '- **Emulação:** sim (talvez)', '- **Emulação:**',
                          '- **Emulação:** sim\n- **Emulação:** não'):
            with self.subTest(valor=nao_ligam):
                self.assertFalse(emul(perfil_com(nao_ligam)), nao_ligam)

    def test_f6_comentario_html_e_codigo_indentado_sao_ignorados(self):
        emul = MOD_PERFIL.emulacao_ligada
        self.assertFalse(emul(perfil_com('<!--\n- **Emulação:** sim\n-->\n- **Emulação:** não')))
        self.assertFalse(emul(perfil_com('<!-- - **Emulação:** sim -->')))
        self.assertFalse(emul(perfil_com('<!--\n- **Emulação:** sim\n')), 'comentário sem fechamento vale até o fim')
        self.assertTrue(emul(perfil_com('<!-- nota -->\n- **Emulação:** sim <!-- ok -->')))
        self.assertFalse(emul(perfil_com('    - **Emulação:** sim')))
        self.assertFalse(emul(perfil_com('\t- **Emulação:** sim')))

    def test_f6_so_a_secao_modo_emulacao_conta(self):
        emul = MOD_PERFIL.emulacao_ligada
        self.assertFalse(emul('# P\n\n## Como desligar o modo emulação\n- **Emulação:** sim\n'))
        self.assertFalse(emul('# P\n\n## Modo emulação ligado em testes\n- **Emulação:** sim\n'))
        self.assertTrue(emul('# P\n\n## Modo emulação\n- **Emulação:** sim\n'))
        self.assertTrue(emul('# P\n\n## MODO EMULAÇÃO (Q147)\n- **Emulação:** sim\n'))
        self.assertTrue(emul('# P\n\n## Modo emulacao\n- **Emulação:** sim\n'))

    def test_f6_validar_perfil_so_avisa_com_valor_ambiguo(self):
        with tempfile.TemporaryDirectory() as t:
            arq = Path(t) / 'perfil.md'
            arq.write_text(perfil_com('- **Emulação:** sim | não'), encoding='utf-8')
            faltam, avisos = MOD_VALIDAR.validar(arq)
            self.assertEqual(faltam, [])
            self.assertTrue(any('valor inválido' in a for a in avisos), avisos)
            self.assertFalse(any('modo emulação ligado' in a for a in avisos), avisos)

    def test_aceita_texto_caminho_pasta_e_objeto(self):
        with tempfile.TemporaryDirectory() as t:
            pasta = Path(t) / 'sociedade'
            pasta.mkdir()
            arq = pasta / 'perfil.md'
            arq.write_text(perfil_com(LIGADA), encoding='utf-8')
            self.assertTrue(MOD_PERFIL.emulacao_ligada(arq))
            self.assertTrue(MOD_PERFIL.emulacao_ligada(str(arq)))
            self.assertTrue(MOD_PERFIL.emulacao_ligada(pasta))
            perfil = MOD_PERFIL.carregar_perfil(arq)
            self.assertTrue(MOD_PERFIL.emulacao_ligada(perfil))
            self.assertTrue(perfil.emulacao)

    def test_cli_do_perfil(self):
        with tempfile.TemporaryDirectory() as t:
            arq = Path(t) / 'perfil.md'
            for chave, esperado in ((LIGADA, 'sim'), (DESLIGADA, 'não')):
                arq.write_text(perfil_com(chave), encoding='utf-8')
                r = rodar(NUCLEO / 'scripts' / 'sc_perfil.py', str(arq), '--emulacao')
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.strip(), esperado)

    def test_motivo_de_emulacao_e_idempotente(self):
        marcar = MOD_PERFIL.marcar_motivo_emulacao
        self.assertEqual(marcar(''), 'emulação')
        self.assertEqual(marcar('sem outro fornecedor'), 'emulação: sem outro fornecedor')
        self.assertEqual(marcar(marcar('x')), 'emulação: x')

    def test_validar_perfil_avisa_e_nao_reprova(self):
        with tempfile.TemporaryDirectory() as t:
            arq = Path(t) / 'perfil.md'
            arq.write_text(perfil_com(LIGADA), encoding='utf-8')
            faltam, avisos = MOD_VALIDAR.validar(arq)
            self.assertEqual(faltam, [])
            self.assertTrue(any('modo emulação ligado' in a for a in avisos), avisos)
            arq.write_text(perfil_com('- **Emulação:** talvez'), encoding='utf-8')
            faltam, avisos = MOD_VALIDAR.validar(arq)
            self.assertEqual(faltam, [])
            self.assertTrue(any('valor inválido' in a for a in avisos), avisos)
            arq.write_text(perfil_com(DESLIGADA), encoding='utf-8')
            _, avisos = MOD_VALIDAR.validar(arq)
            self.assertFalse(any('emulação' in a.lower() for a in avisos), avisos)


class TesteDesligada(Base):
    """Chave desligada: comportamento antigo (D-RT-001 e R1-R3)."""
    chave = DESLIGADA

    def trocar(self, *args):
        return rodar(SCRIPT_RODADA, 'papel', 'trocar', '--pasta', self.pasta, '--autor', 'Odival', *args)

    def test_r1_continua_reprovando(self):
        r = self.trocar('--papel', 'revisor', '--para', 'Claude Code (nuvem)', '--motivo', 'sem emulação ligada')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Violação de R1', r.stderr)
        self.assertNotIn('AVISO (emulação)', r.stderr)

    def test_r3_continua_reprovando(self):
        ok, erros = MOD_RODADA.validar_regras_troca('execucao', 'ativo', 'Claude Code (nuvem)', 'Anthropic',
                                                    MOD_PERFIL.carregar_perfil(self.arq_perfil), self.reg)
        self.assertFalse(ok)
        self.assertTrue(any('Violação de R3' in e for e in erros))

    def test_parecer_do_mesmo_fornecedor_continua_recusado(self):
        with self.assertRaises(ErroValidacaoRegistro) as ctx:
            self.abrir_etapa_com_parecer()
        self.assertIn('Independência violada', str(ctx.exception))

    def test_aceite_em_emulacao_declarado_e_recusado(self):
        with self.assertRaises(ErroValidacaoRegistro):
            self.abrir_etapa_com_parecer(aceite_em_emulacao=True)
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_decisao('E1', 'D-1', 'Odival', 'conversa', 'aceitar', aceite_em_emulacao=True)

    def test_troca_em_emulacao_declarada_e_recusada(self):
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_troca_papel('revisor', 'Claude Code (nuvem)', 'Anthropic', emulacao=True, motivo='x')

    def test_eventos_antigos_sem_campos_novos(self):
        self.reg.abrir_etapa('E2', 'Meta', 'ref', 'aut', 'abc1234', ['C1'])
        self.reg.registrar_decisao('E2', 'D-1', 'Odival', 'conversa', 'aceitar')
        dados = self.eventos('decisao_registrada')[-1]['dados']
        self.assertNotIn('aceite_em_emulacao', dados)
        self.assertNotIn('independencia', dados)

    def test_parecer_de_outro_fornecedor_segue_independente(self):
        self.reg.abrir_etapa('E1', 'Meta', 'ref', 'aut', 'abc1234', ['C1'], responsavel='Gandalf')
        self.reg.registrar_tarefa('E1', 'T1', especialista='Elrond', descricao='dados', fornecedor='Anthropic')
        self.reg.registrar_parecer('E1', 'PAR-1', 'Revisor Externo', 'OutroFornecedor', ['Elrond:Anthropic'],
                                   'abc1234', 'aceitar', {'C1': True})
        par = self.reg.estado()['etapas']['E1']['pareceres'][0]
        self.assertEqual(par['nivel_independencia'], 'A')
        self.assertEqual(par['independencia'], 'sim')
        self.assertFalse(par['aceite_em_emulacao'])
        self.assertFalse(self.reg.estado()['etapas']['E1']['aceite_em_emulacao'])


class TesteLigada(Base):
    chave = LIGADA

    def trocar(self, *args):
        return rodar(SCRIPT_RODADA, 'papel', 'trocar', '--pasta', self.pasta, '--autor', 'Odival', *args)

    # ---- R1-R3 viram aviso ----
    def test_r1_vira_aviso_na_simulacao(self):
        r = self.trocar('--papel', 'revisor', '--para', 'Claude Code (nuvem)', '--motivo', 'um fornecedor só')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('AVISO (emulação): Violação de R1', r.stderr)
        self.assertIn('Modo emulação', r.stdout)
        self.assertIn('independência: não', r.stdout)

    def test_funcao_devolve_ok_com_avisos(self):
        perfil = MOD_PERFIL.carregar_perfil(self.arq_perfil)
        avisos = []
        ok, erros = MOD_RODADA.validar_regras_troca('execucao', 'ativo', 'Claude Code (nuvem)', 'Anthropic',
                                                    perfil, self.reg, avisos=avisos)
        self.assertTrue(ok)
        self.assertEqual(erros, [])
        self.assertTrue(any('Violação de R3' in a for a in avisos), avisos)

    def test_r2_vira_aviso(self):
        self.reg.abrir_etapa('E1', 'Meta', 'ref', 'aut', 'abc1234', ['C1'], responsavel='Gandalf')
        self.reg.registrar_tarefa('E1', 'T1', especialista='Elrond', descricao='dados', fornecedor='Anthropic')
        perfil = MOD_PERFIL.carregar_perfil(self.arq_perfil)
        avisos = []
        ok, erros = MOD_RODADA.validar_regras_troca('revisor', 'ativo', 'Claude Code (nuvem)', 'Anthropic',
                                                    perfil, Registro(self.pasta), avisos=avisos)
        self.assertTrue(ok and not erros)
        self.assertTrue(any('Violação de R2' in a for a in avisos), avisos)

    # ---- R4: motivo "emulação" ----
    def test_troca_aplicada_grava_motivo_emulacao_no_registro_e_no_perfil(self):
        r = self.trocar('--papel', 'revisor', '--para', 'Claude Code (nuvem)', '--modelo', 'Modelo C',
                        '--motivo', 'sem segundo fornecedor', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ev = self.eventos('papel_trocado')[-1]
        self.assertEqual(ev['autor'], 'Odival')
        self.assertTrue(ev['dados']['motivo'].startswith('emulação'), ev['dados']['motivo'])
        self.assertIn('sem segundo fornecedor', ev['dados']['motivo'])
        self.assertTrue(ev['dados']['emulacao'])
        self.assertIn('emulação: sem segundo fornecedor', self.arq_perfil.read_text(encoding='utf-8'))
        self.assertIn('Motivo: emulação: sem segundo fornecedor', r.stdout)

    def test_troca_sem_violacao_tambem_grava_motivo_emulacao(self):
        r = self.trocar('--papel', 'revisor', '--estado', 'espera', '--motivo', 'pausa curta', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(self.eventos('papel_trocado')[-1]['dados']['motivo'].startswith('emulação'))

    # ---- aceite em emulação ----
    def test_parecer_do_mesmo_fornecedor_vale_como_aceite_em_emulacao(self):
        self.abrir_etapa_com_parecer()
        dados = self.eventos('parecer_registrado')[-1]['dados']
        self.assertIs(dados['aceite_em_emulacao'], True)
        self.assertEqual(dados['independencia'], 'não')
        self.assertEqual(dados['nivel_independencia'], 'E')
        etapa = self.reg.estado()['etapas']['E1']
        self.assertTrue(etapa['aceite_em_emulacao'])
        self.assertEqual(etapa['independencia'], 'não')
        self.assertEqual(etapa['pareceres'][0]['independencia'], 'não')
        # vale como aceite: nenhum bloqueio, mas nunca elegível a publicação como independente (D-RT-001)
        ok, bloqueios = self.reg.verificar_condicoes_encerramento('E1')
        self.assertTrue(ok, bloqueios)
        self.assertEqual(bloqueios, [])
        self.reg.encerrar_etapa('E1', 'fechada em emulação')
        est = Registro(self.pasta).estado()
        self.assertNotIn('E1', est['etapas_concluidas'])
        self.assertIn('E1', est['etapas_excepcionadas'])

    def test_auto_revisao_continua_recusada_em_emulacao(self):
        self.reg.abrir_etapa('E1', 'Meta', 'ref', 'aut', 'abc1234', ['C1'], responsavel='Gandalf')
        self.reg.registrar_tarefa('E1', 'T1', especialista='Elrond', descricao='dados', fornecedor='Anthropic')
        with self.assertRaises(ErroValidacaoRegistro) as ctx:
            self.reg.registrar_parecer('E1', 'PAR-1', 'Elrond', 'Anthropic', ['Elrond:Anthropic'],
                                       'abc1234', 'aceitar', {'C1': True})
        self.assertIn('Auto-revisão', str(ctx.exception))

    def test_fornecedor_desconhecido_continua_recusado_em_emulacao(self):
        self.reg.abrir_etapa('E1', 'Meta', 'ref', 'aut', 'abc1234', ['C1'], responsavel='Gandalf')
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_parecer('E1', 'PAR-1', 'Barbárvore', 'Anthropic', ['Fulano Sem Perfil'],
                                       'abc1234', 'aceitar', {'C1': True})

    def test_parecer_de_outro_fornecedor_continua_independente_com_chave_ligada(self):
        self.reg.abrir_etapa('E1', 'Meta', 'ref', 'aut', 'abc1234', ['C1'], responsavel='Gandalf')
        self.reg.registrar_tarefa('E1', 'T1', especialista='Elrond', descricao='dados', fornecedor='Anthropic')
        self.reg.registrar_parecer('E1', 'PAR-1', 'Revisor Externo', 'OutroFornecedor', ['Elrond:Anthropic'],
                                   'abc1234', 'aceitar', {'C1': True})
        etapa = self.reg.estado()['etapas']['E1']
        self.assertFalse(etapa['aceite_em_emulacao'])
        self.assertEqual(etapa['independencia'], 'sim')
        self.assertNotIn('aceite_em_emulacao', self.eventos('parecer_registrado')[-1]['dados'])

    def test_decisao_marcada_aceite_em_emulacao(self):
        self.reg.abrir_etapa('E2', 'Meta', 'ref', 'aut', 'abc1234', ['C1'])
        self.reg.registrar_decisao('E2', 'D-1', 'Odival', 'conversa', 'aceitar', aceite_em_emulacao=True)
        dados = self.eventos('decisao_registrada')[-1]['dados']
        self.assertIs(dados['aceite_em_emulacao'], True)
        self.assertEqual(dados['independencia'], 'não')
        etapa = self.reg.estado()['etapas']['E2']
        self.assertTrue(etapa['aceite_em_emulacao'])
        self.assertTrue(etapa['decisoes'][0]['aceite_em_emulacao'])
        self.assertEqual(etapa['independencia'], 'não')

    def test_decisao_em_emulacao_nao_pode_declarar_independencia_sim(self):
        self.reg.abrir_etapa('E2', 'Meta', 'ref', 'aut', 'abc1234', ['C1'])
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_decisao('E2', 'D-1', 'Odival', 'conversa', 'aceitar',
                                       aceite_em_emulacao=True, independencia='sim')
        with self.assertRaises(ErroValidacaoRegistro):
            self.reg.registrar_decisao('E2', 'D-2', 'Odival', 'conversa', 'aceitar', independencia='talvez')
        self.reg.registrar_decisao('E2', 'D-3', 'Odival', 'conversa', 'aceitar',
                                   aceite_em_emulacao=True, independencia='nao')
        self.assertEqual(self.eventos('decisao_registrada')[-1]['dados']['independencia'], 'não')

    def test_cadeia_de_hash_segue_integra(self):
        self.abrir_etapa_com_parecer()
        self.reg.registrar_decisao('E1', 'D-1', 'Odival', 'conversa', 'aceitar', aceite_em_emulacao=True)
        Registro(self.pasta)  # recarregar valida a cadeia; falha se corrompida


class TestePainel(Base):
    chave = LIGADA

    def test_painel_marca_aceite_em_emulacao_no_md_e_no_html(self):
        self.abrir_etapa_com_parecer()
        self.reg.registrar_decisao('E1', 'D-1', 'Odival', 'conversa', 'aceitar', aceite_em_emulacao=True)
        d = MOD_RESUMO.coletar(self.pasta)
        self.assertTrue(d['emulacao'])
        etapa = d['etapas'][0]
        self.assertTrue(etapa['aceite_em_emulacao'])
        self.assertEqual(etapa['independencia'], 'não')
        md = MOD_RESUMO.gerar_md(d)
        self.assertIn('aceitar (aceite em emulação; independência: não)', md)
        self.assertIn('Modo emulação ligado', md)
        self.assertIn('Etapa E1: aceite em emulação', md)
        html = MOD_RESUMO.gerar_html(d)
        self.assertIn('aceite em emulação', html)
        self.assertIn('independência: não', html)

    def test_painel_sem_emulacao_nao_marca(self):
        self.arq_perfil.write_text(perfil_com(DESLIGADA), encoding='utf-8')
        self.reg.abrir_etapa('E1', 'Meta', 'ref', 'aut', 'abc1234', ['C1'], responsavel='Gandalf')
        self.reg.registrar_tarefa('E1', 'T1', especialista='Elrond', descricao='dados', fornecedor='Anthropic')
        self.reg.registrar_parecer('E1', 'PAR-1', 'Revisor Externo', 'OutroFornecedor', ['Elrond:Anthropic'],
                                   'abc1234', 'aceitar', {'C1': True})
        d = MOD_RESUMO.coletar(self.pasta)
        self.assertFalse(d['emulacao'])
        md = MOD_RESUMO.gerar_md(d)
        self.assertNotIn('emulação', md)
        self.assertNotIn('emulação', MOD_RESUMO.gerar_html(d))


if __name__ == '__main__':
    unittest.main()
