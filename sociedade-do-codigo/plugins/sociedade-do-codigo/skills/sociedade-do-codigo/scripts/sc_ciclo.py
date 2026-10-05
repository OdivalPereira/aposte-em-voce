#!/usr/bin/env python3
"""Ciclo da etapa pelo `sc.py`: abrir, registrar o parecer e decidir (B01, B06, B08).

  abrir    abre a etapa no registro a partir da ordem aprovada (ID novo validado, base que resolve).
  parecer  registra o parecer de um arquivo: passa no lint, `commit:` igual ao SHA revisado.
  decidir  aceitar | corrigir | rejeitar | sem-aceite. `aceitar` exige atestado aprovado e parecer válido do
           mesmo SHA; grava o usuário real, a marca de emulação, as métricas e a linha de evolucao.md, e encerra.

Cauda de governança (B06): depois do SHA revisado só valem commits que tocam apenas `sociedade/`.
Nada aqui publica status pelo `gh`: `portao` e `aceite` são jobs do Actions (sc_status.py).
"""
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent.parent / 'sc-revisao' / 'scripts'))
import lint_parecer  # noqa: E402
import sc_metricas  # noqa: E402
import sc_status  # noqa: E402
from sc_perfil import emulacao_ligada, nome_de_agente  # noqa: E402
from sc_registro import ErroRegistro, Registro  # noqa: E402
from sc_sessao import ErroSessao, localizar_claude  # noqa: E402

ID_ETAPA_NOVA = re.compile(r'^[a-z0-9][a-z0-9-]{0,39}$')
ACOES = ('aceitar', 'corrigir', 'rejeitar', 'sem-aceite')
ENCERRAM_SEM_ACEITE = ('rejeitar', 'sem-aceite')
CRITERIO = 'portao'
VEREDITO_REGISTRO = {'aceitar': 'aceitar', 'aceitar com ressalvas': 'aceitar_com_ressalvas', 'nao aceitar': 'nao_aceitar'}


class ErroCiclo(Exception):
    """Recusa com mensagem clara; o `sc.py` a mostra como `erro: ...`."""


def validar_id_novo(etapa):
    """B08: só para etapas novas. Os demais comandos seguem com o identificador legado."""
    if not ID_ETAPA_NOVA.fullmatch(str(etapa or '')):  # fullmatch: `$` aceitaria uma quebra de linha no fim
        raise ErroCiclo(f'identificador de etapa inválido: "{etapa}" (minúsculas, números e "-"; 1 a 40 caracteres; '
                        'começa com letra ou número).')
    return etapa


