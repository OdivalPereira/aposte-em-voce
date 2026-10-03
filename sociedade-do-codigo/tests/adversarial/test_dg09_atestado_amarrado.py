"""Sondas DG-09 (B11, correção F1c): o aceite e o status `portao` só valem para o atestado do `sc.py entregar`.

Achados da revisão interna da F1: (1) um atestado avulso (`sc_pre_devolucao.py --comando-teste true`, sem `portao`)
passava no `decidir aceitar` e no status; (2) `--area X` gravava APROVADO sem as demais áreas tocadas; (4) o perfil era
lido do disco e nada o comparava depois (trocar o perfil só para rodar o portão e restaurar). Todas verdes.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cenario import NUCLEO, TESTE_PROJETO, Base, AMBIENTE, rodar, sc_status, texto_perfil  # noqa: E402

PRE_DEVOLUCAO = NUCLEO / 'scripts' / 'sc_pre_devolucao.py'
POR = ('--por', 'Odival Sintético')
DUAS_AREAS = ('| projeto | `.` | `{T}` | 120 | `*` |\n| pacote | `.` | `{T}` | 120 | `pacote/` |').replace('{T}', TESTE_PROJETO)


def perfil_com_duas_areas():
    texto = texto_perfil('sim')
    unica = f'| projeto | `.` | `{TESTE_PROJETO}` | 120 | `*` |'
    assert unica in texto
    return texto.replace(unica, DUAS_AREAS)


class SondaAtestadoAvulso(Base):

    def _avulso(self, p):
        """O atestado que o portão antigo dava: sem `--portao-por-area`, com `--comando-teste true`."""
        res = rodar(PRE_DEVOLUCAO, '--etapa', 'soma', '--base', p.base, '--pasta-projeto', p.raiz, '--pasta-sociedade', p.soc,
                    '--comando-teste', 'true', '--saida-json', p.atestado(), cwd=p.raiz, env=AMBIENTE)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        at = json.loads(p.atestado().read_text(encoding='utf-8'))
        self.assertEqual((at['status'], at['versao']), ('APROVADO', '1.2.0'))
        self.assertNotIn('portao', at)

    def test_DG09_decidir_recusa_atestado_avulso(self):
        """Achado 1: com `--comando-teste true` fora do `sc.py`, o atestado saía APROVADO 1.2.0 sem `portao` e o
        `decidir aceitar` o aceitava. Esperado: recusa e nenhuma decisão registrada."""
        p = self.p
        self.ok(p.abrir())
        self._avulso(p)
        self.ok(p.revisar(p.escrever_parecer()))
        self.recusa(p.decidir('aceitar', *POR), 'atestado recusado')
        self.sem_decisao()

    def test_DG09_status_portao_fica_vermelho_com_atestado_avulso(self):
        """Achado 1: o status `portao` dava verde para o atestado avulso commitado. Esperado: vermelho."""
        p = self.p
        self.ok(p.abrir())
        self._avulso(p)
        head = p.commitar_governanca()
        r = sc_status.verificar_portao(p.raiz, 'etapa/soma', head)
        self.assertFalse(r['ok'], r['motivo'])
        self.assertIn('portão por área', r['motivo'])

    def test_DG09_controle_atestado_do_entregar_passa_no_decidir_e_no_status(self):
        """Controle (verde): o atestado oficial, com o perfil intacto, passa nos dois."""
        p = self.p
        p.fluxo_ate_o_parecer()
        head = p.commitar_governanca()
        self.assertTrue(sc_status.verificar_portao(p.raiz, 'etapa/soma', head)['ok'])
        self.ok(p.decidir('aceitar', *POR))


class SondaCobertura(Base):
    perfil = None

    def setUp(self):
        self.perfil = perfil_com_duas_areas()
        super().setUp()
        (self.p.raiz / 'pacote').mkdir()
        self.p.commitar_produto('pacote/x.py')
        self.p.head = self.p.topo()

    def _atestado(self):
        return json.loads(self.p.atestado().read_text(encoding='utf-8'))

    def test_DG09_area_sozinha_nao_da_aceite(self):
        """Achado 2: `entregar --area projeto` gravava APROVADO sem rodar `pacote`, que o candidato também toca, e o
        aceite passava. Esperado: o atestado grava as áreas tocadas e `cobertura_completa` falso; o `decidir` e o status
        recusam."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar('soma', '--area', 'projeto'))
        portao = self._atestado()['portao']
        self.assertEqual(portao['areas_tocadas'], ['projeto', 'pacote'])
        self.assertEqual([a['area'] for a in portao['areas']], ['projeto'])
        self.assertIs(portao['cobertura_completa'], False)
        self.ok(p.revisar(p.escrever_parecer()))
        self.recusa(p.decidir('aceitar', *POR), 'não cobre todas as áreas')
        self.sem_decisao()
        r = sc_status.verificar_portao(p.raiz, 'etapa/soma', p.commitar_governanca())
        self.assertFalse(r['ok'])
        self.assertIn('não cobre todas as áreas', r['motivo'])

    def test_DG09_controle_sem_area_cobre_tudo_e_aceita(self):
        """Controle (verde): sem `--area` roda as duas áreas tocadas, a cobertura é completa e o aceite passa."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        portao = self._atestado()['portao']
        self.assertEqual(portao['areas_tocadas'], ['projeto', 'pacote'])
        self.assertIs(portao['cobertura_completa'], True)
        self.ok(p.revisar(p.escrever_parecer()))
        self.ok(p.decidir('aceitar', *POR))


class SondaPerfilTrocado(Base):

    def test_DG09_perfil_trocado_so_para_rodar_o_portao_nao_da_aceite(self):
        """Achado 4: o portão lê o perfil do disco e nada o comparava depois. Reproduz: troca o comando do perfil, roda o
        `entregar`, restaura o perfil. Esperado: o `decidir` e o status recusam (SHA-256 do perfil diferente)."""
        p = self.p
        perfil = p.soc / 'perfil.md'
        original = perfil.read_text(encoding='utf-8')
        self.ok(p.abrir())
        perfil.write_text(original.replace(f'`{TESTE_PROJETO}`', f'`{TESTE_PROJETO} -k soma`'), encoding='utf-8')
        self.ok(p.entregar())
        perfil.write_text(original, encoding='utf-8')
        self.ok(p.revisar(p.escrever_parecer()))
        self.recusa(p.decidir('aceitar', *POR), 'perfil mudou')
        self.sem_decisao()
        r = sc_status.verificar_portao(p.raiz, 'etapa/soma', p.commitar_governanca())
        self.assertFalse(r['ok'])
        self.assertIn('perfil mudou', r['motivo'])

    def test_DG09_perfil_sem_commit_igual_ao_do_portao_aceita(self):
        """Controle (verde): o perfil da `sociedade/` do worktree fica sem commit durante a etapa, por desenho: o que
        vale é ele ser o mesmo do portão. Muda uma linha antes do `abrir` e deixa sem commit; o aceite passa."""
        p = self.p
        perfil = p.soc / 'perfil.md'
        perfil.write_text(perfil.read_text(encoding='utf-8') + '\n## Nota\n- sem commit\n', encoding='utf-8')
        p.fluxo_ate_o_parecer()
        self.ok(p.decidir('aceitar', *POR))


if __name__ == '__main__':
    unittest.main()
