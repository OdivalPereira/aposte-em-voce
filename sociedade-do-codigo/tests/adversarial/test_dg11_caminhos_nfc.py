"""Sondas DG-11 (B11): caminho com acento em NFD e espaço no nome. Fechado pela B11 (`core.quotepath=off -z` e NFC).

Achado original: o Git devolvia o nome entre aspas e com escapes octais (`"relato\\314\\201rio final.md"`), a lista de
arquivos do atestado e o `arquivos_em` da conferência erravam o nome, e a mesma palavra em NFC e NFD não casava.
Agora: caminhos lidos com `-z`, sem aspas, e normalizados em NFC. Todas as sondas deste arquivo são verdes.
"""
import json
import sys
import unicodedata
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cenario import Base, commit  # noqa: E402

NFC = unicodedata.normalize('NFC', 'relatório final.md')
NFD = unicodedata.normalize('NFD', NFC)


class SondaDG11(Base):

    def setUp(self):
        super().setUp()
        self.assertNotEqual(NFC, NFD)  # a sonda só vale se as duas formas diferem
        (self.p.raiz / NFD).write_text('# Relatório sintético\n', encoding='utf-8')
        self.head_nfd = commit(self.p.raiz, 'docs: relatório com nome em NFD')
        self.p.head = self.head_nfd

    def _ordem_com_entregas(self, *prefixos):
        ordem = self.p.tmp / 'conferir.md'
        ordem.write_text('# Ordem sintética\n\n```entregas\nE1 | arquivos_em | ' + f'{self.p.base}..{self.p.head}'
                         + ' | ' + ' | '.join(prefixos) + '\n```\n', encoding='utf-8')
        return ordem

    def test_DG11_nome_nfd_com_espaco_aparece_certo_na_lista_do_atestado(self):
        """Achado: o nome do arquivo saía entre aspas, com escapes octais, ou em NFD. Reproduz: arquivo `relatório final.md`
        com o acento decomposto (NFD) e espaço; a lista do atestado e os hashes trazem o nome em NFC, inteiro e sem aspas."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        at = json.loads(p.atestado().read_text(encoding='utf-8'))
        self.assertEqual(at['status'], 'APROVADO')
        self.assertIn(NFC, at['arquivos_inspecionados'])
        self.assertIn(NFC, at['hashes_artefatos'])
        for nome in at['arquivos_inspecionados']:
            self.assertEqual(nome, unicodedata.normalize('NFC', nome))
            self.assertNotIn('\\', nome)
            self.assertFalse(nome.startswith('"'), nome)
        self.assertEqual(at['total_arquivos_inspecionados'], len(at['arquivos_inspecionados']))

    def test_DG11_arquivos_em_confere_o_nome_nfd_com_prefixo_nfc(self):
        """Achado: o `arquivos_em` comparava o prefixo com o nome escapado e reprovava o que estava certo. Reproduz:
        o prefixo em NFC casa com o arquivo gravado em NFD."""
        p = self.p
        ordem = self._ordem_com_entregas('soma.py', 'tests/', NFC)
        r = self.ok(p.sc('conferir', '--ordem', ordem, '--raiz', p.raiz, '--json'))
        item = json.loads(r.stdout)['itens'][0]
        self.assertEqual(item['estado'], 'feito', item)

    def test_DG11_arquivos_em_nomeia_o_arquivo_fora_do_prefixo_sem_aspas(self):
        """Reproduz: sem o prefixo do relatório, a entrega fica "não feita" e a mensagem traz o nome em NFC, inteiro."""
        p = self.p
        ordem = self._ordem_com_entregas('soma.py', 'tests/')
        r = p.sc('conferir', '--ordem', ordem, '--raiz', p.raiz, '--json')
        self.assertNotEqual(r.returncode, 0)
        item = json.loads(r.stdout)['itens'][0]
        self.assertEqual(item['estado'], 'não feito')
        self.assertIn(NFC, item['detalhe'])
        self.assertNotIn('\\3', item['detalhe'])

    def test_DG11_arquivo_nfd_novo_sem_commit_reprova_a_arvore_suja_pelo_nome_certo(self):
        """Reproduz: arquivo NFD com espaço, novo e sem commit. A árvore suja reprova e o erro cita o nome em NFC."""
        p = self.p
        self.ok(p.abrir())
        (p.raiz / unicodedata.normalize('NFD', 'rascunho útil.txt')).write_text('x\n', encoding='utf-8')
        p.entregar()
        at = json.loads(p.atestado().read_text(encoding='utf-8'))
        self.assertEqual(at['status'], 'REPROVADO')
        self.assertTrue(any('Árvore suja' in e and 'rascunho útil.txt' in e for e in at['erros']), at['erros'])
        self.assertEqual(at['verificacoes']['arvore_limpa']['suja'], [unicodedata.normalize('NFC', 'rascunho útil.txt')])


if __name__ == '__main__':
    unittest.main()
