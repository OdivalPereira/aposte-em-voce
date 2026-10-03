"""Achados novos da revisão interna da F5 (não estão no backlog). Cada sonda descreve o comportamento desejado e falha
hoje; por isso `@expectedFailure`. Servem de pedido de correção: quem corrigir tira o decorador. Nenhum é DG-01 a DG-05.

Numeração: A-n, a mesma do retorno da subordem F5.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cenario import Base, git, parecer_texto  # noqa: E402
from sc_perfil import emulacao_ligada  # noqa: E402

CABECA = '# Perfil sintético\n\n## Missão\nSintético.\n\n## Modo emulação (Q147)\n'


class AchadosDoPerfil(unittest.TestCase):
    """A chave `Emulação` liga o modo que afrouxa R1 a R3 e a independência: ligar sem querer é o erro caro."""

    @unittest.expectedFailure
    def test_A1_valor_ambiguo_sim_ou_nao_nao_liga_a_emulacao(self):
        """A-1 (médio, F1): o parser lê só a primeira palavra do valor. Hoje: `sim | não`, `sim ou não` e `sim/não`
        ligam a emulação (o texto de um modelo por preencher vira "ligado"). Esperado: valor ambíguo vale como desligado."""
        for valor in ('sim | não', 'sim ou não', 'sim/não (escolha)'):
            with self.subTest(valor=valor):
                self.assertFalse(emulacao_ligada(CABECA + f'- **Emulação:** {valor}\n'), valor)

    @unittest.expectedFailure
    def test_A2_linha_dentro_de_comentario_html_nao_liga_a_emulacao(self):
        """A-2 (médio, F1): o parser ignora blocos de código com cerca, mas não comentários HTML. Hoje: uma linha
        `sim` comentada de propósito (e vencendo a linha `não` que vem depois) liga a emulação. Esperado: desligada."""
        texto = CABECA + '<!--\n- **Emulação:** sim\n-->\n- **Emulação:** não\n'
        self.assertFalse(emulacao_ligada(texto))

    @unittest.expectedFailure
    def test_A3_linha_indentada_como_codigo_e_titulo_de_outra_secao_nao_ligam(self):
        """A-3 (baixo, F1): bloco de código por indentação (4 espaços) e uma seção cujo título só *cita* o modo
        ("Como desligar o modo emulação") ligam a emulação. Esperado: nenhum dos dois liga."""
        self.assertFalse(emulacao_ligada(CABECA + '    - **Emulação:** sim\n'), 'indentação de código')
        self.assertFalse(emulacao_ligada('# P\n\n## Como desligar o modo emulação\n- **Emulação:** sim\n'), 'título que cita')


class AchadosDoDecidir(Base):
    emulacao = 'sim'

    @unittest.expectedFailure
    def test_A4_decisor_nao_pode_ser_um_agente_do_perfil_via_git_config(self):
        """A-4 (alto, F4): na sessão em nuvem o `git config user.name` é o do agente (neste ambiente, o nome do próprio agente). Sem
        `--por`, o `decidir aceitar` grava o agente como quem decidiu e o status `aceite` aceita qualquer nome não vazio.
        Hoje: aceito. Esperado: nome que coincide com um agente do perfil (aqui, Gandalf) não vale como decisor."""
        p = self.p
        p.fluxo_ate_o_parecer()
        git(p.raiz, 'config', 'user.name', 'Gandalf')
        r = p.decidir('aceitar')
        self.assertNotEqual(r.returncode, 0, 'agente gravado como quem decide')

    @unittest.expectedFailure
    def test_A5_decisor_nao_pode_ser_um_agente_do_perfil_via_por(self):
        """A-5 (médio, F4): variante de A-4 com `--por Gandalf`. Nada no script distingue pessoa de agente; a única
        barreira real é o merge humano do PR. Esperado: `--por` com nome de agente do perfil é recusado."""
        p = self.p
        p.fluxo_ate_o_parecer()
        r = p.decidir('aceitar', '--por', 'Gandalf')
        self.assertNotEqual(r.returncode, 0, 'agente gravado como quem decide')

    @unittest.expectedFailure
    def test_A6_head_mais_antigo_nao_contorna_a_cauda_de_governanca(self):
        """A-6 (médio, F4): `decidir --head <sha>` escolhe o head da conferência da cauda. Hoje: com produto novo no
        ramo `etapa/soma` depois do parecer, `--head <SHA revisado>` faz o `decidir aceitar` passar localmente (o job
        `aceite` do PR ainda pegaria, mas o registro já foi gravado). Esperado: `--head` não pode ser anterior à ponta do ramo."""
        p = self.p
        p.fluxo_ate_o_parecer()
        p.commitar_produto()
        git(p.raiz, 'branch', '-f', 'etapa/soma', 'HEAD')
        r = p.decidir('aceitar', '--por', 'Odival Sintético', '--head', p.head)
        self.assertNotEqual(r.returncode, 0, 'aceite gravado ignorando o produto novo no ramo da etapa')

    @unittest.expectedFailure
    def test_A7_parecer_de_outra_etapa_nao_e_registrado(self):
        """A-7 (baixo, F4): o `revisar --parecer` não compara o campo `etapa:` do parecer com `--etapa`, nem o `base` de
        `base..head` com a base da etapa. Hoje: parecer rotulado "outra-etapa" entra na etapa `soma`. O SHA amarra, mas o
        texto arquivado fica errado. Esperado: recusa."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        r = p.revisar(p.escrever_parecer(etapa='outra-etapa'))
        self.assertNotEqual(r.returncode, 0, 'parecer de outra etapa registrado')


if __name__ == '__main__':
    unittest.main()
