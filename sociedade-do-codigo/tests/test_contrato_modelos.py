"""Contrato dos modelos (B04): todo `*-modelo.md` do pacote, preenchido com dados sintéticos, passa no seu analisador.

O teste preenche cada modelo (troca todo marcador `<...>` por um valor sintético), roda o analisador real do
modelo e confere o resultado. Um modelo novo sem entrada em MODELOS reprova; um marcador novo sem valor
sintético reprova e lista o que sobrou. O modelo cru continua reprovado onde o analisador o exige preenchido.

Analisadores:
  parecer-modelo.md   -> sc-revisao/scripts/lint_parecer.py
  perfil-modelo.md    -> sociedade-do-codigo/scripts/validar_perfil.py (+ leitor PerfilProjeto)
  rodada-modelo.md    -> sociedade-do-codigo/scripts/sc_rodada.py lint
  ordem-modelo.md     -> sociedade-do-codigo/scripts/sc_conferir.py (bloco ```entregas)
  avaliacao-modelo.md -> nenhum script o lê (documento de orientação); ver SEM_ANALISADOR.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # permite `unittest tests.test_contrato_modelos`
from util import NUCLEO, RAIZ, SKILLS, rodar  # noqa: E402

sys.path.insert(0, str(NUCLEO / 'scripts'))

LINT_PARECER = SKILLS / 'sc-revisao' / 'scripts' / 'lint_parecer.py'
VALIDAR_PERFIL = NUCLEO / 'scripts' / 'validar_perfil.py'
SC_RODADA = NUCLEO / 'scripts' / 'sc_rodada.py'
SC_CONFERIR = NUCLEO / 'scripts' / 'sc_conferir.py'
MARCADOR = re.compile(r'<[^<>\n]+>')

# Modelos que nenhum script lê. Entrar aqui é decisão explícita: o teste exige o motivo.
SEM_ANALISADOR = {
    'avaliacao-modelo.md': 'documento de orientação: o formulário é texto livre e nenhum script o lê',
}
ANALISADOS = {'parecer-modelo.md', 'perfil-modelo.md', 'rodada-modelo.md', 'ordem-modelo.md'}


def modelos_do_pacote():
    return sorted(p for p in RAIZ.rglob('*-modelo.md') if '.git' not in p.parts)


def modelo(nome):
    achados = [p for p in modelos_do_pacote() if p.name == nome]
    assert len(achados) == 1, f'{nome}: esperado 1 arquivo no pacote, achei {len(achados)}'
    return achados[0].read_text(encoding='utf-8')


def preencher(texto, valores):
    """Troca cada marcador por um valor sintético (chaves mais longas primeiro) e exige que nada sobre."""
    for chave in sorted(valores, key=len, reverse=True):
        texto = texto.replace(chave, valores[chave])
    sobras = sorted(set(MARCADOR.findall(texto)))
    if sobras:
        raise AssertionError(f'marcadores sem valor sintético no contrato: {sobras}')
    return texto


def sem_instrucoes(texto):
    """Apaga as linhas de instrução do modelo (inteiras em itálico), como o modelo pede ao preencher."""
    return '\n'.join(l for l in texto.split('\n') if not re.fullmatch(r'\*[^*\s][^*\n]*\*', l.strip()))


# ---------- valores sintéticos ----------

BASE = 'a1b2c3d'
HEAD = 'e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3'

PARECER = {
    '<ID>': 'etapa-sintetica',
    '<commit congelado ou PR>': f'commit {HEAD[:7]}',
    '<SHA do commit revisado, 7 a 40 hexadecimais, igual ao head de base..head>': HEAD,
    '<sha7>..<sha7>': f'{BASE}..{HEAD[:7]}',
    '<papel e ferramenta> · fornecedor: <fornecedor> · sessão: <id>':
        'Revisor sintético (ferramenta X) · fornecedor: Alfa · sessão: sess_sintetica_01',
    '<modelo configurado> · esforço: <esforço configurado|não exposto>': 'modelo-sintetico · esforço: não exposto',
    '<Nível A (fornecedor diferente), Nível B (sessão distinta) ou Nível C (mesmo fornecedor)>':
        'Nível A (fornecedor diferente)',
    '<aceitar, aceitar com ressalvas ou não aceitar>': 'aceitar com ressalvas',
    '<dd/mm/aaaa hh:mm>': '03/10/2026 10:00',
    'Implementação feita pelo fornecedor <fornecedor>; minha revisão é de fornecedor <diferente|igual: revisão interna>.':
        'Implementação feita pelo fornecedor Beta; minha revisão é de fornecedor diferente.',
    '<defeito ou necessidade, com referência do plano>': 'datas inválidas quebram a tela (plano 3.1)',
    '<comandos, opções, funções públicas>': '`formatarData(texto)`',
    '<quais e quem muda>': 'nenhum estado persistente',
    '| <critério> | <comando executado e resultado, ou arquivo e trecho lido> | <executada, lida ou não verificada> |':
        '| Cobre datas inválidas | `npm test -- formatarData` passou | executada |\n'
        '| Funciona no celular | não exercitado | não verificada |',
    '| <critério> | <sonda, "lida" ou "n/a (motivo)"> | | | | | | | |':
        '| Cobre datas inválidas | S1 | S2 | lida | n/a (sem opção de escape) | S3 | n/a (sem concorrência) | lida | S4 |',
    '- [<severidade>] <lente> · <descrição> (<arquivo:linha>)':
        '- [relevante] L5 · mensagem de erro em inglês (src/formatarData.ts:41)',
    '- <item>': '- Comportamento no celular (sem navegador nesta sessão).',
}

PERFIL_UNIFORME = {
    '<Projeto>': 'Projeto Sintético', '<pessoa>': 'Pessoa Sintética',
    '<nome do papel e ferramenta>': 'Arquiteto sintético (ferramenta X)',
    '<plataforma>': 'Plataforma X', '<fornecedor>': 'Fornecedor Alfa', '<modelo>': 'modelo-sintetico',
    '<esforço>': 'médio', '<data>': '03/10/2026', '<nomes>': 'Executor A',
    '<papéis ativos no projeto>': 'Arquiteto, Revisor Independente, Coordenador',
    '<papéis em reserva, ex.: Jules>': 'Jules', '<papéis em espera, ex.: executores locais>': 'executores locais',
    '<resultado de `inventario_local.py`>': 'máquina sintética, 8 GB', '<tag, ou "nenhum">': 'nenhum',
    '<threads e memória>': '4 threads, 4 GB', '<3 por padrão>': '3',
    '<50 linhas ou 2.000 tokens, por padrão>': '50 linhas',
    '`<comando>`': '`echo ok`', '<comando>': 'echo ok', '`<pasta>`': '`saida/`', '<pasta>': 'saida/',
    '`<pasta autorizada ou "não">`': '`não`',
}

RODADA = {
    '<ID>': 'R-01', '<meta em uma frase>': 'fazer X', '<dd/mm/aaaa>': '03/10/2026',
    '<branch>@<sha7>': 'main@a1b2c3d', '<papel> (<ferramenta>)': 'Coordenador (Ferramenta X)',
    '<o que não tocar>': 'migrações', '<o que o usuário liberou, com data; ou "nenhuma ainda">': 'nenhuma ainda',
    '<critério observável 1>': 'X existe', '<critério observável 2>': 'X passa no teste',
    '1. <nome> — fechada · prova: `<comando>` → <resultado em poucas palavras>':
        '1. primeira — fechada · prova: `python3 -m unittest` → verde',
    '2. <nome> — em andamento': '2. segunda — em andamento', '3. <nome> — pendente': '3. terceira — pendente',
    '<caminho 1>': 'src/a.py', '<caminho 2>': 'src/b.py',
    '<item curto e verificável>': 'fechar a fatia 2 com teste', '<limite>': 'não mexer em migrações',
    'na fatia <n>': 'na fatia 2',
    '- <ID> · <bloqueador|relevante|opcional> · <arquivo:linha> · <uma linha> · <aberto|corrigido|contestado>':
        '- A-01 · relevante · src/a.py:10 · mensagem confusa · aberto',
}


def valores_ordem(raiz):
    return {
        '# Ordem <ID> — <entrega em uma frase>': '# Ordem etapa-sintetica — entregar X',
        '<papel> (<ferramenta>, <modelo>, esforço <x>)': 'Coordenador (Ferramenta X, modelo-sintetico, esforço médio)',
        'Etapa: <ID> · Base: <commit ou tag> · Worktree: <caminho> · Ramo: <ramo>':
            f'Etapa: etapa-sintetica · Base: {SHA_FINAL_BASE[0]} · Worktree: {raiz} · Ramo: etapa/etapa-sintetica',
        '<nome por fatia>': 'Especialista A', '<fatias de alto impacto ou "nenhuma">': 'nenhuma',
        '<tarefas ou "nenhuma">': 'nenhuma',
        '<o que precisa existir no fim e como o usuário vai perceber>': 'X existe e a tela mostra Y',
        '<IDs>': 'D-001', '<outros caminhos, com intervalo quando grandes>': 'src/ (inteira)',
        '1. <nome> · especialista: <nome> · escreva só: <arquivos> · aceite: <critério observável>':
            '1. única · especialista: Especialista A · escreva só: src/ · aceite: X passa no teste',
        '- <outras>': '- Sem rede externa.',
        '<base>..<commit final>': f'{SHA_FINAL_BASE[0]}..{SHA_FINAL_BASE[1]}',
        '<commit final>': SHA_FINAL_BASE[1], '<prefixo permitido>': 'src/', '<ID>': 'etapa-sintetica',
        '<id da conversa>': 'conversa-sintetica-01', '<número de fatias>': '1', '<ramo>': 'etapa/etapa-sintetica',
    }


SHA_FINAL_BASE = ['', '']  # (base, final) do repositório sintético; preenchido por repositorio_ordem()


def git(cwd, *args):
    r = subprocess.run(['git', '-C', str(cwd), '-c', 'user.name=Sintetico', '-c', 'user.email=s@localhost',
                        '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', *args],
                       capture_output=True, text=True)
    assert r.returncode == 0, f'git {args}: {r.stderr}'
    return r.stdout.strip()


def repositorio_ordem(raiz):
    """Repositório sintético com origin local: base, commit final em src/ e atestado aprovado desse commit."""
    origem = raiz.parent / 'origem.git'
    subprocess.run(['git', 'init', '-q', '--bare', str(origem)], check=True)
    raiz.mkdir()
    git(raiz, 'init', '-q', '-b', 'etapa/etapa-sintetica')
    (raiz / 'LEIAME.md').write_text('base\n', encoding='utf-8')
    git(raiz, 'add', '-A')
    git(raiz, 'commit', '-q', '-m', 'base')
    base = git(raiz, 'rev-parse', 'HEAD')
    (raiz / 'src').mkdir()
    (raiz / 'src' / 'x.py').write_text('X = 1\n', encoding='utf-8')
    git(raiz, 'add', '-A')
    git(raiz, 'commit', '-q', '-m', 'entrega')
    final = git(raiz, 'rev-parse', 'HEAD')
    git(raiz, 'remote', 'add', 'origin', str(origem))
    git(raiz, 'push', '-q', 'origin', 'etapa/etapa-sintetica')
    (raiz / 'sociedade' / 'pareceres').mkdir(parents=True)
    (raiz / 'sociedade' / 'pareceres' / 'atestado-etapa-sintetica.json').write_text(
        json.dumps({'status': 'APROVADO', 'commit': final, 'total_arquivos_inspecionados': 1}), encoding='utf-8')
    SHA_FINAL_BASE[:] = [base, final]
    return base, final


class TesteContratoModelos(unittest.TestCase):
    def tmp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)

    # ---------- cobertura do contrato ----------

    def test_todo_modelo_do_pacote_esta_no_contrato(self):
        nomes = {p.name for p in modelos_do_pacote()}
        self.assertEqual(nomes, ANALISADOS | set(SEM_ANALISADOR),
                         'modelo novo ou removido: inclua-o em ANALISADOS (com analisador) ou em SEM_ANALISADOR (com motivo)')
        for nome, motivo in SEM_ANALISADOR.items():
            self.assertTrue(motivo.strip(), f'{nome}: modelo sem analisador exige o motivo')

    # ---------- parecer ----------

    def parecer_preenchido(self, **troca):
        texto = preencher(modelo('parecer-modelo.md'), PARECER)
        for k, v in troca.items():
            self.assertIn(k, texto)
            texto = texto.replace(k, v)
        return texto

    def lint(self, texto):
        arq = self.tmp() / 'parecer.md'
        arq.write_text(texto, encoding='utf-8')
        return rodar(LINT_PARECER, arq)

    def test_parecer_modelo_preenchido_passa_sem_avisos(self):
        r = self.lint(self.parecer_preenchido())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn('aviso', r.stdout)
        self.assertIn('aceitar com ressalvas', r.stdout)

    def test_parecer_modelo_cru_reprovado(self):
        r = self.lint(modelo('parecer-modelo.md'))
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_parecer_modelo_exige_a_linha_commit(self):
        texto = modelo('parecer-modelo.md')
        self.assertRegex(texto, r'(?m)^- commit: <')

    def test_parecer_sem_commit_reprovado(self):
        sem = re.sub(r'(?m)^- commit:.*\n', '', self.parecer_preenchido())
        self.assertNotIn('commit:', sem)
        r = self.lint(sem)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('commit', r.stdout)

    def test_parecer_com_commit_vazio_ou_marcador_reprovado(self):
        base = self.parecer_preenchido()
        for valor in ('', '<SHA do commit revisado>'):
            r = self.lint(base.replace(f'- commit: {HEAD}', f'- commit: {valor}'.rstrip()))
            self.assertEqual(r.returncode, 1, (valor, r.stdout))

    def test_parecer_commit_malformado_reprovado(self):
        base = self.parecer_preenchido()
        for ruim in ('main', 'HEAD', f'`{HEAD}`', 'abc12', 'e4f5a6b (revisado)', 'z' * 40, HEAD + 'f'):
            r = self.lint(base.replace(f'- commit: {HEAD}', f'- commit: {ruim}'))
            self.assertEqual(r.returncode, 1, (ruim, r.stdout))
            self.assertIn('commit', r.stdout)

    def test_parecer_commit_diferente_do_head_reprovado(self):
        base = self.parecer_preenchido()
        r = self.lint(base.replace(f'- commit: {HEAD}', '- commit: 1234567'))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('difere do head', r.stdout)

    def test_parecer_commit_abreviado_compativel_com_o_head_passa(self):
        base = self.parecer_preenchido()
        for forma in (HEAD[:7], HEAD[:12], HEAD.upper()):
            r = self.lint(base.replace(f'- commit: {HEAD}', f'- commit: {forma}'))
            self.assertEqual(r.returncode, 0, (forma, r.stdout))

    def test_parecer_aceita_rodada_no_lugar_de_etapa(self):
        legado = self.parecer_preenchido().replace('- etapa: etapa-sintetica', '- rodada: NT-02')
        self.assertEqual(self.lint(legado).returncode, 0)
        sem_nenhum = re.sub(r'(?m)^- etapa:.*\n', '', self.parecer_preenchido())
        r = self.lint(sem_nenhum)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('etapa', r.stdout)

    def test_parecer_achados_nenhum_com_a_instrucao_do_modelo_passa_sem_aviso(self):
        texto = self.parecer_preenchido()
        item = '- [relevante] L5 · mensagem de erro em inglês (src/formatarData.ts:41)'
        self.assertIn(item, texto)
        r = self.lint(texto.replace(item, 'nenhum'))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn('aviso', r.stdout)

    def test_parecer_ultimo_bloco_vale_e_commit_vem_dele(self):
        antigo = self.parecer_preenchido()
        novo = antigo.replace(HEAD, 'f' * 40).replace(HEAD[:7], 'f' * 7)
        sys.path.insert(0, str(LINT_PARECER.parent))
        try:
            import lint_parecer
        finally:
            sys.path.remove(str(LINT_PARECER.parent))
        self.assertEqual(lint_parecer.commit_revisado(antigo + '\n\n' + novo), 'f' * 40)
        self.assertEqual(lint_parecer.commit_revisado(antigo), HEAD)
        self.assertIsNone(lint_parecer.commit_revisado(re.sub(r'(?m)^- commit:.*\n', '', antigo)))

    # ---------- perfil ----------

    def test_perfil_modelo_preenchido_passa_sem_avisos(self):
        texto = preencher(sem_instrucoes(modelo('perfil-modelo.md')), PERFIL_UNIFORME)
        texto = texto.replace('## Missão\n', '## Missão\nAjudar pessoas sintéticas a testar o método.\n', 1)
        arq = self.tmp() / 'perfil.md'
        arq.write_text(texto, encoding='utf-8')
        r = rodar(VALIDAR_PERFIL, arq)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn('aviso', r.stdout)
        from sc_perfil import PerfilProjeto
        perfil = PerfilProjeto(conteudo=texto)
        papeis = {p['papel'] for p in perfil.listar_papeis()}
        self.assertTrue({'Arquiteto', 'Revisor Independente', 'Coordenador'} <= papeis, papeis)
        self.assertEqual(perfil.obter_fornecedor('Arquiteto'), 'Fornecedor Alfa')

    def test_perfil_modelo_cru_tem_o_minimo_e_avisa_dos_marcadores(self):
        r = rodar(VALIDAR_PERFIL, NUCLEO / 'assets' / 'perfil-modelo.md')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('marcador', r.stdout)

    # ---------- rodada ----------

    def test_rodada_modelo_preenchido_passa_no_lint(self):
        pasta = self.tmp() / 'sociedade'
        pasta.mkdir()
        (pasta / 'rodada.md').write_text(preencher(modelo('rodada-modelo.md'), RODADA), encoding='utf-8')
        r = rodar(SC_RODADA, 'lint', '--pasta', pasta)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn('não há rodada aberta', r.stdout)

    def test_rodada_modelo_preenchido_reprova_se_fatia_fechada_perde_a_prova(self):
        pasta = self.tmp() / 'sociedade'
        pasta.mkdir()
        texto = preencher(modelo('rodada-modelo.md'), RODADA)
        texto = texto.replace(' · prova: `python3 -m unittest` → verde', '')
        (pasta / 'rodada.md').write_text(texto, encoding='utf-8')
        r = rodar(SC_RODADA, 'lint', '--pasta', pasta)
        self.assertNotEqual(r.returncode, 0, 'o analisador deveria reprovar fatia fechada sem prova')

    # ---------- ordem ----------

    def test_ordem_modelo_preenchida_nao_deixa_entrega_por_preencher(self):
        raiz = self.tmp() / 'repo'
        repositorio_ordem(raiz)
        texto = modelo('ordem-modelo.md')
        # a legenda dos tipos é texto de referência, não campo a preencher
        texto = '\n'.join(l for l in texto.split('\n') if not (l.startswith('`') and not l.startswith('```')))
        ordem = raiz / 'sociedade' / 'ordens' / 'etapa-sintetica.md'
        ordem.parent.mkdir(parents=True)
        ordem.write_text(preencher(texto, valores_ordem(raiz)), encoding='utf-8')
        env = dict(os.environ, HOME=str(self.tmp()))  # sem logs de conversa: delegações ficam "não verificado"
        r = subprocess.run([sys.executable, '-B', str(SC_CONFERIR), '--ordem', str(ordem), '--raiz', str(raiz), '--json'],
                           capture_output=True, text=True, env=env)
        self.assertIn(r.returncode, (0, 1), r.stdout + r.stderr)  # 2 = ordem ilegível
        rel = json.loads(r.stdout)
        estados = {i['id']: i['estado'] for i in rel['itens']}
        self.assertEqual(set(estados), {'E1', 'E2', 'E3', 'E4', 'E5', 'E6'}, estados)
        self.assertNotIn('não preenchido', estados.values(), rel['itens'])
        for id_ in ('E1', 'E2', 'E3', 'E6'):
            self.assertEqual(estados[id_], 'feito', rel['itens'])

    def test_ordem_modelo_cru_tem_todas_as_entregas_por_preencher(self):
        raiz = self.tmp() / 'repo'
        raiz.mkdir()
        git(raiz, 'init', '-q')
        ordem = raiz / 'ordem.md'
        ordem.write_text(modelo('ordem-modelo.md'), encoding='utf-8')
        r = subprocess.run([sys.executable, '-B', str(SC_CONFERIR), '--ordem', str(ordem), '--raiz', str(raiz), '--json'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual({i['estado'] for i in json.loads(r.stdout)['itens']}, {'não preenchido'})

    # ---------- avaliação (sem analisador) ----------

    def test_avaliacao_modelo_tem_o_formulario_e_nenhum_marcador_angular(self):
        texto = modelo('avaliacao-modelo.md')
        self.assertIn('# Avaliação da Etapa: [ID da Etapa]', texto)
        self.assertEqual(MARCADOR.findall(texto), [], 'o formulário usa [campo]; marcador <...> confundiria os analisadores')
        self.assertIn('Proibição Absoluta', texto)  # o modelo carrega a regra antitoken


if __name__ == '__main__':
    unittest.main()
