"""Sondas DG-04 (B09): modo emulação e rodízio de fornecedor (R1 a R3). Fechado pela B02, com a marca de emulação
(a independência real fica para a produção, R6). Todas as sondas deste arquivo são verdes.

Achado original: a Sociedade só rodava com fornecedores distintos; com um fornecedor só, o método travava ou o aceite
se passava por independente. Agora: chave ligada = R1 a R3 viram aviso, a troca grava "emulação", o aceite fica
marcado e a independência é "não"; chave desligada = tudo como antes.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cenario import AMBIENTE, SC_RODADA, Base, MODO_EMULACAO, rodar, texto_perfil  # noqa: E402

POR = ('--por', 'Odival Sintético')
TROCA_REVISOR = ('papel', 'trocar', '--papel', 'revisor', '--para', 'Claude Code (nuvem)', '--motivo', 'um fornecedor só',
                 '--autor', 'Odival Sintético')
TROCA_COORDENADOR = ('papel', 'trocar', '--papel', 'coordenador', '--para', 'Claude Code (nuvem)', '--motivo', 'sem Google',
                     '--autor', 'Odival Sintético')


class SondaDG04Ligada(Base):
    emulacao = 'sim'

    def test_DG04_ligada_r1_e_r3_viram_aviso_e_a_troca_grava_emulacao(self):
        """Achado: com um fornecedor só, a troca de papel era sempre recusada (R1 a R3). Reproduz: com a chave ligada, a
        troca do revisor (R1) e a do coordenador (R3) saem com `AVISO (emulação)`, são gravadas e levam o motivo "emulação"."""
        p = self.p
        self.ok(p.abrir())
        r1 = self.ok(p.rodada(*TROCA_REVISOR))
        self.assertIn('AVISO (emulação): Violação de R1', r1.stderr)
        r3 = self.ok(p.rodada(*TROCA_COORDENADOR))
        self.assertIn('AVISO (emulação): Violação de R3', r3.stderr)
        trocas = p.eventos('papel_trocado')
        self.assertEqual(len(trocas), 2)
        for t in trocas:
            self.assertTrue(t['motivo'].startswith('emulação'), t['motivo'])
            self.assertIs(t['emulacao'], True)

    def test_DG04_ligada_a_simulacao_da_troca_diz_que_a_independencia_e_nao(self):
        """Achado: o aviso não dizia o que a emulação custa. Reproduz: sem `--aplicar` o comando só simula, não grava
        nada e declara "independência: não"."""
        p = self.p
        self.ok(p.abrir())
        antes = len(p.registro().eventos)
        r = self.ok(rodar(SC_RODADA, *TROCA_REVISOR, '--pasta', p.soc, cwd=p.raiz, env=AMBIENTE))
        self.assertIn('independência: não', r.stdout)
        self.assertEqual(len(p.registro().eventos), antes)

    def test_DG04_ligada_aceite_marcado_independencia_nao_e_nunca_elegivel(self):
        """Achado: o aceite do mesmo fornecedor se passava por revisão independente. Reproduz o ciclo com o revisor e o
        implementador da mesma empresa: a decisão e a etapa saem marcadas "aceite em emulação", independência "não",
        e a etapa nunca fica elegível à publicação."""
        p = self.p
        p.fluxo_ate_o_parecer()
        self.ok(p.decidir('aceitar', *POR))
        decisao = p.eventos('decisao_registrada')[-1]
        self.assertIs(decisao['aceite_em_emulacao'], True)
        self.assertEqual(decisao['independencia'], 'não')
        etapa = p.etapa()
        self.assertEqual(etapa['estado'], 'encerrada')
        self.assertIs(etapa['aceite_em_emulacao'], True)
        self.assertEqual(etapa['independencia'], 'não')
        self.assertFalse(etapa['elegivel_publicacao'])

    def test_DG04_ligada_parecer_de_nivel_a_do_mesmo_fornecedor_vale_como_aceite_marcado(self):
        """Achado: declarar "Nível A" para um revisor do mesmo fornecedor era recusado e o ciclo travava. Reproduz: com a
        chave ligada o parecer entra, marcado, com nível próprio (não "A") e independência "não"."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        self.ok(p.revisar(p.escrever_parecer(nivel='Nível A (fornecedor diferente)')))
        parecer = p.eventos('parecer_registrado')[-1]
        self.assertIs(parecer['aceite_em_emulacao'], True)
        self.assertEqual(parecer['independencia'], 'não')
        self.assertNotEqual(parecer['nivel_independencia'], 'A')
        self.ok(p.decidir('aceitar', *POR))
        self.assertFalse(p.etapa()['elegivel_publicacao'])

    def test_DG04_ligada_o_painel_marca_o_aceite_em_emulacao(self):
        """Achado: o painel mostrava "aceitar" sem dizer que não era independente. Reproduz: `sc.py estado` marca o
        aceite em emulação e a independência "não"."""
        p = self.p
        p.fluxo_ate_o_parecer()
        self.ok(p.decidir('aceitar', *POR))
        saida = self.ok(p.estado_md()).stdout
        self.assertIn('aceite em emulação', saida)
        self.assertIn('independência: não', saida)
        self.assertIn('Modo emulação ligado', saida)


