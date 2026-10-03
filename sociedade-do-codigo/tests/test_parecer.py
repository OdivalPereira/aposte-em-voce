import tempfile
import unittest
from pathlib import Path

from util import SKILLS, rodar

LINT = SKILLS / 'sc-revisao' / 'scripts' / 'lint_parecer.py'
MODELO = SKILLS / 'sc-revisao' / 'assets' / 'parecer-modelo.md'

PARECER = """## Parecer do Revisor Independente
- rodada: NT-02
- fatia ou fechamento: 1
- entrega: PR 34
- base..head: a1b2c3d..e4f5a6b
- revisor: Claude Code · fornecedor: Anthropic · sessão: sess_abc123
- veredito: aceitar com ressalvas
- data: 19/09/2026 15:30

### Independência
Não implementei nem corrigi nada desta entrega, e não vou corrigir. Implementação do fornecedor Google; revisão de fornecedor diferente.

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| Cobre datas inválidas | `npm test -- formatarData` passou | executada |
| API pública intacta | diff de `src/index.ts` sem mudanças | lida |
| Funciona no celular | não exercitado | não verificada |

### Achados
- [relevante] mensagem de erro em inglês (src/utils/formatarData.ts:41)

### O que não verifiquei
- Comportamento no celular (sem navegador nesta sessão).
"""


class TesteParecer(unittest.TestCase):
    def arquivo(self, texto):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        a = Path(d.name) / 'parecer.md'
        a.write_text(texto, encoding='utf-8')
        return a

    def rodar(self, texto):
        return rodar(LINT, self.arquivo(texto))

    def test_parecer_valido(self):
        r = self.rodar(PARECER)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_aceitar_com_criterio_nao_verificado_e_erro(self):
        r = self.rodar(PARECER.replace('veredito: aceitar com ressalvas', 'veredito: aceitar'))
        self.assertEqual(r.returncode, 1)
        self.assertIn('não combina', r.stdout)

    def test_bloqueador_pede_nao_aceitar(self):
        texto = PARECER.replace('[relevante]', '[bloqueador]')
        self.assertEqual(self.rodar(texto).returncode, 1)
        self.assertEqual(self.rodar(texto.replace('aceitar com ressalvas', 'não aceitar')).returncode, 0)

    def test_estado_invalido(self):
        r = self.rodar(PARECER.replace('| lida |', '| talvez |'))
        self.assertEqual(r.returncode, 1)
        self.assertIn('estado inválido', r.stdout)

    def test_secao_nao_verifiquei_obrigatoria(self):
        i = PARECER.index('### O que não verifiquei')
        r = self.rodar(PARECER[:i])
        self.assertEqual(r.returncode, 1)
        self.assertIn('O que não verifiquei', r.stdout)

    def test_revisor_precisa_declarar_sessao_e_fornecedor(self):
        r = self.rodar(PARECER.replace(' · fornecedor: Anthropic · sessão: sess_abc123', ''))
        self.assertEqual(r.returncode, 1)
        self.assertIn('sessão', r.stdout)
        r = self.rodar(PARECER.replace(' · fornecedor: Anthropic', ''))
        self.assertEqual(r.returncode, 1)
        self.assertIn('fornecedor', r.stdout)

    def test_shas_mal_formados(self):
        r = self.rodar(PARECER.replace('a1b2c3d..e4f5a6b', 'main..HEAD'))
        self.assertEqual(r.returncode, 1)

    def test_modelo_cru_reprovado(self):
        r = rodar(LINT, MODELO)
        self.assertEqual(r.returncode, 1)


if __name__ == '__main__':
    unittest.main()
