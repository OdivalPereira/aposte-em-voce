"""CI honesto (B07, DG-13): todo passo `run` do workflow tem `pipefail`, e a falha do validador deixa o job vermelho.

Só biblioteca padrão: o leitor abaixo entende o subconjunto de YAML que os workflows usam (jobs, defaults.run.shell,
steps com name, shell, working-directory e run em linha ou em bloco `|`/`>`). Um passo tem `pipefail` se:
  - o shell dele, do job ou do workflow (nessa precedência) traz `-o pipefail` (ex.: `bash -eo pipefail {0}`); ou
  - o script tem uma linha `set ... -o pipefail` (ex.: `set -euo pipefail`) antes de qualquer pipe.
`shell: bash` sozinho NÃO basta: a regra é explícita, não depende do padrão da plataforma.
"""
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # permite `unittest tests.test_ci_pipefail`
from util import RAIZ  # noqa: E402

CI_YML = RAIZ.parent / '.github' / 'workflows' / 'ci.yml'
SHELL_PIPEFAIL = re.compile(r'(?:^|\s)-[A-Za-z]*o\s+pipefail\b')
SET_PIPEFAIL = re.compile(r'^\s*set\s+(?:\S+\s+)*?-[A-Za-z]*o\s+pipefail\b')
PIPE = re.compile(r'(?<!\|)\|(?!\|)')
ENTRE = r'(?:[ \t]*(?:#.*)?\n)*'  # linhas em branco ou de comentário entre as chaves
DEFAULTS_SHELL = re.compile(r'^[ \t]*defaults:[ \t]*\n' + ENTRE + r'[ \t]+run:[ \t]*\n' + ENTRE
                            + r'[ \t]+shell:[ \t]*(.+?)[ \t]*(?:#.*)?$', re.M)


def indent(linha):
    return len(linha) - len(linha.lstrip(' '))


def valor(texto):
    texto = re.sub(r'\s+#.*$', '', texto.strip())
    if len(texto) >= 2 and texto[0] == texto[-1] and texto[0] in '"\'':
        texto = texto[1:-1]
    return texto


def shell_padrao(trecho):
    m = DEFAULTS_SHELL.search(trecho)
    return valor(m.group(1)) if m else None


def passos_run(texto):
    """Lista os passos com `run`: job, nome, linha (1-based), shell efetivo, working-directory e script."""
    linhas = texto.replace('\r\n', '\n').split('\n')
    idx_jobs = next((i for i, l in enumerate(linhas) if re.match(r'^jobs:\s*$', l)), None)
    if idx_jobs is None:
        return []
    padrao_workflow = shell_padrao('\n'.join(linhas[:idx_jobs]))
    # cabeçalhos de job: primeira indentação depois de `jobs:`
    resto = [(i, l) for i, l in enumerate(linhas) if i > idx_jobs and l.strip() and not l.lstrip().startswith('#')]
    if not resto:
        return []
    nivel_job = indent(resto[0][1])
    cabecalhos = [i for i, l in resto if indent(l) == nivel_job and re.match(r'^\s*[\w-]+:\s*$', l)]
    passos = []
    for n, ini in enumerate(cabecalhos):
        fim = cabecalhos[n + 1] if n + 1 < len(cabecalhos) else len(linhas)
        job = linhas[ini].strip().rstrip(':')
        bloco = linhas[ini:fim]
        i_steps = next((k for k, l in enumerate(bloco) if re.match(r'^\s*steps:\s*$', l)), None)
        if i_steps is None:
            continue
        padrao_job = shell_padrao('\n'.join(bloco[:i_steps])) or padrao_workflow
        itens, atual = [], None
        for k in range(i_steps + 1, len(bloco)):
            l = bloco[k]
            if re.match(r'^\s*- ', l) and (atual is None or indent(l) == atual['dash']):
                atual = {'dash': indent(l), 'linhas': [], 'ini': ini + k}
                itens.append(atual)
            if atual is not None and (l.strip() == '' or indent(l) >= atual['dash'] or l.lstrip().startswith('#')):
                atual['linhas'].append((ini + k, l))
        for it in itens:
            passo = ler_passo(it, job, padrao_job)
            if passo and passo['run'] is not None:
                passos.append(passo)
    return passos


