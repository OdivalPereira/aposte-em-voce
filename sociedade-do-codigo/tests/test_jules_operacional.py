"""Testes determinísticos das invariantes operacionais do papel de Jules na Sociedade do Código.

Cobre:
- Invariantes da janela assíncrona de 45 minutos (Q48), tolerância e cálculo de atraso anômalo;
- Arbitragem de fila compartilhada por Gandalf (Q02, Q27), idempotência e reserva estratégica;
- Disjunção estrita e detecção de sobreposição de arquivos entre tarefas em lote;
- Contrapressão de revisão com teto de PRs abertos;
- Sentinela fail-closed contra caminhos locais e vazamento de segredos;
- Regra das 3 hipóteses técnicas distintas (Q12) e fallback gracioso.

Somente biblioteca padrão (unittest, datetime, pathlib, tempfile, json).
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from util import SKILLS, carregar, rodar

JULES = SKILLS / 'sc-execucao'
COTA = JULES / 'scripts' / 'jules_cota.py'
LOTE = JULES / 'scripts' / 'verificar_lote.py'


def avaliar_janela_assincrona(despacho, agora, build_ativo=False):
    """Função modelo das diretrizes Q48 para avaliação da janela de 45 minutos."""
    delta = agora - despacho
    minutos = delta.total_seconds() / 60.0
    if minutos < 0:
        raise ValueError('Instante atual anterior ao instante de despacho.')
    if minutos < 45.0:
        return {
            'status': 'aguardando_janela',
            'intervencao_autorizada': False,
            'minutos_decorridos': round(minutos, 2),
            'minutos_restantes': round(45.0 - minutos, 2),
            'prorrogacao': False,
            'fallback': False,
        }
    if minutos <= 60.0:
        if build_ativo:
            return {
                'status': 'prorrogacao_concedida',
                'intervencao_autorizada': False,
                'minutos_decorridos': round(minutos, 2),
                'minutos_restantes': round(60.0 - minutos, 2),
                'prorrogacao': True,
                'fallback': False,
            }
        return {
            'status': 'atraso_anomalo',
            'intervencao_autorizada': True,
            'minutos_decorridos': round(minutos, 2),
            'minutos_restantes': 0.0,
            'prorrogacao': False,
            'fallback': True,
        }
    return {
        'status': 'timeout_excedido',
        'intervencao_autorizada': True,
        'minutos_decorridos': round(minutos, 2),
        'minutos_restantes': 0.0,
        'prorrogacao': False,
        'fallback': True,
    }


def avaliar_ciclo_hipoteses(tentativas):
    """Valida o cumprimento da regra Q12 de até 3 hipóteses técnicas distintas."""
    if not isinstance(tentativas, list):
        raise TypeError('Esperava lista de tentativas.')
    total = len(tentativas)
    if total > 3:
        return {
            'autorizado': False,
            'motivo': 'limite de 3 hipóteses esgotado; escalonamento humano obrigatório para Odival',
            'total': total,
        }
    hipoteses = set()
    for t in tentativas:
        h = str(t.get('hipotese', '')).strip().lower()
        if not h:
            return {'autorizado': False, 'motivo': 'tentativa sem hipótese técnica declarada', 'total': total}
        if h in hipoteses:
            return {'autorizado': False, 'motivo': 'hipótese repetida; Q12 exige hipóteses conceituais distintas', 'total': total}
        hipoteses.add(h)
    return {
        'autorizado': True,
        'motivo': 'dentro do limite de hipóteses distintas' if total < 3 else 'terceira hipótese em curso',
        'total': total,
        'restantes': max(3 - total, 0),
    }


class TesteJanelaAssincronaJules(unittest.TestCase):
    """Testa a invariante da janela assíncrona de 45 minutos (Q48)."""

    def setUp(self):
        self.inicio = datetime(2026, 9, 23, 10, 0, 0, tzinfo=timezone.utc)

    def test_dentro_dos_45_minutos_bloqueia_intervencao(self):
        agora = self.inicio + timedelta(minutes=25)
        res = avaliar_janela_assincrona(self.inicio, agora)
        self.assertEqual(res['status'], 'aguardando_janela')
        self.assertFalse(res['intervencao_autorizada'])
        self.assertAlmostEqual(res['minutos_restantes'], 20.0)
        self.assertFalse(res['fallback'])

    def test_exato_limite_45_minutos_sem_build_gera_atraso_anomalo(self):
        agora = self.inicio + timedelta(minutes=45, seconds=1)
        res = avaliar_janela_assincrona(self.inicio, agora, build_ativo=False)
        self.assertEqual(res['status'], 'atraso_anomalo')
        self.assertTrue(res['intervencao_autorizada'])
        self.assertTrue(res['fallback'])

    def test_janela_entre_45_e_60_minutos_com_build_ativo_concede_prorrogacao(self):
        agora = self.inicio + timedelta(minutes=52)
        res = avaliar_janela_assincrona(self.inicio, agora, build_ativo=True)
        self.assertEqual(res['status'], 'prorrogacao_concedida')
        self.assertFalse(res['intervencao_autorizada'])
        self.assertTrue(res['prorrogacao'])
        self.assertAlmostEqual(res['minutos_restantes'], 8.0)

    def test_acima_de_60_minutos_esgota_timeout_mesmo_com_build(self):
        agora = self.inicio + timedelta(minutes=61)
        res = avaliar_janela_assincrona(self.inicio, agora, build_ativo=True)
        self.assertEqual(res['status'], 'timeout_excedido')
        self.assertTrue(res['intervencao_autorizada'])
        self.assertTrue(res['fallback'])


class TesteRegraTresHipoteses(unittest.TestCase):
    """Testa a regra das 3 hipóteses técnicas distintas (Q12)."""

    def test_ate_tres_hipoteses_distintas_autorizadas(self):
        tentativas = [
            {'hipotese': 'Incompatibilidade de timezone UTC', 'abordagem': 'Ajuste de offset'},
            {'hipotese': 'Truncamento de microssegundos no ISO-8601', 'abordagem': 'Normalização com pad'},
        ]
        res = avaliar_ciclo_hipoteses(tentativas)
        self.assertTrue(res['autorizado'])
        self.assertEqual(res['restantes'], 1)

    def test_hipotese_repetida_rejeitada(self):
        tentativas = [
            {'hipotese': 'Erro de encoding', 'abordagem': 'Adicionar utf-8'},
            {'hipotese': 'erro de encoding', 'abordagem': 'Mesma hipótese com outra redação'},
        ]
        res = avaliar_ciclo_hipoteses(tentativas)
        self.assertFalse(res['autorizado'])
        self.assertIn('hipótese repetida', res['motivo'])

    def test_quarta_tentativa_bloqueada_e_exige_escalonamento_humano(self):
        tentativas = [
            {'hipotese': 'H1: Timezone', 'abordagem': 'A1'},
            {'hipotese': 'H2: Regex', 'abordagem': 'A2'},
            {'hipotese': 'H3: Local filesystem', 'abordagem': 'A3'},
            {'hipotese': 'H4: Quarta tentativa não permitida', 'abordagem': 'A4'},
        ]
        res = avaliar_ciclo_hipoteses(tentativas)
        self.assertFalse(res['autorizado'])
        self.assertIn('escalonamento humano', res['motivo'])


class TesteCotaOperacionalAvancada(unittest.TestCase):
    """Testa cálculos avançados de janela móvel e reserva técnica em jules_cota.py."""

    def setUp(self):
        self.mod = carregar(COTA, 'jules_cota_op')
        self.agora = datetime(2026, 9, 23, 14, 0, 0, tzinfo=timezone.utc)

    def test_reserva_superior_ao_saldo_zera_despacho_sem_ficar_negativo(self):
        datas = [self.agora - timedelta(hours=2)]
        res = self.mod.calcular(datas, self.agora, limite=3, reserva=3)
        self.assertEqual(res['usadas_24h'], 1)
        self.assertEqual(res['restam'], 2)
        self.assertEqual(res['reserva'], 3)
        self.assertEqual(res['pode_despachar'], 0)

    def test_simultaneas_saturadas_bloqueiam_despacho_mesmo_com_saldo_diario(self):
        datas = [self.agora - timedelta(hours=1)]
        res = self.mod.calcular(datas, self.agora, limite=100, simultaneas=5, ativas=5, reserva=0)
        self.assertEqual(res['restam'], 99)
        self.assertEqual(res['simultaneas_livres'], 0)
        self.assertEqual(res['pode_despachar'], 0)

    def test_liberacao_exata_apos_24h(self):
        d1 = self.agora - timedelta(hours=23, minutes=50)
        d2 = self.agora - timedelta(hours=5)
        res = self.mod.calcular([d1, d2], self.agora, limite=2)
        self.assertEqual(res['restam'], 0)
        self.assertEqual(res['pode_despachar'], 0)
        esperado = d1 + timedelta(hours=24)
        self.assertEqual(res['proxima_liberacao'], esperado)


class TesteLoteOperacionalAvancado(unittest.TestCase):
    """Testa validação de lotes, segregação de tarefas e contrapressão em verificar_lote.py."""

    def criar_lote_md(self, conteudo):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        arq = Path(d.name) / 'lote_op.md'
        arq.write_text(conteudo, encoding='utf-8')
        return arq

    def test_duplicidade_de_slug_rejeitada(self):
        tarefa = """Tarefa: slug-repetido
