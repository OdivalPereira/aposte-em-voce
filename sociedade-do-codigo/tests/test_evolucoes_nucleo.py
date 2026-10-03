"""Testes unitários para as evoluções do núcleo pós-teste operacional.

Cobre as 5 frentes de melhoria:
1. Sincronização de versão e resolução de <preencher>.
2. Portão pré-devolução multilinguagem (build e checagem de tipos estáticos).
3. Desacoplamento de fatias paralelas em workspaces compartilhados (--ignorar-arquivos-externos).
4. Operações macro atômicas de despacho e devolução em sc_passagem.py (despachar e receber).
5. Tolerância a sinônimos de estado de achados (--status resolvido/fechado/atendido e --id).
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from util import NUCLEO, carregar, rodar

MOD_REG = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REG.Registro
ErroValidacaoRegistro = MOD_REG.ErroValidacaoRegistro

MOD_ROD = carregar(NUCLEO / 'scripts' / 'sc_rodada.py', 'sc_rodada')
MOD_PRE = carregar(NUCLEO / 'scripts' / 'sc_pre_devolucao.py', 'sc_pre_devolucao')
VerificadorPreDevolucao = MOD_PRE.VerificadorPreDevolucao
ler_comandos_perfil = MOD_PRE.ler_comandos_perfil

MOD_PSG = carregar(NUCLEO / 'scripts' / 'sc_passagem.py', 'sc_passagem')
GerenciadorPassagem = MOD_PSG.GerenciadorPassagem
ErroPassagem = MOD_PSG.ErroPassagem

SCRIPT_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'
SCRIPT_PASSAGEM = NUCLEO / 'scripts' / 'sc_passagem.py'
SCRIPT_PRE = NUCLEO / 'scripts' / 'sc_pre_devolucao.py'
SCRIPT_INIT = NUCLEO / 'scripts' / 'sc_init.py'


class TesteSincronizacaoVersao(unittest.TestCase):
    """Frente 1: Resolução de <preencher> e sincronização Git HEAD."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'

        # Inicializa um repositório git real no diretório temporário
        subprocess.run(['git', 'init'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Tester'], cwd=self.p, capture_output=True, check=True)
        (self.p / 'README.md').write_text('# Projeto Teste\n', encoding='utf-8')
        subprocess.run(['git', 'add', 'README.md'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'commit inicial'], cwd=self.p, capture_output=True, check=True)
        r = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.p, capture_output=True, text=True, check=True)
        self.commit_inicial = r.stdout.strip()

    def tearDown(self):
        self._tmp.cleanup()

    def test_registro_captura_e_usa_versao_inicial(self):
        reg = Registro.inicializar(self.pasta_sociedade, 'proj-v', str(self.p), versao_inicial=self.commit_inicial)
        self.assertEqual(reg.versao_inicial, self.commit_inicial)

        # Ao abrir etapa com '<preencher>', o registro substitui pela versao_inicial
        reg.abrir_etapa(
            etapa_id='SC-E1',
            objetivo='Teste',
            plano_ref='plano.md',
            autorizacao_ref='AUT-1',
            base_efetiva='<preencher>',
            criterios=['C1']
        )
        est = reg.estado()
        self.assertEqual(est['etapa_atual']['base_efetiva'], self.commit_inicial)

    def test_versao_atualizada_substitui_preencher_na_base_efetiva(self):
        reg = Registro.inicializar(self.pasta_sociedade, 'proj-v', str(self.p))
        reg.abrir_etapa(
            etapa_id='SC-E1',
            objetivo='Teste',
            plano_ref='plano.md',
            autorizacao_ref='AUT-1',
            base_efetiva='<preencher>',
            criterios=['C1']
        )
        # Registra nova versão e valida que base_efetiva deixa de ser <preencher>
        reg.sincronizar_versao('SC-E1', 'commit-hash-abc1234')
        est = reg.estado()
        self.assertEqual(est['etapa_atual']['versao_atual'], 'commit-hash-abc1234')
        self.assertEqual(est['etapa_atual']['base_efetiva'], 'commit-hash-abc1234')

    def test_cli_sincronizar_versao_e_abrir_git(self):
        # Abre rodada via CLI com --sincronizar-git
        res = rodar(SCRIPT_RODADA, 'abrir', '--pasta', str(self.pasta_sociedade),
                    '--id', 'SC-E1',
                    '--meta', 'Meta teste', '--aceite', 'C1', '--sincronizar-git', '--aplicar',
                    cwd=self.p)
        self.assertEqual(res.returncode, 0, res.stderr)

        p_rod = self.pasta_sociedade / 'rodada.md'
        self.assertTrue(p_rod.is_file())
        conteudo = p_rod.read_text(encoding='utf-8')
        self.assertIn(f'- base: {self.commit_inicial}', conteudo)

        # Testa comando dedicado sincronizar-versao
        res_sync = rodar(SCRIPT_RODADA, 'sincronizar-versao', '--pasta', str(self.pasta_sociedade),
                         '--versao', 'novo-hash-999', '--aplicar', cwd=self.p)
        self.assertEqual(res_sync.returncode, 0, res_sync.stderr)

        reg = Registro(self.pasta_sociedade)
        est = reg.estado()
        self.assertEqual(est['etapa_atual']['versao_atual'], 'novo-hash-999')


class TestePreDevolucaoMultilinguagemEDesacoplamento(unittest.TestCase):
    """Frentes 2 e 3: Comandos de build, checagem de tipos estáticos e escopo de fatias."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.pasta_sociedade.mkdir(parents=True, exist_ok=True)
        (self.p / 'docs' / 'sociedade').mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_leitura_comandos_perfil(self):
        perfil_md = self.p / 'docs' / 'sociedade' / 'perfil.md'
        perfil_md.write_text(
            "# Perfil\n\n"
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

    def test_comando_build_falho_reprova_pre_devolucao(self):
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'main.py').write_text('print("ok")\n', encoding='utf-8')

        verificador = VerificadorPreDevolucao(pasta_projeto=self.p, pasta_sociedade=self.pasta_sociedade)
        atestado = verificador.executar(
            comando_build='python3 -c "import sys; sys.exit(42)"',
            ignorar_testes=True,
            motivo_ignorar='teste isolado de build',
            arquivos_alvo=['src/main.py']
        )
        self.assertEqual(atestado['status'], 'REPROVADO')
        self.assertTrue(any('42' in e for e in atestado['erros']))

    def test_comando_tipos_falho_reprova_pre_devolucao(self):
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'app.ts').write_text('const x: number = 1;\n', encoding='utf-8')

        verificador = VerificadorPreDevolucao(pasta_projeto=self.p, pasta_sociedade=self.pasta_sociedade)
        atestado = verificador.executar(
            comando_lint='python3 -c "import sys; print(\'Type error\', file=sys.stderr); sys.exit(1)"',
            ignorar_testes=True,
            motivo_ignorar='teste de tipos',
            arquivos_alvo=['src/app.ts']
        )
        self.assertEqual(atestado['status'], 'REPROVADO')

    def test_desacoplamento_ignorar_arquivos_externos(self):
        """Arquivos com erro de sintaxe fora do escopo da fatia são ignorados."""
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'fatia_1.py').write_text('def f(): return 1\n', encoding='utf-8')
        # Arquivo alheio quebrado no workspace
        (self.p / 'src' / 'outro_desenvolvedor.py').write_text('def quebrado(:::\n', encoding='utf-8')

        verificador = VerificadorPreDevolucao(pasta_projeto=self.p, pasta_sociedade=self.pasta_sociedade)

        # Com arquivos_alvo e ignorar_arquivos_externos, apenas fatia_1.py é validado
        atestado = verificador.executar(
            arquivos_alvo=['src/fatia_1.py'],
            ignorar_arquivos_externos=True,
            ignorar_testes=True,
            motivo_ignorar='validando fatia isolada'
        )
        self.assertEqual(atestado['status'], 'APROVADO')

    def test_cli_pre_devolucao_aceita_build_e_ignorar_externos(self):
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'alvo.py').write_text('print("alvo")\n', encoding='utf-8')
        json_path = self.p / 'saida.json'

        res = rodar(
            SCRIPT_PRE,
            '--pasta-projeto', str(self.p),
            '--arquivos-alvo', 'src/alvo.py',
            '--ignorar-arquivos-externos',
            '--ignorar-testes',
            '--motivo-ignorar', 'teste cli',
            '--comando-build', 'python3 -c "exit(0)"',
            '--saida-json', str(json_path),
            cwd=self.p
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(json_path.is_file())
        dados = json.loads(json_path.read_text(encoding='utf-8'))
        self.assertEqual(dados['status'], 'APROVADO')


class TesteMacroPassagemDespacharReceber(unittest.TestCase):
    """Frente 4: Operações macro despachar e receber em sc_passagem.py."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.pasta_sociedade.mkdir(parents=True, exist_ok=True)

        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'codigo.py').write_text('def execute(): return True\n', encoding='utf-8')

        (self.p / 'tests').mkdir(parents=True, exist_ok=True)
        (self.p / 'tests' / 'test_codigo.py').write_text(
            'import unittest\n\nclass Teste(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n',
            encoding='utf-8'
        )

        # Inicializa rodada via CLI
        r_abrir = rodar(SCRIPT_RODADA, 'abrir', '--pasta', str(self.pasta_sociedade),
                        '--id', 'SC-E1',
                        '--meta', 'Meta Macro', '--fatia', 'Implementar codigo',
                        '--aceite', 'fatia_1', '--aplicar', cwd=self.p)
        if r_abrir.returncode != 0:
            raise RuntimeError(f"Falha ao abrir rodada no setUp: {r_abrir.stderr}")

        self.reg = Registro(self.pasta_sociedade)
        self.gerente = GerenciadorPassagem(self.reg, self.p)

    def tearDown(self):
        self._tmp.cleanup()

    def test_despachar_e_receber_atomicos_completos(self):
        # 1. Despachar atomicamente
        res_despacho = self.gerente.despachar(
            para='Legolas',
            faca=['Refatorar modulo codigo.py'],
            leia_so=['src/codigo.py'],
            fatia=1,
            de='Gandalf',
            aplicar=True
        )
        self.assertEqual(res_despacho['status'], 'confirmada')
        self.assertEqual(res_despacho['bastao'], 'Legolas')

        # Verifica sincronia em rodada.md
        p_rod = self.pasta_sociedade / 'rodada.md'
        conteudo_rod = p_rod.read_text(encoding='utf-8')
        self.assertIn('- bastao: Legolas', conteudo_rod)
        self.assertIn('1. Implementar codigo — em andamento', conteudo_rod)
        self.assertIn('bastão está com: Legolas', conteudo_rod)

        # 2. Receber devolução com sucesso
        res_recebimento = self.gerente.receber(
            executor='Legolas',
            resultado='Modulo refatorado com sucesso',
            prova='python3 -m py_compile src/codigo.py',
            fatia=1,
            ignorar_arquivos_externos=True,
            devolver_para='Gandalf',
            aplicar=True
        )
        self.assertEqual(res_recebimento['status'], 'concluida')
        self.assertEqual(res_recebimento['devolver_para'], 'Gandalf')

        # Verifica sincronia pós-devolução em rodada.md
        conteudo_pos = p_rod.read_text(encoding='utf-8')
        self.assertIn('- bastao: Gandalf', conteudo_pos)
        self.assertIn('1. Implementar codigo — fechada · prova:', conteudo_pos)

        # Verifica tarefa concluída no registro.json
        est = self.reg.estado()
        tarefa_info = est['etapa_atual']['tarefas'].get('fatia_1')
        self.assertEqual(tarefa_info['estado'], 'concluida')

    def test_receber_com_falha_de_pre_devolucao_bloqueia_fail_closed(self):
        # Despacha fatia
        self.gerente.despachar(
            para='Legolas',
            faca=['Modificar codigo'],
            leia_so=['src/codigo.py'],
            fatia=1,
            aplicar=True
        )

        # Insere erro de sintaxe no arquivo
        (self.p / 'src' / 'codigo.py').write_text('def erro(::\n', encoding='utf-8')

        # Tentativa de receber deve falhar fechada levantando ErroPassagem
        with self.assertRaises(ErroPassagem) as ctx:
            self.gerente.receber(
                executor='Legolas',
                resultado='Entregue',
                fatia=1,
                ignorar_arquivos_externos=True,
                aplicar=True
            )
        self.assertIn('Portão de Pré-Devolução reprovou', str(ctx.exception))

    def test_cli_despachar_e_receber(self):
        # CLI despachar
        r_desp = rodar(
            SCRIPT_PASSAGEM,
            'despachar',
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--pasta-projeto', str(self.p),
            '--para', 'Legolas',
            '--faca', 'Ajustar codigo',
            '--leia-so', 'src/codigo.py',
            '--fatia', '1',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(r_desp.returncode, 0, r_desp.stderr)
        self.assertIn('PASSAGEM DESPACHADA E CONFIRMADA ATOMICAMENTE', r_desp.stdout)

        # CLI receber
        r_rec = rodar(
            SCRIPT_PASSAGEM,
            'receber',
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--pasta-projeto', str(self.p),
            '--executor', 'Legolas',
            '--fatia', '1',
            '--prova', 'testes passaram',
            '--ignorar-arquivos-externos',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(r_rec.returncode, 0, r_rec.stderr)
        self.assertIn('DEVOLUÇÃO RECEBIDA E CONCLUÍDA ATOMICAMENTE', r_rec.stdout)


class TesteSinonimosAchadosEFatias(unittest.TestCase):
    """Frente 5: Tolerância a sinônimos de estado de achados e parsing de fatias."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.pasta_sociedade.mkdir(parents=True, exist_ok=True)

        r_abrir = rodar(SCRIPT_RODADA, 'abrir', '--pasta', str(self.pasta_sociedade),
                        '--id', 'SC-E1',
                        '--meta', 'Meta Achados', '--fatia', 'Fatia unica',
                        '--aceite', 'fatia_1', '--aplicar', cwd=self.p)
        if r_abrir.returncode != 0:
            raise RuntimeError(f"Falha ao abrir rodada no setUp: {r_abrir.stderr}")

    def tearDown(self):
        self._tmp.cleanup()

    def test_achado_sinonimos_status_e_id(self):
        # 1. Cria achado
        rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
              '--severidade', 'relevante', '--onde', 'src/app.py:10',
              '--texto', 'Falta tratamento de nulo', '--aplicar', cwd=self.p)

        p_rod = self.pasta_sociedade / 'rodada.md'
        conteudo = p_rod.read_text(encoding='utf-8')
        self.assertIn('REV-001 · relevante · src/app.py:10 · Falta tratamento de nulo · aberto', conteudo)

        # 2. Atualiza usando --status resolvido e --id REV-001
        res = rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
                    '--id', 'REV-001', '--status', 'resolvido', '--aplicar', cwd=self.p)
        self.assertEqual(res.returncode, 0, res.stderr)

        conteudo_resolvido = p_rod.read_text(encoding='utf-8')
        self.assertIn('REV-001 · relevante · src/app.py:10 · Falta tratamento de nulo · corrigido', conteudo_resolvido)

        # 3. Testa sinônimo 'fechado'
        # Cria segundo achado
        rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
              '--severidade', 'opcional', '--onde', 'docs/spec.md:5',
              '--texto', 'Tipografia', '--aplicar', cwd=self.p)

        res2 = rodar(SCRIPT_RODADA, 'achado', '--pasta', str(self.pasta_sociedade),
                     '--fechar', 'REV-002', '--status', 'fechado', '--aplicar', cwd=self.p)
        self.assertEqual(res2.returncode, 0, res2.stderr)

        conteudo_fechado = p_rod.read_text(encoding='utf-8')
        self.assertIn('REV-002 · opcional · docs/spec.md:5 · Tipografia · corrigido', conteudo_fechado)


if __name__ == '__main__':
    unittest.main()