def ler_passo(item, job, padrao):
    pares = item['linhas']
    primeira = pares[0][1]
    m = re.match(r'^(\s*)-(\s+)', primeira)
    chave_ind = len(m.group(1)) + 1 + len(m.group(2))
    # a linha do traço vira uma linha de chave comum
    pares = [(pares[0][0], ' ' * chave_ind + primeira[m.end():])] + pares[1:]
    campos, i = {}, 0
    while i < len(pares):
        no, l = pares[i]
        mk = re.match(r'^(\s*)([\w-]+):[ \t]*(.*)$', l)
        if mk and len(mk.group(1)) == chave_ind:
            chave, resto = mk.group(2), mk.group(3)
            if re.match(r'^[|>][+-]?\d*[ \t]*(#.*)?$', resto):
                corpo = []
                i += 1
                while i < len(pares) and (pares[i][1].strip() == '' or indent(pares[i][1]) > chave_ind):
                    corpo.append(pares[i][1])
                    i += 1
                nao_vazias = [c for c in corpo if c.strip()]
                recuo = min((indent(c) for c in nao_vazias), default=0)
                campos[chave] = ('\n'.join(c[recuo:] for c in corpo).rstrip('\n'), no)
                continue
            campos[chave] = (valor(resto), no)
        i += 1
    if 'run' not in campos:
        return {'run': None}
    return {'job': job, 'nome': campos.get('name', ('(sem nome)',))[0], 'linha': campos['run'][1] + 1,
            'run': campos['run'][0], 'shell': (campos.get('shell') or (None,))[0] or padrao,
            'pasta': (campos.get('working-directory') or (None,))[0]}


def tem_pipe(script):
    return any(PIPE.search(l) for l in script.split('\n') if not l.lstrip().startswith('#'))


def tem_pipefail(passo):
    if passo['shell'] and SHELL_PIPEFAIL.search(passo['shell']):
        return True
    pf = pipe = None
    for n, l in enumerate(passo['run'].split('\n')):
        if l.lstrip().startswith('#'):
            continue
        if pf is None and SET_PIPEFAIL.match(l):
            pf = n
        if pipe is None and PIPE.search(l):
            pipe = n
    return pf is not None and (pipe is None or pf < pipe)


def sem_pipefail(texto):
    """Passos `run` sem pipefail, com o motivo (diz se o passo tem pipe)."""
    return [{**p, 'motivo': 'tem pipe e não tem pipefail' if tem_pipe(p['run']) else 'não tem pipefail'}
            for p in passos_run(texto) if not tem_pipefail(p)]


def wf(passos, cabecalho_job='', cabecalho_wf=''):
    return f"""name: ci
on: push
{cabecalho_wf}jobs:
  ci:
    runs-on: ubuntu-latest
{cabecalho_job}    steps:
{passos}"""