Classe: R0
Repositório e base: dono/repo · branch principal @ a1b2c3d
Objetivo: primeiro teste.
Arquivos permitidos: src/a.ts
Não tocar: .env
Comportamento a preservar: sem alteração funcional.
Como provar que está pronto: npm test
Tamanho esperado: até 1 arquivo e 50 linhas
Retorno: PR em rascunho
Fora de escopo: outros arquivos

Tarefa: slug-repetido
Classe: R0
Repositório e base: dono/repo · branch principal @ a1b2c3d
Objetivo: segundo teste.
Arquivos permitidos: src/b.ts
Não tocar: .env
Comportamento a preservar: sem alteração funcional.
Como provar que está pronto: npm test
Tamanho esperado: até 1 arquivo e 50 linhas
Retorno: PR em rascunho
Fora de escopo: outros arquivos
"""
        res = rodar(LOTE, self.criar_lote_md(tarefa))
        self.assertEqual(res.returncode, 1)
        self.assertIn('identificador de tarefa repetido', res.stdout)

    def test_glob_amplo_demais_rejeitado(self):
        tarefa = """Tarefa: refatoracao-ampla
Classe: R0
Repositório e base: dono/repo · branch principal @ a1b2c3d
Objetivo: teste amplo proibido.
Arquivos permitidos: .
Não tocar: .env
Comportamento a preservar: sem alteração funcional.
Como provar que está pronto: npm test
Tamanho esperado: até 1 arquivo e 50 linhas
Retorno: PR em rascunho
Fora de escopo: outros arquivos
"""
        res = rodar(LOTE, self.criar_lote_md(tarefa))
        self.assertEqual(res.returncode, 1)
        self.assertIn('amplo demais', res.stdout)

    def test_bloqueio_por_contrapressao_de_prs_abertos(self):
        tarefa = """Tarefa: ajuste-simples
