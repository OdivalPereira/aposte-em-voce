#!/usr/bin/env python3
"""Testes de processo P1, P2 e P3 da etapa d1b-robustez.

- P1: `passar` exige `--por` (sem autor padrão) e grava sempre a hora atual (sem sobrescrever).
      Uma segunda passagem para o mesmo destino na mesma etapa exige `--nova-rodada --motivo`.
- P2: `revisar` recusa preparar a cópia se `sociedade/perfil.md` ou `sociedade/regras.md`
      do worktree diferirem do HEAD (Q178). A cópia roda, sem rede, o comando de teste de cada
      área do perfil (dependências levadas ou ligadas só para leitura, como `node_modules`).
- P3: `decidir corrigir|rejeitar` exige `--motivo`. Um segundo `revisar --parecer` na mesma etapa
      grava `parecer-<etapa>-reconferencia.md` e nunca sobrescreve o primeiro; o registro liga os dois.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, carregar, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
MOD_REGISTRO = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REGISTRO.Registro
SC = NUCLEO / 'scripts' / 'sc.py'

AMBIENTE = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}

PERFIL_TESTE = """# Perfil sintético
## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Arquiteto | Círdan | Claude Code | Anthropic | Claude Opus 5.5 | high | ativo | 2026-10-03 | formação real |
| Revisor Independente | Barbárvore | Codex | OpenAI | GPT-6 Sol | high | ativo | 2026-10-03 | formação real |
| Coordenador | Gandalf | Antigravity | Google | Gemini 3.8 Flash | high | ativo | 2026-10-03 | formação real |

## Portão por área
| Área | Pasta | Testes | Timeout (s) | Prefixos |
|---|---|---|---|---|
| projeto | `.` | `python3 -B -m unittest discover -s tests` | 120 | `*` |

## Modo emulação (Q147)
- **Emulação:** sim.
"""


def git(raiz, *args):
    return subprocess.run(
        ['git', '-C', str(raiz), '-c', 'user.name=test', '-c', 'user.email=t@t.com',
         '-c', 'commit.gpgsign=false', *args],
        capture_output=True, text=True, check=True, env=AMBIENTE
    ).stdout.strip()


def commit_gov(raiz, msg):
    git(raiz, 'add', '-A')
    git(raiz, 'commit', '-q', '-m', msg)
    return git(raiz, 'rev-parse', 'HEAD')


def commit_produto(raiz, msg):
    git(raiz, 'add', '-A', '--', ':(exclude)sociedade')
    git(raiz, 'commit', '-q', '-m', msg)
    return git(raiz, 'rev-parse', 'HEAD')


def parecer_texto(head, base, etapa='p3-etapa', veredito='aceitar', commit_revisado=None):
    return f"""## Parecer do Revisor Independente
- etapa: {etapa}
- entrega: commit {head[:7]}
- commit: {commit_revisado or head}
- base..head: {base[:7]}..{head[:7]}
- revisor: Barbárvore (Codex) · fornecedor: OpenAI · sessão: sess_sintetica
- modelo: GPT-6 Sol · esforço: high
- independência: Nível A (fornecedor diferente)
- veredito: {veredito}
- data: 05/10/2026 12:00

### Independência
Não implementei nem corrigi nada desta entrega.

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| portao | `python3 -m unittest discover -s tests` verde | executada |

### Achados
nenhum

