"""Testes das permissões de merge em .claude/settings.json e adapters/claude/settings.json.modelo (A06).

Garante delimitação estrita de -s, -r, --squash, --rebase, --auto e --admin sem bloquear
opções legítimas com --merge ou -m (--repo, --subject, --body, etc.).
"""
import fnmatch
import json
import sys
import unittest
from pathlib import Path

PASTA_TESTES = Path(__file__).resolve().parent
if str(PASTA_TESTES) not in sys.path:
    sys.path.insert(0, str(PASTA_TESTES))

from util import RAIZ

ARQUIVOS_CONFIG = [
    RAIZ.parent / '.claude' / 'settings.json',
    RAIZ / 'adapters' / 'claude' / 'settings.json.modelo',
]


def _casar(cmd: str, padroes: list[str]) -> bool:
    return any(
        fnmatch.fnmatchcase(cmd, p[5:-1])
        for p in padroes
        if p.startswith('Bash(') and p.endswith(')')
    )


class TestPermissoesMerge(unittest.TestCase):
    def setUp(self):
        self.configs = {}
        for arq in ARQUIVOS_CONFIG:
            self.assertTrue(arq.is_file(), f"Arquivo não encontrado: {arq}")
            dados = json.loads(arq.read_text(encoding='utf-8'))
            self.assertIn('permissions', dados, f"Sem chave 'permissions' em {arq}")
            self.configs[arq.name] = dados['permissions']

    def test_arquivos_possuem_ask_e_deny(self):
        for nome, perms in self.configs.items():
            self.assertIn('ask', perms, f"Sem chave 'ask' em {nome}")
            self.assertIn('deny', perms, f"Sem chave 'deny' em {nome}")
            self.assertIn("Bash(gh pr merge*)", perms['ask'], f"Sem ask padrão em {nome}")

    def test_sem_curingas_genericos_que_causam_regressao_a06(self):
        """A06: curingas genéricos *-s* e *-r* capturam --subject e --repo e devem ser eliminados."""
        for nome, perms in self.configs.items():
            deny = perms['deny']
            self.assertNotIn("Bash(gh pr merge*-s*)", deny, f"Curinga genérico -s ainda presente em {nome}")
            self.assertNotIn("Bash(gh pr merge*-r*)", deny, f"Curinga genérico -r ainda presente em {nome}")

    def test_opcoes_proibidas_presentes_em_deny(self):
        """As opções proibidas devem constar delimitadas nas permissões deny."""
        padroes_obrigatorios = [
            "Bash(gh pr merge*--squash*)",
            "Bash(gh pr merge* -s *)",
            "Bash(gh pr merge* -s)",
            "Bash(gh pr merge*--rebase*)",
            "Bash(gh pr merge* -r *)",
            "Bash(gh pr merge* -r)",
            "Bash(gh pr merge*--auto*)",
            "Bash(gh pr merge*--admin*)",
        ]
        for nome, perms in self.configs.items():
            deny = perms['deny']
            for padrao in padroes_obrigatorios:
                self.assertIn(padrao, deny, f"Padrão {padrao} ausente em {nome}")

    def test_tabela_aceite_pedem_confirmacao_ask_true_deny_false(self):
        """Caminho legítimo: ask=True e deny=False para merge commit com opções válidas."""
        casos = [
            'gh pr merge 12 --merge',
            'gh pr merge 12 -m',
            'gh pr merge 123 --merge',
            'gh pr merge 123 -m',
            'gh pr merge 123 --merge --repo O/P',
            'gh pr merge 123 --merge --repo Organizacao/Projeto',
            'gh pr merge 123 --merge --subject "x"',
            'gh pr merge 123 --merge --subject "Etapa d1"',
            'gh pr merge 123 --merge --body "x"',
            'gh pr merge 123 --merge --body "texto longo"',
            'gh pr merge 123 -m --repo O/P',
            'gh pr merge 123 -m --subject "x"',
            'gh pr merge 123 -m --body "x"',
            'gh pr merge 123 -m -d',
            'gh pr merge 123 --merge -d',
            'gh pr merge 123 --merge --delete-branch',
            'gh pr merge --merge',
            'gh pr merge -m',
        ]
        for nome, perms in self.configs.items():
            for cmd in casos:
                with self.subTest(arquivo=nome, comando=cmd):
                    ask = _casar(cmd, perms.get('ask', []))
                    deny = _casar(cmd, perms.get('deny', []))
                    self.assertTrue(ask, f"Esperado ask=True para '{cmd}' em {nome}")
                    self.assertFalse(deny, f"Esperado deny=False para '{cmd}' em {nome}")

    def test_tabela_aceite_sao_negados_deny_true(self):
        """Opções proibidas e combinações: deny=True."""
        casos = [
            'gh pr merge 12 --squash',
            'gh pr merge 12 -s',
            'gh pr merge 12 --rebase',
            'gh pr merge 12 -r',
            'gh pr merge 12 --auto',
            'gh pr merge 12 --admin',
            'gh pr merge 123 --squash',
            'gh pr merge 123 -s',
            'gh pr merge 123 --rebase',
            'gh pr merge 123 -r',
            'gh pr merge 123 --auto',
            'gh pr merge 123 --admin',
            'gh pr merge --squash',
            'gh pr merge -s',
            'gh pr merge --rebase',
            'gh pr merge -r',
            'gh pr merge --auto',
            'gh pr merge --admin',
            'gh pr merge -s 123',
            'gh pr merge -r 123',
            'gh pr merge --squash 123',
            'gh pr merge --rebase 123',
            'gh pr merge --auto 123',
            'gh pr merge --admin 123',
            # Combinações
            'gh pr merge 123 --merge --squash',
            'gh pr merge 123 --merge -s',
            'gh pr merge 123 -s --merge',
            'gh pr merge 123 --merge --rebase',
            'gh pr merge 123 --merge -r',
            'gh pr merge 123 -r --merge',
            'gh pr merge 123 --merge --auto',
            'gh pr merge 123 --merge --admin',
            'gh pr merge 123 -s --auto',
            'gh pr merge 123 -r --auto',
            'gh pr merge 123 -s --admin',
            'gh pr merge 123 -r --admin',
            'gh pr merge 123 --squash --admin',
            'gh pr merge 123 --rebase --admin',
            'gh pr merge 123 --squash --auto',
            'gh pr merge 123 --rebase --auto',
        ]
        for nome, perms in self.configs.items():
            for cmd in casos:
                with self.subTest(arquivo=nome, comando=cmd):
                    deny = _casar(cmd, perms.get('deny', []))
                    self.assertTrue(deny, f"Esperado deny=True para '{cmd}' em {nome}")

    def test_sonda_A06_configuracoes_equivalente(self):
        """Replicação exata da sonda test_A06_configuracoes de Barbárvore contra W."""
        comandos = [
            'gh pr merge 123 --merge',
            'gh pr merge 123 -m',
            'gh pr merge 123 -s',
            'gh pr merge 123 -r',
            'gh pr merge 123 --squash',
            'gh pr merge 123 --rebase',
            'gh pr merge 123 --auto',
            'gh pr merge 123 --admin',
        ]
        for nome, perms in self.configs.items():
            for cmd in comandos:
                with self.subTest(arquivo=nome, comando=cmd):
                    ask = _casar(cmd, perms.get('ask', []))
                    deny = _casar(cmd, perms.get('deny', []))
                    self.assertTrue(ask, f"Esperado ask=True para '{cmd}' em {nome}")
                    esperado_deny = not (cmd.endswith('--merge') or cmd.endswith('-m'))
                    self.assertEqual(
                        deny,
                        esperado_deny,
                        f"Esperado deny={esperado_deny} para '{cmd}' em {nome}, obtido {deny}",
                    )

    def test_sonda_A06_caminho_legitimo_equivalente(self):
        """Replicação exata da sonda test_A06_caminho_legitimo de Barbárvore contra W."""
        comandos = [
            'gh pr merge 123 --merge --repo Organizacao/Projeto',
            'gh pr merge 123 --merge --subject "Etapa d1"',
        ]
        for nome, perms in self.configs.items():
            deny = perms.get('deny', [])
            for cmd in comandos:
                with self.subTest(arquivo=nome, comando=cmd):
                    padroes_casados = [
                        p for p in deny
                        if p.startswith('Bash(') and fnmatch.fnmatchcase(cmd, p[5:-1])
                    ]
                    self.assertFalse(
                        padroes_casados,
                        f"Caminho legítimo bloqueado em {nome}: '{cmd}' casou com {padroes_casados}",
                    )


if __name__ == '__main__':
    unittest.main()