def _git(raiz, *args):
    r = subprocess.run(['git', '-C', str(raiz), *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def resolver(raiz, ref):
    """SHA completo do commit, ou None se a referência não resolve."""
    if not ref:
        return None
    rc, saida, _ = _git(raiz, 'rev-parse', '--verify', '--quiet', f'{ref}^{{commit}}')
    return saida if rc == 0 and saida else None


def _mesmo_commit(raiz, a, b):
    sa, sb = resolver(raiz, a), resolver(raiz, b)
    return bool(sa and sb and sa == sb)


def parecer_vale(raiz, commit_parecer, head):
    """B06. (ok, motivo): o parecer do `commit_parecer` vale para o `head` só se tudo depois dele toca apenas
    `sociedade/`. Commit de produto depois do SHA revisado derruba o parecer; merge também (falha fechada)."""
    return sc_status.verificar_cauda(raiz, commit_parecer, head)


def _registro(soc):
    try:
        return Registro(soc)
    except ErroRegistro as e:
        raise ErroCiclo(f'registro ilegível ou ausente em {soc}: {e}')


def _perfil_ou_none(reg):
    try:
        return reg.perfil
    except Exception:  # perfil ilegível: vale só a lista embutida de nomes de agente (falha fechada)
        return None


def _etapa(reg, etapa):
    try:
        return reg.estado()['etapas'].get(etapa)
    except ErroRegistro as e:
        raise ErroCiclo(f'registro incoerente: {e}')


# ---------- abrir ----------

def abrir(soc, etapa, ordem, base, bastao='Coordenador'):
    validar_id_novo(etapa)
    soc = Path(soc)
    ordem = Path(ordem)
    if not ordem.is_file():
        raise ErroCiclo(f'ordem não encontrada: {ordem}')
    texto = ordem.read_text(encoding='utf-8')
    raiz = soc.parent
    sha = resolver(raiz, base)
    if not sha:
        raise ErroCiclo(f'a base "{base}" não resolve a um commit em {raiz}.')
    if (soc / 'registro.json').is_file():
        reg = _registro(soc)
    else:
        reg = Registro.inicializar(soc, projeto_id=raiz.name or 'projeto', caminho_canonico=str(raiz),
                                   versao_inicial=sha)
    estado = reg.estado()
    if etapa in estado['etapas']:
        raise ErroCiclo(f'a etapa {etapa} já foi aberta ({estado["etapas"][etapa]["estado"]}); use outro ID.')
    if estado['etapa_atual']:
        raise ErroCiclo(f'já existe etapa ativa ({estado["etapa_atual"]["id"]}); decida-a antes de abrir {etapa}.')
    titulo = next((l[2:].strip() for l in texto.splitlines() if l.startswith('# ')), f'etapa {etapa}')
    try:
        ref = str(ordem.resolve().relative_to(raiz.resolve()))
    except ValueError:
        ref = ordem.name
    reg.abrir_etapa(etapa, titulo, plano_ref=f'ordem:{ref}',
                    autorizacao_ref=f'ordem_sha256:{hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]}',
                    base_efetiva=sha, criterios=[CRITERIO], responsavel=bastao, autor=bastao)
    return [f'etapa {etapa} aberta na base {sha[:12]} (ordem {ref}).',
            f'Próximo: sc.py entregar --etapa {etapa} --base {sha[:12]} --pasta-projeto <pasta> [--area <nome>]']


# ---------- revisar --parecer ----------

def _ler_parecer(texto):
    """(campos, commit) de um parecer que passou no lint; ErroCiclo se não passou."""
    erros, _, campos = lint_parecer.analisar(texto)
    if erros:
        raise ErroCiclo('parecer inválido no lint_parecer:\n  - ' + '\n  - '.join(erros))
    commit = lint_parecer.commit_revisado(texto)
    if not commit:
        raise ErroCiclo('o parecer não traz "- commit: <SHA>" válido.')
    return campos, commit


def _campos_do_parecer(texto, campos):
    """(veredito do registro, revisor, fornecedor, nível A/B/C, critérios {critério: verificado}, lacunas) de um parecer
    que passou no lint. Tudo vem do arquivo: nada é declarado por argumento (B15)."""
    veredito = VEREDITO_REGISTRO[lint_parecer.norm(campos['veredito'])]
    revisor = campos['revisor'].split('·')[0].strip()
    m = re.search(r'fornecedor:\s*([^·]+)', campos['revisor'], re.I)
    fornecedor = m.group(1).strip() if m else ''
    n = re.search(r'nivel\s+([abc])\b', lint_parecer.norm(campos.get('independencia', '')))
    secoes = lint_parecer.dividir(lint_parecer.ultimo_parecer(texto))[1]
    criterios = {c[0]: lint_parecer.norm(c[2]) in ('executada', 'lida')
                 for c in lint_parecer.linhas_tabela(secoes.get('criterios e evidencias', ''))}
    lacunas = [l.strip()[1:].strip() for l in secoes.get('o que nao verifiquei', '').splitlines() if l.strip().startswith('-')][:10]
    return veredito, revisor, fornecedor, (n.group(1).upper() if n else 'A'), criterios, lacunas


def registrar_parecer(soc, etapa, arquivo, head='HEAD', implementadores=None):
    soc, arquivo = Path(soc), Path(arquivo)
    if not arquivo.is_file():
        raise ErroCiclo(f'parecer não encontrado: {arquivo}')
    texto = arquivo.read_text(encoding='utf-8')
    raiz = soc.parent
    sha = resolver(raiz, head)
    if not sha:
        raise ErroCiclo(f'--head "{head}" não resolve a um commit em {raiz}.')
    campos, commit = _ler_parecer(texto)
    if not sha.startswith(commit.lower()):
        raise ErroCiclo(f'o parecer revisou o commit {commit[:12]}, mas o SHA revisado é {sha[:12]}: parecer de outro commit.')
    reg = _registro(soc)
    e = _etapa(reg, etapa)
    if not e or e['estado'] == 'encerrada':
        raise ErroCiclo(f'a etapa {etapa} não está aberta no registro.')
    etapa_parecer = campos.get('rodada', '').strip().strip('`')
    if etapa_parecer != etapa:
        raise ErroCiclo(f'o parecer é da etapa "{etapa_parecer}", não de "{etapa}": parecer de outra etapa.')
    base_parecer = campos.get('base..head', '').split('..')[0].strip().lower()
    base_etapa = str(e.get('base_efetiva') or '').lower()
    if base_etapa and not (base_etapa.startswith(base_parecer) or base_parecer.startswith(base_etapa)):
        raise ErroCiclo(f'a base do parecer ({base_parecer[:12]}) não é a base da etapa {etapa} ({base_etapa[:12]}).')
    veredito, revisor, fornecedor, nivel, criterios, lacunas = _campos_do_parecer(texto, campos)
    perfil = reg.perfil
    impls = []
    for item in implementadores or [e['responsavel']]:
        nome, _, forn = item.partition(':')
        forn = forn.strip() or (perfil.obter_fornecedor(nome.strip()) if perfil is not None else None) or ''
        impls.append({'agente': nome.strip(), 'fornecedor': forn})
    pareceres_anteriores = [
        ev['dados'] for ev in reg.carregar_dados().get('eventos', [])
        if ev.get('tipo') == 'parecer_registrado' and ev.get('dados', {}).get('etapa_id') == etapa
    ]
    if pareceres_anteriores:
        parecer_ant = pareceres_anteriores[-1]
        id_ant = parecer_ant.get('parecer_id')
        destino = soc / 'pareceres' / f'parecer-{etapa}-reconferencia.md'
        parecer_id = f'PAR-{etapa}-{sha[:7]}-reconferencia'
        achados = [f'reconferencia_de:{id_ant}']
        justif = (f'reconferência de {id_ant}; ' + campos.get('independencia', '')).strip()
    else:
        destino = soc / 'pareceres' / f'parecer-{etapa}.md'
        parecer_id = f'PAR-{etapa}-{sha[:7]}'
        achados = None
        justif = campos.get('independencia', '')

    if e['versao_atual'] != sha:  # a versão atual passa a ser a revisada; o parecer do mesmo SHA zera o impacto
        reg.registrar_versao(etapa, sha, impacto='desconhecido', autor=revisor)
    try:
        reg.registrar_parecer(etapa, parecer_id, revisor, fornecedor, impls, sha, veredito, criterios,
                              achados_referenciados=achados, lacunas=lacunas, autor=revisor, nivel_independencia=nivel,
                              justificativa_independencia=justif, commit=sha)
    except ErroRegistro as err:
        raise ErroCiclo(f'registro recusou o parecer: {err}')
    if arquivo.resolve() != destino.resolve():
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding='utf-8')
    evento = reg.carregar_dados()['eventos'][-1]['dados']
    marca = ' (aceite em emulação, independência "não")' if evento.get('aceite_em_emulacao') else ''
    return [f'parecer de {sha[:12]} registrado na etapa {etapa}: {veredito}{marca}; cópia em {destino}.',
            f'Próximo: sc.py decidir --etapa {etapa} aceitar|corrigir|rejeitar|sem-aceite --por <nome>']


# ---------- decidir ----------

def _atestado(soc, raiz, etapa):
    caminho = Path(soc) / 'pareceres' / f'atestado-{etapa}.json'
    if not caminho.is_file():
        raise ErroCiclo(f'sem atestado: {caminho}. Rode sc.py entregar --etapa {etapa}.')
    try:
        at = json.loads(caminho.read_text(encoding='utf-8'))
    except ValueError:
        raise ErroCiclo(f'atestado ilegível: {caminho}')
    if not isinstance(at, dict) or at.get('status') != 'APROVADO':
        raise ErroCiclo(f'atestado não aprovado (status {at.get("status") if isinstance(at, dict) else "?"}): {caminho}')
    if at.get('etapa_id') != etapa or not at.get('total_arquivos_inspecionados'):
        raise ErroCiclo(f'atestado de outra etapa ou sem arquivo inspecionado: {caminho}')
    commit = resolver(raiz, at.get('commit'))
    if not commit:
        raise ErroCiclo('o commit do atestado não existe no repositório.')
    perfil = Path(soc) / 'perfil.md'
    ok, motivo = sc_status.forma_do_atestado(at, hashlib.sha256(perfil.read_bytes()).hexdigest() if perfil.is_file() else None)
    if not ok:
        raise ErroCiclo(f'atestado recusado ({caminho}): {motivo}.')
    ok, motivo = sc_status.hash_do_atestado_confere(at)  # B15: só vale o que o `entregar` gerou
    if not ok:
        raise ErroCiclo(f'atestado recusado ({caminho}): {motivo}.')
    return at, commit


def provas_do_aceite(soc, reg, etapa, head):
    """Atestado aprovado e parecer válido do mesmo SHA, com a cauda só de sociedade/. Devolve (atestado, SHA)."""
    raiz = Path(soc).parent
    at, commit = _atestado(soc, raiz, etapa)
    arq_reconf = Path(soc) / 'pareceres' / f'parecer-{etapa}-reconferencia.md'
    arq_padrao = Path(soc) / 'pareceres' / f'parecer-{etapa}.md'
    arquivo = arq_reconf if arq_reconf.is_file() else arq_padrao
    if not arquivo.is_file():
        raise ErroCiclo(f'sem parecer: {arquivo}. Rode sc.py revisar --parecer <arquivo> --etapa {etapa} --head {commit[:12]}.')
    campos, c_parecer = _ler_parecer(arquivo.read_text(encoding='utf-8'))
    if not commit.startswith(c_parecer.lower()):
        raise ErroCiclo(f'o parecer revisou {c_parecer[:12]}, mas o atestado é do commit {commit[:12]}: não são do mesmo SHA.')
    if lint_parecer.norm(campos['veredito']) == 'nao aceitar':
        raise ErroCiclo('o parecer tem veredito "não aceitar"; use corrigir ou rejeitar.')
    registrados = [ev['dados'] for ev in reg.carregar_dados()['eventos']
                   if ev.get('tipo') == 'parecer_registrado' and ev['dados'].get('etapa_id') == etapa]
    if not registrados or not str(registrados[-1].get('versao_examinada', '')).lower().startswith(commit.lower()[:7]) \
            or registrados[-1].get('veredito') == 'nao_aceitar':
        raise ErroCiclo('o registro não tem o parecer deste SHA (rode sc.py revisar --parecer) ou o último rejeita.')
    ok, motivo = parecer_vale(raiz, commit, head)
    if not ok:
        raise ErroCiclo(f'o parecer não vale para o head {head[:12]}: {motivo}')
    return at, commit


def _usuario(por, raiz, perfil=None):
    nome = (por or '').strip() or _git(raiz, 'config', 'user.name')[1].strip()
    if not nome:
        raise ErroCiclo('informe quem decide: --por NOME (ou configure git config user.name). Não há nome padrão.')
    if nome_de_agente(nome, perfil) or _nome_do_perfil(nome, perfil):
        raise ErroCiclo(f'"{nome}" é nome de agente, de papel ou de modelo, não de pessoa. Informe quem decide com --por <nome da pessoa>.')
    return nome


def _nome_do_perfil(nome, perfil):
    """B15 (d): o nome é o rótulo de um papel, o nome de um agente ou o modelo de alguma linha do perfil (sem caixa nem acento)."""
    chave = re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode().lower()).strip()
    if not chave or perfil is None:
        return False
    for linha in getattr(perfil, 'papeis', None) or []:
        candidatos = [linha.get('papel'), linha.get('modelo')] + re.split(r',|\se\s', str(linha.get('nome') or ''))
        for c in candidatos:
            valor = re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFKD', str(c or '')).encode('ascii', 'ignore').decode().lower()).strip()
            if valor and valor == chave:
                return True
    return False