class TesteLeitorDeWorkflow(unittest.TestCase):
    """O leitor e a regra, em workflows sintéticos (o caso reprovado é o que importa)."""

    def nomes_reprovados(self, texto):
        return [p['nome'] for p in sem_pipefail(texto)]

    def test_pipe_sem_pipefail_reprova(self):
        texto = wf("""      - name: Ruim
        run: |
          python3 -B -m unittest 2>&1 | tee saida.txt
""")
        r = sem_pipefail(texto)
        self.assertEqual([p['nome'] for p in r], ['Ruim'])
        self.assertEqual(r[0]['motivo'], 'tem pipe e não tem pipefail')
        self.assertEqual(r[0]['job'], 'ci')

    def test_pipe_em_run_de_uma_linha_sem_pipefail_reprova(self):
        self.assertEqual(self.nomes_reprovados(wf("      - name: Linha\n        run: echo a | tee b\n")), ['Linha'])

    def test_pipe_com_shell_bash_simples_reprova(self):
        texto = wf("      - name: Bash puro\n        shell: bash\n        run: echo a | tee b\n")
        self.assertEqual(self.nomes_reprovados(texto), ['Bash puro'])
        texto = wf("      - name: Padrão bash\n        run: echo a | tee b\n", cabecalho_job='    defaults:\n      run:\n        shell: bash\n')
        self.assertEqual(self.nomes_reprovados(texto), ['Padrão bash'])

    def test_passo_sem_pipe_e_sem_pipefail_tambem_reprova(self):
        r = sem_pipefail(wf("      - name: Seco\n        run: npm ci\n"))
        self.assertEqual([p['motivo'] for p in r], ['não tem pipefail'])

    def test_formas_validas_de_pipefail(self):
        casos = {
            'set -euo pipefail': "      - name: A\n        run: |\n          set -euo pipefail\n          a | b\n",
            'set -o pipefail': "      - name: B\n        run: |\n          set -o pipefail\n          a | b\n",
            'set -e -o pipefail': "      - name: C\n        run: |\n          set -e -o pipefail\n          a | b\n",
            'set -o errexit -o pipefail': "      - name: D\n        run: |\n          set -o errexit -o pipefail\n          a | b\n",
            'shell no passo': "      - name: E\n        shell: bash -eo pipefail {0}\n        run: a | b\n",
            'run com aspas': "      - name: F\n        shell: 'bash -eo pipefail {0}'\n        run: a | b\n",
        }
        for nome, passo in casos.items():
            self.assertEqual(sem_pipefail(wf(passo)), [], nome)

    def test_default_do_job_e_do_workflow_valem(self):
        passo = "      - name: P\n        run: a | b\n"
        job = wf(passo, cabecalho_job='    defaults:\n      run:\n        shell: bash -eo pipefail {0}\n')
        flow = wf(passo, cabecalho_wf='defaults:\n  run:\n    shell: bash -eo pipefail {0}\n')
        self.assertEqual(sem_pipefail(job), [])
        self.assertEqual(sem_pipefail(flow), [])

    def test_shell_do_passo_sobrescreve_o_default(self):
        texto = wf("      - name: Sobrescreve\n        shell: bash\n        run: a | b\n",
                   cabecalho_job='    defaults:\n      run:\n        shell: bash -eo pipefail {0}\n')
        self.assertEqual(self.nomes_reprovados(texto), ['Sobrescreve'])

    def test_so_o_texto_ou_o_comentario_nao_valem(self):
        casos = ["      - name: Eco\n        run: |\n          echo 'use pipefail'\n          a | b\n",
                 "      - name: Comentário\n        run: |\n          # set -o pipefail\n          a | b\n",
                 "      - name: Só errexit\n        run: |\n          set -e\n          a | b\n",
                 "      - name: Desliga\n        run: |\n          set +o pipefail\n          a | b\n"]
        for passo in casos:
            self.assertEqual(len(sem_pipefail(wf(passo))), 1, passo)

    def test_pipefail_depois_do_pipe_nao_vale(self):
        texto = wf("      - name: Tarde\n        run: |\n          a | b\n          set -o pipefail\n")
        self.assertEqual(self.nomes_reprovados(texto), ['Tarde'])

    def test_passo_sem_run_e_ignorado_e_cada_passo_e_julgado_sozinho(self):
        texto = wf("""      - uses: actions/checkout@v4
      - name: Bom
        run: |
          set -euo pipefail
          a | b
      - name: Ruim
        run: a | b
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
""")
        self.assertEqual(self.nomes_reprovados(texto), ['Ruim'])
        self.assertEqual(len(passos_run(texto)), 2)

    def test_pipe_logico_ou_nao_conta_como_pipe(self):
        self.assertFalse(tem_pipe('a || b'))
        self.assertTrue(tem_pipe('a | b'))


class TesteCiReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texto = CI_YML.read_text(encoding='utf-8')
        cls.passos = passos_run(cls.texto)

    def test_todo_passo_run_do_ci_real_tem_pipefail(self):
        self.assertGreaterEqual(len(self.passos), 4, 'o leitor deveria achar os passos run do ci.yml')
        reprovados = sem_pipefail(self.texto)
        self.assertEqual(reprovados, [], [f'{p["nome"]} (linha {p["linha"]}): {p["motivo"]}' for p in reprovados])

    def test_job_se_chama_ci_e_roda_na_main_nos_ramos_e_no_pr(self):
        self.assertRegex(self.texto, r'(?m)^jobs:\n  ci:\n')
        self.assertEqual({p['job'] for p in self.passos}, {'ci'})
        self.assertRegex(self.texto, r'(?m)^name: ci$')
        self.assertRegex(self.texto, r'(?m)^  pull_request:')
        self.assertIn("'etapa/**'", self.texto)

    def passo_com(self, trecho):
        achados = [p for p in self.passos if trecho in p['run']]
        self.assertEqual(len(achados), 1, f'esperado 1 passo com "{trecho}", achei {len(achados)}')
        return achados[0]

    def test_ci_roda_a_suite_e_o_validador_do_pacote_copiado(self):
        suite = self.passo_com('python3 -B -m unittest discover -s tests')
        validador = self.passo_com('python3 -B scripts/validar_pacote.py')
        self.assertEqual(suite['pasta'], 'sociedade-do-codigo')
        self.assertEqual(validador['pasta'], 'sociedade-do-codigo')
        self.assertTrue((RAIZ / 'tests').is_dir() and (RAIZ / 'scripts' / 'validar_pacote.py').is_file())

    def test_nada_no_ci_mascara_a_falha(self):
        self.assertNotIn('continue-on-error', self.texto)
        for trecho in ('unittest discover', 'validar_pacote.py'):
            for linha in self.passo_com(trecho)['run'].split('\n'):
                if trecho in linha:
                    self.assertNotRegex(linha, r'\|\|\s*(true|:|exit 0)', linha)

    @unittest.skipUnless(shutil.which('bash'), 'precisa do bash')
    def test_validador_falhando_deixa_o_passo_vermelho(self):
        """Executa o script real do passo com um `python3` falso: falha do comando tem de virar falha do passo."""
        for trecho in ('unittest discover -s tests', 'scripts/validar_pacote.py'):
            passo = self.passo_com(trecho)
            with self.subTest(passo=passo['nome']):
                self.assertTrue(passo['shell'] and '{0}' in passo['shell'], passo['shell'])
                falho = self.executar(passo, saida_falsa=1)
                self.assertNotEqual(falho.returncode, 0, 'o passo deveria falhar quando o comando falha')
                self.assertIn('FALSO-FALHOU', falho.stdout + falho.stderr)
                # controle 1: com o comando verde o passo passa e o texto fica registrado
                ok = self.executar(passo, saida_falsa=0)
                self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
                # controle 2: sem pipefail o mesmo pipe esconderia a falha (é isto que o teste previne)
                mascarado = self.executar(passo, saida_falsa=1, shell='bash -e {0}', tirar_pipefail=True)
                self.assertEqual(mascarado.returncode, 0, 'sem pipefail o tee deveria mascarar a falha; o teste não discrimina')

    def executar(self, passo, saida_falsa, shell=None, tirar_pipefail=False):
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            (raiz / 'bin').mkdir()
            (raiz / passo['pasta']).mkdir()
            falso = raiz / 'bin' / 'python3'
            falso.write_text(f'#!/bin/sh\necho FALSO-{"FALHOU" if saida_falsa else "OK"}\nexit {saida_falsa}\n', encoding='utf-8')
            falso.chmod(falso.stat().st_mode | stat.S_IEXEC)
            script = raiz / 'passo.sh'
            corpo = passo['run']
            if tirar_pipefail:
                corpo = '\n'.join(l for l in corpo.split('\n') if not SET_PIPEFAIL.match(l))
            script.write_text(corpo + '\n', encoding='utf-8')
            argv = (shell or passo['shell']).replace('{0}', str(script)).split()
            env = {'PATH': f'{raiz / "bin"}:/usr/bin:/bin', 'HOME': d}
            return subprocess.run(argv, cwd=raiz / passo['pasta'], env=env, capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()