class SondaDG04Desligada(Base):
    emulacao = 'não'

    def test_DG04_desligada_r1_e_r3_continuam_reprovando(self):
        """Achado: o modo emulação não pode afrouxar um projeto que o deixou desligado. Reproduz: R1 e R3 recusam a troca,
        sem aviso de emulação, sem evento e sem reescrever o perfil."""
        p = self.p
        self.ok(p.abrir())
        perfil_antes = (p.soc / 'perfil.md').read_text(encoding='utf-8')
        r1 = self.recusa(p.rodada(*TROCA_REVISOR), 'Violação de R1')
        self.assertNotIn('AVISO (emulação)', r1.stderr)
        r3 = self.recusa(p.rodada(*TROCA_COORDENADOR), 'Violação de R3')
        self.assertNotIn('AVISO (emulação)', r3.stderr)
        self.assertEqual(p.eventos('papel_trocado'), [])
        self.assertEqual((p.soc / 'perfil.md').read_text(encoding='utf-8'), perfil_antes)

    def test_DG04_desligada_parecer_de_nivel_a_do_mesmo_fornecedor_e_recusado(self):
        """Achado: a recusa de mesmo fornecedor (D-RT-001) precisa valer com a chave desligada. Reproduz: o parecer "Nível A"
        do mesmo fornecedor é recusado por independência violada e nada entra no registro."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        self.recusa(p.revisar(p.escrever_parecer(nivel='Nível A (fornecedor diferente)')), 'Independência violada')
        self.assertEqual(p.eventos('parecer_registrado'), [])

    def test_DG04_desligada_parecer_de_outro_fornecedor_sai_independente_sem_marca(self):
        """Pergunta 1 da subordem: fora da emulação, o parecer "Nível A" de outro fornecedor não leva marca de emulação e
        o estado derivado diz independência "sim"."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        arq = p.escrever_parecer(nivel='Nível A (fornecedor diferente)', revisor='Revisor Externo (Ferramenta X)',
                                 fornecedor='OutraEmpresa')
        self.ok(p.revisar(arq))
        self.ok(p.decidir('aceitar', *POR))
        decisao = p.eventos('decisao_registrada')[-1]
        self.assertFalse(decisao.get('aceite_em_emulacao'))
        self.assertNotEqual(decisao.get('independencia'), 'não')
        etapa = p.etapa()
        self.assertIs(etapa['aceite_em_emulacao'], False)
        self.assertEqual(etapa['independencia'], 'sim')
        self.assertEqual(etapa['pareceres'][-1]['nivel_independencia'], 'A')
        self.assertTrue(etapa['elegivel_publicacao'])

    def test_DG04_desligada_o_painel_nao_fala_de_emulacao(self):
        """Achado: marca de emulação aparecendo onde ela não existe esconderia a marca verdadeira. Reproduz: aceite de
        parecer independente com a chave desligada; o painel não cita emulação."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        self.ok(p.revisar(p.escrever_parecer(nivel='Nível A (fornecedor diferente)', revisor='Revisor Externo (Ferramenta X)',
                                             fornecedor='OutraEmpresa')))
        self.ok(p.decidir('aceitar', *POR))
        self.assertNotIn('emulação', self.ok(p.estado_md()).stdout)


class SondaDG04FalsificarAChave(Base):
    """A chave só vale escrita como manda o perfil: linha `- **Emulação:** sim` na seção "Modo emulação"."""

    def projeto_com(self, **kw):
        return self.novo_projeto(**kw)

    def assert_nao_liga(self, p, rotulo):
        """Chave que não deve valer: o parecer "Nível A" do mesmo fornecedor continua recusado."""
        self.ok(p.abrir())
        self.ok(p.entregar())
        r = p.revisar(p.escrever_parecer(nivel='Nível A (fornecedor diferente)'))
        self.recusa(r, 'Independência violada')
        self.assertEqual(p.eventos('parecer_registrado'), [], rotulo)

    def test_DG04_chave_ausente_vale_como_desligada(self):
        """Achado: perfil sem a seção "Modo emulação" não pode ligar nada. Reproduz."""
        self.assert_nao_liga(self.projeto_com(emulacao=None), 'sem a seção')

    def test_DG04_chave_sim_fora_da_secao_nao_liga(self):
        """Achado: um "Emulação: sim" escrito em outra seção (aqui, "Missão") ligaria o modo sem querer. Reproduz com a
        seção "Modo emulação" dizendo "não"."""
        p = self.projeto_com(perfil=texto_perfil('não', extra_missao='- **Emulação:** sim\n'))
        self.assert_nao_liga(p, 'sim na Missão')

    def test_DG04_chave_sim_dentro_de_bloco_de_codigo_nao_liga(self):
        """Achado: exemplo em bloco de código não é configuração. Reproduz com a cerca ``` na seção certa."""
        modo = '\n## Modo emulação (Q147)\n```\n- **Emulação:** sim\n```\n'
        self.assert_nao_liga(self.projeto_com(perfil=texto_perfil(modo=modo)), 'sim em bloco de código')

    def test_DG04_valor_diferente_de_sim_nao_liga(self):
        """Achado: "talvez" e "simulado" não são "sim". Reproduz com os dois."""
        for valor in ('talvez', 'simulado'):
            with self.subTest(valor=valor):
                p = self.novo_projeto(perfil=texto_perfil(modo=MODO_EMULACAO.replace('{VALOR}', valor)))
                self.assert_nao_liga(p, valor)

    def test_DG04_linha_citada_em_bloco_de_citacao_nao_liga(self):
        """Achado: linha comentada com ">" não é configuração. Reproduz."""
        modo = '\n## Modo emulação (Q147)\n> - **Emulação:** sim\n'
        self.assert_nao_liga(self.projeto_com(perfil=texto_perfil(modo=modo)), 'sim em citação')


if __name__ == '__main__':
    unittest.main()
