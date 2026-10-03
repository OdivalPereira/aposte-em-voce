"""B11a: durante a etapa, os comandos do ciclo leem e gravam a `sociedade/` do worktree da etapa, sem cópia manual.

Raiz de trabalho temporária: o `HOME` dos comandos é uma pasta temporária, então `~/.sociedade` real nunca é tocado.
Repositório temporário e dados sintéticos.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from util import NUCLEO, SKILLS, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))
import sc_registro  # noqa: E402
from sc_registro import Registro  # noqa: E402

SC = NUCLEO / 'scripts' / 'sc.py'
ETAPA = 'soma'
POR = ('--por', 'Odival Sintético')

PERFIL = """# Perfil sintético

## Missão
Projeto sintético do worktree da etapa.

## Papel × ferramenta
| Papel | Nome | Plataforma | Fornecedor | Modelo | Esforço | Estado (ativo/reserva/espera) | Desde | Motivo |
|---|---|---|---|---|---|---|---|---|
| Revisor Independente | Barbárvore | Claude Code (nuvem) | Anthropic | Modelo A | high | ativo | 2026-10-03 | subagente |
| Coordenador | Gandalf | Claude Code (nuvem) | Anthropic | Modelo B | high | ativo | 2026-10-03 | subagente |

## Portão por área
| Área | Pasta | Testes | Timeout (s) | Prefixos |
|---|---|---|---|---|
| projeto | `.` | `python3 -B -m unittest discover -s tests` | 120 | `*` |

## Modo emulação (Q147)
- **Emulação:** sim.
"""

ORDEM = """# Ordem soma — somar dois números

```entregas
E1 | arquivo_existe | soma.py
```
"""


def parecer(head, base):
    return f"""## Parecer do Revisor Independente
- etapa: {ETAPA}
- entrega: commit {head[:7]}
- commit: {head}
- base..head: {base[:7]}..{head[:7]}
- revisor: Barbárvore (Claude Code) · fornecedor: Anthropic · sessão: sess_sintetica
- modelo: modelo-sintetico · esforço: não exposto
- independência: Nível C (mesmo fornecedor)
- veredito: aceitar
- data: 03/10/2026 10:00

### Independência
Não implementei nem corrigi nada desta entrega. Revisão interna, em emulação.

### Critérios e evidências
| Critério do aceite | Evidência | Estado |
|---|---|---|
| soma funciona | `python3 -m unittest discover -s tests` verde | executada |

### Achados
nenhum