### O que não verifiquei
- Nada.
"""


class TestProcessoP1(unittest.TestCase):
    """P1: passar exige --por e grava hora atual sem sobrescrever; segunda passagem exige --nova-rodada --motivo."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

        # Worktree da etapa
        self.wt = self.raiz / 'worktree-p1'
        self.wt.mkdir(parents=True)
        self.soc_wt = self.wt / 'sociedade'
        self.soc_wt.mkdir(parents=True)
        (self.soc_wt / 'perfil.md').write_text(PERFIL_TESTE, encoding='utf-8')
        (self.soc_wt / 'ordens').mkdir(parents=True)
        (self.soc_wt / 'ordens' / 'p1.md').write_text(
            '# Ordem p1\nRevisão independente: testar fluxo P1.\n', encoding='utf-8'
        )

        # Cópia de revisão
        self.rev = self.raiz / 'revisao-p1'
        self.rev.mkdir(parents=True)

        self.reg = Registro.inicializar(self.soc_wt, projeto_id='proj-p1', caminho_canonico=str(self.wt), aplicar=True)

    def test_passar_sem_por_e_recusado(self):
        """passar exige --por (sem autor padrão)."""
        r = rodar(
            SC, 'passar',
            '--etapa', 'p1',
            '--para', 'gandalf',
            '--pasta-sociedade', str(self.soc_wt),
            env=AMBIENTE
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('--por', r.stderr)

    def test_passar_com_por_grava_hora_atual_e_autor(self):
        """passar grava hora atual e o autor declarado em --por."""
        t_antes = datetime.now(timezone.utc)
        r = rodar(
            SC, 'passar',
            '--etapa', 'p1',
            '--para', 'gandalf',
            '--por', 'Círdan',
            '--pasta-sociedade', str(self.soc_wt),
            env=AMBIENTE
        )
        t_depois = datetime.now(timezone.utc)
        self.assertEqual(r.returncode, 0, r.stderr)
        linhas = [l for l in r.stdout.splitlines() if l.strip()]
        self.assertEqual(len(linhas), 3)

        reg = Registro(self.soc_wt)
        evs = [e for e in reg.dados.get('eventos', []) if e.get('tipo') == 'passagem']
        self.assertEqual(len(evs), 1)
        ev = evs[0]
        self.assertEqual(ev.get('autor'), 'Círdan')
        self.assertEqual(ev['dados'].get('por'), 'Círdan')
        self.assertEqual(ev['dados'].get('para'), 'gandalf')
        self.assertIn('data_hora', ev['dados'])
        t_evento = datetime.fromisoformat(ev['dados']['data_hora'])
        self.assertTrue(t_antes <= t_evento <= t_depois)

    def test_segunda_passagem_mesmo_destino_exige_nova_rodada_e_motivo(self):
        """Uma segunda passagem para o mesmo destino na mesma etapa exige --nova-rodada --motivo."""
        # 1ª passagem para gandalf: sucesso
        r1 = rodar(
            SC, 'passar',
            '--etapa', 'p1',
            '--para', 'gandalf',
            '--por', 'Círdan',
            '--pasta-sociedade', str(self.soc_wt),
            env=AMBIENTE
        )
        self.assertEqual(r1.returncode, 0)

        # 2ª passagem para gandalf sem --nova-rodada e sem --motivo: recusada
        r2 = rodar(
            SC, 'passar',
            '--etapa', 'p1',
            '--para', 'gandalf',
            '--por', 'Círdan',
            '--pasta-sociedade', str(self.soc_wt),
            env=AMBIENTE
        )
        self.assertNotEqual(r2.returncode, 0)
        self.assertIn('--nova-rodada --motivo', r2.stderr)

        # 2ª passagem com --nova-rodada mas sem --motivo: recusada
        r3 = rodar(
            SC, 'passar',
            '--etapa', 'p1',
            '--para', 'gandalf',
            '--por', 'Círdan',
            '--nova-rodada',
            '--pasta-sociedade', str(self.soc_wt),
            env=AMBIENTE
        )
        self.assertNotEqual(r3.returncode, 0)
        self.assertIn('--nova-rodada --motivo', r3.stderr)

        # 2ª passagem com --motivo mas sem --nova-rodada: recusada
        r4 = rodar(
            SC, 'passar',
            '--etapa', 'p1',
            '--para', 'gandalf',
            '--por', 'Círdan',
            '--motivo', 'correção de bug',
            '--pasta-sociedade', str(self.soc_wt),
            env=AMBIENTE
        )
        self.assertNotEqual(r4.returncode, 0)
        self.assertIn('--nova-rodada --motivo', r4.stderr)

        # 2ª passagem com --nova-rodada e --motivo: sucesso!
        r5 = rodar(
            SC, 'passar',
            '--etapa', 'p1',
            '--para', 'gandalf',
            '--por', 'Círdan',
            '--nova-rodada',
            '--motivo', 'correção de bug',
            '--pasta-sociedade', str(self.soc_wt),
            env=AMBIENTE
        )
        self.assertEqual(r5.returncode, 0, r5.stderr)

        # Confere dois eventos no registro, sem sobrescrever
        reg = Registro(self.soc_wt)
        evs = [e for e in reg.dados.get('eventos', []) if e.get('tipo') == 'passagem']
        self.assertEqual(len(evs), 2)
        self.assertTrue(evs[1]['dados'].get('nova_rodada'))
        self.assertEqual(evs[1]['dados'].get('motivo'), 'correção de bug')

    def test_passar_para_outro_destino_nao_exige_nova_rodada(self):
        """Passagem para barbarvore após gandalf não é mesmo destino e não exige --nova-rodada."""
        r1 = rodar(
            SC, 'passar',
            '--etapa', 'p1',
            '--para', 'gandalf',
            '--por', 'Círdan',
            '--pasta-sociedade', str(self.soc_wt),
            env=AMBIENTE
        )
        self.assertEqual(r1.returncode, 0)

        r2 = rodar(
            SC, 'passar',
            '--etapa', 'p1',
            '--para', 'barbarvore',
            '--por', 'Círdan',
            '--pasta-sociedade', str(self.soc_wt),
            env=AMBIENTE
        )
        self.assertEqual(r2.returncode, 0, r2.stderr)


class TestProcessoP2(unittest.TestCase):
    """P2: revisar recusa preparar cópia se perfil.md ou regras.md diferirem do HEAD; roda testes sem rede e liga deps."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name) / 'repo'
        self.raiz.mkdir()
        self.soc = self.raiz / 'sociedade'
        self.soc.mkdir(parents=True)
        (self.raiz / 'tests').mkdir()

        git(self.raiz, 'init', '-q')
        (self.soc / 'perfil.md').write_text(PERFIL_TESTE, encoding='utf-8')
        (self.soc / 'regras.md').write_text('# Regras\nRegra base\n', encoding='utf-8')
        (self.soc / 'ordens').mkdir()
        (self.soc / 'ordens' / 'p2.md').write_text('# Ordem p2\n', encoding='utf-8')
        (self.raiz / 'app.py').write_text('v = 1\n', encoding='utf-8')
        (self.raiz / 'tests' / 'test_app.py').write_text(
            'import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n',
            encoding='utf-8'
        )

        self.base = commit_gov(self.raiz, 'base')
        (self.raiz / 'app.py').write_text('v = 2\n', encoding='utf-8')
        self.head = commit_produto(self.raiz, 'feat: p2')

        self.copia = Path(self._tmp.name) / 'copia-p2'

    def test_revisar_recusa_se_perfil_difere_do_head(self):
        """revisar recusa preparar a cópia se perfil.md do worktree difere do HEAD (Q178)."""
        (self.soc / 'perfil.md').write_text(PERFIL_TESTE + '\n# modificação sem commit\n', encoding='utf-8')
        r = rodar(
            SC, 'revisar',
            '--etapa', 'p2',
            '--base', self.base,
            '--head', self.head,
            '--destino', str(self.copia),
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('perfil.md do worktree difere do HEAD', r.stderr)
        self.assertFalse(self.copia.exists())

    def test_revisar_recusa_se_regras_difere_do_head(self):
        """revisar recusa preparar a cópia se regras.md do worktree difere do HEAD (Q178)."""
        (self.soc / 'regras.md').write_text('# Regras\nRegra modificada sem commit\n', encoding='utf-8')
        r = rodar(
            SC, 'revisar',
            '--etapa', 'p2',
            '--base', self.base,
            '--head', self.head,
            '--destino', str(self.copia),
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('regras.md do worktree difere do HEAD', r.stderr)
        self.assertFalse(self.copia.exists())

    def test_revisar_prepara_copia_liga_dependencias_e_roda_testes(self):
        """Quando perfil e regras conferem com HEAD, prepara cópia, liga node_modules e roda testes sem rede."""
        # Cria um diretório de dependências simulado
        (self.raiz / 'node_modules').mkdir()
        (self.raiz / 'node_modules' / 'pacote_fake.txt').write_text('conteudo', encoding='utf-8')

        r = rodar(
            SC, 'revisar',
            '--etapa', 'p2',
            '--base', self.base,
            '--head', self.head,
            '--destino', str(self.copia),
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.copia.is_dir())
        self.assertTrue((self.copia / 'ORDEM-REVISAO.md').is_file())

        # Dependência ligada como symlink
        self.assertTrue((self.copia / 'node_modules').is_symlink())
        self.assertTrue((self.copia / 'node_modules' / 'pacote_fake.txt').is_file())


class TestProcessoP3(unittest.TestCase):
    """P3: decidir corrigir|rejeitar exige --motivo; segundo parecer grava reconferencia.md sem sobrescrever."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name) / 'repo'
        self.raiz.mkdir()
        self.soc = self.raiz / 'sociedade'
        self.soc.mkdir(parents=True)
        (self.soc / 'ordens').mkdir()
        (self.soc / 'ordens' / 'p3.md').write_text('# Ordem p3\n', encoding='utf-8')
        (self.raiz / 'tests').mkdir()

        git(self.raiz, 'init', '-q')
        (self.soc / 'perfil.md').write_text(PERFIL_TESTE, encoding='utf-8')
        (self.raiz / 'app.py').write_text('v = 1\n', encoding='utf-8')
        (self.raiz / 'tests' / 'test_app.py').write_text(
            'import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n',
            encoding='utf-8'
        )

        self.base = commit_gov(self.raiz, 'base')
        (self.raiz / 'app.py').write_text('v = 2\n', encoding='utf-8')
        self.head1 = commit_produto(self.raiz, 'feat: v1')

        # Abre a etapa
        r = rodar(
            SC, 'abrir',
            '--etapa', 'p3',
            '--ordem', str(self.soc / 'ordens' / 'p3.md'),
            '--base', self.base,
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_decidir_corrigir_sem_motivo_e_recusado(self):
        """decidir corrigir exige --motivo."""
        r = rodar(
            SC, 'decidir',
            '--etapa', 'p3',
            'corrigir',
            '--por', 'Odival Pessoa',
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('exige --motivo', r.stderr)

    def test_decidir_rejeitar_sem_motivo_e_recusado(self):
        """decidir rejeitar exige --motivo."""
        r = rodar(
            SC, 'decidir',
            '--etapa', 'p3',
            'rejeitar',
            '--por', 'Odival Pessoa',
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('exige --motivo', r.stderr)

    def test_decidir_corrigir_com_motivo_sucesso(self):
        """decidir corrigir com --motivo é aceito e registra a referência."""
        r = rodar(
            SC, 'decidir',
            '--etapa', 'p3',
            'corrigir',
            '--por', 'Odival Pessoa',
            '--motivo', 'necessário ajustar cobertura de testes',
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        reg = Registro(self.soc)
        decisoes = reg.estado()['etapas']['p3']['decisoes']
        self.assertEqual(len(decisoes), 1)
        self.assertEqual(decisoes[0]['acao'], 'corrigir')
        self.assertEqual(decisoes[0]['referencia'], 'necessário ajustar cobertura de testes')

    def test_segundo_parecer_grava_reconferencia_sem_sobrescrever_primeiro(self):
        """Segundo revisar --parecer grava parecer-<etapa>-reconferencia.md e liga os dois no registro."""
        # Entrega 1
        r_ent = rodar(
            SC, 'entregar',
            '--etapa', 'p3',
            '--base', self.base,
            '--pasta-projeto', str(self.raiz),
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertEqual(r_ent.returncode, 0, r_ent.stderr)

        # Parecer 1 (com ressalvas ou reprovação para exigir correção)
        arq_parecer1 = self.raiz / 'parecer1.md'
        arq_parecer1.write_text(parecer_texto(self.head1, self.base, etapa='p3', veredito='não aceitar'), encoding='utf-8')
        r_rev1 = rodar(
            SC, 'revisar',
            '--etapa', 'p3',
            '--parecer', str(arq_parecer1),
            '--head', self.head1,
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertEqual(r_rev1.returncode, 0, r_rev1.stderr)
        p1_path = self.soc / 'pareceres' / 'parecer-p3.md'
        self.assertTrue(p1_path.is_file())
        conteudo_p1 = p1_path.read_text(encoding='utf-8')

        # Decisão de corrigir com motivo
        r_corrigir = rodar(
            SC, 'decidir',
            '--etapa', 'p3',
            'corrigir',
            '--por', 'Odival Pessoa',
            '--motivo', 'corrigir falhas apontadas no primeiro parecer',
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertEqual(r_corrigir.returncode, 0, r_corrigir.stderr)

        # Nova alteração no código para gerar novo commit
        (self.raiz / 'app.py').write_text('v = 3\n', encoding='utf-8')
        head2 = commit_produto(self.raiz, 'fix: p3 corrigido')

        # Nova entrega
        r_ent2 = rodar(
            SC, 'entregar',
            '--etapa', 'p3',
            '--base', self.base,
            '--pasta-projeto', str(self.raiz),
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertEqual(r_ent2.returncode, 0, f"stdout: {r_ent2.stdout}\nstderr: {r_ent2.stderr}")

        # Segundo parecer (reconferência)
        arq_parecer2 = self.raiz / 'parecer2.md'
        arq_parecer2.write_text(parecer_texto(head2, self.base, etapa='p3', veredito='aceitar'), encoding='utf-8')
        r_rev2 = rodar(
            SC, 'revisar',
            '--etapa', 'p3',
            '--parecer', str(arq_parecer2),
            '--head', head2,
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertEqual(r_rev2.returncode, 0, r_rev2.stderr)

        # 1. parecer-p3.md original NÃO foi sobrescrito
        self.assertEqual(p1_path.read_text(encoding='utf-8'), conteudo_p1)

        # 2. parecer-p3-reconferencia.md foi criado
        p2_path = self.soc / 'pareceres' / 'parecer-p3-reconferencia.md'
        self.assertTrue(p2_path.is_file())
        self.assertIn(head2[:7], p2_path.read_text(encoding='utf-8'))

        # 3. O registro liga os dois pareceres
        reg = Registro(self.soc)
        pareceres = [e['dados'] for e in reg.dados.get('eventos', []) if e.get('tipo') == 'parecer_registrado']
        self.assertEqual(len(pareceres), 2)
        id_primeiro = pareceres[0]['parecer_id']
        id_segundo = pareceres[1]['parecer_id']
        self.assertIn(f'reconferencia_de:{id_primeiro}', pareceres[1].get('achados_referenciados', []))
        self.assertIn('reconferencia', id_segundo)

        # 4. Decisão de aceitar valida o parecer de reconferência com sucesso
        r_dec = rodar(
            SC, 'decidir',
            '--etapa', 'p3',
            'aceitar',
            '--por', 'Odival Pessoa',
            '--pasta-sociedade', str(self.soc),
            cwd=self.raiz,
            env=AMBIENTE
        )
        self.assertEqual(r_dec.returncode, 0, r_dec.stderr)
        self.assertEqual(Registro(self.soc).estado()['etapas']['p3']['estado'], 'encerrada')


if __name__ == '__main__':
    unittest.main()
