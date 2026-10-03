"""Sondas DG-02 (B09): aceite forjável.

Achado original: o aceite de uma etapa se forjava com argumentos declarativos e com arquivos escritos à mão.

- Parte fechada pela B01 (`sc.py decidir aceitar`): verde nesta etapa (classe `SondaDG02ParteB01`).
- Resto, que fecha na B15: `@expectedFailure` até lá (classe `SondaDG02RestoB15`). Cada teste diz no docstring o que
  ainda é aceito e o que a B15 muda. Quando a B15 chegar, o teste passa a "unexpected success": tire o decorador.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cenario import AMBIENTE, SC, Base, atestado_a_mao, git, parecer_texto, rodar, sc_status  # noqa: E402

POR = ('--por', 'Odival Sintético')


class SondaDG02ParteB01(Base):
    """O `decidir aceitar` exige atestado aprovado, parecer do mesmo SHA, usuário real e cauda só de `sociedade/`."""

    def test_DG02_aceitar_sem_atestado_e_recusado(self):
        """Achado: o aceite não dependia de prova do portão. Reproduz: etapa aberta, nenhum `entregar`; recusa."""
        self.ok(self.p.abrir())
        self.recusa(self.p.decidir('aceitar', *POR), 'sem atestado')
        self.sem_decisao()

    def test_DG02_aceitar_com_atestado_reprovado_e_recusado(self):
        """Achado: atestado REPROVADO ainda abria o aceite. Reproduz: o atestado gerado é adulterado para REPROVADO."""
        self.p.fluxo_ate_o_parecer()
        arq = self.p.atestado()
        dados = json.loads(arq.read_text(encoding='utf-8'))
        dados['status'] = 'REPROVADO'
        arq.write_text(json.dumps(dados), encoding='utf-8')
        self.recusa(self.p.decidir('aceitar', *POR), 'atestado não aprovado')
        self.sem_decisao()

    def test_DG02_aceitar_com_atestado_de_outra_etapa_ou_vazio_e_recusado(self):
        """Achado: atestado de outra etapa, ou sem nenhum arquivo inspecionado, valia como prova. Reproduz os dois."""
        self.p.fluxo_ate_o_parecer()
        arq = self.p.atestado()
        original = arq.read_text(encoding='utf-8')
        for campo, valor in (('etapa_id', 'outra'), ('total_arquivos_inspecionados', 0)):
            with self.subTest(campo=campo):
                dados = json.loads(original)
                dados[campo] = valor
                arq.write_text(json.dumps(dados), encoding='utf-8')
                self.recusa(self.p.decidir('aceitar', *POR), 'atestado de outra etapa ou sem arquivo inspecionado')
                self.sem_decisao()

    def test_DG02_aceitar_com_parecer_de_outro_sha_e_recusado(self):
        """Achado: parecer de um commit valia para outro. Reproduz: atestado do commit novo, parecer do antigo."""
        p = self.p
        self.ok(p.abrir())
        novo = p.commitar_produto()
        self.ok(p.entregar())  # atestado do commit novo
        self.ok(p.revisar(p.escrever_parecer(head=p.head), head=p.head))  # parecer do commit antigo
        self.assertNotEqual(novo, p.head)
        self.recusa(p.decidir('aceitar', *POR), 'não são do mesmo SHA')
        self.sem_decisao()

    def test_DG02_aceitar_com_parecer_nao_aceitar_e_recusado(self):
        """Achado: o veredito do parecer não travava o aceite. Reproduz: parecer "não aceitar"."""
        self.p.fluxo_ate_o_parecer(veredito='não aceitar')
        self.recusa(self.p.decidir('aceitar', *POR), 'não aceitar')
        self.sem_decisao()

    def test_DG02_parecer_copiado_a_mao_sem_passar_pelo_revisar_nao_vale(self):
        """Achado: bastava um arquivo de parecer na pasta. Reproduz: o parecer é gravado à mão em
        `sociedade/pareceres/` e o registro nunca o recebeu; o `decidir` exige o registro do mesmo SHA."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        (p.soc / 'pareceres' / 'parecer-soma.md').write_text(parecer_texto(p.head, p.base), encoding='utf-8')
        self.recusa(p.decidir('aceitar', *POR), 'registro não tem o parecer deste SHA')
        self.sem_decisao()

    def test_DG02_aceitar_sem_por_e_sem_git_user_name_e_recusado(self):
        """Achado: o aceite gravava um nome padrão como decisor. Reproduz: sem `--por` e sem `git config user.name`."""
        self.p.fluxo_ate_o_parecer()
        self.recusa(self.p.decidir('aceitar'), 'Não há nome padrão')
        self.recusa(self.p.decidir('aceitar', '--por', '   '), 'Não há nome padrão')
        self.sem_decisao()

    def test_DG02_aceitar_sem_por_usa_o_git_user_name_de_verdade(self):
        """Controle da sonda anterior: com `git config user.name` e sem `--por`, o nome gravado é o do git, não um padrão."""
        self.p.fluxo_ate_o_parecer()
        git(self.p.raiz, 'config', 'user.name', 'Pessoa Configurada')
        self.ok(self.p.decidir('aceitar'))
        self.assertEqual(self.p.eventos('decisao_registrada')[-1]['quem'], 'Pessoa Configurada')

    def test_DG02_commit_de_produto_depois_do_parecer_derruba_o_aceite(self):
        """Achado (B06): código novo entrava depois da revisão sem derrubar o parecer. Reproduz: commit de produto
        depois do SHA revisado, no ramo `etapa/soma`; o `decidir aceitar` recusa e o status `aceite` fica vermelho."""
        p = self.p
        p.fluxo_ate_o_parecer()
        git(p.raiz, 'branch', '-f', 'etapa/soma', 'HEAD')
        p.commitar_produto()
        git(p.raiz, 'branch', '-f', 'etapa/soma', 'HEAD')
        self.recusa(p.decidir('aceitar', *POR), 'toca fora de sociedade/')
        self.sem_decisao()

    def test_DG02_produto_escondido_num_commit_misto_tambem_derruba(self):
        """Achado (B06): um commit que também toca `sociedade/` escondia produto. Reproduz: um commit com `soma.py`
        e uma nota em `sociedade/`; a cauda é conferida arquivo a arquivo."""
        p = self.p
        p.fluxo_ate_o_parecer()
        (p.raiz / 'soma.py').write_text('def soma(a, b):\n    return 3\n', encoding='utf-8')
        (p.soc / 'nota.md').write_text('governança\n', encoding='utf-8')
        git(p.raiz, 'add', '-A')
        git(p.raiz, 'commit', '-q', '-m', 'sociedade: nota (e um produto escondido)')
        ok, motivo = sc_status.verificar_cauda(p.raiz, p.head, p.topo())
        self.assertFalse(ok)
        self.assertIn('toca fora de sociedade/', motivo)
        git(p.raiz, 'branch', '-f', 'etapa/soma', 'HEAD')
        self.recusa(p.decidir('aceitar', *POR), 'toca fora de sociedade/')

    def test_DG02_renomear_produto_para_dentro_de_sociedade_nao_passa_pela_cauda(self):
        """Achado (B06): mover um arquivo de produto para `sociedade/` parecia commit de governança. Reproduz com
        `git mv`; a cauda lê a remoção do caminho antigo (sem detecção de renomeação)."""
        p = self.p
        p.fluxo_ate_o_parecer()
        git(p.raiz, 'mv', 'soma.py', 'sociedade/soma.py')
        git(p.raiz, 'commit', '-q', '-m', 'sociedade: mover')
        ok, motivo = sc_status.verificar_cauda(p.raiz, p.head, p.topo())
        self.assertFalse(ok)
        self.assertIn('toca fora de sociedade/', motivo)

    def test_DG02_merge_na_cauda_derruba_o_aceite(self):
        """Achado (B06): um merge de ramo lateral trazia produto sem passar pela cauda. Reproduz: merge (mesmo só de
        `sociedade/`) na cauda; falha fechada, sem tentar julgar o conteúdo do merge."""
        p = self.p
        p.fluxo_ate_o_parecer()
        git(p.raiz, 'checkout', '-q', '-b', 'lateral')
        (p.soc / 'a.md').write_text('a\n', encoding='utf-8')
        git(p.raiz, 'add', '-A')
        git(p.raiz, 'commit', '-q', '-m', 'lateral')
        git(p.raiz, 'checkout', '-q', '-')
        (p.soc / 'b.md').write_text('b\n', encoding='utf-8')
        git(p.raiz, 'add', '-A')
        git(p.raiz, 'commit', '-q', '-m', 'principal')
        git(p.raiz, 'merge', '-q', '--no-edit', 'lateral')
        ok, motivo = sc_status.verificar_cauda(p.raiz, p.head, p.topo())
        self.assertFalse(ok)
        self.assertIn('merge', motivo)

    def test_DG02_parecer_fora_da_historia_do_head_nao_vale(self):
        """Achado (B06): parecer de um commit que não é ancestral do head (outro ramo, depois de rebase) valia. Reproduz:
        o ramo `etapa/soma` é reescrito para um commit que não contém o SHA revisado."""
        p = self.p
        p.fluxo_ate_o_parecer()
        git(p.raiz, 'checkout', '-q', '-b', 'reescrito', p.base)
        p.commitar_produto('soma.py', 'def soma(a, b):\n    return a - b\n', 'feat: soma reescrita')
        git(p.raiz, 'branch', '-f', 'etapa/soma', 'HEAD')
        self.recusa(p.decidir('aceitar', *POR), 'não é ancestral do head')

    def test_DG02_commit_so_de_sociedade_depois_do_parecer_nao_derruba(self):
        """Controle da B06: a cauda de governança é legítima. Reproduz: o commit que o próprio `decidir` manda fazer
        (só `sociedade/`) mantém o `portao` e o `aceite` verdes no SHA revisado."""
        p = self.p
        p.fluxo_ate_o_parecer()
        self.ok(p.decidir('aceitar', *POR))
        topo = p.commitar_governanca()
        self.assertNotEqual(topo, p.head)
        aceite = sc_status.verificar_aceite(p.raiz, 'etapa/soma', topo)
        self.assertTrue(aceite['ok'], aceite['motivo'])
        self.assertEqual(aceite['commit'], p.head)
        portao = sc_status.verificar_portao(p.raiz, 'etapa/soma', topo)
        self.assertTrue(portao['ok'], portao['motivo'])

    def test_DG02_status_aceite_recusa_decisao_de_outra_etapa_acao_diferente_ou_sha_antigo(self):
        """Achado: o status `aceite` valia para qualquer decisão do registro. Reproduz: decisão de outra etapa, com
        `acao` diferente de "aceitar", com SHA anterior ao produto, e "aceitar" seguido de "rejeitar"; todas vermelhas."""
        p = self.p
        p.fluxo_ate_o_parecer()
        self.ok(p.decidir('aceitar', *POR))
        topo = p.commitar_governanca()

        def registro(*decisoes):
            return {'eventos': [{'tipo': 'decisao_registrada',
                                 'dados': {'etapa_id': 'soma', 'quem': 'Odival Sintético', 'acao': 'aceitar', 'commit': p.head, **d}}
                                for d in decisoes]}
        casos = {'outra etapa': registro({'etapa_id': 'outra'}), 'acao corrigir': registro({'acao': 'corrigir'}),
                 'sha antigo': registro({'commit': p.base}), 'sem sha': registro({'commit': ''}),
                 'sem decisor': registro({'quem': ' '}), 'aceitar e depois rejeitar': registro({}, {'acao': 'rejeitar'})}
        for nome, reg in casos.items():
            with self.subTest(caso=nome):
                r = sc_status.verificar_aceite(p.raiz, 'etapa/soma', topo, registro=reg)
                self.assertFalse(r['ok'], r['motivo'])
        self.assertTrue(sc_status.verificar_aceite(p.raiz, 'etapa/soma', topo, registro=registro({}))['ok'])