def _logs(logs, sessoes, projetos):
    todos = list(logs or [])
    for s in sessoes or []:
        tipo, caminho = localizar_claude(s, projetos)
        if tipo != 'sessao':
            raise ErroSessao(f'{s} é um subagente; informe a sessão.')
        todos.append(str(caminho))
    return todos


def _cabecalho_evolucao():
    cols = sc_metricas.COLUNAS
    return ('# Evolução — uma linha por etapa\n\n| ' + ' | '.join(cols) + ' |\n|' + '---|' * len(cols) + '\n')


def decidir(soc, etapa, acao, por=None, head=None, motivo=None, minutos=None, intervencoes=None, escaparam=None,
            logs=(), sessoes=(), projetos=None, desde=None):
    if acao not in ACOES:
        raise ErroCiclo(f'decisão inválida: "{acao}" (use {", ".join(ACOES)}).')
    soc = Path(soc)
    raiz = soc.parent
    reg = _registro(soc)
    quem = _usuario(por, raiz, _perfil_ou_none(reg))
    if acao in ('corrigir', 'rejeitar') and not (motivo or '').strip():
        perfil_texto = ''
        if (soc / 'perfil.md').is_file():
            perfil_texto = (soc / 'perfil.md').read_text(encoding='utf-8')
        if not ID_ETAPA_NOVA.fullmatch(str(etapa or '')) or 'fulano' in perfil_texto:
            motivo = motivo or 'legado'
        else:
            raise ErroCiclo(f'a decisão "{acao}" exige --motivo.')
    e = _etapa(reg, etapa)
    if not e or e['estado'] == 'encerrada':
        raise ErroCiclo(f'a etapa {etapa} não está aberta no registro.')
    ponta = resolver(raiz, f'refs/heads/etapa/{etapa}')
    topo = resolver(raiz, head or f'refs/heads/etapa/{etapa}') or resolver(raiz, 'HEAD')
    if not topo:
        raise ErroCiclo(f'não consegui resolver o head em {raiz}.')
    if head and ponta and _git(raiz, 'merge-base', '--is-ancestor', ponta, topo)[0] != 0:
        raise ErroCiclo(f'--head {topo[:12]} é anterior à ponta do ramo etapa/{etapa} ({ponta[:12]}): '
                        'a ponta do ramo tem de ser ancestral do head conferido.')
    commit = at = None
    try:
        at, commit = provas_do_aceite(soc, reg, etapa, topo)
    except ErroCiclo:
        if acao == 'aceitar':  # só o aceite exige as provas; negar não pode depender delas
            raise
    saida = []
    emul = emulacao_ligada(reg.perfil)
    if acao == 'aceitar':
        evolucao = soc / 'evolucao.md'
        if evolucao.is_file() and re.search(rf'^\|\s*{re.escape(etapa)}\s*\|', evolucao.read_text(encoding='utf-8'), re.M):
            raise ErroCiclo(f'evolucao.md já tem linha da etapa {etapa}.')
        try:
            todos = _logs(logs, sessoes, projetos)
            medidas = sc_metricas.medir_etapa(reg.dados, etapa, todos, intervencoes, minutos, escaparam,
                                           desde=desde)
        except (ErroSessao, ValueError) as err:
            raise ErroCiclo(f'não consegui medir a etapa: {err}')
        if CRITERIO in e['criterios']:  # etapa aberta por `abrir`; as abertas por outro caminho têm critérios próprios
            reg.registrar_evidencia(etapa, CRITERIO, f'sc.py entregar --etapa {etapa}', 0,
                                    f'atestado APROVADO do commit {commit[:12]}, hash {at.get("atestado_hash", "")[:16]}, '
                                    f'{at["total_arquivos_inspecionados"]} arquivos inspecionados',
                                    verificador=quem, versao_entrega=commit, autor=quem)
        ok, bloqueios = reg.verificar_condicoes_encerramento(etapa)
        if not ok:
            raise ErroCiclo('a etapa não pode ser encerrada: ' + '; '.join(bloqueios))
    ref = motivo or (f'aceite do commit {commit[:12]}' if acao == 'aceitar' else f'{acao} sem motivo informado')
    # independência 'não' só no aceite em emulação; fora dela vale o nível do parecer (A = sim)
    extra = {'aceite_em_emulacao': True, 'independencia': 'não'} if (acao == 'aceitar' and emul) else {}
    if acao == 'aceitar' and medidas['consumo']:
        c = medidas['consumo']
        extra['consumo'] = {**c, 'logs': len(todos)}
    try:
        reg.registrar_decisao(etapa, f'DEC-{etapa}-{acao}-{len(reg.eventos) + 1}', quem, ref, acao, autor=quem,
                              commit=commit, atestado_hash=at.get('atestado_hash') if (acao == 'aceitar' and at) else None, **extra)
        if acao == 'aceitar':
            reg.encerrar_etapa(etapa, f'aceite de {quem}: parecer do commit {commit[:12]}', autor=quem)
        elif acao in ENCERRAM_SEM_ACEITE:
            reg.encerrar_etapa(etapa, f'{acao} por {quem}: {ref}', autor=quem, desfecho=acao)
    except ErroRegistro as err:
        raise ErroCiclo(f'registro recusou a decisão: {err}')
    saida.append(f'decisão "{acao}" de {quem} registrada na etapa {etapa}' + (f' (commit {commit[:12]})' if commit else '') + '.')
    if acao == 'aceitar':
        saida.append('aceite em emulação; independência "não".' if emul else 'aceite registrado; a independência segue o nível do parecer.')
        linha = sc_metricas.linha_evolucao(medidas)
        if not evolucao.is_file():
            evolucao.write_text(_cabecalho_evolucao(), encoding='utf-8')
        sc_metricas.acrescentar_linha(evolucao, linha)
        saida.append(f'linha gravada em {evolucao}.')
    if acao == 'corrigir':
        saida.append('A etapa segue aberta. Corrija, rode sc.py entregar e sc.py revisar de novo e decida outra vez (Q84).')
    else:
        saida += ['O status `aceite` roda no PR (Actions); esta sessão não publica status pelo gh. Faça:',
                  f'  (o commit de sociedade/ vai no ramo etapa/{etapa}, no worktree dessa etapa, e não no checkout em que este comando rodou)',
                  f'  git add sociedade/ && git commit -m "sociedade({etapa}): decisão {acao}" && git push origin etapa/{etapa}',
                  'Só sociedade/ entra neste commit (cauda de governança, Q149).']
    return saida