### O que não verifiquei
- Nada além do critério acima.
"""


class Cenario(unittest.TestCase):
    """Checkout principal em `<tmp>/proj` e worktree da etapa em `<tmp>/home/.sociedade/trabalho/proj/soma`."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / 'home'
        self.home.mkdir()
        self.env = {**os.environ, 'HOME': str(self.home), 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
        self.raiz = self.tmp / 'proj'
        self.soc = self.raiz / 'sociedade'
        (self.soc / 'ordens').mkdir(parents=True)
        (self.raiz / 'tests').mkdir()
        self.git(self.raiz, 'init', '-q')
        (self.soc / 'perfil.md').write_text(PERFIL, encoding='utf-8')
        (self.soc / 'ordens' / f'{ETAPA}.md').write_text(ORDEM, encoding='utf-8')
        (self.raiz / '.gitignore').write_text('sociedade/.registro.lock\n', encoding='utf-8')
        (self.raiz / 'app.py').write_text('x = 1\n', encoding='utf-8')
        self.base = self.commit(self.raiz, 'base')
        self.trabalho = self.home / '.sociedade' / 'trabalho' / 'proj'
        self.wt = self.trabalho / ETAPA
        self.wt_soc = self.wt / 'sociedade'

    def git(self, raiz, *args):
        return subprocess.run(['git', '-C', str(raiz), '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false',
                               *args], capture_output=True, text=True, check=True, env=self.env).stdout.strip()

    def commit(self, raiz, msg):
        self.git(raiz, 'add', '-A')
        self.git(raiz, 'commit', '-q', '-m', msg)
        return self.git(raiz, 'rev-parse', 'HEAD')

    def criar_worktree(self):
        self.trabalho.mkdir(parents=True)
        self.git(self.raiz, 'worktree', 'add', '-q', str(self.wt), '-b', f'etapa/{ETAPA}', self.base)

    def codificar_no_worktree(self):
        (self.wt / 'soma.py').write_text('def soma(a, b):\n    return a + b\n', encoding='utf-8')
        (self.wt / 'tests').mkdir(exist_ok=True)
        (self.wt / 'tests' / 'test_soma.py').write_text(
            'import sys, unittest\nsys.path.insert(0, ".")\nfrom soma import soma\n\n\n'
            'class T(unittest.TestCase):\n    def test_soma(self):\n        self.assertEqual(soma(1, 2), 3)\n', encoding='utf-8')
        self.git(self.wt, 'add', '--', 'soma.py', 'tests')  # só produto: nada de sociedade/ num commit do candidato
        self.git(self.wt, 'commit', '-q', '-m', 'feat: soma')
        return self.git(self.wt, 'rev-parse', 'HEAD')

    def sc(self, *args, cwd=None):
        """Comando documentado, sem `--pasta-sociedade`, com `HOME` temporário."""
        return rodar(SC, *args, cwd=cwd or self.raiz, env=self.env)

    def ok(self, res):
        self.assertEqual(res.returncode, 0, f'stdout: {res.stdout}\nstderr: {res.stderr}')
        return res

    def estado_do_git(self, raiz):
        return self.git(raiz, 'status', '--porcelain', '--untracked-files=all')


class TestResolucao(Cenario):
    def resolver(self, *args, **kw):
        with mock.patch.dict(os.environ, {'HOME': str(self.home)}):
            return sc_registro.localizar_sociedade_da_etapa(*args, **kw)

    def test_sem_worktree_vale_a_canonica(self):
        self.assertEqual(self.resolver(ETAPA, self.raiz), self.soc.resolve())

    def test_com_worktree_da_etapa_vale_a_do_worktree(self):
        self.criar_worktree()
        self.assertEqual(self.resolver(ETAPA, self.raiz), self.wt_soc.resolve())

    def test_outra_etapa_continua_na_canonica(self):
        self.criar_worktree()
        self.assertEqual(self.resolver('outra', self.raiz), self.soc.resolve())

    def test_sem_etapa_vale_o_worktree_em_que_a_pasta_esta(self):
        self.criar_worktree()
        self.assertEqual(self.resolver(None, self.wt), self.wt_soc.resolve())
        self.assertEqual(self.resolver(None, self.raiz), self.soc.resolve())

    def test_etapa_com_nome_invalido_cai_na_canonica(self):
        self.criar_worktree()
        self.assertEqual(self.resolver('../x', self.raiz), self.soc.resolve())


class TestEtapaNoWorktree(Cenario):
    def test_etapa_fecha_sem_copia_manual_e_sem_gravar_no_checkout_principal(self):
        self.criar_worktree()
        antes = self.estado_do_git(self.raiz)
        ordem = self.wt_soc / 'ordens' / f'{ETAPA}.md'

        self.ok(self.sc('abrir', f'--etapa={ETAPA}', '--ordem', ordem, '--base', self.base))
        head = self.codificar_no_worktree()
        self.ok(self.sc('entregar', '--etapa', ETAPA, '--base', self.base, '--pasta-projeto', self.wt))
        at = json.loads((self.wt_soc / 'pareceres' / f'atestado-{ETAPA}.json').read_text(encoding='utf-8'))
        self.assertEqual((at['status'], at['commit']), ('APROVADO', head))

        arq = self.tmp / 'parecer.md'
        arq.write_text(parecer(head, self.base), encoding='utf-8')
        self.ok(self.sc('revisar', '--etapa', ETAPA, '--parecer', arq, '--head', head))
        self.ok(self.sc('conferir', '--ordem', ordem, '--registrar', '--raiz', self.wt))
        self.ok(self.sc('decidir', '--etapa', ETAPA, 'aceitar', *POR))
        estado = self.ok(self.sc('estado', '--etapa', ETAPA, '--imprimir', '--sem-html'))
        self.assertIn(ETAPA, estado.stdout)

        reg = Registro(self.wt_soc)
        tipos = [e['tipo'] for e in reg.eventos]
        for esperado in ('etapa_aberta', 'parecer_registrado', 'conferencia_registrada', 'decisao_registrada'):
            self.assertIn(esperado, tipos)
        self.assertEqual(reg.estado()['etapas'][ETAPA]['estado'], 'encerrada')
        self.assertTrue((self.wt_soc / 'estado.md').is_file())
        self.assertTrue((self.wt_soc / 'evolucao.md').is_file())

        # nada disso gravou no checkout principal
        self.assertFalse((self.soc / 'registro.json').exists())
        self.assertFalse((self.soc / 'pareceres').exists())
        self.assertFalse((self.soc / 'estado.md').exists())
        self.assertFalse((self.soc / 'evolucao.md').exists())
        self.assertEqual(self.estado_do_git(self.raiz), antes)

    def test_estado_dentro_do_worktree_sem_etapa_le_o_do_worktree(self):
        self.criar_worktree()
        ordem = self.wt_soc / 'ordens' / f'{ETAPA}.md'
        self.ok(self.sc('abrir', f'--etapa={ETAPA}', '--ordem', ordem, '--base', self.base))
        res = self.ok(self.sc('estado', '--imprimir', '--sem-html', cwd=self.wt))
        self.assertIn(ETAPA, res.stdout)
        self.assertFalse((self.soc / 'estado.md').exists())

    def test_conferir_aceita_pasta_sociedade_explicita(self):
        self.criar_worktree()
        outra = self.tmp / 'outra-soc'
        outra.mkdir()
        self.ok(self.sc('abrir', f'--etapa={ETAPA}', '--ordem', self.wt_soc / 'ordens' / f'{ETAPA}.md', '--base', self.base))
        (self.wt / 'soma.py').write_text('x = 1\n', encoding='utf-8')
        # registro explícito noutra pasta: vale o --pasta-sociedade, não o worktree
        Registro.inicializar(outra, projeto_id='proj', caminho_canonico=str(self.raiz), versao_inicial=self.base)
        self.ok(self.sc('conferir', '--ordem', self.wt_soc / 'ordens' / f'{ETAPA}.md', '--registrar', '--raiz', self.wt,
                        '--pasta-sociedade', outra))
        self.assertIn('conferencia_registrada', [e['tipo'] for e in Registro(outra).eventos])
        self.assertNotIn('conferencia_registrada', [e['tipo'] for e in Registro(self.wt_soc).eventos])

    def test_pasta_sociedade_explicita_vale_antes_do_worktree(self):
        self.criar_worktree()
        ordem = self.soc / 'ordens' / f'{ETAPA}.md'
        self.ok(self.sc('abrir', f'--etapa={ETAPA}', '--ordem', ordem, '--base', self.base, '--pasta-sociedade', self.soc))
        self.assertTrue((self.soc / 'registro.json').is_file())
        self.assertFalse((self.wt_soc / 'registro.json').exists())

    def test_sem_worktree_o_comportamento_de_hoje_continua(self):
        ordem = self.soc / 'ordens' / f'{ETAPA}.md'
        self.ok(self.sc('abrir', f'--etapa={ETAPA}', '--ordem', ordem, '--base', self.base))
        self.assertTrue((self.soc / 'registro.json').is_file())


if __name__ == '__main__':
    unittest.main()
