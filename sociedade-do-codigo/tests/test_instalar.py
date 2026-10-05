import json
import tempfile
import unittest
from pathlib import Path

from util import RAIZ, SKILLS, rodar

INSTALAR = RAIZ / 'scripts' / 'instalar.py'
NOMES = sorted(p.name for p in SKILLS.iterdir() if p.is_dir())


class TesteInstalar(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def inst(self, *args):
        return rodar(INSTALAR, '--home', self.home, *args)

    def test_simulacao_nao_cria_nada(self):
        r = self.inst('--alvo', 'claude,codex')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Simulação', r.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_aplicar_copia_para_cada_alvo(self):
        r = self.inst('--alvo', 'claude,codex,antigravity,antigravity-cli', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for base in ('.claude/skills', '.agents/skills', '.gemini/config/skills', '.gemini/antigravity-cli/skills'):
            for nome in NOMES:
                self.assertTrue((self.home / base / nome / 'SKILL.md').is_file(), f'{base}/{nome}')
        self.assertTrue((self.home / '.sociedade-do-codigo' / 'instalado.json').is_file())

    def test_agentes_so_onde_existem(self):
        self.inst('--alvo', 'claude,antigravity,codex', '--agentes', '--aplicar')
        self.assertTrue((self.home / '.claude/agents/barbarvore.md').is_file())
        self.assertTrue((self.home / '.gemini/config/agents/legolas.md').is_file())

    def test_idempotente_e_protege_alteracao_do_usuario(self):
        self.inst('--alvo', 'codex', '--aplicar')
        r = self.inst('--alvo', 'codex', '--aplicar')
        self.assertEqual(r.returncode, 0)
        self.assertNotIn('criar', r.stdout.replace('criar arquivo', ''))
        alvo = self.home / '.agents/skills/sc-papeis/SKILL.md'
        alvo.write_text(alvo.read_text(encoding='utf-8') + '\n# ajuste meu\n', encoding='utf-8')
        r = self.inst('--alvo', 'codex', '--aplicar')
        self.assertEqual(r.returncode, 1)
        self.assertIn('CONFLITO', r.stdout)
        self.assertIn('# ajuste meu', alvo.read_text(encoding='utf-8'))
        r = self.inst('--alvo', 'codex', '--aplicar', '--substituir')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn('# ajuste meu', alvo.read_text(encoding='utf-8'))
        copias = list((self.home / '.sociedade-do-codigo' / 'backup').rglob('SKILL.md'))
        self.assertTrue(any('# ajuste meu' in c.read_text(encoding='utf-8') for c in copias))

    def test_nao_sobrescreve_o_que_ja_existia_sem_registro(self):
        pasta = self.home / '.claude/skills/sc-papeis'
        pasta.mkdir(parents=True)
        (pasta / 'SKILL.md').write_text('meu conteúdo', encoding='utf-8')
        r = self.inst('--alvo', 'claude', '--skills', 'sc-papeis', '--aplicar')
        self.assertEqual(r.returncode, 1)
        self.assertEqual((pasta / 'SKILL.md').read_text(encoding='utf-8'), 'meu conteúdo')

    def test_remover_so_o_que_foi_instalado(self):
        self.inst('--alvo', 'codex', '--aplicar')
        estranha = self.home / '.agents/skills/minha-skill'
        estranha.mkdir()
        (estranha / 'SKILL.md').write_text('x', encoding='utf-8')
        r = self.inst('--alvo', 'codex', '--remover', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for nome in NOMES:
            self.assertFalse((self.home / '.agents/skills' / nome).exists())
        self.assertTrue((estranha / 'SKILL.md').is_file())

    def test_recusa_link_simbolico(self):
        externo = tempfile.TemporaryDirectory()
        self.addCleanup(externo.cleanup)
        (self.home / '.agents').symlink_to(externo.name)
        r = self.inst('--alvo', 'codex', '--aplicar')
        self.assertEqual(r.returncode, 1)
        self.assertEqual(list(Path(externo.name).iterdir()), [])

    def test_alvo_invalido(self):
        self.assertEqual(self.inst('--alvo', 'foo').returncode, 2)

    def test_nao_toca_em_configuracoes(self):
        cfg = self.home / '.claude' / 'settings.json'
        cfg.parent.mkdir(parents=True)
        cfg.write_text('{"a": 1}', encoding='utf-8')
        self.inst('--alvo', 'claude', '--agentes', '--aplicar')
        self.assertEqual(cfg.read_text(encoding='utf-8'), '{"a": 1}')

    def test_adaptadores_todos_possuem_leia_me(self):
        adaptadores = RAIZ / 'adapters'
        for nome in ('antigravity', 'claude', 'codex', 'jules'):
            leia_me = adaptadores / nome / 'LEIA-ME.md'
            self.assertTrue(leia_me.is_file(), f'LEIA-ME.md ausente em {nome}')
            self.assertGreater(len(leia_me.read_text(encoding='utf-8')), 50)

    def test_agentes_antigravity_e_claude_completos(self):
        r = self.inst('--alvo', 'antigravity,claude', '--agentes', '--aplicar')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        
        # 3.0.0: só os especialistas; revisão Google é interna (D-RT-001); locais são módulo opcional
        esperados_ag = ['aragorn.md', 'elrond.md', 'galadriel.md', 'legolas.md']
        pasta_ag = self.home / '.gemini/config/agents'
        for esp in esperados_ag:
            arq = pasta_ag / esp
            self.assertTrue(arq.is_file(), f'Agente {esp} ausente no Antigravity')
            conteudo = arq.read_text(encoding='utf-8')
            self.assertTrue(conteudo.startswith('---\n'), f'{esp} sem frontmatter')
            self.assertIn('name: ', conteudo)
            self.assertIn('description: ', conteudo)

        pasta_claude = self.home / '.claude/agents'
        revisor_claude = pasta_claude / 'barbarvore.md'
        self.assertTrue(revisor_claude.is_file())
        conteudo_c = revisor_claude.read_text(encoding='utf-8')
        self.assertTrue(conteudo_c.startswith('---\n'))
        self.assertIn('name: barbarvore', conteudo_c)

    def test_agentes_revisor_somente_leitura(self):
        self.inst('--alvo', 'antigravity,claude', '--agentes', '--aplicar')
        self.assertFalse((self.home / '.gemini/config/agents/revisor-independente.md').exists())
        rev_cl = (self.home / '.claude/agents/barbarvore.md').read_text(encoding='utf-8')
        linha_tools = next(l for l in rev_cl.splitlines() if l.startswith('tools:'))
        self.assertNotIn('Edit', linha_tools)
        self.assertNotIn('Write', linha_tools)

    def test_claude_settings_deny_patterns_contem_opcoes_curtas_gh_pr_merge(self):
        # A06: deny em .claude/settings.json e adapters/claude/settings.json.modelo possui -s e -r
        modelo_path = RAIZ / 'adapters' / 'claude' / 'settings.json.modelo'
        self.assertTrue(modelo_path.is_file())
        modelo_data = json.loads(modelo_path.read_text(encoding='utf-8'))
        deny_modelo = modelo_data.get('permissions', {}).get('deny', [])
        self.assertIn("Bash(gh pr merge*-s*)", deny_modelo)
        self.assertIn("Bash(gh pr merge*-r*)", deny_modelo)
        self.assertIn("Bash(gh pr merge*--squash*)", deny_modelo)
        self.assertIn("Bash(gh pr merge*--rebase*)", deny_modelo)

        settings_path = RAIZ.parent / '.claude' / 'settings.json'
        if settings_path.is_file():
            settings_data = json.loads(settings_path.read_text(encoding='utf-8'))
            deny_settings = settings_data.get('permissions', {}).get('deny', [])
            self.assertIn("Bash(gh pr merge*-s*)", deny_settings)
            self.assertIn("Bash(gh pr merge*-r*)", deny_settings)
            self.assertIn("Bash(gh pr merge*--squash*)", deny_settings)
            self.assertIn("Bash(gh pr merge*--rebase*)", deny_settings)


if __name__ == '__main__':
    unittest.main()