class SondaDG02RestoB15(Base):
    """O que ainda se forja. Cada teste afirma o comportamento desejado (B15) e falha hoje, de propósito."""
    emulacao = 'não'

    def abrir_legado(self, fatias=True):
        """Etapa aberta pelo caminho legado (`sc_rodada abrir`), como a própria m0-destravar, com a fatia fechada."""
        args = ['abrir', '--id', 'leg', '--meta', 'etapa legada', '--aceite', 'C1', '--base', self.p.head, '--limites', 'x']
        if fatias:
            args += ['--fatia', 'fatia inicial']
        self.ok(self.p.rodada(*args))

    @unittest.expectedFailure
    def test_DG02_sc_rodada_encerrar_fecha_a_etapa_sem_evento_de_decisao(self):
        """Achado (B15): `sc_rodada encerrar` fecha a etapa sem nenhum evento `decisao_registrada` (ninguém decidiu).
        Hoje: evidência declarada, parecer declarado e `encerrar` passam, e a etapa fica encerrada sem decisão.
        B15 muda: o `encerrar` do legado passa a exigir o evento `decisao`. Esperado: sem decisão, a etapa não encerra."""
        p = self.p
        self.abrir_legado()
        self.ok(p.rodada('evidencia', '--criterio', 'C1', '--comando', 'conferido a olho', '--saida', 'ok', '--versao', p.head))
        self.ok(p.rodada('parecer', '--revisor', 'Revisor Externo', '--fornecedor', 'OutraEmpresa', '--implementador',
                         'Coordenador:Anthropic', '--versao', p.head, '--veredito', 'aceitar', '--criterio-ok', 'C1'))
        self.ok(p.rodada('fatia', '1', '--fechar', '--prova', 'sem prova real'))
        p.rodada('encerrar', '--resumo', 'fechada sem decisão')
        fechada_sem_decisao = p.etapa('leg')['estado'] == 'encerrada' and not p.eventos('decisao_registrada')
        self.assertFalse(fechada_sem_decisao, 'etapa encerrada sem nenhum evento de decisão de quem decide')

    @unittest.expectedFailure
    def test_DG02_exit_code_declarado_vale_como_evidencia_sem_rodar_nada(self):
        """Achado (B15): `sc_rodada evidencia --exit-code 0` é um argumento declarativo; nenhum comando é executado.
        Hoje: o critério fica atendido por um comando que nunca rodou. B15 muda: sai o argumento declarativo do legado.
        Esperado: evidência sem execução verificada não atende o critério."""
        p = self.p
        self.abrir_legado()
        p.rodada('evidencia', '--criterio', 'C1', '--comando', 'comando-que-nunca-rodou', '--saida', 'tudo verde',
                 '--exit-code', '0', '--versao', p.head)
        self.assertFalse(p.etapa('leg')['criterios']['C1']['atendido'], 'critério atendido por exit-code declarado')

    @unittest.expectedFailure
    def test_DG02_veredito_declarado_sem_arquivo_de_parecer_e_registrado(self):
        """Achado (B15): `sc_rodada parecer --veredito aceitar` registra parecer sem arquivo e sem `lint_parecer`.
        Hoje: um revisor inventado, sem sessão nem texto, vira parecer registrado. B15 muda: `--veredito` sem arquivo sai
        do legado. Esperado: nenhum parecer entra no registro sem passar pelo lint de um arquivo."""
        p = self.p
        self.abrir_legado()
        p.rodada('parecer', '--revisor', 'Revisor Inventado', '--fornecedor', 'OutraEmpresa', '--implementador',
                 'Coordenador:Anthropic', '--versao', p.head, '--veredito', 'aceitar', '--criterio-ok', 'C1')
        self.assertEqual(p.eventos('parecer_registrado'), [], 'parecer registrado sem arquivo e sem lint')

    def test_DG02_controle_implementador_honesto_do_mesmo_fornecedor_e_recusado(self):
        """Controle da sonda seguinte (verde): declarando a verdade, o revisor da Anthropic contra o implementador
        da Anthropic é recusado pela independência, com a chave de emulação desligada."""
        p = self.p
        self.abrir_legado()
        r = p.rodada('parecer', '--revisor', 'Barbárvore', '--fornecedor', 'Anthropic', '--implementador',
                     'Coordenador:Anthropic', '--versao', p.head, '--veredito', 'aceitar', '--criterio-ok', 'C1')
        self.recusa(r, 'Independência violada')
        self.assertEqual(p.eventos('parecer_registrado'), [])

    @unittest.expectedFailure
    def test_DG02_implementador_declarado_com_fornecedor_falso_compra_independencia(self):
        """Achado (B15): `--implementador Coordenador:OtherCo` sobrepõe o fornecedor real do implementador (a linha do
        perfil diz Anthropic) e o parecer da Anthropic sai com independência "sim". Hoje: aceito. B15 muda: sai
        `--implementador` do legado. Esperado: o fornecedor do implementador vem do perfil, não do argumento."""
        p = self.p
        self.abrir_legado()
        p.rodada('parecer', '--revisor', 'Barbárvore', '--fornecedor', 'Anthropic', '--implementador',
                 'Coordenador:OutraEmpresa', '--versao', p.head, '--veredito', 'aceitar', '--criterio-ok', 'C1')
        registrados = p.eventos('parecer_registrado')
        independencia = p.etapa('leg')['independencia'] if registrados else None
        self.assertNotEqual(independencia, 'sim', 'independência "sim" comprada com fornecedor de implementador falso')

    @unittest.expectedFailure
    def test_DG02_conferencia_aceita_atestado_escrito_a_mao(self):
        """Achado (B15): a conferência `atestado_aprovado` lê status, commit e contagem de um JSON qualquer; não confere
        o `atestado_hash`. Hoje: um atestado escrito à mão, sem nenhum teste rodado, marca a entrega como "feito".
        B15 muda: a conferência verifica o hash dos atestados. Esperado: "não feito"."""
        p = self.p
        (p.soc / 'pareceres').mkdir(parents=True, exist_ok=True)
        (p.soc / 'pareceres' / 'atestado-soma.json').write_text(
            json.dumps(atestado_a_mao(p.head, perfil=p.soc / 'perfil.md')), encoding='utf-8')
        ordem = p.raiz / 'ordem-conferencia.md'
        ordem.write_text('# Ordem\n\n```entregas\nE1 | atestado_aprovado | sociedade/pareceres/atestado-soma.json | HEAD\n```\n',
                         encoding='utf-8')
        r = rodar(SC, 'conferir', '--ordem', ordem, '--raiz', p.raiz, '--json', env=AMBIENTE)
        itens = {i['id']: i for i in json.loads(r.stdout)['itens']}
        self.assertEqual(itens['E1']['estado'], 'não feito', itens['E1'])

    @unittest.expectedFailure
    def test_DG02_conferencia_aceita_atestado_gerado_e_depois_adulterado(self):
        """Achado (B15): trocar o conteúdo de um atestado verdadeiro (aqui, o número de arquivos) não é detectado.
        Hoje: o `atestado_hash` do arquivo não é recalculado pela conferência. B15 muda: a conferência o verifica.
        Esperado: "não feito"."""
        p = self.p
        self.ok(p.abrir())
        self.ok(p.entregar())
        arq = p.atestado()
        dados = json.loads(arq.read_text(encoding='utf-8'))
        dados['total_arquivos_inspecionados'] = 999
        arq.write_text(json.dumps(dados), encoding='utf-8')
        ordem = p.raiz / 'ordem-conferencia.md'
        ordem.write_text('# Ordem\n\n```entregas\nE1 | atestado_aprovado | sociedade/pareceres/atestado-soma.json | HEAD\n```\n',
                         encoding='utf-8')
        r = rodar(SC, 'conferir', '--ordem', ordem, '--raiz', p.raiz, '--json', env=AMBIENTE)
        itens = {i['id']: i for i in json.loads(r.stdout)['itens']}
        self.assertEqual(itens['E1']['estado'], 'não feito', itens['E1'])

    @unittest.expectedFailure
    def test_DG02_decidir_aceita_atestado_escrito_a_mao(self):
        """Achado (B15): o `decidir aceitar` lê o atestado como um JSON qualquer. Hoje: sem nenhum `entregar`, um atestado
        escrito à mão (APROVADO, commit certo, contagem inventada) mais um parecer registrado bastam para o aceite.
        B15 muda: o `decidir` exige o atestado oficial do SHA (hash conferido). Esperado: recusa."""
        p = self.p
        self.ok(p.abrir())
        p.atestado().parent.mkdir(parents=True, exist_ok=True)
        p.atestado().write_text(json.dumps(atestado_a_mao(p.head, perfil=p.soc / 'perfil.md')), encoding='utf-8')
        self.ok(p.revisar(p.escrever_parecer(nivel='Nível C (mesmo fornecedor)')))
        r = p.decidir('aceitar', *POR)
        self.assertNotEqual(r.returncode, 0, 'aceite concedido com atestado escrito à mão')

    @unittest.expectedFailure
    def test_DG02_status_aceite_fica_verde_com_decisao_forjada_sem_atestado_nem_parecer(self):
        """Achado (B15 e B18): o job `aceite` confia no `registro.json` do head, que qualquer commit de `sociedade/`
        pode reescrever (sem cadeia de hash). Hoje: abre-se a etapa, grava-se uma decisão "aceitar" pela API do registro,
        sem atestado nem parecer, commita-se só `sociedade/` e o `aceite` fica verde. Esperado: vermelho."""
        p = self.p
        self.ok(p.abrir())
        p.registro().registrar_decisao('soma', 'DEC-forjada', 'Odival Sintético', 'forjada', 'aceitar', autor='forja',
                                       commit=p.head)
        topo = p.commitar_governanca('sociedade(soma): decisão (forjada)')
        r = sc_status.verificar_aceite(p.raiz, 'etapa/soma', topo)
        self.assertFalse(r['ok'], 'status aceite verde para decisão sem atestado e sem parecer')


if __name__ == '__main__':
    unittest.main()
