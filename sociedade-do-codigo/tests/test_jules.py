import json
import re
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from util import SKILLS, carregar, rodar

JULES = SKILLS / 'sc-execucao'
COTA = JULES / 'scripts' / 'jules_cota.py'
LOTE = JULES / 'scripts' / 'verificar_lote.py'
TAREFAS = JULES / 'assets' / 'tarefa-jules.md'


def exemplo_do_modelo():
    """Extrai o lote de exemplo (comentário HTML do modelo) para usar como caso válido."""
    texto = TAREFAS.read_text(encoding='utf-8')
    blocos = re.findall(r'<!--(.*?)-->', texto, re.S)
    return blocos[1].replace('Exemplo de lote (dois blocos com arquivos disjuntos):', '')


class TesteCota(unittest.TestCase):
    def setUp(self):
        self.mod = carregar(COTA, 'jules_cota')
        self.agora = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)

    def datas(self, *isos):
        return [self.mod.parse_data(i) for i in isos]

    def test_janela_movel_de_24_horas(self):
        d = self.datas('2026-09-19T11:00:00Z', '2026-09-18T12:00:00Z', '2026-09-18T11:59:59Z')
        r = self.mod.calcular(d, self.agora, limite=15)
        self.assertEqual(r['usadas_24h'], 1)  # a de 12:00 do dia anterior está no limite e sai; a das 11:59:59 também
        self.assertEqual(r['restam'], 14)

    def test_cota_esgotada_informa_proxima_vaga(self):
        d = self.datas('2026-09-19T08:00:00Z', '2026-09-19T09:00:00Z', '2026-09-19T10:00:00Z')
        r = self.mod.calcular(d, self.agora, limite=3)
        self.assertEqual(r['restam'], 0)
        self.assertEqual(r['pode_despachar'], 0)
        self.assertEqual(r['proxima_liberacao'], datetime(2026, 9, 20, 8, 0, tzinfo=timezone.utc))

    def test_simultaneas_e_reserva_limitam(self):
        r = self.mod.calcular(self.datas('2026-09-19T08:00:00Z'), self.agora, limite=10, simultaneas=3, ativas=2, reserva=2)
        self.assertEqual(r['pode_despachar'], 1)

    def test_fracao_de_segundos_longa_e_deslocamento(self):
        self.assertEqual(self.mod.parse_data('2026-09-19T08:30:00.123456789Z').minute, 30)
        self.assertEqual(self.mod.parse_data('2026-09-19T05:00:00-03:00').astimezone(timezone.utc).hour, 8)

    def test_cli_exige_plano_ou_limite(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        arq = Path(d.name) / 'd.json'
        arq.write_text('[]', encoding='utf-8')
        self.assertEqual(rodar(COTA, '--arquivo', arq).returncode, 2)
        r = rodar(COTA, '--arquivo', arq, '--plano', 'pro', '--json')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['restam'], 100)

    def test_api_sem_chave_nao_vaza_nada(self):
        import os
        env = {k: v for k, v in os.environ.items() if k != 'JULES_API_KEY'}
        r = rodar(COTA, '--api', '--plano', 'pro', env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn('JULES_API_KEY', r.stderr)


class TesteLote(unittest.TestCase):
    def arquivo(self, texto):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        a = Path(d.name) / 'lote.md'
        a.write_text(texto, encoding='utf-8')
        return a

    def test_exemplo_do_modelo_e_valido(self):
        r = rodar(LOTE, self.arquivo(exemplo_do_modelo()))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('2 tarefa(s)', r.stdout)

    def test_modelo_cru_reprovado_por_marcadores(self):
        r = rodar(LOTE, TAREFAS)
        self.assertEqual(r.returncode, 1)
        self.assertIn('marcador', r.stdout)

    def test_sobreposicao_de_arquivos(self):
        ex = exemplo_do_modelo().replace('src/components/MenuMovel.tsx, src/components/MenuMovel.test.tsx', 'src/utils/formatarData.test.ts')
        r = rodar(LOTE, self.arquivo(ex))
        self.assertEqual(r.returncode, 1)
        self.assertIn('sobreposição', r.stdout)

    def test_r2_exige_permissao_explicita(self):
        ex = exemplo_do_modelo().replace('Classe: R1', 'Classe: R2')
        self.assertEqual(rodar(LOTE, self.arquivo(ex)).returncode, 1)
        self.assertEqual(rodar(LOTE, self.arquivo(ex), '--permitir-r2').returncode, 0)

    def test_caminho_local_e_segredo(self):
        ex = exemplo_do_modelo().replace('src/utils/formatarData.test.ts', '/home/usuario/x.test.ts', 1)
        r = rodar(LOTE, self.arquivo(ex))
        self.assertEqual(r.returncode, 1)
        self.assertIn('caminho', r.stdout)
        ex2 = exemplo_do_modelo().replace('Fora de escopo: alterar a função', 'Fora de escopo: token: abcdefgh12345678', 1)
        self.assertIn('segredo', rodar(LOTE, self.arquivo(ex2)).stdout)

    def test_contrapressao(self):
        r = rodar(LOTE, self.arquivo(exemplo_do_modelo()), '--prs-abertos', '8', '--max-prs-abertos', '8')
        self.assertEqual(r.returncode, 1)
        self.assertIn('contrapressão', r.stdout)
        r = rodar(LOTE, self.arquivo(exemplo_do_modelo()), '--prs-abertos', '7', '--max-prs-abertos', '8', '--restam', '10')
        self.assertEqual(r.returncode, 0)
        self.assertIn('pode despachar 1 de 2', r.stdout)
        # teto padrão de 3 tarefas abertas (Q93, Q129)
        r = rodar(LOTE, self.arquivo(exemplo_do_modelo()), '--prs-abertos', '3')
        self.assertEqual(r.returncode, 1)
        self.assertIn('contrapressão', r.stdout)

    def test_pasta_permitida_com_excecao_proibida_e_legitima(self):
        ex = exemplo_do_modelo().replace('Arquivos permitidos: src/utils/formatarData.test.ts', 'Arquivos permitidos: src/utils', 1)
        r = rodar(LOTE, self.arquivo(ex))
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == '__main__':
    unittest.main()
