import tempfile
import unittest
from pathlib import Path

from util import NUCLEO, carregar

MOD_REG = carregar(NUCLEO / 'scripts' / 'sc_registro.py', 'sc_registro')
Registro = MOD_REG.Registro

MOD_PSG = carregar(NUCLEO / 'scripts' / 'sc_passagem.py', 'sc_passagem')
GerenciadorPassagem = MOD_PSG.GerenciadorPassagem
ErroParadaHumana = MOD_PSG.ErroParadaHumana
ErroCaminhoIncorreto = MOD_PSG.ErroCaminhoIncorreto
ErroEntregaDuplicada = MOD_PSG.ErroEntregaDuplicada
ErroEstadoPassagem = MOD_PSG.ErroEstadoPassagem


class TestePassagem(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.p = Path(self._tmp.name)
        self.pasta_sociedade = self.p / 'sociedade'
        self.reg = Registro.inicializar(self.pasta_sociedade, 'projeto-passagem', str(self.p))
        self.reg.abrir_etapa(
            etapa_id='SC-E5-01',
            objetivo='Testar automação gradual de passagem e recuperação de falhas',
            plano_ref='planejamento.md#E5',
            autorizacao_ref='A-SC-E5-001',
            base_efetiva='head-e5',
            criterios=['C_PASSAGEM_CONFIRMADA', 'C_RECUPERACAO_FALHA']
        )
        self.gerente = GerenciadorPassagem(self.reg, self.p)

        # Cria arquivos reais no projeto para teste de leitura estrita
        (self.p / 'src').mkdir(parents=True, exist_ok=True)
        (self.p / 'src' / 'modulo_a.py').write_text('# Modulo A\n', encoding='utf-8')
        (self.p / 'src' / 'modulo_b.py').write_text('# Modulo B\n', encoding='utf-8')
        (self.p / 'docs').mkdir(parents=True, exist_ok=True)
        (self.p / 'docs' / 'especificacao.md').write_text('# Spec\n', encoding='utf-8')

    def tearDown(self):
        self._tmp.cleanup()

    def test_fluxo_normal_despacho_e_confirmacao(self):
        """Fluxo completo: despacho com caminhos válidos, handshake do destinatário e conclusão."""
        passagem = self.gerente.despachar_passagem(
            etapa_id='SC-E5-01',
            de='Gandalf',
            para='Elrond',
            tarefa_id='T-01',
            leia_so=['src/modulo_a.py', 'docs/especificacao.md'],
            faca=['Refatorar persistência'],
            nao_faca=['Não alterar schema'],
            limites='Restrito a src/modulo_a.py'
        )
        self.assertEqual(passagem['status'], 'despachada')
        self.assertEqual(passagem['para'], 'Elrond')
        self.assertTrue(passagem['passagem_id'].startswith('PSG-'))

        # Confirmação pelo recebedor (handshake)
        conf = self.gerente.confirmar_recebimento('SC-E5-01', passagem['passagem_id'], recebedor='Elrond')
        self.assertEqual(conf['status'], 'confirmada')

        # Conclusão
        conc = self.gerente.concluir_passagem(
            'SC-E5-01', passagem['passagem_id'], executor='Elrond', resultado='Persistência refatorada com sucesso.'
        )
        self.assertEqual(conc['status'], 'concluida')

    def test_simulacao_entrega_duplicada(self):
        """Garante que tentativa de duplicar entrega ativa levanta ErroEntregaDuplicada."""
        self.gerente.despachar_passagem(
            etapa_id='SC-E5-01',
            de='Gandalf',
            para='Elrond',
            tarefa_id='T-01',
            leia_so=['src/modulo_a.py'],
            faca=['Primeira ordem']
        )

        # Tentativa de despachar outra passagem diferente para o mesmo executor na mesma tarefa antes de concluir
        with self.assertRaises(ErroEntregaDuplicada):
            self.gerente.despachar_passagem(
                etapa_id='SC-E5-01',
                de='Gandalf',
                para='Elrond',
                tarefa_id='T-01',
                leia_so=['src/modulo_b.py'],
                faca=['Segunda ordem concorrente']
            )

    def test_simulacao_caminho_incorreto(self):
        """Valida que caminhos inexistentes ou que escapam do projeto são bloqueados."""
        # 1. Caminho inexistente
        with self.assertRaises(ErroCaminhoIncorreto) as ctx:
            self.gerente.despachar_passagem(
                etapa_id='SC-E5-01',
                de='Gandalf',
                para='Elrond',
                tarefa_id='T-02',
                leia_so=['src/arquivo_fantasma.py'],
                faca=['Tarefa']
            )
        self.assertIn('não existe no projeto', str(ctx.exception))

        # 2. Caminho que escapa da raiz do projeto
        with self.assertRaises(ErroCaminhoIncorreto) as ctx:
            self.gerente.despachar_passagem(
                etapa_id='SC-E5-01',
                de='Gandalf',
                para='Elrond',
                tarefa_id='T-02',
                leia_so=['../../fora_do_projeto.txt'],
                faca=['Tarefa']
            )
        self.assertIn('fora dos limites', str(ctx.exception))

        # 3. Excesso de caminhos sem justificativa de expansão (> 5)
        for i in range(6):
            (self.p / f'arq_{i}.txt').write_text('teste', encoding='utf-8')
        seis_caminhos = [f'arq_{i}.txt' for i in range(6)]

        with self.assertRaises(ErroCaminhoIncorreto) as ctx:
            self.gerente.despachar_passagem(
                etapa_id='SC-E5-01',
                de='Gandalf',
                para='Elrond',
                tarefa_id='T-02',
                leia_so=seis_caminhos,
                faca=['Tarefa'],
                justificativa_expansao=''
            )
        self.assertIn('no máximo 5 caminhos', str(ctx.exception))

        # 4. Com justificativa de expansão, permite mais de 5 caminhos
        passagem = self.gerente.despachar_passagem(
            etapa_id='SC-E5-01',
            de='Gandalf',
            para='Elrond',
            tarefa_id='T-02',
            leia_so=seis_caminhos,
            faca=['Tarefa'],
            justificativa_expansao='Análise de múltiplos módulos interdependentes'
        )
        self.assertEqual(passagem['status'], 'despachada')

    def test_simulacao_ferramenta_indisponivel_fallback(self):
        """Identifica ferramenta/comando indisponível e faz fallback gracioso para Gandalf."""
        passagem = self.gerente.despachar_passagem(
            etapa_id='SC-E5-01',
            de='Gandalf',
            para='Celebrimbor',
            tarefa_id='T-03',
            leia_so=['src/modulo_a.py'],
            faca=['Executar otimização binária'],
            ferramentas_necessarias=['cmd:binario_inexistente_xyz_123']
        )
        self.assertEqual(passagem['status'], 'fallback_necessario')
        self.assertEqual(passagem['para'], 'Gandalf')
        self.assertIn('não encontrado', passagem['motivo_fallback'])

    def test_recuperacao_apos_interrupcao(self):
        """Simula interrupção no meio da execução e recuperação de ponteiro por nova sessão."""
        passagem = self.gerente.despachar_passagem(
            etapa_id='SC-E5-01',
            de='Gandalf',
            para='Galadriel',
            tarefa_id='T-04',
            leia_so=['docs/especificacao.md'],
            faca=['Auditoria de métricas analíticas']
        )
        self.gerente.confirmar_recebimento('SC-E5-01', passagem['passagem_id'], recebedor='Galadriel')

        # Nova sessão ou reinício de processo
        novo_gerente = GerenciadorPassagem(self.reg, self.p)
        recuperada = novo_gerente.recuperar_passagem('SC-E5-01')

        self.assertIsNotNone(recuperada)
        self.assertEqual(recuperada['passagem_id'], passagem['passagem_id'])
        self.assertEqual(recuperada['status'], 'confirmada')
        self.assertEqual(recuperada['para'], 'Galadriel')

        # Conclui normalmente sem retrabalho
        novo_gerente.concluir_passagem(
            'SC-E5-01', recuperada['passagem_id'], executor='Galadriel', resultado='Auditoria concluída sem desvios.'
        )

        # Após conclusão, não resta passagem pendente
        self.assertIsNone(novo_gerente.recuperar_passagem('SC-E5-01'))

    def test_manutencao_estrita_de_paradas_humanas(self):
        """Garante que ordens contendo ações críticas (push, merge, deploy) são barradas sem decisão."""
        ordens_perigosas = [
            'Fazer git push na branch principal',
            'Executar merge do pull request para producao',
            'Publicar nova versao no marketplace',
            'Alterar credencial e token de acesso'
        ]

        for ordem in ordens_perigosas:
            with self.assertRaises(ErroParadaHumana) as ctx:
                self.gerente.despachar_passagem(
                    etapa_id='SC-E5-01',
                    de='Gandalf',
                    para='Elrond',
                    tarefa_id='T-05',
                    leia_so=['src/modulo_a.py'],
                    faca=[ordem]
                )
            self.assertIn('Exige decisão humana explícita', str(ctx.exception))

        # Com referência de decisão humana explícita, a ordem é autorizada
        passagem_autorizada = self.gerente.despachar_passagem(
            etapa_id='SC-E5-01',
            de='Gandalf',
            para='Elrond',
            tarefa_id='T-05',
            leia_so=['src/modulo_a.py'],
            faca=['Fazer git push na branch principal'],
            decisao_ref='DEC-HUMANA-ODIVAL-001'
        )
        self.assertEqual(passagem_autorizada['status'], 'despachada')


if __name__ == '__main__':
    unittest.main()