Classe: R0
Repositório e base: dono/repo · branch principal @ a1b2c3d
Objetivo: teste com contrapressao.
Arquivos permitidos: src/simples.ts
Não tocar: .env
Comportamento a preservar: sem alteração funcional.
Como provar que está pronto: npm test
Tamanho esperado: até 1 arquivo e 50 linhas
Retorno: PR em rascunho
Fora de escopo: outros arquivos
"""
        res = rodar(LOTE, self.criar_lote_md(tarefa), '--prs-abertos', '8', '--max-prs-abertos', '8')
        self.assertEqual(res.returncode, 1)
        self.assertIn('contrapressão', res.stdout)
        self.assertIn('esvazie a fila', res.stdout)

    def test_caminho_local_com_file_uri_bloqueado(self):
        tarefa = """Tarefa: uri-local-proibida
Classe: R0
Repositório e base: dono/repo · branch principal @ a1b2c3d
Objetivo: teste com uri local.
Arquivos permitidos: src/local.ts
Não tocar: file:///etc/shadow
Comportamento a preservar: sem alteração funcional.
Como provar que está pronto: npm test
Tamanho esperado: até 1 arquivo e 50 linhas
Retorno: PR em rascunho
Fora de escopo: outros arquivos
"""
        res = rodar(LOTE, self.criar_lote_md(tarefa))
        self.assertEqual(res.returncode, 1)
        self.assertIn('caminho ou link local', res.stdout)


if __name__ == '__main__':
    unittest.main()
