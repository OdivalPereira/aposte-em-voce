"""Testes unitários dedicados para sc_pre_devolucao.py pós-teste operacional.

Cobre:
1. Leitura de comandos do perfil.md (Build e Lint e tipos).
2. Validação física de comando de build (--comando-build e perfil.md).
3. Checagem estática de tipos estritos multi-linguagem (TypeScript/tsconfig e comando-lint).
4. Desacoplamento de fatias concorrentes via --ignorar-arquivos-externos e --arquivos-alvo.
5. Interface CLI de sc_pre_devolucao.py e geração de atestado JSON estruturado com código 1 em falhas.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, carregar, rodar

MOD_PRE = carregar(NUCLEO / 'scripts' / 'sc_pre_devolucao.py', 'sc_pre_devolucao')
VerificadorPreDevolucao = MOD_PRE.VerificadorPreDevolucao
ler_comandos_perfil = MOD_PRE.ler_comandos_perfil

SCRIPT_PRE = NUCLEO / 'scripts' / 'sc_pre_devolucao.py'


class TesteScPreDevolucaoEvolucoes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.pasta_sociedade.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_ler_comandos_perfil_md(self):
        pasta_docs = self.p / 'docs' / 'sociedade'
        pasta_docs.mkdir(parents=True, exist_ok=True)
        perfil = pasta_docs / 'perfil.md'
        perfil.write_text(
            "# Perfil de Teste\n\n"
            "## Comandos\n"
            "- Build: `npm run build`\n"
            "- Testes: `npm test`\n"
            "- Lint e tipos: `npm run typecheck`\n",
            encoding='utf-8'
        )

        cmds = ler_comandos_perfil(self.p)
        self.assertEqual(cmds['build'], 'npm run build')
        self.assertEqual(cmds['testes'], 'npm test')
        self.assertEqual(cmds['lint'], 'npm run typecheck')

    def test_comando_build_sucesso_e_falha(self):
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'main.py').write_text('print("ok")\n', encoding='utf-8')

        verificador = VerificadorPreDevolucao(pasta_projeto=self.p, pasta_sociedade=self.pasta_sociedade)

        # 1. Falha no build reprova com evidência reproduzível
        atestado_falha = verificador.executar(
            comando_build='python3 -c "import sys; sys.exit(42)"',
            ignorar_testes=True,
            motivo_ignorar='teste isolado de build',
            arquivos_alvo=['src/main.py']
        )
        self.assertEqual(atestado_falha['status'], 'REPROVADO')
        self.assertFalse(atestado_falha['verificacoes']['build']['ok'])
        self.assertEqual(atestado_falha['verificacoes']['build']['codigo'], 42)
        self.assertTrue(any('42' in e for e in atestado_falha['erros']))
        self.assertIn('atestado_hash', atestado_falha)
        self.assertEqual(len(atestado_falha['atestado_hash']), 64)

        # 2. Sucesso no build
        atestado_ok = verificador.executar(
            comando_build='python3 -c "exit(0)"',
            ignorar_testes=True,
            motivo_ignorar='teste isolado de build',
            arquivos_alvo=['src/main.py']
        )
        self.assertEqual(atestado_ok['status'], 'APROVADO')
        self.assertTrue(atestado_ok['verificacoes']['build']['ok'])
        self.assertIn('atestado_hash', atestado_ok)
        self.assertEqual(len(atestado_ok['atestado_hash']), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in atestado_ok['atestado_hash']))

    def test_checagem_estatica_tipos_typescript_falho_reprova(self):
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'app.ts').write_text('const x: number = "texto";\n', encoding='utf-8')

        verificador = VerificadorPreDevolucao(pasta_projeto=self.p, pasta_sociedade=self.pasta_sociedade)
        atestado = verificador.executar(
            comando_lint='python3 -c "import sys; print(\'Type error TS2322: Type string is not assignable to type number\', file=sys.stderr); sys.exit(1)"',
            ignorar_testes=True,
            motivo_ignorar='teste estatico ts',
            arquivos_alvo=['src/app.ts']
        )
        self.assertEqual(atestado['status'], 'REPROVADO')
        self.assertFalse(atestado['verificacoes']['tipos_estaticos']['ok'])
        self.assertTrue(any('Type error TS2322' in e for e in atestado['erros']))

    def test_desacoplamento_fatias_concorrentes_ignorar_externos(self):
        """Valida que erros em arquivos fora do escopo delimitado da fatia não bloqueiam o atestado."""
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        # Arquivo da nossa fatia (válido)
        (self.p / 'src' / 'fatia_ativa.py').write_text('def f(): return True\n', encoding='utf-8')
        # Arquivo de outra fatia concorrente no mesmo workspace (com erro de sintaxe)
        (self.p / 'src' / 'outra_fatia.py').write_text('def sintaxe_quebrada(:::\n', encoding='utf-8')

        verificador = VerificadorPreDevolucao(pasta_projeto=self.p, pasta_sociedade=self.pasta_sociedade)

        # Sem ignorar arquivos externos ou sem escopo delimitado, falharia
        atestado_isolado = verificador.executar(
            arquivos_alvo=['src/fatia_ativa.py'],
            ignorar_arquivos_externos=True,
            ignorar_testes=True,
            motivo_ignorar='fatia isolada em workspace compartilhado'
        )
        self.assertEqual(atestado_isolado['status'], 'APROVADO')
        self.assertEqual(atestado_isolado['total_arquivos_inspecionados'], 1)

    def test_cli_pre_devolucao_exit_code_1_em_reprovacao(self):
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'alvo.py').write_text('print("alvo")\n', encoding='utf-8')

        # Falha de build via CLI
        res = rodar(
            SCRIPT_PRE,
            '--pasta-projeto', str(self.p),
            '--arquivos-alvo', 'src/alvo.py',
            '--ignorar-testes',
            '--motivo-ignorar', 'teste cli erro',
            '--comando-build', 'python3 -c "exit(1)"',
            cwd=self.p
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn('ATESTADO PRÉ-DEVOLUÇÃO: REPROVADO', res.stdout)

    def test_atestado_hash_sha256_determinismo_e_diferenciacao(self):
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'det.py').write_text('x = 1\n', encoding='utf-8')

        verificador = VerificadorPreDevolucao(pasta_projeto=self.p, pasta_sociedade=self.pasta_sociedade)

        atest_1 = verificador.executar(
            etapa_id='SC-E1',
            fatia_id='1',
            papel='Legolas',
            arquivos_alvo=['src/det.py'],
            ignorar_testes=True,
            motivo_ignorar='teste hash determinismo'
        )
        atest_2 = verificador.executar(
            etapa_id='SC-E1',
            fatia_id='1',
            papel='Legolas',
            arquivos_alvo=['src/det.py'],
            ignorar_testes=True,
            motivo_ignorar='teste hash determinismo'
        )
        # Determinístico para mesmo conteúdo estruturado
        self.assertEqual(atest_1['atestado_hash'], atest_2['atestado_hash'])

        # Se mudar algo estrutural (ex: outro papel), o hash muda
        atest_3 = verificador.executar(
            etapa_id='SC-E1',
            fatia_id='1',
            papel='Aragorn',
            arquivos_alvo=['src/det.py'],
            ignorar_testes=True,
            motivo_ignorar='teste hash determinismo'
        )
        self.assertNotEqual(atest_1['atestado_hash'], atest_3['atestado_hash'])

    def test_portao_sem_testes_sem_justificativa_gera_reprovado_fail_closed(self):
        """BLOQUEADOR R03-002: Ausência de testes sem justificativa explícita reprova a pré-devolução."""
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'codigo.py').write_text('def f(): return True\n', encoding='utf-8')

        verificador = VerificadorPreDevolucao(pasta_projeto=self.p, pasta_sociedade=self.pasta_sociedade)

        # 1. Sem testes e sem justificativa -> REPROVADO
        atestado_reprovado = verificador.executar(
            arquivos_alvo=['src/codigo.py']
        )
        self.assertEqual(atestado_reprovado['status'], 'REPROVADO')
        self.assertFalse(atestado_reprovado['verificacoes']['testes']['ok'])
        msg_esperada = (
            'Nenhum teste configurado ou diretório de testes detectado no projeto. '
            'Para dispensar testes na pré-devolução, utilize --ignorar-testes '
            'acompanhado de justificativa explícita (--motivo-ignorar).'
        )
        self.assertIn(msg_esperada, atestado_reprovado['verificacoes']['testes']['detalhes'])
        self.assertIn(msg_esperada, atestado_reprovado['erros'])

        # 2. Com --ignorar-testes mas sem motivo -> REPROVADO
        atestado_sem_motivo = verificador.executar(
            arquivos_alvo=['src/codigo.py'],
            ignorar_testes=True,
            motivo_ignorar=''
        )
        self.assertEqual(atestado_sem_motivo['status'], 'REPROVADO')
        self.assertFalse(atestado_sem_motivo['verificacoes']['testes']['ok'])
        self.assertTrue(any('exige justificativa explícita' in e for e in atestado_sem_motivo['erros']))

        # 3. Com --ignorar-testes e justificativa válida -> APROVADO
        atestado_aprovado = verificador.executar(
            arquivos_alvo=['src/codigo.py'],
            ignorar_testes=True,
            motivo_ignorar='Projeto embrionário sem suíte automatizada configurada'
        )
        self.assertEqual(atestado_aprovado['status'], 'APROVADO')
        self.assertTrue(atestado_aprovado['verificacoes']['testes']['ok'])
        self.assertIn('Dispensado com justificativa', atestado_aprovado['verificacoes']['testes']['detalhes'])

        # 4. Via CLI: sem flags falha com código 1; com flags passa com código 0
        r_cli_falha = rodar(
            SCRIPT_PRE,
            '--pasta-projeto', str(self.p),
            '--arquivos-alvo', 'src/codigo.py',
            cwd=self.p
        )
        self.assertEqual(r_cli_falha.returncode, 1)
        self.assertIn('ATESTADO PRÉ-DEVOLUÇÃO: REPROVADO', r_cli_falha.stdout)
        self.assertIn(msg_esperada, r_cli_falha.stdout)

        r_cli_ok = rodar(
            SCRIPT_PRE,
            '--pasta-projeto', str(self.p),
            '--arquivos-alvo', 'src/codigo.py',
            '--ignorar-testes',
            '--motivo-ignorar', 'dispensa via cli autorizada',
            cwd=self.p
        )
        self.assertEqual(r_cli_ok.returncode, 0)
        self.assertIn('ATESTADO PRÉ-DEVOLUÇÃO: APROVADO', r_cli_ok.stdout)

    def test_linter_antitoken_proibicoes_legitimas(self):
        """Casos legítimos de negação e proibição explícita devem ser aceitos (isentos)."""
        docs_dir = self.p / 'docs'
        docs_dir.mkdir(parents=True, exist_ok=True)
        md_legitimo = docs_dir / 'regras_legitimas.md'
        md_legitimo.write_text(
            '# Regras\n\n'
            '- Nunca estime nem relate consumo de tokens, cota ou custo.\n'
            '- Sem medição de tokens na rodada.\n'
            '- Não há estimativa de tokens nesta etapa.\n'
            '- Proibido estimar tokens e custos operacionais.\n'
            '- Ausência de medição de tokens comprovada.\n'
            '- Dispensada a medição de consumo na fase de planejamento.\n',
            encoding='utf-8'
        )

        verificador = VerificadorPreDevolucao(pasta_projeto=self.p, pasta_sociedade=self.pasta_sociedade)
        atestado_legitimo = verificador.executar(
            arquivos_alvo=['docs/regras_legitimas.md'],
            ignorar_testes=True,
            motivo_ignorar='teste regras legitimas'
        )
        self.assertEqual(atestado_legitimo['status'], 'APROVADO')
        self.assertTrue(atestado_legitimo['verificacoes']['seguranca_antitoken']['ok'])

    @unittest.skip("R03-006 adiado para a RM-2 (Q118)")
    def test_linter_antitoken_sem_bypass_incidental(self):
        """OPCIONAL R03-006: Negação incidental como 'sem' não pode burlar o linter antitoken."""
        docs_dir = self.p / 'docs'
        docs_dir.mkdir(parents=True, exist_ok=True)
        md_bypass = docs_dir / 'relatorio_incidental.md'
        # Linha proibida que tem a palavra 'sem' no final, mas relata medição real de tokens
        md_bypass.write_text(
            '# Relatorio\n\n'
            'Gandalf estimou consumo de 40 mil tokens, sem revisar antes.\n',
            encoding='utf-8'
        )

        verificador = VerificadorPreDevolucao(pasta_projeto=self.p, pasta_sociedade=self.pasta_sociedade)

        atestado_bypass = verificador.executar(
            arquivos_alvo=['docs/relatorio_incidental.md'],
            ignorar_testes=True,
            motivo_ignorar='teste linter antitoken'
        )
        self.assertEqual(atestado_bypass['status'], 'REPROVADO')
        self.assertFalse(atestado_bypass['verificacoes']['seguranca_antitoken']['ok'])
        self.assertTrue(any('Violação da regra antitoken' in e for e in atestado_bypass['erros']))
        self.assertTrue(any('40 mil tokens' in e for e in atestado_bypass['erros']))


def _git(pasta, *args):
    return subprocess.run(['git', '-C', str(pasta), *args], capture_output=True, text=True, check=True).stdout.strip()


def _commit(pasta, msg):
    _git(pasta, 'add', '-A')
    _git(pasta, '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', msg)
    return _git(pasta, 'rev-parse', 'HEAD')


class TestPortaoCandidatoCommitado(unittest.TestCase):
    """D01 do diagnóstico de 25/09/2026: o portão inspecionava 0 arquivos com o candidato commitado
    ou com o pacote numa subpasta, e aprovava sem olhar nada."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / 'repo'
        (self.repo / 'pacote' / 'tests').mkdir(parents=True)
        (self.repo / 'sociedade').mkdir()
        (self.repo / 'pacote' / 'a.py').write_text('x = 1\n', encoding='utf-8')
        (self.repo / 'sociedade' / 'andamento.md').write_text('# estado\n', encoding='utf-8')
        _git(self.repo, 'init', '-q')
        self.base = _commit(self.repo, 'base')

    def tearDown(self):
        self.tmp.cleanup()

    def _executar(self, pasta, **kw):
        v = VerificadorPreDevolucao(pasta_projeto=pasta, pasta_sociedade=self.repo / 'sociedade')
        return v.executar(ignorar_testes=True, motivo_ignorar='sonda D01', **kw)

    def test_candidato_commitado_com_base_inspeciona_arquivos(self):
        (self.repo / 'pacote' / 'a.py').write_text('x = 2\n', encoding='utf-8')
        head = _commit(self.repo, 'candidato')
        at = self._executar(self.repo, base=self.base)
        self.assertEqual(at['status'], 'APROVADO', at['erros'])
        self.assertEqual(at['total_arquivos_inspecionados'], 1)
        self.assertEqual(at['commit'], head)
        self.assertEqual(at['base'], self.base)
        self.assertEqual(at['versao'], '1.2.0')
        self.assertIn('pacote/a.py', at['hashes_artefatos'])

    def test_candidato_commitado_sem_base_reprova_em_vez_de_aprovar_vazio(self):
        (self.repo / 'pacote' / 'a.py').write_text('x = 3\n', encoding='utf-8')
        _commit(self.repo, 'candidato')
        at = self._executar(self.repo)
        self.assertEqual(at['status'], 'REPROVADO')
        self.assertTrue(any('Nada a inspecionar' in e for e in at['erros']))

    def test_pacote_em_subpasta_inspeciona_alteracao(self):
        (self.repo / 'pacote' / 'a.py').write_text('def f(:\n', encoding='utf-8')
        at = self._executar(self.repo / 'pacote')
        self.assertEqual(at['total_arquivos_inspecionados'], 1)
        self.assertEqual(at['status'], 'REPROVADO')
        self.assertFalse(at['verificacoes']['compilacao']['ok'])

    def test_commit_do_candidato_em_sociedade_reprova(self):
        (self.repo / 'sociedade' / 'andamento.md').write_text('# alterado pelo candidato\n', encoding='utf-8')
        _commit(self.repo, 'candidato mexe na governança')
        at = self._executar(self.repo, base=self.base)
        self.assertEqual(at['status'], 'REPROVADO')
        self.assertTrue(any('governança' in e for e in at['erros']))

    def test_governanca_nao_commitada_na_pasta_principal_nao_contamina_candidato(self):
        (self.repo / 'pacote' / 'a.py').write_text('x = 4\n', encoding='utf-8')
        _commit(self.repo, 'candidato')
        (self.repo / 'sociedade' / 'andamento.md').write_text('# registro em andamento\n', encoding='utf-8')
        at = self._executar(self.repo, base=self.base)
        self.assertEqual(at['status'], 'APROVADO', at['erros'])

    def test_base_invalida_reprova(self):
        at = self._executar(self.repo, base='nao-existe')
        self.assertEqual(at['status'], 'REPROVADO')
        self.assertTrue(any('Base inválida' in e for e in at['erros']))

    def test_portao_nao_grava_arquivos_no_projeto(self):
        (self.repo / 'pacote' / 'a.py').write_text('x = 6\n', encoding='utf-8')
        self._executar(self.repo / 'pacote')
        self.assertFalse((self.repo / 'pacote' / '__pycache__').exists())
        at = self._executar(self.repo / 'pacote')
        self.assertEqual(at['total_arquivos_inspecionados'], 1)

    def test_cli_aceita_base(self):
        (self.repo / 'pacote' / 'a.py').write_text('x = 5\n', encoding='utf-8')
        _commit(self.repo, 'candidato')
        saida = Path(self.tmp.name) / 'at.json'
        r = rodar(SCRIPT_PRE, '--pasta-projeto', str(self.repo / 'pacote'), '--base', self.base,
                  '--pasta-sociedade', str(self.repo / 'sociedade'),
                  '--ignorar-testes', '--motivo-ignorar', 'cli', '--saida-json', str(saida))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(saida.read_text())['total_arquivos_inspecionados'], 1)


if __name__ == '__main__':
    unittest.main()
