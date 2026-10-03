"""B15 e B17b: o aceite só aceita o que um script oficial gerou e o que um humano decidiu. Dados sintéticos.

Um teste por item. Cada um falha no código anterior à F3 e passa depois. As sondas DG-02 (`tests/adversarial`)
guardam os achados de origem; aqui ficam os comportamentos novos, um a um.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adversarial._cenario import AMBIENTE, SC, Base, git, rodar  # noqa: E402
from adversarial._cenario import sc_status  # noqa: E402

POR = ('--por', 'Odival Sintético')
CAMPOS_DO_HASH = ('commit', 'base', 'papel', 'etapa_id', 'fatia_id', 'status', 'verificacoes', 'hashes_artefatos', 'portao', 'erros')


def hash_do_atestado(at):
    """Cópia deliberada da fórmula do `sc_pre_devolucao`: o teste não depende do código que vigia."""
    return hashlib.sha256(json.dumps({k: at.get(k) for k in CAMPOS_DO_HASH}, sort_keys=True).encode('utf-8')).hexdigest()


def regravar(arquivo, mudar, rehash=False):
    dados = json.loads(arquivo.read_text(encoding='utf-8'))
    mudar(dados)
    if rehash:
        dados['atestado_hash'] = hash_do_atestado(dados)
    arquivo.write_text(json.dumps(dados), encoding='utf-8')
    return dados


def conferir_atestado(p, caminho='sociedade/pareceres/atestado-soma.json'):
    ordem = p.raiz / 'ordem-conferencia.md'
    ordem.write_text(f'# Ordem\n\n```entregas\nE1 | atestado_aprovado | {caminho} | HEAD\n```\n', encoding='utf-8')
    r = rodar(SC, 'conferir', '--ordem', ordem, '--raiz', p.raiz, '--json', env=AMBIENTE)
    return {i['id']: i for i in json.loads(r.stdout)['itens']}['E1']


class DecidirExigeAtestadoOficial(Base):
    def test_B15_decidir_recusa_atestado_com_conteudo_alterado(self):
        """O atestado gerado e depois adulterado (nº de arquivos) não bate com o próprio hash."""
        self.p.fluxo_ate_o_parecer()
        regravar(self.p.atestado(), lambda d: d.update(total_arquivos_inspecionados=999))
        self.recusa(self.p.decidir('aceitar', *POR), 'adulterado')
        self.sem_decisao()

    def test_B15_decidir_recusa_atestado_sem_hash(self):
        """Atestado sem `atestado_hash` é atestado escrito à mão, mesmo com todos os outros campos."""
        self.p.fluxo_ate_o_parecer()
        regravar(self.p.atestado(), lambda d: d.pop('atestado_hash'))
        self.recusa(self.p.decidir('aceitar', *POR), 'atestado_hash')
        self.sem_decisao()

    def test_B15_decidir_grava_o_hash_do_atestado_na_decisao(self):
        """O hash do atestado fica na decisão: é o que o status `aceite` confere na cauda."""
        self.p.fluxo_ate_o_parecer()
        hash_gerado = json.loads(self.p.atestado().read_text(encoding='utf-8'))['atestado_hash']
        self.ok(self.p.decidir('aceitar', *POR))
        self.assertEqual(self.p.eventos('decisao_registrada')[-1].get('atestado_hash'), hash_gerado)

    def test_B15_d_decidir_recusa_nomes_de_papel_e_de_modelo_do_perfil(self):
        """Não só "Claude": o rótulo do papel, o do modelo e o nome do agente não decidem por ninguém."""
        self.p.fluxo_ate_o_parecer()
        for nome in ('Coordenador', 'Revisor Independente', 'Arquiteto', 'Modelo A', 'modelo b', 'Círdan', 'Gandalf'):
            with self.subTest(nome=nome):
                self.recusa(self.p.decidir('aceitar', '--por', nome), 'não de pessoa')
        self.sem_decisao()
        self.ok(self.p.decidir('aceitar', *POR))


class AceiteNaCauda(Base):
    def decidido(self):
        self.p.fluxo_ate_o_parecer()
        self.ok(self.p.decidir('aceitar', *POR))
        return self.p.commitar_governanca('sociedade(soma): decisão')

    def aceite(self, topo):
        return sc_status.verificar_aceite(self.p.raiz, 'etapa/soma', topo)

    def test_B15_b_aceite_verde_com_atestado_integro(self):
        topo = self.decidido()
        r = self.aceite(topo)
        self.assertTrue(r['ok'], r['motivo'])

    def test_B15_b_aceite_recusa_atestado_alterado_na_cauda(self):
        """Atestado mudado num commit de `sociedade/` depois da decisão: vermelho, com o hash refeito ou sem."""
        self.decidido()
        for rehash, campo in ((False, 'total_arquivos_inspecionados'), (True, 'verificacoes')):
            with self.subTest(rehash=rehash):
                regravar(self.p.atestado(), lambda d: d.update({campo: 77 if not rehash else {'forjada': True}}), rehash=rehash)
                topo = self.p.commitar_governanca(f'sociedade(soma): atestado alterado {rehash}')
                r = self.aceite(topo)
                self.assertFalse(r['ok'], r['motivo'])

    def test_B15_b_aceite_recusa_decisao_sem_atestado_no_head(self):
        self.p.fluxo_ate_o_parecer()
        self.ok(self.p.decidir('aceitar', *POR))
        self.p.atestado().unlink()
        topo = self.p.commitar_governanca('sociedade(soma): sem atestado')
        r = self.aceite(topo)
        self.assertFalse(r['ok'])
        self.assertIn('atestado', r['motivo'])


class AceiteEWorkflows(Base):
    ORDEM_COM_WORKFLOW = ('# Ordem soma\n\n1. soma · escreva só: `soma.py`, `tests/`, `.github/workflows/ci.yml` · aceite: soma\n')

    def etapa_que_mexe_no_workflow(self, ordem=None):
        p = self.p
        if ordem is not None:
            (p.soc / 'ordens' / 'soma.md').write_text(ordem, encoding='utf-8')
        self.ok(p.abrir())
        (p.raiz / '.github' / 'workflows').mkdir(parents=True)
        p.head = p.commitar_produto('.github/workflows/ci.yml', 'name: ci\n', 'ci: mexe no workflow')
        self.ok(p.entregar())
        self.ok(p.revisar(p.escrever_parecer(head=p.head), head=p.head))
        self.ok(p.decidir('aceitar', *POR))
        return p.commitar_governanca('sociedade(soma): decisão')

    def test_B15_c_aceite_vermelho_se_o_pr_altera_workflow_fora_do_escreva_so(self):
        topo = self.etapa_que_mexe_no_workflow()
        r = sc_status.verificar_aceite(self.p.raiz, 'etapa/soma', topo)
        self.assertFalse(r['ok'], r['motivo'])
        self.assertIn('.github/workflows', r['motivo'])

    def test_B15_c_aceite_verde_se_a_ordem_lista_o_workflow(self):
        topo = self.etapa_que_mexe_no_workflow(self.ORDEM_COM_WORKFLOW)
        r = sc_status.verificar_aceite(self.p.raiz, 'etapa/soma', topo)
        self.assertTrue(r['ok'], r['motivo'])

    def test_B15_c_aceite_vermelho_se_a_ordem_foi_editada_depois_da_abertura(self):
        """Listar o workflow na ordem depois de aberta a etapa não vale: o hash da ordem é o da abertura."""
        self.etapa_que_mexe_no_workflow()
        (self.p.soc / 'ordens' / 'soma.md').write_text(self.ORDEM_COM_WORKFLOW, encoding='utf-8')
        topo = self.p.commitar_governanca('sociedade(soma): ordem editada')
        r = sc_status.verificar_aceite(self.p.raiz, 'etapa/soma', topo)
        self.assertFalse(r['ok'], r['motivo'])
        self.assertIn('ordem', r['motivo'])


class ConferenciaDoAtestado(Base):
    def a_mao(self, **portao):
        """Atestado coerente e com o hash certo, escrito à mão: só a forma (ou a falta de teste rodado) o denuncia."""
        p = self.p
        perfil = hashlib.sha256((p.soc / 'perfil.md').read_bytes()).hexdigest()
        at = {'tipo': 'atestado_pre_devolucao', 'versao': '1.3.0', 'papel': 'Coordenador', 'etapa_id': 'soma', 'fatia_id': 'N/A',
              'status': 'APROVADO', 'commit': p.head, 'base': p.base, 'verificacoes': {}, 'erros': [],
              'total_arquivos_inspecionados': 1, 'hashes_artefatos': {'soma.py': 'a' * 64}, 'arquivos_inspecionados': ['soma.py']}
        at['portao'] = {'modo': 'por_area', 'commit': p.head, 'perfil_sha256': perfil, 'areas_tocadas': ['projeto'],
                        'cobertura_completa': True, 'areas': [{'area': 'projeto', 'ok': True}], **portao}
        at['atestado_hash'] = hash_do_atestado(at)
        (p.soc / 'pareceres').mkdir(parents=True, exist_ok=True)
        p.atestado().write_text(json.dumps(at), encoding='utf-8')

    def test_B15_conferencia_recusa_atestado_sem_hash_ou_adulterado(self):
        self.ok(self.p.abrir())
        self.ok(self.p.entregar())
        self.assertEqual(conferir_atestado(self.p)['estado'], 'feito')  # controle: o atestado do `entregar`
        regravar(self.p.atestado(), lambda d: d.pop('atestado_hash'))
        item = conferir_atestado(self.p)
        self.assertEqual(item['estado'], 'não feito', item)
        self.assertIn('atestado_hash', item['detalhe'])

    def test_B17b_conferencia_recusa_atestado_avulso(self):
        """Sem `portao` (o `sc_pre_devolucao --comando-teste`), mesmo com hash certo."""
        self.a_mao()
        regravar(self.p.atestado(), lambda d: d.pop('portao'), rehash=True)
        item = conferir_atestado(self.p)
        self.assertEqual(item['estado'], 'não feito', item)
        self.assertIn('portão por área', item['detalhe'])

    def test_B17b_conferencia_recusa_area_parcial(self):
        """`--area` sozinho: áreas tocadas além das rodadas, com o hash certo."""
        self.a_mao(areas_tocadas=['projeto', 'docs'], cobertura_completa=False)
        item = conferir_atestado(self.p)
        self.assertEqual(item['estado'], 'não feito', item)
        self.assertIn('não cobre todas as áreas', item['detalhe'])

    def test_B17b_conferencia_recusa_atestado_do_perfil_que_mudou(self):
        self.a_mao(perfil_sha256='b' * 64)
        item = conferir_atestado(self.p)
        self.assertEqual(item['estado'], 'não feito', item)
        self.assertIn('perfil', item['detalhe'])


class IndependenciaDeclarada(Base):
    def test_B15_a_implementador_declarado_nao_sobrepoe_o_fornecedor_do_perfil(self):
        """`--implementador Gandalf:OutraEmpresa`: o perfil diz Anthropic; a declaração falsa é recusada."""
        self.ok(self.p.abrir())
        self.recusa(self.p.revisar(self.p.escrever_parecer(), self.p.head, '--implementador', 'Gandalf:OutraEmpresa'), 'perfil')
        self.assertEqual(self.p.eventos('parecer_registrado'), [])

    def test_B15_a_implementador_declarado_igual_ao_perfil_continua_valendo(self):
        self.ok(self.p.abrir())
        self.ok(self.p.revisar(self.p.escrever_parecer(), self.p.head, '--implementador', 'Gandalf:Anthropic'))

    def test_B15_a_fornecedor_declarado_pelo_revisor_e_conferido_com_o_perfil(self):
        """O perfil põe Barbárvore na Anthropic; um parecer que se declara de outro fornecedor não compra independência."""
        self.ok(self.p.abrir())
        arq = self.p.escrever_parecer(nivel='Nível A (fornecedor diferente)', fornecedor='OutraEmpresa')
        self.recusa(self.p.revisar(arq), 'perfil')
        self.assertEqual(self.p.eventos('parecer_registrado'), [])


class RodadaLegadoSemDeclaracao(Base):
    emulacao = 'não'

    def abrir_legado(self):
        self.ok(self.p.rodada('abrir', '--id', 'leg', '--meta', 'etapa legada', '--aceite', 'C1', '--base', self.p.head,
                              '--limites', 'x', '--fatia', 'fatia inicial'))

    def test_B15_evidencia_nao_aceita_exit_code_declarado(self):
        self.abrir_legado()
        r = self.p.rodada('evidencia', '--criterio', 'C1', '--comando', 'true', '--exit-code', '0', '--versao', self.p.head)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.p.etapa('leg')['criterios']['C1']['atendido'])

    def test_B15_evidencia_registra_o_codigo_de_saida_medido(self):
        self.abrir_legado()
        falha = f'{sys.executable} -c "import sys; print(\'falhou\'); sys.exit(3)"'
        self.ok(self.p.rodada('evidencia', '--criterio', 'C1', '--comando', falha, '--versao', self.p.head))
        self.assertFalse(self.p.etapa('leg')['criterios']['C1']['atendido'], 'comando que falhou não atende o critério')
        self.assertEqual(self.p.eventos('evidencia_registrada')[-1]['exit_code'], 3)
        passa = f'{sys.executable} -c "print(\'12 passed\')"'
        self.ok(self.p.rodada('evidencia', '--criterio', 'C1', '--comando', passa, '--versao', self.p.head))
        self.assertTrue(self.p.etapa('leg')['criterios']['C1']['atendido'])
        self.assertEqual(self.p.eventos('evidencia_registrada')[-1]['exit_code'], 0)

    def test_B15_parecer_nao_aceita_veredito_nem_implementador_declarados(self):
        self.abrir_legado()
        for extra in (('--veredito', 'aceitar'), ('--implementador', 'Gandalf:Anthropic')):
            with self.subTest(extra=extra):
                r = self.p.rodada('parecer', '--arquivo', self.p.escrever_parecer(etapa='leg'), '--versao', self.p.head, *extra)
                self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.p.eventos('parecer_registrado'), [])

    def test_B15_parecer_vem_do_arquivo_com_lint(self):
        self.abrir_legado()
        ruim = self.p.tmp / 'ruim.md'
        ruim.write_text('# parecer sem forma\n', encoding='utf-8')
        self.recusa(self.p.rodada('parecer', '--arquivo', ruim), 'lint')
        self.assertEqual(self.p.eventos('parecer_registrado'), [])
        self.ok(self.p.rodada('parecer', '--arquivo', self.p.escrever_parecer(etapa='leg', nivel='Nível A (fornecedor diferente)',
                                                                              revisor='Revisor Externo (outra casa)', fornecedor='OutraEmpresa')))
        ev = self.p.eventos('parecer_registrado')[-1]
        self.assertEqual((ev['veredito'], ev['fornecedor_revisor']), ('aceitar', 'OutraEmpresa'))

    def test_B15_encerrar_exige_o_evento_de_decisao(self):
        p = self.p
        self.abrir_legado()
        passa = f'{sys.executable} -c "print(\'12 passed\')"'
        self.ok(p.rodada('evidencia', '--criterio', 'C1', '--comando', passa, '--versao', p.head))
        self.ok(p.rodada('parecer', '--arquivo', p.escrever_parecer(etapa='leg', nivel='Nível A (fornecedor diferente)',
                                                                     revisor='Revisor Externo (outra casa)', fornecedor='OutraEmpresa')))
        self.ok(p.rodada('fatia', '1', '--fechar', '--prova', 'passou'))
        self.recusa(p.rodada('encerrar', '--resumo', 'sem decisão'), 'decisão')
        self.assertNotEqual(p.etapa('leg')['estado'], 'encerrada')
        p.registro().registrar_decisao('leg', 'DEC-leg-1', 'Odival Sintético', 'aceite de teste', 'aceitar', autor='Odival Sintético')
        self.ok(p.rodada('encerrar', '--resumo', 'com decisão'))
        self.assertEqual(p.etapa('leg')['estado'], 'encerrada')

    def test_B15_encerrar_forcar_tambem_exige_a_decisao(self):
        """`--forcar` com motivo e decisão-ref válidos dispensa fatia aberta, mas não o evento de decisão."""
        p = self.p
        self.abrir_legado()  # a fatia segue aberta
        r = p.rodada('encerrar', '--forcar', '--regra', 'fatias_pendentes', '--motivo', 'motivo substantivo longo',
                     '--decisao-ref', 'DEC-ODIVAL-001')
        self.recusa(r, 'decisão')
        self.assertEqual(p.eventos('excecao_registrada'), [], 'a recusa não pode deixar exceção registrada')
        self.assertNotEqual(p.etapa('leg')['estado'], 'encerrada')


class RevisarLevaOsPapeis(Base):
    def test_B17b_revisar_usa_o_worktree_da_etapa_e_leva_ordem_atestado_e_perfil(self):
        p = self.p
        casa = Path(self._tmp.name) / 'casa'
        wt = casa / '.sociedade' / 'trabalho' / 'repo' / 'soma'
        wt.parent.mkdir(parents=True)
        git(p.raiz, 'worktree', 'add', '-q', '-b', 'etapa/soma', str(wt), p.head)
        (wt / 'sociedade' / 'pareceres').mkdir(parents=True, exist_ok=True)
        (wt / 'sociedade' / 'pareceres' / 'atestado-soma.json').write_text('{"so_no_worktree": true}\n', encoding='utf-8')
        destino = Path(self._tmp.name) / 'revisao-soma'
        env = {**AMBIENTE, 'HOME': str(casa)}
        r = rodar(SC, 'revisar', '--etapa', 'soma', '--base', p.base, '--head', p.head, '--destino', destino, cwd=p.raiz, env=env)
        self.ok(r)
        for rel in ('ordens/soma.md', 'pareceres/atestado-soma.json', 'perfil.md'):
            self.assertTrue((destino / 'sociedade' / rel).is_file(), f'a cópia não leva sociedade/{rel}')
        self.assertIn('so_no_worktree', (destino / 'sociedade' / 'pareceres' / 'atestado-soma.json').read_text(encoding='utf-8'))
        sujo = subprocess.run(['git', '-C', str(destino), 'status', '--porcelain'], capture_output=True, text=True).stdout
        self.assertEqual(sujo.strip(), '', 'o que a cópia leva não pode sujar o repositório do revisor')


if __name__ == '__main__':
    unittest.main()
