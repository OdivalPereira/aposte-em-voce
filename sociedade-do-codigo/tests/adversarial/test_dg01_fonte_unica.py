"""Sondas DG-01 (B09): duas fontes de verdade no ciclo da etapa. Fechado pela B01 (`sc.py abrir` e `sc.py decidir`).

Achado original: o estado da etapa dependia do `rodada.md` escrito à mão, ao lado do registro, e as duas fontes
podiam divergir. Agora o estado deriva só de `registro.json`. Todas as sondas deste arquivo são verdes.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cenario import Base  # noqa: E402

ARQUIVOS_DE_CONTROLE_LEGADOS = ('rodada.md', 'historico.md', 'avaliacao.md')


class SondaDG01(Base):

    def legados_presentes(self):
        return [n for n in ARQUIVOS_DE_CONTROLE_LEGADOS if (self.p.soc / n).exists()]

    def test_DG01_abre_por_sc_abrir_e_fecha_por_sc_decidir_sem_rodada_md_nem_sc_rodada(self):
        """Achado: abrir e fechar uma etapa exigia o `sc_rodada` e o `rodada.md`. Reproduz: o ciclo inteiro roda só
        com `sc.py abrir/entregar/revisar/decidir`, nenhum arquivo de controle legado nasce e o estado vem do registro."""
        p = self.p
        self.ok(p.abrir())
        self.assertEqual(self.legados_presentes(), [], 'o abrir criou arquivo de controle legado')
        self.assertEqual(p.etapa()['estado'], 'aberta')
        self.ok(p.entregar())
        self.ok(p.revisar(p.escrever_parecer()))
        self.assertEqual(self.legados_presentes(), [])
        self.ok(p.decidir('aceitar', '--por', 'Odival Sintético'))
        self.assertEqual(self.legados_presentes(), [], 'o decidir criou ou exigiu arquivo de controle legado')
        etapa = p.etapa()
        self.assertEqual(etapa['estado'], 'encerrada')
        self.assertEqual([d['acao'] for d in etapa['decisoes']], ['aceitar'])
        tipos = [e['tipo'] for e in p.registro().eventos]
        for esperado in ('etapa_aberta', 'parecer_registrado', 'decisao_registrada', 'etapa_encerrada'):
            self.assertIn(esperado, tipos)

    def test_DG01_o_painel_mostra_o_estado_do_registro(self):
        """Achado: o painel podia contar uma história diferente da do registro. Reproduz: `sc.py estado` lê a etapa
        encerrada no registro, sem nenhum `rodada.md` em disco."""
        self.p.fluxo_ate_o_parecer()
        self.ok(self.p.decidir('aceitar', '--por', 'Odival Sintético'))
        r = self.ok(self.p.estado_md())
        linha = [l for l in r.stdout.splitlines() if l.startswith('| soma |')]
        self.assertEqual(len(linha), 1, r.stdout)
        self.assertIn('encerrada', linha[0])

    def test_DG01_rodada_md_escrito_a_mao_nao_move_o_estado_nem_destrava_o_aceite(self):
        """Achado: um `rodada.md` dizendo "tudo fechado" valia como prova. Reproduz: com a etapa aberta no registro,
        um `rodada.md` forjado (critério marcado, fatia fechada) não muda o estado e o `decidir aceitar` segue recusando."""
        p = self.p
        self.ok(p.abrir())
        (p.soc / 'rodada.md').write_text(
            '# Rodada soma\n\n- nivel: 2\n\n## Aceite\n- [x] portao\n\n## Fatias\n1. soma — fechada · prova: `tudo verde`\n'
            '\n## Achados abertos\n', encoding='utf-8')
        (p.soc / 'historico.md').write_text('03/10/2026 · Coordenador · soma · encerramento\nresultado: ok\n', encoding='utf-8')
        self.assertEqual(p.etapa()['estado'], 'aberta')
        self.assertFalse(p.etapa()['criterios']['portao']['atendido'])
        self.recusa(p.decidir('aceitar', '--por', 'Odival Sintético'), 'sem atestado')
        self.sem_decisao()
        r = self.ok(p.estado_md())
        linha = [l for l in r.stdout.splitlines() if l.startswith('| soma |')]
        self.assertEqual(len(linha), 1, r.stdout)
        self.assertIn('aberta', linha[0])

    def test_DG01_sem_registro_nao_ha_fallback_para_o_rodada_md(self):
        """Achado: na falta do registro, o fluxo caía no arquivo escrito à mão. Reproduz: só com `rodada.md` e sem
        `registro.json`, `decidir` recusa por registro ausente, em vez de aceitar o texto."""
        p = self.p
        (p.soc / 'rodada.md').write_text('# Rodada soma\n\n## Fatias\n1. soma — fechada\n', encoding='utf-8')
        self.assertFalse((p.soc / 'registro.json').exists())
        self.recusa(p.decidir('aceitar', '--por', 'Odival Sintético'), 'registro ilegível ou ausente')
        self.recusa(p.decidir('rejeitar', '--por', 'Odival Sintético'), 'registro ilegível ou ausente')
        self.assertFalse((p.soc / 'registro.json').exists(), 'a recusa criou registro')

    def test_DG01_registro_corrompido_nao_e_substituido_por_texto(self):
        """Achado: registro ilegível não pode virar "estado vazio" nem ser contornado. Reproduz: depois do `abrir`, o
        `registro.json` truncado faz `decidir` recusar com `erro:` e saída diferente de zero (falha fechada)."""
        p = self.p
        self.ok(p.abrir())
        (p.soc / 'registro.json').write_text('{"eventos": [', encoding='utf-8')
        r = p.decidir('aceitar', '--por', 'Odival Sintético')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('erro:', r.stderr)

    def test_DG01_um_abrir_repetido_nao_cria_segunda_verdade(self):
        """Achado: abrir de novo a mesma etapa ou outra em paralelo criava estados concorrentes. Reproduz: segundo
        `abrir` do mesmo ID e `abrir` de outra etapa com a primeira ativa são recusados e o registro fica com uma só etapa."""
        p = self.p
        self.ok(p.abrir())
        self.recusa(p.abrir(), 'já foi aberta')
        self.recusa(p.abrir('outra'), 'já existe etapa ativa')
        self.assertEqual([e['etapa_id'] for e in p.eventos('etapa_aberta')], ['soma'])


if __name__ == '__main__':
    unittest.main()
