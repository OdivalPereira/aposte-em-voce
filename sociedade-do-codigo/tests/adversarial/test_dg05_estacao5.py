"""Sondas DG-05 (B09): estação 5 (revisão) de ponta a ponta. Fechado pela B04 (modelo de parecer que passa no
`lint_parecer`) e pela B01 (`sc.py revisar --parecer` registra sem passo manual). Todas as sondas são verdes.

Achado original: o modelo de parecer entregue ao revisor não passava no `lint_parecer` e o parecer chegava ao
registro por passos manuais (colar, editar, rodar o `sc_rodada parecer`).
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cenario import (AMBIENTE, LINT, MODELO_PARECER, NUCLEO, Base, git, preencher_modelo_de_parecer, rodar)  # noqa: E402

POR = ('--por', 'Odival Sintético')


class SondaDG05(Base):

    def lint(self, texto):
        arq = self.p.tmp / 'parecer-lint.md'
        arq.write_text(texto, encoding='utf-8')
        return rodar(LINT, arq, env=AMBIENTE)

    def modelo_preenchido(self, **kw):
        return preencher_modelo_de_parecer(self.p.head, self.p.base, **kw)

    def test_DG05_modelo_de_parecer_preenchido_passa_no_lint(self):
        """Achado: o modelo que o revisor recebe não passava no `lint_parecer`. Reproduz: o `parecer-modelo.md` do pacote,
        com cada marcador trocado por dado sintético (e nenhum marcador sobrando), sai do lint com código 0."""
        r = self.lint(self.modelo_preenchido())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_DG05_modelo_cru_nao_passa_no_lint(self):
        """Controle: o lint não aprova o modelo intacto, com os marcadores `<...>`. Um lint que aprova tudo não prova nada."""
        r = self.lint(MODELO_PARECER.read_text(encoding='utf-8'))
        self.assertNotEqual(r.returncode, 0, r.stdout)

    def test_DG05_o_modelo_exige_a_linha_commit(self):
        """Achado: o parecer não ligava a revisão a um SHA. Reproduz: o modelo traz a linha `- commit:` e o parecer
        preenchido sem ela reprova no lint."""
        self.assertRegex(MODELO_PARECER.read_text(encoding='utf-8'), r'(?m)^- commit:')
        sem_commit = re.sub(r'(?m)^- commit:.*\n', '', self.modelo_preenchido())
        r = self.lint(sem_commit)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn('commit', r.stdout.lower() + r.stderr.lower())

    def test_DG05_commit_vazio_malformado_ou_de_outro_head_reprova(self):
        """Achado: `commit:` aceito sem valor ou com SHA que não é o head revisado. Reproduz quatro casos de reprovação."""
        p = self.p
        base = self.modelo_preenchido()
        casos = {'vazio': ('- commit: ' + p.head, '- commit: '),
                 'marcador': ('- commit: ' + p.head, '- commit: <SHA>'),
                 'malformado': ('- commit: ' + p.head, '- commit: nao-e-sha'),
                 'outro head': ('- commit: ' + p.head, '- commit: ' + p.base)}
        for nome, (de, para) in casos.items():
            with self.subTest(caso=nome):
                self.assertIn(de, base)
                r = self.lint(base.replace(de, para))
                self.assertNotEqual(r.returncode, 0, r.stdout)

    def test_DG05_revisar_parecer_registra_sem_passo_manual_e_o_decidir_segue(self):
        """Achado: do parecer escrito ao registro havia colagem e edição à mão. Reproduz: o modelo preenchido é só
        entregue a `sc.py revisar --parecer`; o registro recebe o parecer com o `commit`, a cópia vai para
        `sociedade/pareceres/` e o `decidir aceitar` fecha a etapa, sem editar nenhum arquivo de controle."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        arq = p.tmp / 'parecer-do-revisor.md'
        arq.write_text(self.modelo_preenchido(), encoding='utf-8')
        r = self.ok(p.revisar(arq))
        self.assertIn('registrado', r.stdout)
        eventos = p.eventos('parecer_registrado')
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]['commit'], p.head)
        self.assertEqual(eventos[0]['veredito'], 'aceitar')
        copia = p.soc / 'pareceres' / 'parecer-soma.md'
        self.assertTrue(copia.is_file())
        self.assertEqual(copia.read_text(encoding='utf-8'), arq.read_text(encoding='utf-8'))
        self.ok(p.decidir('aceitar', *POR))
        self.assertEqual(p.etapa()['estado'], 'encerrada')

    def test_DG05_revisar_parecer_recusa_o_que_o_lint_reprova_e_nao_registra(self):
        """Achado: parecer inválido entrava no registro. Reproduz: modelo cru, parecer sem `commit:` e parecer com
        achado bloqueador e veredito "aceitar" são recusados por `revisar --parecer` e o registro fica sem parecer."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        cru = p.tmp / 'cru.md'
        cru.write_text(MODELO_PARECER.read_text(encoding='utf-8'), encoding='utf-8')
        sem_commit = p.tmp / 'sem-commit.md'
        sem_commit.write_text(re.sub(r'(?m)^- commit:.*\n', '', self.modelo_preenchido()), encoding='utf-8')
        incoerente = p.tmp / 'incoerente.md'
        incoerente.write_text(self.modelo_preenchido().replace('\nnenhum\n', '\n- [bloqueador] L1 · defeito (soma.py:1)\n'),
                              encoding='utf-8')
        for arq in (cru, sem_commit, incoerente):
            with self.subTest(arquivo=arq.name):
                self.recusa(p.revisar(arq), 'parecer')
        self.assertEqual(p.eventos('parecer_registrado'), [])
        self.assertFalse((p.soc / 'pareceres' / 'parecer-soma.md').exists())

    def test_DG05_parecer_do_modelo_gerado_pelo_pacote_de_revisao_passa_no_lint(self):
        """Achado: o modelo embutido no pacote de revisão (`sc_passagem exportar-revisao`) divergia do `parecer-modelo.md`.
        Reproduz: o bloco de parecer do pacote traz `- commit:` e a seção "O que não verifiquei"."""
        p = self.p
        self.ok(p.abrir())
        saida = p.tmp / 'pacote.md'
        self.ok(rodar(NUCLEO / 'scripts' / 'sc_passagem.py', 'exportar-revisao', '--pasta-projeto', p.raiz,
                      '--pasta-sociedade', p.soc, '--etapa', 'soma', '--base', p.base, '--head', p.head,
                      '--revisor', 'Barbárvore', '--fornecedor-revisor', 'Anthropic', '--saida', saida, env=AMBIENTE))
        modelo = saida.read_text(encoding='utf-8').split('```markdown\n', 1)[1].split('```', 1)[0]
        self.assertIn(f'- commit: {p.head}', modelo)
        self.assertIn('### O que não verifiquei', modelo)
        self.assertIn('### Independência', modelo)
        self.assertEqual(git(p.raiz, 'rev-parse', 'HEAD'), p.head)


if __name__ == '__main__':
    unittest.main()
