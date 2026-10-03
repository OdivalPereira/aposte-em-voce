"""Testes unitários dedicados para sc_passagem.py pós-teste operacional.

Cobre:
1. Operações macro atômicas de despacho e devolução (despachar e receber).
2. Inferência automática de fatia pendente no despacho e de fatia em andamento no recebimento.
3. Portão de pré-devolução fail-closed no macro receber (bloqueio quando pré-devolução reprova).
4. Suporte a --comando-regressao e alias --comando-lint no macro receber.
5. Retrocompatibilidade com subcomandos granulares (despachar-local, confirmar, concluir).
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

MOD_PSG = carregar(NUCLEO / 'scripts' / 'sc_passagem.py', 'sc_passagem')
GerenciadorPassagem = MOD_PSG.GerenciadorPassagem
ErroPassagem = MOD_PSG.ErroPassagem
ErroEstadoPassagem = MOD_PSG.ErroEstadoPassagem

SCRIPT_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'
SCRIPT_PASSAGEM = NUCLEO / 'scripts' / 'sc_passagem.py'


class TesteScPassagemEvolucoes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.pasta_sociedade.mkdir(parents=True, exist_ok=True)

        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'modulo.py').write_text('def executar(): return True\n', encoding='utf-8')

        (self.p / 'tests').mkdir(parents=True, exist_ok=True)
        (self.p / 'tests' / 'test_modulo.py').write_text(
            'import unittest\n'
            'class TesteModulo(unittest.TestCase):\n'
            '    def test_ok(self):\n'
            '        self.assertTrue(True)\n',
            encoding='utf-8'
        )

        # Abre rodada com 2 fatias
        r_abrir = rodar(
            SCRIPT_RODADA, 'abrir',
            '--pasta', str(self.pasta_sociedade),
            '--id', 'SC-E1',
            '--meta', 'Meta Passagem',
            '--fatia', 'Primeira fatia',
            '--fatia', 'Segunda fatia',
            '--aceite', 'fatia_1',
            '--aceite', 'fatia_2',
            '--aplicar',
            cwd=self.p
        )
        if r_abrir.returncode != 0:
            raise RuntimeError(f"Falha ao abrir rodada no setUp: {r_abrir.stderr}")

        self.reg = Registro(self.pasta_sociedade)
        self.gerente = GerenciadorPassagem(self.reg, self.p)

    def tearDown(self):
        self._tmp.cleanup()

    def test_despacho_com_inferencia_automatica_de_fatia(self):
        # Despacha sem informar --fatia nem --tarefa; deve inferir a primeira pendente (fatia_1)
        res_despacho = self.gerente.despachar(
            para='Legolas',
            faca=['Construir feature A'],
            leia_so=['src/modulo.py'],
            de='Gandalf',
            aplicar=True
        )
        self.assertEqual(res_despacho['status'], 'confirmada')
        self.assertEqual(res_despacho['bastao'], 'Legolas')
        self.assertEqual(res_despacho['tarefa_id'], 'fatia_1')

        # Valida que rodada.md colocou fatia 1 em andamento
        p_rod = self.pasta_sociedade / 'rodada.md'
        txt = p_rod.read_text(encoding='utf-8')
        self.assertIn('- bastao: Legolas', txt)
        self.assertIn('1. Primeira fatia — em andamento', txt)
        self.assertIn('2. Segunda fatia — pendente', txt)

    def test_receber_com_inferencia_automatica_e_sucesso(self):
        # 1. Despacha fatia 1
        self.gerente.despachar(
            para='Legolas',
            faca=['Construir feature A'],
            leia_so=['src/modulo.py'],
            fatia=1,
            aplicar=True
        )

        # 2. Recebe sem especificar fatia nem tarefa; deve inferir a fatia em andamento
        res_rec = self.gerente.receber(
            executor='Legolas',
            resultado='Feature A concluída',
            prova='python3 -m py_compile src/modulo.py',
            ignorar_arquivos_externos=True,
            ignorar_testes=True,
            motivo_ignorar='Compilação de módulo sem suíte de testes',
            devolver_para='Gandalf',
            aplicar=True
        )
        self.assertEqual(res_rec['status'], 'concluida')
        self.assertEqual(res_rec['tarefa_id'], 'fatia_1')
        self.assertEqual(res_rec['devolver_para'], 'Gandalf')

        # Valida que rodada.md fechou a fatia 1 e devolveu o bastão
        p_rod = self.pasta_sociedade / 'rodada.md'
        txt = p_rod.read_text(encoding='utf-8')
        self.assertIn('- bastao: Gandalf', txt)
        self.assertIn('1. Primeira fatia — fechada · prova: python3 -m py_compile src/modulo.py', txt)
        self.assertIn('2. Segunda fatia — pendente', txt)

        # Valida tarefa concluída no registro.json
        est = self.reg.estado()
        self.assertEqual(est['etapa_atual']['tarefas']['fatia_1']['estado'], 'concluida')
        self.assertIsNotNone(res_rec.get('atestado'))
        self.assertIn('atestado_hash', res_rec['atestado'])
        self.assertEqual(len(res_rec['atestado']['atestado_hash']), 64)

    def test_receber_falha_fechada_no_pre_devolucao(self):
        self.gerente.despachar(
            para='Legolas',
            faca=['Modificar codigo'],
            leia_so=['src/modulo.py'],
            fatia=1,
            aplicar=True
        )

        # Insere erro de sintaxe
        (self.p / 'src' / 'modulo.py').write_text('def erro_sintaxe(::\n', encoding='utf-8')

        with self.assertRaises(ErroPassagem) as ctx:
            self.gerente.receber(
                executor='Legolas',
                resultado='Tentativa',
                fatia=1,
                ignorar_arquivos_externos=True,
                aplicar=True
            )
        self.assertIn('Portão de Pré-Devolução reprovou', str(ctx.exception))

        # Confirma que a fatia NÃO foi fechada em rodada.md
        p_rod = self.pasta_sociedade / 'rodada.md'
        txt = p_rod.read_text(encoding='utf-8')
        self.assertIn('1. Primeira fatia — em andamento', txt)

    def test_receber_com_comando_regressao_falho(self):
        self.gerente.despachar(
            para='Legolas',
            faca=['Modificar codigo'],
            leia_so=['src/modulo.py'],
            fatia=1,
            aplicar=True
        )

        with self.assertRaises(ErroPassagem) as ctx:
            self.gerente.receber(
                executor='Legolas',
                resultado='OK',
                fatia=1,
                comando_regressao='python3 -c "import sys; sys.exit(7)"',
                ignorar_arquivos_externos=True,
                aplicar=True
            )
        self.assertIn('Comando de regressão falhou com código 7', str(ctx.exception))

    def test_cli_despachar_e_receber_com_comando_lint(self):
        r_desp = rodar(
            SCRIPT_PASSAGEM, 'despachar',
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--pasta-projeto', str(self.p),
            '--para', 'Legolas',
            '--faca', 'Implementar modulo',
            '--leia-so', 'src/modulo.py',
            '--fatia', '1',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(r_desp.returncode, 0, r_desp.stderr)

        r_rec = rodar(
            SCRIPT_PASSAGEM, 'receber',
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--pasta-projeto', str(self.p),
            '--executor', 'Legolas',
            '--fatia', '1',
            '--prova', 'passou',
            '--comando-lint', 'python3 -c "exit(0)"',
            '--ignorar-arquivos-externos',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(r_rec.returncode, 0, r_rec.stderr)
        self.assertIn('DEVOLUÇÃO RECEBIDA E CONCLUÍDA ATOMICAMENTE', r_rec.stdout)

    def test_retrocompatibilidade_comandos_granulares(self):
        # Testa despachar-local, confirmar e concluir
        r_local = rodar(
            SCRIPT_PASSAGEM, 'despachar-local',
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--pasta-projeto', str(self.p),
            '--etapa', 'SC-E1',
            '--para', 'Aragorn',
            '--tarefa', 'fatia_2',
            '--faca', 'Executar tarefa manual',
            '--leia-so', 'src/modulo.py',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(r_local.returncode, 0, r_local.stderr)
        self.assertIn('PASSAGEM DESPACHADA: PSG-', r_local.stdout)

        # Recupera ID da passagem criada
        dados_reg = self.reg.carregar_dados()
        ev_pass = next(ev for ev in reversed(dados_reg['eventos']) if ev['tipo'] == 'passagem_despachada')
        passagem_id = ev_pass['dados']['passagem_id']

        # Confirmar
        r_conf = rodar(
            SCRIPT_PASSAGEM, 'confirmar',
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--pasta-projeto', str(self.p),
            '--etapa', 'SC-E1',
            '--passagem', passagem_id,
            '--recebedor', 'Aragorn',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(r_conf.returncode, 0, r_conf.stderr)
        self.assertIn('RECEBIMENTO CONFIRMADO', r_conf.stdout)

        # Concluir
        r_conc = rodar(
            SCRIPT_PASSAGEM, 'concluir',
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--pasta-projeto', str(self.p),
            '--etapa', 'SC-E1',
            '--passagem', passagem_id,
            '--executor', 'Aragorn',
            '--resultado', 'Sucesso absoluto',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(r_conc.returncode, 0, r_conc.stderr)
        self.assertIn('PASSAGEM CONCLUÍDA', r_conc.stdout)

    def test_receber_sem_prova_explicita_usa_hash_atestado_em_rodada_md(self):
        # Despacha fatia 1
        self.gerente.despachar(
            para='Legolas',
            faca=['Construir feature sem prova explicita'],
            leia_so=['src/modulo.py'],
            fatia=1,
            aplicar=True
        )

        # Recebe sem parâmetro prova (deve gerar prova automática com hash de 12 caracteres)
        res_rec = self.gerente.receber(
            executor='Legolas',
            resultado='Feature concluída',
            ignorar_arquivos_externos=True,
            devolver_para='Gandalf',
            aplicar=True
        )
        self.assertEqual(res_rec['status'], 'concluida')
        h12 = res_rec['atestado']['atestado_hash'][:12]
        self.assertEqual(len(h12), 12)
        self.assertIn(f'Pré-devolução aprovado (hash={h12})', res_rec['prova'])

        # Valida que rodada.md contém o hash não vazio
        p_rod = self.pasta_sociedade / 'rodada.md'
        txt = p_rod.read_text(encoding='utf-8')
        self.assertIn(f'prova: Pré-devolução aprovado (hash={h12})', txt)

    def test_receber_com_fallback_git_status_em_arquivos_alvo(self):
        # Inicializa git no projeto temporário
        subprocess.run(['git', 'init'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 't@s.org'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Tester'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'add', '.'], cwd=self.p, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'base'], cwd=self.p, capture_output=True, check=True)

        # Despacha fatia 1 com leia_so restrito
        self.gerente.despachar(
            para='Legolas',
            faca=['Criar novo modulo'],
            leia_so=['src/modulo.py'],
            fatia=1,
            aplicar=True
        )

        # Cria novo arquivo durante o trabalho
        (self.p / 'src' / 'novo_modulo.py').write_text('def novo(): pass\n', encoding='utf-8')

        # Recebe sem especificar arquivos_alvo; deve incluir src/novo_modulo.py via git status
        res_rec = self.gerente.receber(
            executor='Legolas',
            fatia=1,
            devolver_para='Gandalf',
            aplicar=True
        )
        self.assertEqual(res_rec['status'], 'concluida')
        inspecionados = list(res_rec['atestado']['hashes_artefatos'].keys())
        self.assertTrue(any('novo_modulo.py' in a for a in inspecionados))

    def test_concluir_passagem_inexistente_lanca_erro(self):
        with self.assertRaises(ErroEstadoPassagem) as ctx:
            self.gerente.concluir_passagem(
                etapa_id='SC-E1',
                passagem_id='PSG-NAOEXISTE',
                executor='Legolas',
                resultado='Trabalho feito',
                aplicar=True
            )
        self.assertIn('Passagem PSG-NAOEXISTE não encontrada para conclusão.', str(ctx.exception))

    def test_concluir_passagem_executor_invalido_lanca_erro(self):
        desp = self.gerente.despachar(
            para='Legolas',
            faca=['Construir feature A'],
            leia_so=['src/modulo.py'],
            fatia=1,
            aplicar=True
        )
        passagem_id = desp['passagem']['passagem_id']

        with self.assertRaises(ErroEstadoPassagem) as ctx:
            self.gerente.concluir_passagem(
                etapa_id='SC-E1',
                passagem_id=passagem_id,
                executor='Elrond',
                resultado='Feature A concluída',
                aplicar=True
            )
        self.assertIn('Executor inválido: passagem foi despachada para Legolas, não Elrond.', str(ctx.exception))

    def test_concluir_passagem_idempotencia_e_divergencia(self):
        desp = self.gerente.despachar(
            para='Legolas',
            faca=['Construir feature A'],
            leia_so=['src/modulo.py'],
            fatia=1,
            aplicar=True
        )
        passagem_id = desp['passagem']['passagem_id']

        # Primeira conclusão
        res1 = self.gerente.concluir_passagem(
            etapa_id='SC-E1',
            passagem_id=passagem_id,
            executor='Legolas',
            resultado='Feature A concluída com perfeição',
            aplicar=True
        )
        self.assertEqual(res1['status'], 'concluida')

        # Segunda conclusão idêntica (idempotência)
        res2 = self.gerente.concluir_passagem(
            etapa_id='SC-E1',
            passagem_id=passagem_id,
            executor='Legolas',
            resultado='Feature A concluída com perfeição',
            aplicar=True
        )
        self.assertEqual(res2['status'], 'concluida')

        dados_registro = self.reg.carregar_dados() if hasattr(self.reg, 'carregar_dados') else self.reg._dados
        conclusoes = [
            ev for ev in dados_registro.get('eventos', [])
            if ev.get('tipo') == 'passagem_concluida' and ev.get('dados', {}).get('passagem_id') == passagem_id
        ]
        self.assertEqual(len(conclusoes), 1, "Apenas um evento deve ser gravado para chamadas idempotentes")

        # Tentativa com dados divergentes
        with self.assertRaises(ErroEstadoPassagem) as ctx:
            self.gerente.concluir_passagem(
                etapa_id='SC-E1',
                passagem_id=passagem_id,
                executor='Legolas',
                resultado='Outro resultado divergente',
                aplicar=True
            )
        self.assertIn('já concluída com dados divergentes', str(ctx.exception))

    def test_cli_receber_com_ignorar_testes_e_motivo(self):
        # Despacha fatia 1
        r_desp = rodar(
            SCRIPT_PASSAGEM, 'despachar',
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--pasta-projeto', str(self.p),
            '--para', 'Legolas',
            '--faca', 'Implementar modulo sem suite de testes',
            '--leia-so', 'src/modulo.py',
            '--fatia', '1',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(r_desp.returncode, 0, r_desp.stderr)

        # Recebe via CLI com flags de ignorar testes
        r_rec = rodar(
            SCRIPT_PASSAGEM, 'receber',
            '--pasta-sociedade', str(self.pasta_sociedade),
            '--pasta-projeto', str(self.p),
            '--executor', 'Legolas',
            '--fatia', '1',
            '--prova', 'apenas_build',
            '--ignorar-testes',
            '--motivo-ignorar', 'dispensa de testes via CLI justificada',
            '--ignorar-arquivos-externos',
            '--aplicar',
            cwd=self.p
        )
        self.assertEqual(r_rec.returncode, 0, r_rec.stderr)
        self.assertIn('DEVOLUÇÃO RECEBIDA E CONCLUÍDA ATOMICAMENTE', r_rec.stdout)


if __name__ == '__main__':
    unittest.main()
