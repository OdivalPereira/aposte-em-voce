#!/usr/bin/env python3
"""Estado da rodada da Sociedade do Código: abre, passa o bastão, fecha fatia, encerra e confere.

Integra com o subsistema de eventos e persistência atômica em registro.json
e mantém as projeções em rodada.md e historico.md.

Comandos:
  abrir       cria a rodada (recusa se já houver uma aberta: uma rodada por vez)
  bastao      troca quem escreve e preenche "Para quem pega o bastão agora"
  fatia       acrescenta, fecha (exige prova executada válida) ou lista as fatias
  autorizar   registra uma autorização do usuário, com data
  achado      registra ou fecha um achado da revisão (bloqueador aberto ou contestado bloqueia encerramento)
  evidencia   registra evidência vinculada a um critério da etapa
  parecer     registra parecer de revisão independente (com segregação de fornecedor)
  excecao     registra exceção estruturada com autorização humana
  encerrar    fecha a rodada, escreve o histórico e atualiza o estado operacional
  lint        confere teto, seções, ordem das fatias, prova e ausência de medição de consumo algorítmica
  colar       imprime um bloco curto para colar em ferramenta que não enxerga o repositório
  rotacionar  arquiva os meses antigos do histórico
  resumo      exporta ou importa resumos entre projetos (agregação de contagens)
  migrar      migra estado legado para registro.json
  calibrar    avalia retrospectivamente a eficácia preditiva dos fatores de rigor (Q22)

Os comandos que escrevem simulam por padrão; só gravam com --aplicar.
Sem dependências externas.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Carrega sc_registro
try:
    from sc_registro import (
        Registro,
        ErroRegistroCorrompido,
        ErroValidacaoRegistro,
        ErroConcorrenciaRegistro,
        caminhos_registro,
        carregar_dados_registro,
        migrar_legado_para_registro,
        PADRAO_PLACEHOLDER,
        PADRAO_NAO_EXECUTADO,
        calcular_hash_conteudo,
        localizar_sociedade_canonica,
    )
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from sc_registro import (
            Registro,
            ErroRegistroCorrompido,
            ErroValidacaoRegistro,
            ErroConcorrenciaRegistro,
            caminhos_registro,
            carregar_dados_registro,
            migrar_legado_para_registro,
            PADRAO_PLACEHOLDER,
            PADRAO_NAO_EXECUTADO,
            calcular_hash_conteudo,
            localizar_sociedade_canonica,
        )
    except Exception:
        Registro = None
        carregar_dados_registro = None
        calcular_hash_conteudo = None
        def localizar_sociedade_canonica(pasta_base=None):
            b = Path(pasta_base).resolve() if pasta_base else Path.cwd().resolve()
            return (b / 'sociedade').resolve()

try:
    from verificar_disjuncao import conflito, normalizar as normalizar_caminho
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from verificar_disjuncao import conflito, normalizar as normalizar_caminho
    except Exception:
        conflito = None
        normalizar_caminho = None


def obter_commit_git_head(pasta=None):
    """Obtém o hash do HEAD git se pasta pertencer a um repositório git."""
    try:
        p = Path(pasta).resolve() if pasta else Path.cwd()
        res_top = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=p,
            capture_output=True,
            text=True,
            check=False
        )
        if res_top.returncode != 0:
            return None
        top_level = Path(res_top.stdout.strip()).resolve()
        try:
            p.relative_to(top_level)
        except ValueError:
            return None

        res = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=p,
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode == 0:
            h = res.stdout.strip()
            if h and len(h) >= 7 and not h.startswith('fatal:'):
                return h
    except Exception:
        pass
    return None


def obter_sincronia_info(reg):
    if not reg or not getattr(reg, '_dados', None):
        return None
    eventos = reg._dados.get('eventos', [])
    if not eventos:
        sha = '0' * 16
    else:
        sha = calcular_hash_conteudo(json.dumps(eventos[-1], sort_keys=True))[:16] if calcular_hash_conteudo else ('0' * 16)
    return {'rev': reg.revisao, 'sha': sha}

PASTA_PADRAO = 'sociedade'
TETO_RODADA = 6144          # bytes do estado vivo
TETO_HISTORICO = 32768      # bytes antes de arquivar
MAX_LEIA = 5                # caminhos em "leia só"
NIVEIS = ('1', '2', '3', 'adaptativo')
ESTADOS = ('fechada', 'concluida', 'em andamento', 'pendente')
SECOES = ('Aceite', 'Fatias', 'Para quem pega o bastão agora', 'Achados abertos')
CAMPOS = ('nivel', 'aberta', 'base', 'bastao', 'limites', 'autorizacoes')
SEVERIDADES = ('bloqueador', 'relevante', 'opcional')
ESTADOS_ACHADO_VALIDOS = ('aberto', 'contestado', 'corrigido', 'excepcionado')
MAPA_SINONIMOS_ESTADO_ACHADO = {
    'resolvido': 'corrigido',
    'fechado': 'corrigido',
    'atendido': 'corrigido',
    'abrir': 'aberto',
    'novo': 'aberto',
}

# Proíbe medição algorítmica de consumo por agentes dentro do estado vivo (REV-013)
MEDICAO_SUSPEITA = re.compile(r'\b(tokens?|cotas?|quotas?|custos?|consumo|gastei|gastos?)\b|R\$|\bUSD\b', re.I)
PADRAO_AVISO_MANUAL_COTA = re.compile(
    r'^\s*-\s+aviso\s+manual\s+de\s+cota:\s+disponibilidade\s+abaixo\s+de\s+30%\s+·\s+autor:\s+[^·\n]+?\s+·\s+janela:\s+[^·\n]+\s+·\s+data:\s+\d{2}/\d{2}/\d{4}',
    re.I
)

PLACEHOLDER = re.compile(r'<[^<>\n]{2,60}>')
FATIA = re.compile(r'^(\d+)\.\s+(.+?)\s+—\s+(fechada|concluida|em[ _]andamento|pendente)\b(.*)$')


# ---------- leitura e escrita ----------

def caminhos(pasta=None):
    p = Path(pasta) if pasta else localizar_sociedade_canonica()
    return p / 'rodada.md', p / 'historico.md', p / 'historico'


def ler(arq):
    return arq.read_text(encoding='utf-8') if arq.is_file() else ''


def agora(fmt='%d/%m/%Y %H:%M'):
    return datetime.now().strftime(fmt)


def gravar(arq, texto, aplicar, rotulo):
    if not aplicar:
        print(f'[simulação] {rotulo}: {arq} ({len(texto.encode("utf-8"))} bytes)')
        return False
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(texto, encoding='utf-8')
    print(f'{rotulo}: {arq}')
    return True


def anexar_historico(hist, linha_titulo, corpo, aplicar):
    atual = ler(hist)
    novo = (atual.rstrip('\n') + '\n\n' if atual.strip() else '') + f'## {linha_titulo}\n{corpo}\n'
    return gravar(hist, novo, aplicar, 'histórico')


def obter_registro_opcional(pasta):
    """Carrega registro.json se existir. Se o arquivo existir e for corrompido, falha imediatamente (REV-001)."""
    if Registro is None:
        return None
    p_pasta = Path(pasta)
    reg_file, _ = caminhos_registro(p_pasta)
    if reg_file.is_file():
        try:
            return Registro(p_pasta)
        except ErroRegistroCorrompido as e:
            raise SystemExit(f'erro de integridade: registro corrompido em {reg_file}: {e}')
        except Exception as e:
            raise SystemExit(f'erro ao carregar registro em {reg_file}: {e}')
    return None


def obter_registro_obrigatorio(pasta):
    """Exige que registro.json exista e esteja íntegro para operações de mutação (REV-001)."""
    reg = obter_registro_opcional(pasta)
    if reg is None:
        raise SystemExit(
            f'erro: registro estruturado não encontrado em {pasta}/registro.json. '
            'Execute "abrir" ou "migrar" para inicializar a etapa antes de registrar mutações.'
        )
    return reg


# ---------- estrutura do rodada.md ----------

def partir(texto):
    """Devolve (titulo, campos, secoes) — secoes é um dicionário nome -> lista de linhas."""
    linhas = texto.replace('\r\n', '\n').split('\n')
    titulo, campos, secoes, atual = '', {}, {}, None
    for linha in linhas:
        if linha.strip().startswith('<!-- registro_sincronia:') or linha.strip().startswith('<!-- registro_revisao:'):
            continue
        if linha.startswith('# ') and not titulo:
            titulo = linha[2:].strip()
            continue
        if linha.startswith('## '):
            atual = linha[3:].strip()
            secoes[atual] = []
            continue
        if atual is not None:
            secoes[atual].append(linha)
        else:
            m = re.match(r'^- ([a-z_]+):\s*(.*)$', linha)
            if m and m.group(1) in CAMPOS:
                campos[m.group(1)] = m.group(2).strip()
    return titulo, campos, secoes


def montar(titulo, campos, secoes, sincronia=None):
    out = [f'# {titulo}', '']
    for c in CAMPOS:
        if c in campos:
            out.append(f'- {c}: {campos[c]}')
    out.append('')
    for s in SECOES:
        out.append(f'## {s}')
        for linha in secoes.get(s, []):
            if not linha.strip().startswith('<!-- registro_sincronia:') and not linha.strip().startswith('<!-- registro_revisao:'):
                out.append(linha)
        out.append('')
    res = '\n'.join(out).rstrip() + '\n'
    if sincronia:
        res = res.rstrip() + f'\n\n<!-- registro_sincronia: rev={sincronia["rev"]} sha={sincronia["sha"]} -->\n'
    return res


def fatias_de(secoes):
    res = []
    for linha in secoes.get('Fatias', []):
        m = FATIA.match(linha.strip())
        if m:
            raw_st = m.group(3)
            if raw_st == 'concluida':
                st = 'fechada'
            elif raw_st in ('em andamento', 'em_andamento'):
                st = 'em andamento'
            else:
                st = raw_st
            res.append({
                'n': int(m.group(1)),
                'nome': m.group(2),
                'estado': st,
                'raw_estado': raw_st,
                'resto': m.group(4).strip(),
                'linha': linha,
            })
    return res


def exigir_rodada(rodada):
    if not rodada.is_file():
        raise SystemExit(f'erro: não há rodada aberta em {rodada}')
    return ler(rodada)


def rotulo(titulo):
    m = re.match(r'^Rodada\s+([A-Za-z0-9_-]+)', titulo)
    return f'rodada {m.group(1)}' if m else 'rodada'


def etapa_id_de(titulo):
    m = re.match(r'^Rodada\s+([A-Za-z0-9_-]+)', titulo)
    return m.group(1) if m else 'RODADA'


# ---------- comandos ----------

def cmd_abrir(a):
    nivel = getattr(a, 'nivel', None) or '2'
    if nivel not in NIVEIS:
        raise SystemExit(f'erro: nível inválido "{nivel}" (use {", ".join(NIVEIS)})')

    rodada, hist, _ = caminhos(a.pasta)
    if rodada.is_file():
        if not a.forcar:
            raise SystemExit(f'erro: já existe rodada aberta em {rodada}: uma rodada por vez (use --forcar só com motivo registrado).')
        if not getattr(a, 'motivo', None) or len(a.motivo.strip()) < 10 or not getattr(a, 'decisao_ref', None) or a.decisao_ref.strip() == 'autorizacao_cli':
            raise SystemExit('erro: --forcar exige --motivo substantivo (mínimo 10 caracteres) e --decisao-ref informando instrução humana do usuário.')

    proj_id = getattr(a, 'projeto_id', None)
    p_pasta = Path(a.pasta).resolve()
    p_canonico = p_pasta if p_pasta.name != 'sociedade' else p_pasta.parent
    if not proj_id:
        proj_id = p_canonico.name if p_canonico.name else 'projeto'

    commit_git = obter_commit_git_head(p_canonico) or obter_commit_git_head(p_pasta)
    if getattr(a, 'sincronizar_git', False) or not a.base or a.base == '<preencher>':
        if commit_git:
            a.base = commit_git
        elif getattr(a, 'sincronizar_git', False):
            raise SystemExit('erro: --sincronizar-git exige que o projeto seja um repositório Git com ao menos um commit.')

    # Inicializa ou carrega o registro.json (REV-001, N4)
    reg = obter_registro_opcional(a.pasta)
    if reg is None:
        reg = Registro.inicializar(a.pasta, projeto_id=proj_id, caminho_canonico=str(p_canonico), aplicar=a.aplicar, versao_inicial=commit_git)
    elif (not a.base or a.base == '<preencher>') and reg.dados.get('versao_inicial'):
        a.base = reg.dados['versao_inicial']

    fatias_linhas = [f'{i+1}. {nome} — pendente' for i, nome in enumerate(a.fatia)] if a.fatia else ['1. fatia inicial — pendente']
    fatias_lista = a.fatia if a.fatia else ['fatia inicial']

    criterios = [f'fatia_{i+1}' for i in range(len(fatias_lista))]
    if a.aceite:
        for ac in a.aceite:
            if ac not in criterios:
                criterios.append(ac)

    exigir_rev = not getattr(a, 'sem_revisao', False)
    if not exigir_rev:
        if not a.forcar or not getattr(a, 'motivo', None) or len(a.motivo.strip()) < 10 or not getattr(a, 'decisao_ref', None):
            raise SystemExit('erro: --sem-revisao exige --forcar com --motivo substantivo (mínimo 10 caracteres) e --decisao-ref com a decisão humana do usuário.')

    try:
        reg.abrir_etapa(
            etapa_id=a.id,
            objetivo=a.meta,
            plano_ref=f'plano:{a.id}',
            autorizacao_ref='abertura_cli',
            base_efetiva=a.base,
            criterios=criterios,
            responsavel=a.bastao,
            limites=a.limites,
            exigir_revisao=exigir_rev,
            autor=a.bastao,
            aplicar=a.aplicar,
            nivel=nivel,
        )
        if not exigir_rev:
            reg.registrar_excecao(
                etapa_id=a.id,
                excecao_id=f'EXC-REV-{a.id}',
                regra='revisao_independente',
                motivo=a.motivo,
                referencia_humana=a.decisao_ref,
                autor=a.bastao,
                aplicar=a.aplicar,
            )
        for i, nome in enumerate(fatias_lista):
            try:
                reg.registrar_tarefa(
                    etapa_id=a.id,
                    tarefa_id=f'fatia_{i+1}',
                    especialista=a.bastao,
                    descricao=nome,
                    autor=a.bastao,
                    aplicar=a.aplicar,
                )
            except Exception:
                pass
    except ErroValidacaoRegistro as e:
        raise SystemExit(f'erro na abertura da etapa: {e}')
    campos = {
        'nivel': nivel,
        'aberta': agora(),
        'base': a.base,
        'bastao': a.bastao,
        'limites': a.limites,
        'autorizacoes': 'nenhuma ainda',
    }
    secoes = {
        'Aceite': [f'- [ ] {c}' for c in criterios],
        'Fatias': fatias_linhas,
        'Para quem pega o bastão agora': [
            f'bastão está com: {a.bastao}',
            'leia só:',
            f'- {a.pasta}/rodada.md',
            'faça:',
            '- iniciar a primeira fatia',
            'não faça:',
            '- não pule validações de evidência',
            'devolva:',
            'neste arquivo e uma linha no histórico',
        ],
        'Achados abertos': [],
    }
    titulo = f'Rodada {a.id} — {a.meta}'
    gravar(rodada, montar(titulo, campos, secoes, sincronia=obter_sincronia_info(reg)), a.aplicar, 'rodada aberta')
    anexar_historico(hist, f'{agora()} · {a.bastao} · {rotulo(titulo)} · abertura',
                     f'meta: {a.meta}  nível: {nivel}  base: {a.base}', a.aplicar)
    return 0


def cmd_bastao(a):
    caminhos_leia = a.leia or []
    justificativa = getattr(a, 'justificativa_expansao', '') or ''
    if len(caminhos_leia) > MAX_LEIA and not justificativa.strip():
        raise SystemExit(f'erro: "leia só" aceita no máximo {MAX_LEIA} caminhos iniciais sem justificativa de expansão (--justificativa-expansao)')

    rodada, hist, _ = caminhos(a.pasta)
    titulo, campos, secoes = partir(exigir_rodada(rodada))
    de = campos.get('bastao', '?')
    campos['bastao'] = a.para

    linhas = [f'bastão está com: {a.para}', 'leia só:']
    if justificativa.strip():
        linhas.append(f'<!-- expansão justificada: {justificativa.strip()} -->')
    for p in caminhos_leia:
        linhas.append(f'- {p}')
    linhas.append('faça:')
    for f in (a.faca or []):
        linhas.append(f'- {f}')
    if a.nao_faca:
        linhas.append('não faça:')
        for nf in a.nao_faca:
            linhas.append(f'- {nf}')
    linhas.append(f'devolva: {a.devolva}')
    secoes['Para quem pega o bastão agora'] = linhas

    reg = obter_registro_obrigatorio(a.pasta)
    etapa_id = etapa_id_de(titulo)
    reg.passar_bastao(etapa_id, a.para, autor=de, nota=a.nota or '', aplicar=a.aplicar)

    gravar(rodada, montar(titulo, campos, secoes, sincronia=obter_sincronia_info(reg)), a.aplicar, f'bastão passado para {a.para}')
    anexar_historico(hist, f'{agora()} · {de} → {a.para} · {rotulo(titulo)} · passagem',
                     f'passou o bastão para {a.para}' + (f' ({a.nota})' if a.nota else ''), a.aplicar)
    return 0


def cmd_fatia(a):
    reg = obter_registro_obrigatorio(a.pasta)
    rodada, hist, _ = caminhos(a.pasta)
    titulo, campos, secoes = partir(exigir_rodada(rodada))
    fs = fatias_de(secoes)
    etapa_id = etapa_id_de(titulo)

    if a.listar or (not a.add and a.numero is None):
        for f in fs:
            print(f'{f["n"]}. {f["nome"]} — {f["estado"]} {f["resto"]}'.rstrip())
        return 0

    if a.add:
        n = (max([f['n'] for f in fs]) + 1) if fs else 1
        secoes['Fatias'] = secoes.get('Fatias', []) + [f'{n}. {a.add} — pendente']
        try:
            reg.registrar_tarefa(etapa_id, f'fatia_{n}', campos.get('bastao', 'Especialista'),
                                 a.add, autor=campos.get('bastao', 'Gandalf'), aplicar=a.aplicar)
        except ErroValidacaoRegistro as e:
            raise SystemExit(f'erro no registro da tarefa: {e}')
        gravar(rodada, montar(titulo, campos, secoes, sincronia=obter_sincronia_info(reg)), a.aplicar, f'fatia {n} acrescentada')
        return 0

    alvo = next((f for f in fs if f['n'] == a.numero), None)
    if not alvo:
        raise SystemExit(f'erro: fatia {a.numero} não existe')

    if a.fechar:
        # Validação estrita de prova (REV-003, C04, C08)
        prova_limpa = (a.prova or '').strip()
        eh_invalida = (not prova_limpa) or bool(PADRAO_NAO_EXECUTADO.search(prova_limpa)) or bool(PADRAO_PLACEHOLDER.search(prova_limpa))

        if eh_invalida:
            if not a.forcar:
                raise SystemExit(
                    'erro: fechar fatia exige --prova com a saída válida de um comando executado. '
                    'Para registrar exceção justificada, use --forcar com --motivo e --decisao-ref.'
                )
            if not a.motivo or len(a.motivo.strip()) < 10 or not a.decisao_ref or a.decisao_ref.strip() == 'autorizacao_cli':
                raise SystemExit(
                    'erro: --forcar exige --motivo substantivo (mínimo 10 caracteres) e --decisao-ref informando instrução humana do usuário.'
                )

        anteriores = [f for f in fs if f['n'] < a.numero and f['estado'] != 'fechada']
        eh_paralela = ('paralela' in alvo.get('resto', '')) or bool(getattr(a, 'paralelo', False))
        if anteriores and not a.forcar and not eh_paralela:
            nomes = ', '.join(str(f['n']) for f in anteriores)
            raise SystemExit(f'erro: as fatias {nomes} ainda não fecharam; nenhuma fatia começa antes da anterior (use --forcar só com motivo registrado).')

        nova = f'{alvo["n"]}. {alvo["nome"]} — fechada · prova: {a.prova}'
    else:
        eh_paralela_req = bool(getattr(a, 'paralelo', False))
        if eh_paralela_req:
            nivel_rodada = campos.get('nivel', '2')
            if nivel_rodada == '3' and not a.forcar:
                raise SystemExit('erro: fatias paralelas não são permitidas no nível 3 (rigor máximo exige execução sequencial). Use --forcar com justificativa se autorizado.')

            arqs_candidatos = getattr(a, 'arquivos', []) or []
            if not arqs_candidatos:
                raise SystemExit('erro: --paralelo exige --arquivos com lista de caminhos afetados para verificação de disjunção.')

            tarefas = reg.estado().get('etapa_atual', {}).get('tarefas', {})
            for f in fs:
                if f['n'] != a.numero and f['estado'] == 'em andamento':
                    t_info = tarefas.get(f'fatia_{f["n"]}', {})
                    arqs_em_andamento = t_info.get('arquivos', [])
                    if not arqs_em_andamento:
                        m_par = re.search(r'paralela:\s*([^)]+)', f.get('resto', ''))
                        if m_par:
                            arqs_em_andamento = [x.strip() for x in m_par.group(1).split(',') if x.strip()]
                    if not arqs_em_andamento and not a.forcar:
                        raise SystemExit(
                            f'erro: fatia {f["n"]} está em andamento sem lista de arquivos declarada; '
                            f'impossível garantir disjunção para paralelismo seguro com fatia {a.numero}.'
                        )
                    for ca in arqs_candidatos:
                        for cb in arqs_em_andamento:
                            c1 = normalizar_caminho(ca) if normalizar_caminho else ca.strip()
                            c2 = normalizar_caminho(cb) if normalizar_caminho else cb.strip()
                            motivo = conflito(c1, c2) if conflito else ('caminho duplicado' if c1 == c2 else None)
                            if motivo:
                                raise SystemExit(
                                    f'erro: sobreposição de arquivos detectada entre fatia {a.numero} e fatia {f["n"]} em andamento: '
                                    f'"{ca}" conflita com "{cb}" ({motivo}). Execução paralela bloqueada (fail-closed).'
                                )
            arqs_str = ', '.join(arqs_candidatos)
            nova = f'{alvo["n"]}. {alvo["nome"]} — em andamento (paralela: {arqs_str})'
        else:
            pend = [f for f in fs if f['n'] < a.numero and f['estado'] != 'fechada']
            if pend and not a.forcar:
                nomes = ', '.join(str(f['n']) for f in pend)
                raise SystemExit(f'erro: comece pela fatia {nomes[0]}: as fatias {nomes} ainda não fecharam.')
            nova = f'{alvo["n"]}. {alvo["nome"]} — em andamento'

    # Grava no registro estruturado primeiro (REV-002)
    novo_st = 'concluida' if a.fechar else 'em_andamento'
    try:
        if a.fechar and a.forcar and a.motivo:
            reg.registrar_excecao(
                etapa_id=etapa_id,
                excecao_id=f'EXC-FATIA-{a.numero}',
                regra=f'criterio:fatia_{a.numero}',
                motivo=a.motivo,
                referencia_humana=a.decisao_ref,
                autor=campos.get('bastao', 'Gandalf'),
                aplicar=a.aplicar,
            )

        reg.atualizar_tarefa(
            etapa_id,
            f'fatia_{a.numero}',
            novo_st,
            autor=campos.get('bastao', 'Gandalf'),
            arquivos=getattr(a, 'arquivos', None) or None,
            aplicar=a.aplicar
        )

        if a.fechar and a.prova:
            est_etapa = reg.estado().get('etapa_atual') or {}
            criterios_existentes = est_etapa.get('criterios', {})
            alvos = [c for c in criterios_existentes if c in (f'fatia_{a.numero}', f'FATIA-{a.numero}') or (len(fs) == 1 and not c.startswith('C'))]
            if not alvos and f'fatia_{a.numero}' in criterios_existentes:
                alvos = [f'fatia_{a.numero}']

            for c_alvo in alvos:
                reg.registrar_evidencia(
                    etapa_id=etapa_id,
                    criterio_id=c_alvo,
                    comando=f'fatia {a.numero}',
                    exit_code=0 if not eh_invalida else 1,
                    saida=a.prova,
                    verificador=campos.get('bastao', 'Gandalf'),
                    autor=campos.get('bastao', 'Gandalf'),
                    aplicar=a.aplicar,
                )
    except ErroValidacaoRegistro as e:
        raise SystemExit(f'erro ao atualizar fatia no registro: {e}')

    secoes['Fatias'] = [nova if l.strip() == alvo['linha'].strip() else l for l in secoes['Fatias']]
    gravar(rodada, montar(titulo, campos, secoes, sincronia=obter_sincronia_info(reg)), a.aplicar, f'fatia {a.numero} atualizada')
    if a.fechar:
        anexar_historico(hist, f'{agora()} · {campos.get("bastao", "?")} · {rotulo(titulo)} · fatia {a.numero}',
                         f'fez: {alvo["nome"]}  prova: {a.prova}', a.aplicar)
    return 0


def cmd_autorizar(a):
    reg = obter_registro_obrigatorio(a.pasta)
    rodada, hist, _ = caminhos(a.pasta)
    titulo, campos, secoes = partir(exigir_rodada(rodada))
    etapa_id = etapa_id_de(titulo)

    atual = campos.get('autorizacoes', '').strip()
    nova = f'{a.texto} ({a.quem}, {agora("%d/%m %H:%M")})'
    campos['autorizacoes'] = nova if atual in ('', 'nenhuma ainda') else f'{atual}; {nova}'

    try:
        reg.registrar_decisao(
            etapa_id=etapa_id,
            decisao_id=f'DEC-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            quem=a.quem,
            referencia=a.texto,
            acao='autorizacao',
            autor=a.quem,
            aplicar=a.aplicar,
        )
    except ErroValidacaoRegistro as e:
        raise SystemExit(f'erro no registro de autorização: {e}')

    gravar(rodada, montar(titulo, campos, secoes, sincronia=obter_sincronia_info(reg)), a.aplicar, 'autorização registrada')
    anexar_historico(hist, f'{agora()} · {a.quem} · {rotulo(titulo)} · autorização',
                     f'autorizou: {a.texto}', a.aplicar)
    return 0


def cmd_achado(a):
    reg = obter_registro_obrigatorio(a.pasta)
    rodada, _, _ = caminhos(a.pasta)
    titulo, campos, secoes = partir(exigir_rodada(rodada))
    etapa_id = etapa_id_de(titulo)
    linhas = [l for l in secoes.get('Achados abertos', []) if l.strip()]
    raw_estado = (getattr(a, 'estado', None) or 'corrigido').strip().lower()
    estado_normalizado = MAPA_SINONIMOS_ESTADO_ACHADO.get(raw_estado, raw_estado)

    alvo_id = a.fechar
    if not alvo_id and getattr(a, 'id', None) and not getattr(a, 'texto', None):
        alvo_id = a.id

    if alvo_id:
        if estado_normalizado not in ESTADOS_ACHADO_VALIDOS:
            raise SystemExit(f'erro: estado inválido "{a.estado}" (use {", ".join(ESTADOS_ACHADO_VALIDOS)})')

        achou = False
        novas = []
        for l in linhas:
            if l.strip().startswith(f'- {alvo_id} ') or l.strip().startswith(f'- {alvo_id}·'):
                achou = True
                novas.append(re.sub(r'·\s*(aberto|contestado|corrigido|excepcionado)\s*$', f'· {estado_normalizado}', l.rstrip()))
            else:
                novas.append(l)
        if not achou:
            raise SystemExit(f'erro: achado {alvo_id} não encontrado')

        try:
            reg.atualizar_achado(etapa_id, alvo_id, estado_normalizado, justificativa=a.justificativa or '', aplicar=a.aplicar)
        except ErroValidacaoRegistro as e:
            raise SystemExit(f'erro ao atualizar achado no registro: {e}')

        secoes['Achados abertos'] = novas
    else:
        if a.severidade not in SEVERIDADES:
            raise SystemExit(f'erro: severidade inválida (use {", ".join(SEVERIDADES)})')
        ident = a.id or f'REV-{len(linhas) + 1:03d}'
        try:
            reg.registrar_achado(etapa_id, ident, a.severidade, a.onde, a.texto, autor='Revisor', aplicar=a.aplicar)
        except ErroValidacaoRegistro as e:
            raise SystemExit(f'erro ao registrar achado no registro: {e}')

        linhas.append(f'- {ident} · {a.severidade} · {a.onde} · {a.texto} · aberto')
        secoes['Achados abertos'] = linhas

    gravar(rodada, montar(titulo, campos, secoes, sincronia=obter_sincronia_info(reg)), a.aplicar, 'achados atualizados')
    return 0


def cmd_evidencia(a):
    """Registra evidência formal para critério no registro estruturado (REV-002)."""
    reg = obter_registro_obrigatorio(a.pasta)
    etapa_id = a.etapa or reg.estado().get('etapa_atual', {}).get('id')
    if not etapa_id:
        raise SystemExit('erro: nenhuma etapa ativa encontrada no registro.')

    try:
        reg.registrar_evidencia(
            etapa_id=etapa_id,
            criterio_id=a.criterio,
            comando=a.comando,
            exit_code=a.exit_code,
            saida=a.saida,
            verificador=a.verificador,
            ambiente=a.ambiente,
            versao_entrega=a.versao or '',
            autor=a.verificador,
            aplicar=a.aplicar,
        )
        print(f'evidência registrada para critério {a.criterio} na etapa {etapa_id}.')
    except ErroValidacaoRegistro as e:
        raise SystemExit(f'erro ao registrar evidência: {e}')
    return 0


def cmd_parecer(a):
    """Registra parecer independente no registro estruturado (REV-002, REV-005)."""
    reg = obter_registro_obrigatorio(a.pasta)
    etapa_id = a.etapa or reg.estado().get('etapa_atual', {}).get('id')
    if not etapa_id:
        raise SystemExit('erro: nenhuma etapa ativa encontrada no registro.')

    if getattr(a, 'sincronizar_git', False):
        p_pasta = Path(a.pasta).resolve()
        p_canonico = p_pasta if p_pasta.name != 'sociedade' else p_pasta.parent
        commit_git = obter_commit_git_head(p_canonico) or obter_commit_git_head(p_pasta)
        if not commit_git:
            raise SystemExit('erro: --sincronizar-git exige que o projeto seja um repositório Git com ao menos um commit.')
        a.versao = commit_git

    if not getattr(a, 'versao', None):
        raise SystemExit('erro: subcomando parecer exige --versao ou --sincronizar-git.')

    # Se a etapa ativa estiver com versão placeholder, atualiza atomicamente para a versão examinada
    est_atual = reg.estado().get('etapa_atual') or {}
    if est_atual.get('versao_atual') in ('<preencher>', '', None):
        try:
            # A versão registrada aqui é a própria versão examinada pelo parecer: não há mudança pós-revisão a classificar.
            reg.registrar_versao(etapa_id, a.versao, impacto='sem_alto', autor=a.revisor, aplicar=a.aplicar)
        except Exception:
            pass

    implementadores = []
    for imp in a.implementadores:
        if ':' in imp:
            parts = imp.split(':', 1)
            implementadores.append({'agente': parts[0].strip(), 'fornecedor': parts[1].strip()})
        else:
            ag_nome = imp.strip()
            forn = 'desconhecido'
            try:
                if reg.perfil:
                    forn_p = reg.perfil.obter_fornecedor(ag_nome)
                    if forn_p:
                        forn = forn_p
            except Exception:
                pass
            implementadores.append({'agente': ag_nome, 'fornecedor': forn})

    criterios_verificados = {c: True for c in a.criterio_ok}
    for c in a.criterio_pendente:
        criterios_verificados[c] = False

    try:
        pid = f'PAR-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        reg.registrar_parecer(
            etapa_id=etapa_id,
            parecer_id=pid,
            revisor=a.revisor,
            fornecedor_revisor=a.fornecedor,
            implementadores=implementadores,
            versao_examinada=a.versao,
            veredito=a.veredito,
            criterios_verificados=criterios_verificados,
            achados_referenciados=a.achado or [],
            lacunas=a.lacuna or [],
            autor=a.revisor,
            aplicar=a.aplicar,
            nivel_independencia=getattr(a, 'nivel_independencia', 'A') or 'A',
            justificativa_independencia=getattr(a, 'justificativa_independencia', '') or '',
            perfil=getattr(a, 'perfil', None) or reg.perfil,
        )
        print(f'parecer {pid} ({a.veredito}) registrado para etapa {etapa_id}.')
    except ErroValidacaoRegistro as e:
        raise SystemExit(f'erro ao registrar parecer: {e}')
    return 0


def cmd_excecao(a):
    """Registra exceção estruturada no registro (REV-003, C08)."""
    reg = obter_registro_obrigatorio(a.pasta)
    etapa_id = a.etapa or reg.estado().get('etapa_atual', {}).get('id')
    if not etapa_id:
        raise SystemExit('erro: nenhuma etapa ativa encontrada no registro.')

    try:
        eid = f'EXC-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        reg.registrar_excecao(
            etapa_id=etapa_id,
            excecao_id=eid,
            regra=a.regra,
            motivo=a.motivo,
            referencia_humana=a.decisao_ref,
            alcance=a.alcance or 'etapa',
            autor='Gandalf',
            aplicar=a.aplicar,
        )
        print(f'exceção {eid} registrada para regra {a.regra} na etapa {etapa_id}.')
    except ErroValidacaoRegistro as e:
        raise SystemExit(f'erro ao registrar exceção: {e}')
    return 0


def cmd_encerrar(a):
    reg = obter_registro_obrigatorio(a.pasta)
    rodada, hist, _ = caminhos(a.pasta)
    texto = exigir_rodada(rodada)
    titulo, campos, secoes = partir(texto)
    fs = fatias_de(secoes)
    abertas = [f for f in fs if f['estado'] != 'fechada']
    etapa_id = etapa_id_de(titulo)

    if getattr(a, 'sincronizar_git', False):
        p_pasta = Path(a.pasta).resolve()
        p_canonico = p_pasta if p_pasta.name != 'sociedade' else p_pasta.parent
        commit_git = obter_commit_git_head(p_canonico) or obter_commit_git_head(p_pasta)
        if not commit_git:
            raise SystemExit('erro: --sincronizar-git exige que o projeto seja um repositório Git com ao menos um commit.')
        try:
            # Q145: a versão final chega sem classificação; mudança pós-revisão bloqueia até alguém classificar.
            reg.registrar_versao(etapa_id, commit_git, impacto='desconhecido', autor=campos.get('bastao', 'Gandalf'), aplicar=a.aplicar)
            campos['base'] = commit_git
        except Exception as e:
            raise SystemExit(f'erro ao sincronizar versão no encerramento: {e}')

    # C05: Bloqueadores abertos e contestados impedem encerramento normal
    bloqueadores = [l for l in secoes.get('Achados abertos', [])
                    if 'bloqueador' in l and (l.rstrip().endswith('aberto') or l.rstrip().endswith('contestado'))]

    if (abertas or bloqueadores) and not a.forcar:
        det = []
        if abertas:
            det.append('fatias não fechadas: ' + ', '.join(str(f['n']) for f in abertas))
        if bloqueadores:
            det.append(f'achados bloqueadores abertos ou contestados: {len(bloqueadores)}')
        raise SystemExit('erro: ' + '; '.join(det) + '. Use --forcar só com motivo registrado e autorização humana.')

    if a.forcar and (abertas or bloqueadores):
        if not a.motivo or len(a.motivo.strip()) < 10 or not a.decisao_ref or a.decisao_ref.strip() == 'autorizacao_cli':
            raise SystemExit(
                'erro: --forcar isolado não é permitido; exceção exige --motivo substantivo (mínimo 10 caracteres) e --decisao-ref com a decisão humana do usuário.'
            )
        try:
            regra_exc = a.regra or ('achados_bloqueadores' if bloqueadores else 'criterios_gerais')
            reg.registrar_excecao(
                etapa_id=etapa_id,
                excecao_id=f'EXC-{etapa_id}',
                regra=regra_exc,
                motivo=a.motivo,
                referencia_humana=a.decisao_ref,
                autor=campos.get('bastao', 'Gandalf'),
                aplicar=a.aplicar,
            )
        except ErroValidacaoRegistro as e:
            raise SystemExit(f'erro ao registrar exceção de encerramento: {e}')

    resumo = a.resumo or f'{len(fs)} fatias fechadas'

    # VALIDA E GRAVA PRIMEIRO O REGISTRO ESTRUTURADO (REV-002, REV-009)
    # Se falhar, NÃO escreve em historico.md e NÃO remove rodada.md
    try:
        reg.encerrar_etapa(etapa_id, resumo, autor=campos.get('bastao', 'Gandalf'), aplicar=a.aplicar)
    except (ErroValidacaoRegistro, ErroConcorrenciaRegistro) as e:
        raise SystemExit(f'erro no encerramento da etapa: {e}')

    # Somente após sucesso do registro, atualiza arquivos secundários e projeções
    anexar_historico(hist, f'{agora()} · {campos.get("bastao", "?")} · {rotulo(titulo)} · encerramento',
                     f'resultado: {resumo}', a.aplicar)

    andamento_md = Path(a.pasta) / 'andamento.md'
    if andamento_md.is_file() and a.aplicar:
        try:
            reg.projetar_andamento(andamento_md, aplicar=True)
        except Exception:
            pass

    if a.aplicar:
        rodada.unlink()
        print(f'rodada encerrada e removida: {rodada}')
    else:
        print(f'[simulação] encerraria e removeria {rodada}')

    aval = Path(a.pasta) / 'avaliacao.md'
    if not aval.is_file():
        modelo = ('# Avaliação das rodadas\n\n'
                  '<!-- Uma entrada por rodada. A linha de cota é preenchida à mão pelo usuário; '
                  'nenhum agente estima consumo. -->\n')
        gravar(aval, modelo, a.aplicar, 'avaliação criada')
    entrada = (f'\n## {titulo}\n'
               f'- deu certo: <preencher>\n- deu errado: <preencher>\n- houve retrabalho: <sim|não>\n'
               f'- mudar no método: <preencher ou "nada">\n- cota usada (preenchido pelo usuário): <opcional>\n')
    if a.aplicar:
        aval.write_text(ler(aval).rstrip('\n') + '\n' + entrada, encoding='utf-8')
        print(f'avaliação: {aval}')
    else:
        print(f'[simulação] acrescentaria a entrada de avaliação em {aval}')
    return 0


def cmd_lint(a):
    rodada, hist, _ = caminhos(a.pasta)
    problemas, avisos = [], []
    if not rodada.is_file():
        print(f'não há rodada aberta em {rodada} (isso é válido: fora de rodada a Sociedade fica calada)')
        return 0
    bruto = ler(rodada)
    tam = len(bruto.encode('utf-8'))
    if tam > a.teto:
        problemas.append(f'estado vivo com {tam} bytes, acima do teto de {a.teto}: encurte ou mova para o histórico')
    titulo, campos, secoes = partir(bruto)
    if not titulo.startswith('Rodada '):
        problemas.append('título deve começar com "Rodada <ID> — <meta>"')
    for c in ('nivel', 'aberta', 'base', 'bastao'):
        if not campos.get(c):
            problemas.append(f'campo obrigatório ausente ou vazio: {c}')
    if campos.get('nivel') and campos['nivel'] not in NIVEIS:
        problemas.append(f'nível inválido: {campos["nivel"]}')
    for s in SECOES:
        if s not in secoes:
            problemas.append(f'seção obrigatória ausente: {s}')
    bloco = secoes.get('Para quem pega o bastão agora', [])
    leia = [l for l in bloco if l.strip().startswith('- ')]
    dentro, contados, expansao_justificada = False, 0, False
    for l in bloco:
        t = l.strip()
        if 'expansão justificada:' in t:
            expansao_justificada = True
        if t.startswith('leia só'):
            dentro = True
            continue
        if t.startswith(('faça', 'não faça', 'devolva')):
            dentro = False
        if dentro and t.startswith('- '):
            contados += 1
    if contados > MAX_LEIA and not expansao_justificada:
        problemas.append(f'"leia só" com {contados} caminhos, acima de {MAX_LEIA} (exige justificativa de expansão)')
    if leia and not any(l.strip().startswith('devolva:') for l in bloco):
        problemas.append('"Para quem pega o bastão agora" sem a linha "devolva:"')
    fs = fatias_de(secoes)
    if not fs:
        problemas.append('nenhuma fatia reconhecida (formato: "1. nome — pendente")')
    vistos = set()
    for f in fs:
        if f['n'] in vistos:
            problemas.append(f'fatia {f["n"]} repetida')
        vistos.add(f['n'])
        if f['estado'] == 'fechada' and 'prova:' not in f['resto']:
            problemas.append(f'fatia {f["n"]} fechada sem prova executada')
    andamento = [f for f in fs if f['estado'] == 'em andamento']
    if len(andamento) > 1:
        problemas.append('mais de uma fatia em andamento: uma por vez')
    for f in andamento:
        atras = [g for g in fs if g['n'] < f['n'] and g['estado'] != 'fechada']
        if atras:
            problemas.append(f'fatia {f["n"]} em andamento com as fatias '
                             f'{", ".join(str(g["n"]) for g in atras)} não fechadas')

    # C11 e REV-013: Detecção rigorosa de medições algorítmicas de consumo por agentes
    for linha in bruto.splitlines():
        if MEDICAO_SUSPEITA.search(linha):
            if linha.strip().startswith('<!--'):
                continue
            if re.search(r'\d', linha):
                if PADRAO_AVISO_MANUAL_COTA.match(linha):
                    continue
                problemas.append(f'medição de consumo no estado vivo ("{linha.strip()[:40]}"): nenhum agente estima ou relata gasto')
                break
            else:
                if 'nenhum agente estima' in linha.lower() or 'não medir' in linha.lower():
                    continue
                problemas.append(f'medição de consumo no estado vivo ("{linha.strip()[:40]}"): nenhum agente estima ou relata gasto')
                break

    andamento_md = Path(a.pasta) / 'andamento.md'
    if andamento_md.is_file():
        reg = obter_registro_opcional(a.pasta)
        if reg:
            try:
                sinc, msg = reg.verificar_sincronia_projecao(andamento_md)
                if not sinc:
                    avisos.append(f'projeção em andamento.md desatualizada ({msg}): execute subcomando "projetar"')
            except Exception:
                pass

    ph = PLACEHOLDER.findall(bruto)
    if ph:
        avisos.append(f'{len(ph)} campo(s) por preencher: {", ".join(sorted(set(ph))[:4])}')
    if hist.is_file() and len(ler(hist).encode('utf-8')) > TETO_HISTORICO:
        avisos.append('histórico acima do teto: rode "rotacionar" (nada é apagado, só arquivado)')
    for p in problemas:
        print(f'problema: {p}')
    for v in avisos:
        print(f'aviso: {v}')
    if not problemas:
        print(f'rodada válida ({tam} bytes, {len(fs)} fatias, bastão com {campos.get("bastao", "?")})')
    return 1 if problemas else 0


def cmd_colar(a):
    rodada, _, _ = caminhos(a.pasta)
    titulo, campos, secoes = partir(exigir_rodada(rodada))
    fs = fatias_de(secoes)
    atual = next((f for f in fs if f['estado'] == 'em andamento'), None) or \
        next((f for f in fs if f['estado'] == 'pendente'), None)

    reg = obter_registro_opcional(a.pasta)
    rev_info = f' · rev {reg.revisao}' if reg else ''

    linhas = [f'[Sociedade do Código] {titulo}{rev_info}',
              f'nível {campos.get("nivel", "?")} · base {campos.get("base", "?")} · '
              f'bastão com {campos.get("bastao", "?")}',
              f'limites: {campos.get("limites", "—")}',
              f'autorizações: {campos.get("autorizacoes", "nenhuma ainda")}', '']
    fechadas = [f for f in fs if f['estado'] == 'fechada']
    if fechadas:
        linhas.append('já fechado: ' + '; '.join(f'{f["n"]}. {f["nome"]}' for f in fechadas))
    if atual:
        linhas.append(f'fatia atual: {atual["n"]}. {atual["nome"]}')
    linhas.append('')
    linhas += [l for l in secoes.get('Para quem pega o bastão agora', []) if l.strip()]
    abertos = [l for l in secoes.get('Achados abertos', []) if l.strip().endswith('aberto') or l.strip().endswith('contestado')]
    if abertos:
        linhas += ['', 'achados abertos ou contestados:'] + abertos
    bloco = '\n'.join(linhas).strip() + '\n'
    print(bloco)
    n = len(bloco.encode('utf-8'))
    if n > a.teto_colar:
        print(f'\n[aviso] bloco com {n} bytes, acima de {a.teto_colar}: encurte "leia só" e "faça".',
              file=sys.stderr)
    return 0


def cmd_rotacionar(a):
    _, hist, pasta_hist = caminhos(a.pasta)
    if not hist.is_file():
        print(f'nada a rotacionar: {hist} não existe')
        return 0
    texto = ler(hist)
    partes = re.split(r'\n(?=## )', texto)
    cabeca = [partes[0]] if partes and not partes[0].startswith('## ') else []
    entradas = partes[1:] if cabeca else partes
    mes_atual = agora('%m/%Y')
    manter, arquivar = [], {}
    for b in entradas:
        m = re.match(r'## (\d{2})/(\d{2})/(\d{4})', b)
        chave = f'{m.group(3)}-{m.group(2)}' if m else None
        if m and f'{m.group(2)}/{m.group(3)}' != mes_atual:
            arquivar.setdefault(chave, []).append(b)
        else:
            manter.append(b)
    if not arquivar:
        print('nada a arquivar (só há entradas do mês corrente)')
        return 0
    for chave, blocos_mes in sorted(arquivar.items()):
        destino = pasta_hist / f'{chave}.md'
        anterior = ler(destino)
        conteudo = (anterior.rstrip('\n') + '\n\n' if anterior.strip() else f'# Histórico {chave}\n\n')
        gravar(destino, conteudo + ''.join(blocos_mes).rstrip('\n') + '\n', a.aplicar, f'arquivado {chave}')
    gravar(hist, (''.join(cabeca) + ''.join(manter)).rstrip('\n') + '\n', a.aplicar, 'histórico enxugado')
    print('nada foi apagado: as entradas antigas estão em ' + str(pasta_hist))
    return 0


def cmd_resumo(a):
    """Exporta ou importa resumos entre projetos (agregação de contagens) (REV-015, C10)."""
    reg = obter_registro_obrigatorio(a.pasta)

    if a.exportar:
        try:
            res = reg.exportar_resumo_etapa(a.exportar)
            txt = json.dumps(res, indent=2, ensure_ascii=False)
            if a.destino:
                Path(a.destino).write_text(txt, encoding='utf-8')
                print(f'resumo da etapa {a.exportar} exportado para {a.destino}.')
            else:
                print(txt)
        except ErroValidacaoRegistro as e:
            raise SystemExit(f'erro ao exportar resumo: {e}')
        return 0

    if a.importar:
        origem = Path(a.importar)
        if not origem.is_file():
            raise SystemExit(f'erro: arquivo de resumo {origem} não encontrado.')
        try:
            res_dados = json.loads(origem.read_text(encoding='utf-8'))
            reg.importar_resumo_projeto(res_dados, aplicar=a.aplicar)
            print(f'resumo de {origem} importado com sucesso.')
        except Exception as e:
            raise SystemExit(f'erro ao importar resumo: {e}')
        return 0

    raise SystemExit('erro: informe --exportar <etapa_id> ou --importar <arquivo.json>')


def cmd_migrar(a):
    """Migra estado legado para registro.json (REV-001, REV-006)."""
    origem = Path(a.origem)
    if not origem.is_file():
        raise SystemExit(f'erro: arquivo de origem {origem} não encontrado.')

    reg = obter_registro_opcional(a.pasta)
    if reg is None:
        p_canonico = Path(a.pasta).resolve().parent
        proj_id = p_canonico.name if p_canonico.name else 'projeto'
        reg = Registro.inicializar(a.pasta, projeto_id=proj_id, caminho_canonico=str(p_canonico), aplicar=a.aplicar)

    migrado = migrar_legado_para_registro(reg, origem, aplicar=a.aplicar)
    if migrado:
        print(f'migrado legado {migrado["id"]} com {len(migrado["fatias"])} fatias.')
    else:
        print('migração não gerou alterações.')
    return 0


def cmd_projetar(a):
    """Atualiza a projeção textual do andamento da etapa no markdown autoral."""
    reg = obter_registro_obrigatorio(a.pasta)
    destino = Path(a.destino) if getattr(a, 'destino', None) else Path(a.pasta) / 'andamento.md'
    reg.projetar_andamento(destino, aplicar=a.aplicar)
    print(f'projeção atualizada em {destino}')
    return 0


def cmd_sincronizar(a):
    """Verifica se a projeção em markdown está em sincronia com o registro.json."""
    reg = obter_registro_obrigatorio(a.pasta)
    if getattr(a, 'destino', None):
        destinos = [Path(a.destino)]
    else:
        p_pasta = Path(a.pasta)
        destinos = [p_pasta / 'andamento.md']
        p_rodada = p_pasta / 'rodada.md'
        if p_rodada.is_file():
            destinos.append(p_rodada)

    tudo_ok = True
    encontrou_algum = False
    for destino in destinos:
        if not destino.is_file():
            if getattr(a, 'destino', None):
                print(f'arquivo de projeção {destino} inexistente')
                return 1
            continue
        encontrou_algum = True
        sinc, msg = reg.verificar_sincronia_projecao(destino)
        status_str = "sincronizado" if sinc else "desatualizado"
        print(f'sincronia da projeção {destino}: {status_str} ({msg})')
        if not sinc:
            tudo_ok = False

    if not encontrou_algum:
        print(f'nenhum arquivo de projeção encontrado em {a.pasta}')
        return 1
    return 0 if tudo_ok else 1


def cmd_sincronizar_versao(a):
    """Atualiza a versão atual no registro.json de forma atômica sob lock (elimina scripts ad-hoc)."""
    reg = obter_registro_obrigatorio(a.pasta)
    rodada, _, _ = caminhos(a.pasta)
    texto = ler(rodada)
    titulo, campos, secoes = partir(texto) if texto else ('', {}, {})
    etapa_id = getattr(a, 'etapa', None) or etapa_id_de(titulo)
    if not etapa_id or etapa_id == 'RODADA':
        est = reg.estado()
        etapa_atual = est.get('etapa_atual')
        if etapa_atual:
            etapa_id = etapa_atual['id']
        else:
            raise SystemExit('erro: nenhuma etapa ativa encontrada no registro.')

    versao = getattr(a, 'versao', None)
    if not versao or versao == '<preencher>':
        p_pasta = Path(a.pasta).resolve()
        p_canonico = p_pasta if p_pasta.name != 'sociedade' else p_pasta.parent
        versao = obter_commit_git_head(p_canonico) or obter_commit_git_head(p_pasta)
        if not versao:
            raise SystemExit('erro: --versao não fornecida e não foi possível obter commit Git HEAD.')

    impacto = getattr(a, 'impacto', None) or 'sem_alto'
    autor = campos.get('bastao', 'Gandalf') if campos else 'Gandalf'

    try:
        reg.registrar_versao(etapa_id, versao, impacto=impacto, autor=autor, aplicar=a.aplicar)
        if texto:
            campos['base'] = versao
            gravar(rodada, montar(titulo, campos, secoes, sincronia=obter_sincronia_info(reg)), a.aplicar, 'versão sincronizada em rodada.md')
        print(f'versão da etapa {etapa_id} sincronizada para {versao} (impacto: {impacto}).')
    except ErroValidacaoRegistro as e:
        raise SystemExit(f'erro ao sincronizar versão no registro: {e}')
    return 0


def cmd_calibrar(a):
    """Executa a calibração retrospectiva da regra dos 5 fatores de rigor (Q22)."""
    p_pasta = Path(getattr(a, 'pasta', PASTA_PADRAO))
    p_reg = p_pasta / 'registro.json'
    if not p_reg.is_file():
        print(f'ERRO: Arquivo de registro não encontrado em {p_reg}', file=sys.stderr)
        return 1

    try:
        from sc_calibrar_gatilho import calibrar_gatilho_rigor, formatar_relatorio_texto
    except ImportError:
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from sc_calibrar_gatilho import calibrar_gatilho_rigor, formatar_relatorio_texto
        except Exception as e:
            print(f'ERRO ao importar módulo de calibração: {e}', file=sys.stderr)
            return 1

    if carregar_dados_registro is not None:
        dados = carregar_dados_registro(p_reg)
    else:
        dados = json.loads(p_reg.read_text(encoding='utf-8'))

    res = calibrar_gatilho_rigor(
        dados,
        limiar_fatores=getattr(a, 'limiar_fatores', 2),
        etapas_filtro=getattr(a, 'etapas', None)
    )

    fmt = getattr(a, 'formato', 'texto')
    if fmt == 'json':
        saida = json.dumps(res, indent=2, ensure_ascii=False)
    else:
        saida = formatar_relatorio_texto(res)

    if getattr(a, 'saida', None):
        p_dest = Path(a.saida)
        p_dest.parent.mkdir(parents=True, exist_ok=True)
        p_dest.write_text(saida, encoding='utf-8')
        print(f'Relatório de calibração gravado em: {a.saida}')
    else:
        print(saida)

    return 0 if res.get('sucesso', False) else 1


def cmd_worktree(a):
    try:
        from sc_worktree import criar_worktree, listar_worktrees, remover_worktree, ErroWorktree
    except ImportError:
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from sc_worktree import criar_worktree, listar_worktrees, remover_worktree, ErroWorktree
        except Exception as e:
            print(f'ERRO ao carregar sc_worktree: {e}', file=sys.stderr)
            return 1

    p_base = Path(a.pasta_base) if getattr(a, 'pasta_base', None) else None
    p_raiz = Path(a.raiz) if getattr(a, 'raiz', None) else None

    try:
        if a.subcmd == 'criar':
            res = criar_worktree(
                etapa=a.etapa,
                branch=getattr(a, 'branch', None),
                base=getattr(a, 'base', None),
                projeto=getattr(a, 'projeto', None),
                pasta_base=p_base,
                pasta_raiz=p_raiz
            )
            print(f"Worktree criado com sucesso em: {res['caminho']} (branch: {res['branch']})")
            return 0
        elif a.subcmd == 'listar':
            wts = listar_worktrees(projeto=getattr(a, 'projeto', None), pasta_base=p_base, pasta_raiz=p_raiz)
            if not wts:
                print("Nenhum worktree encontrado.")
                return 0
            print("Worktrees encontrados:")
            for w in wts:
                padrao_tag = " [padrão]" if w.get('padrao') else ""
                print(f"  - Etapa: {w['etapa']} | Branch: {w['branch']} | Caminho: {w['caminho']}{padrao_tag}")
            return 0
        elif a.subcmd == 'remover':
            res = remover_worktree(
                etapa=a.etapa,
                forcar=getattr(a, 'forcar', False),
                projeto=getattr(a, 'projeto', None),
                pasta_base=p_base,
                pasta_raiz=p_raiz
            )
            print(f"Worktree da etapa '{res['etapa']}' removido com sucesso: {res['caminho']}")
            return 0
    except ErroWorktree as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1

# ---------- papel e matriz de troca (M2, R1-R3) ----------

class ErroTroca(Exception):
    """Troca de papel recusada por dado ausente, ambíguo ou por regra invariante."""


def _norm(texto):
    return (texto or '').strip().lower()


def resolver_destino(perfil, papel, para=None, fornecedor=None, modelo=None, esforco=None):
    """Plataforma, fornecedor, modelo e esforço do destino, sem nenhum valor fixo no código (M5, Q61).

    Sem --para, mantém a plataforma atual do papel (troca só de estado ou esforço). Com --para, o
    fornecedor vem de --fornecedor ou das linhas do perfil que já usam essa plataforma (casamento
    exato); o modelo vem de --modelo ou do modelo atual, se o fornecedor não mudar.
    """
    atual = perfil.obter_papel(papel) or {}
    if not para:
        if not atual:
            raise ErroTroca(f'Papel "{papel}" não encontrado no perfil.')
        return (atual.get('plataforma'), fornecedor or atual.get('fornecedor'),
                modelo or atual.get('modelo'), esforco or atual.get('esforco'))
    forn = fornecedor
    if not forn:
        fornecedores = {p['fornecedor'] for p in perfil.listar_papeis()
                        if _norm(p.get('plataforma')) == _norm(para) and p.get('fornecedor')}
        if len(fornecedores) > 1:
            raise ErroTroca(f'A plataforma "{para}" aparece no perfil com fornecedores diferentes: {sorted(fornecedores)}. Informe --fornecedor.')
        if not fornecedores:
            raise ErroTroca(f'A plataforma "{para}" não está no perfil. Informe --fornecedor e --modelo.')
        forn = fornecedores.pop()
    # Modelo ausente (None) é cobrado depois das regras invariantes, para a violação aparecer primeiro.
    mod = modelo or (atual.get('modelo') if _norm(forn) == _norm(atual.get('fornecedor')) else None)
    return para, forn, mod, esforco or atual.get('esforco') or 'padrão'


def validar_regras_troca(papel, novo_estado, nova_plataforma, novo_fornecedor, perfil, reg, decisao_ref=None):
    """Valida as regras invariantes R1-R3. Retorna (ok, lista_erros)."""
    if novo_estado == 'espera':
        return True, []

    erros = []
    papel_norm = _norm(papel)
    novo_forn = _norm(novo_fornecedor)

    # R1: arquiteto e revisor nunca na mesma plataforma de assinatura ao mesmo tempo
    if papel_norm in ('arquiteto', 'revisor'):
        outro_nome = 'revisor' if papel_norm == 'arquiteto' else 'arquiteto'
        outro = perfil.obter_papel(outro_nome) if perfil else None
        if outro and outro.get('estado') == 'ativo':
            mesma_plat = _norm(outro.get('plataforma')) == _norm(nova_plataforma) and nova_plataforma
            mesmo_forn = _norm(outro.get('fornecedor')) == novo_forn and novo_forn
            if mesma_plat or mesmo_forn:
                erros.append(
                    f"Violação de R1: Arquiteto e revisor não podem ficar na mesma plataforma ao mesmo tempo. "
                    f"'{outro_nome.capitalize()}' já está ativo na plataforma '{outro.get('plataforma')}' (fornecedor '{outro.get('fornecedor')}')."
                )

    # R2: o revisor nunca é do fornecedor de algum implementador da etapa aberta (D03: sem lista vazia)
    if papel_norm == 'revisor':
        etapa_atual = (reg.estado().get('etapa_atual') or {}) if reg else {}
        if etapa_atual and etapa_atual.get('estado') == 'aberta':
            impls = reg.implementadores_da_etapa(etapa_atual.get('id'), perfil=perfil)
            if not impls:
                erros.append('Violação de R2: a etapa aberta não tem implementador registrado; não é possível conferir o fornecedor.')
            for impl in impls:
                if not impl['fornecedor']:
                    erros.append(
                        f"Violação de R2: fornecedor desconhecido para o implementador '{impl['agente']}'. "
                        f"Declare-o no perfil antes de trocar o revisor (A2-P01)."
                    )
                elif _norm(impl['fornecedor']) == novo_forn:
                    erros.append(
                        f"Violação de R2: O revisor ('{novo_fornecedor}') não pode pertencer ao mesmo fornecedor "
                        f"do implementador da etapa aberta ('{impl['agente']}': '{impl['fornecedor']}')."
                    )

    # R3: execução só com Google, salvo decisão registrada específica (D04)
    if papel_norm in ('execucao', 'coordenador') and novo_forn != 'google':
        decisao = None
        if decisao_ref and reg:
            for ev in reg.dados.get('eventos', []):
                d = ev.get('dados', {})
                if ev.get('tipo') == 'decisao_registrada' and decisao_ref in (d.get('decisao_id'), d.get('referencia')):
                    decisao = d
        if not decisao:
            erros.append(
                f"Violação de R3: Execução fora do Google ('{novo_fornecedor}') requer decisão registrada no registro.json. "
                f"Registre a decisão e informe --decisao-ref com o identificador dela."
            )
        elif 'execu' not in _norm(decisao.get('acao')):
            erros.append(
                f"Violação de R3: a decisão '{decisao_ref}' não trata de execução fora do Google (ação: '{decisao.get('acao')}')."
            )

    return (len(erros) == 0, erros)


def formatar_mensagem_passagem_troca(papel, plataforma, fornecedor, modelo, esforco, estado, motivo, data_str):
    return f"""======================================================================
MENSAGEM DE PASSAGEM — TROCA DE PAPEL (M2, Q40)
======================================================================
- Papel: {papel.capitalize()}
- Plataforma: {plataforma}
- Fornecedor: {fornecedor}
- Modelo: {modelo}
- Esforço: {esforco}
- Estado: {estado}
- Motivo: {motivo}
- Data: {data_str}
----------------------------------------------------------------------
Instruções para o próximo agente:
1. Leia o estado em sociedade/rodada.md e o histórico em sociedade/historico.md.
2. Respeite as barreiras e conectores definidos no perfil.md (Q109).
3. O revisor não corrige o que revisa. Nenhuma fatia começa sem prova da anterior.
======================================================================"""


def cmd_papel_status(a):
    p_soc = Path(a.pasta) if getattr(a, 'pasta', None) else localizar_sociedade_canonica()
    c_perfil = getattr(a, 'perfil', None)

    try:
        from sc_perfil import carregar_perfil
        perfil = carregar_perfil(c_perfil or p_soc)
    except Exception as e:
        print(f"ERRO ao carregar perfil: {e}", file=sys.stderr)
        return 1

    reg = None
    try:
        reg = obter_registro_obrigatorio(p_soc)
    except Exception:
        pass

    print("=== MATRIZ DE PAPÉIS DO PROJETO ===")
    for p in perfil.listar_papeis():
        st = p['estado'].upper()
        print(f"- [{st:7s}] {p['papel']}: {p['nome']} | Plataforma: {p['plataforma']} | Fornecedor: {p['fornecedor']} | Modelo: {p['modelo']} (esforço: {p['esforco']})")

    print("\n=== EQUIPE ATIVA (Q95) ===")
    for p in perfil.equipe_ativa():
        print(f"- {p['papel']}: {p['nome']} ({p['plataforma']}, {p['fornecedor']})")

    if perfil.conectores:
        print("\n=== CONECTORES POR PAPEL (Q109) ===")
        for c in perfil.conectores:
            print(f"- {c['papel']}: {c['conectores']} [Ambiente: {c['ambiente']}]")

    if reg:
        trocas = [e for e in reg.dados.get('eventos', []) if e.get('tipo') == 'papel_trocado']
        if trocas:
            print("\n=== HISTÓRICO DE TROCAS DE PAPEL (registro.json) ===")
            for tr in trocas[-5:]:
                d = tr.get('dados', {})
                print(f"- {d.get('desde', '')}: {d.get('papel')} -> {d.get('plataforma')} ({d.get('estado')}) · Motivo: {d.get('motivo')}")

    return 0


def cmd_papel_trocar(a):
    p_soc = Path(a.pasta) if getattr(a, 'pasta', None) else localizar_sociedade_canonica()
    c_perfil = getattr(a, 'perfil', None)

    try:
        from sc_perfil import carregar_perfil, atualizar_papel
        perfil = carregar_perfil(c_perfil or p_soc)
    except Exception as e:
        raise SystemExit(f"erro ao carregar perfil: {e}")

    reg = obter_registro_obrigatorio(p_soc)

    papel = a.papel.lower()
    novo_estado = getattr(a, 'estado', 'ativo') or 'ativo'
    motivo = a.motivo.strip()
    data_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    try:
        plat, forn, mod, esf = resolver_destino(
            perfil, papel, getattr(a, 'para', None), getattr(a, 'fornecedor', None),
            getattr(a, 'modelo', None), getattr(a, 'esforco', None)
        )
    except Exception as e:
        raise SystemExit(f"erro: {e}")

    ok, erros = validar_regras_troca(
        papel=papel,
        novo_estado=novo_estado,
        nova_plataforma=plat,
        novo_fornecedor=forn,
        perfil=perfil,
        reg=reg,
        decisao_ref=getattr(a, 'decisao_ref', None)
    )

    if not ok:
        for err in erros:
            print(f"ERRO: {err}", file=sys.stderr)
        raise SystemExit(f"erro: troca de papel recusada por violação de regra invariante.")
    if not mod:
        raise SystemExit(f'erro: Informe --modelo: o fornecedor muda para "{forn}" e o modelo atual não vale mais.')

    msg_passagem = formatar_mensagem_passagem_troca(
        papel=papel,
        plataforma=plat,
        fornecedor=forn,
        modelo=mod,
        esforco=esf,
        estado=novo_estado,
        motivo=motivo,
        data_str=data_str
    )

    if not getattr(a, 'aplicar', False):
        print("=== SIMULAÇÃO DE TROCA DE PAPEL (M2) ===")
        print("Regras R1-R3 verificadas e aprovadas com sucesso.")
        print("Nenhuma alteração foi gravada em disco. Use --aplicar para efetivar.\n")
        print(msg_passagem)
        return 0

    caminho_perfil = perfil.caminho or (p_soc / 'perfil.md')
    atualizar_papel(
        caminho_perfil,
        papel=papel,
        plataforma=plat,
        fornecedor=forn,
        modelo=mod,
        esforco=esf,
        estado=novo_estado,
        motivo=motivo,
        desde=data_str
    )

    reg.registrar_troca_papel(
        papel=papel,
        plataforma=plat,
        fornecedor=forn,
        modelo=mod,
        esforco=esf,
        estado=novo_estado,
        motivo=motivo,
        decisao_ref=getattr(a, 'decisao_ref', None),
        autor=a.autor,
        aplicar=True
    )

    print(f"Papel '{papel}' atualizado com sucesso para '{plat}' ({novo_estado}) no perfil.md e registro.json.\n")
    print(msg_passagem)
    return 0


# ---------- linha de comando ----------

def main(argv=None):
    p = argparse.ArgumentParser(description='Estado da rodada da Sociedade do Código.')
    p.add_argument('--pasta', default=None, help='pasta do estado (padrão: sociedade canônica via Git)')
    p.add_argument('--aplicar', action='store_true', help='grava; sem isto, apenas simula')

    comum = argparse.ArgumentParser(add_help=False)
    comum.add_argument('--pasta', default=argparse.SUPPRESS)
    comum.add_argument('--aplicar', action='store_true', default=argparse.SUPPRESS)

    sub = p.add_subparsers(dest='cmd', required=True, parser_class=lambda **kw: argparse.ArgumentParser(
        parents=[comum], **kw))

    s = sub.add_parser('abrir')
    s.add_argument('--id', required=True)
    s.add_argument('--meta', required=True)
    s.add_argument('--nivel', default='2', help='nível de rigor (1, 2, 3 ou adaptativo; padrão 2)')
    s.add_argument('--base', default='<preencher>')
    s.add_argument('--bastao', default='Coordenador')
    s.add_argument('--limites', default='<preencher>')
    s.add_argument('--aceite', action='append', default=[])
    s.add_argument('--fatia', action='append', default=[])
    s.add_argument('--forcar', action='store_true')
    s.add_argument('--sem-revisao', action='store_true', help='Abre sem exigir revisão independente')
    s.add_argument('--projeto-id', help='Identificador estável do projeto')
    s.add_argument('--sincronizar-git', '--versao-git', dest='sincronizar_git', action='store_true',
                   help='Sincroniza a versão base com o commit Git HEAD atual')
    s.add_argument('--motivo')
    s.add_argument('--decisao-ref', dest='decisao_ref')
    s.set_defaults(func=cmd_abrir)

    s = sub.add_parser('bastao')
    s.add_argument('--para', required=True)
    s.add_argument('--leia', action='append', default=[])
    s.add_argument('--justificativa-expansao', default='', help='justificativa para expansão além do teto inicial de caminhos (Q21)')
    s.add_argument('--faca', action='append', default=[])
    s.add_argument('--nao-faca', action='append', default=[], dest='nao_faca')
    s.add_argument('--devolva', default='neste arquivo e uma linha no histórico')
    s.add_argument('--nota')
    s.set_defaults(func=cmd_bastao)

    s = sub.add_parser('fatia')
    s.add_argument('numero', nargs='?', type=int)
    s.add_argument('--add')
    s.add_argument('--fechar', action='store_true')
    s.add_argument('--prova')
    s.add_argument('--listar', action='store_true')
    s.add_argument('--forcar', action='store_true')
    s.add_argument('--motivo')
    s.add_argument('--decisao-ref')
    s.add_argument('--paralelo', action='store_true', help='Permite iniciar ou fechar fatia em paralelo caso arquivos sejam disjuntos')
    s.add_argument('--arquivos', nargs='+', default=[], help='Lista de caminhos ou arquivos afetados pela fatia paralela')
    s.set_defaults(func=cmd_fatia)

    s = sub.add_parser('autorizar')
    s.add_argument('texto')
    s.add_argument('--quem', default='Odival')
    s.set_defaults(func=cmd_autorizar)

    s = sub.add_parser('achado')
    s.add_argument('--id')
    s.add_argument('--severidade', default='relevante')
    s.add_argument('--onde', default='—')
    s.add_argument('--texto', default='')
    s.add_argument('--fechar', help='ID do achado a atualizar')
    s.add_argument('--estado', '--status', dest='estado', default='corrigido')
    s.add_argument('--justificativa', default='')
    s.set_defaults(func=cmd_achado)

    s = sub.add_parser('evidencia')
    s.add_argument('--etapa')
    s.add_argument('--criterio', required=True)
    s.add_argument('--comando', required=True)
    s.add_argument('--saida', required=True)
    s.add_argument('--exit-code', type=int, default=0, dest='exit_code')
    s.add_argument('--verificador', default='Gandalf')
    s.add_argument('--ambiente', default='local')
    s.add_argument('--versao')
    s.set_defaults(func=cmd_evidencia)

    s = sub.add_parser('parecer')
    s.add_argument('--etapa')
    s.add_argument('--revisor', required=True)
    s.add_argument('--fornecedor', required=True)
    s.add_argument('--implementador', action='append', default=[], dest='implementadores')
    s.add_argument('--versao', required=False, default=None)
    s.add_argument('--sincronizar-git', '--versao-git', dest='sincronizar_git', action='store_true',
                   help='Sincroniza a versão examinada com o commit Git HEAD atual')
    s.add_argument('--veredito', required=True, choices=['aceitar', 'aceitar_com_ressalvas', 'nao_aceitar'])
    s.add_argument('--criterio-ok', action='append', default=[], dest='criterio_ok')
    s.add_argument('--criterio-pendente', action='append', default=[], dest='criterio_pendente')
    s.add_argument('--achado', action='append', default=[])
    s.add_argument('--lacuna', action='append', default=[])
    s.add_argument('--nivel-independencia', default='A', choices=['A', 'B', 'C'], dest='nivel_independencia',
                   help='escala tripartite de independência do revisor: A (fornecedor externo), B (modelo distinto), C (sessão isolada)')
    s.add_argument('--justificativa-independencia', default='', dest='justificativa_independencia',
                   help='justificativa formal obrigatória para níveis B e C de independência')
    s.set_defaults(func=cmd_parecer)

    s = sub.add_parser('excecao')
    s.add_argument('--etapa')
    s.add_argument('--regra', required=True)
    s.add_argument('--motivo', required=True)
    s.add_argument('--decisao-ref', required=True, dest='decisao_ref')
    s.add_argument('--alcance', default='etapa')
    s.set_defaults(func=cmd_excecao)

    s = sub.add_parser('encerrar')
    s.add_argument('--resumo')
    s.add_argument('--forcar', action='store_true')
    s.add_argument('--sincronizar-git', '--versao-git', dest='sincronizar_git', action='store_true',
                   help='Sincroniza a versão atual com commit Git HEAD antes de encerrar')
    s.add_argument('--regra')
    s.add_argument('--motivo')
    s.add_argument('--decisao-ref')
    s.set_defaults(func=cmd_encerrar)

    s = sub.add_parser('sincronizar-versao', help='Atualiza a versão atual no registro.json de forma atômica sob lock')
    s.add_argument('--versao', default=None, help='Hash da versão (se omitido, captura git rev-parse HEAD)')
    s.add_argument('--etapa', default=None, help='ID da etapa (se omitido, usa a etapa ativa)')
    s.add_argument('--impacto', default='desconhecido', choices=['sem_alto', 'alto', 'desconhecido'],
                   help='Classificação de impacto da versão (padrão: sem_alto)')
    s.set_defaults(func=cmd_sincronizar_versao)

    s = sub.add_parser('lint')
    s.add_argument('--teto', type=int, default=TETO_RODADA)
    s.set_defaults(func=cmd_lint)

    s = sub.add_parser('colar')
    s.add_argument('--teto-colar', type=int, default=2000, dest='teto_colar')
    s.set_defaults(func=cmd_colar)

    s = sub.add_parser('rotacionar')
    s.set_defaults(func=cmd_rotacionar)

    s = sub.add_parser('resumo')
    s.add_argument('--exportar')
    s.add_argument('--importar')
    s.add_argument('--destino')
    s.set_defaults(func=cmd_resumo)

    s = sub.add_parser('migrar')
    s.add_argument('--origem', required=True)
    s.set_defaults(func=cmd_migrar)

    s = sub.add_parser('projetar')
    s.add_argument('--destino')
    s.set_defaults(func=cmd_projetar)

    s = sub.add_parser('sincronizar')
    s.add_argument('--destino')
    s.set_defaults(func=cmd_sincronizar)

    s = sub.add_parser('calibrar', help='Avalia retrospectivamente a eficácia dos 5 fatores de rigor (Q22)')
    s.add_argument('--limiar-fatores', type=int, default=2, dest='limiar_fatores',
                   help='Limiar mínimo de fatores para recomendar elevação (padrão: 2)')
    s.add_argument('--formato', choices=['texto', 'json'], default='texto',
                   help='Formato de saída do relatório (padrão: texto)')
    s.add_argument('--saida', default=None, help='Arquivo de destino para o relatório de calibração')
    s.add_argument('--etapas', nargs='*', default=None, help='Lista de etapas para filtrar análise')
    s.set_defaults(func=cmd_calibrar)

    s_wt = sub.add_parser('worktree', help='Gerencia worktrees Git de etapas')
    sub_wt = s_wt.add_subparsers(dest='subcmd', required=True)

    s_wt_c = sub_wt.add_parser('criar', help='Cria worktree para uma etapa')
    s_wt_c.add_argument('--etapa', required=True, help='Identificador da etapa')
    s_wt_c.add_argument('--branch', default=None, help='Nome da branch')
    s_wt_c.add_argument('--base', default=None, help='Commit ou ref base')
    s_wt_c.add_argument('--projeto', default=None, help='Nome do projeto')
    s_wt_c.add_argument('--raiz', default=None, help='Diretório raiz de trabalho')
    s_wt_c.add_argument('--pasta-base', default=None, help='Pasta base para localização Git')

    s_wt_l = sub_wt.add_parser('listar', help='Lista worktrees do projeto')
    s_wt_l.add_argument('--projeto', default=None, help='Nome do projeto')
    s_wt_l.add_argument('--raiz', default=None, help='Diretório raiz de trabalho')
    s_wt_l.add_argument('--pasta-base', default=None, help='Pasta base para localização Git')

    s_wt_r = sub_wt.add_parser('remover', help='Remove worktree de uma etapa')
    s_wt_r.add_argument('--etapa', required=True, help='Identificador da etapa')
    s_wt_r.add_argument('--forcar', action='store_true', help='Força remoção mesmo com alterações não commitadas')
    s_wt_r.add_argument('--projeto', default=None, help='Nome do projeto')
    s_wt_r.add_argument('--raiz', default=None, help='Diretório raiz de trabalho')
    s_wt_r.add_argument('--pasta-base', default=None, help='Pasta base para localização Git')

    s_wt.set_defaults(func=cmd_worktree)

    s_papel = sub.add_parser('papel', help='Gerencia papéis, matriz e trocas (M2, R1-R3)')
    sub_papel = s_papel.add_subparsers(dest='subcmd_papel', required=True,
                                       parser_class=lambda **kw: argparse.ArgumentParser(parents=[comum], **kw))

    s_papel_st = sub_papel.add_parser('status', help='Exibe o status dos papéis e equipe ativa')
    s_papel_st.add_argument('--perfil', help='Caminho do perfil.md (opcional)')
    s_papel_st.set_defaults(func=cmd_papel_status)

    s_papel_tr = sub_papel.add_parser('trocar', help='Efetua ou simula a troca de papel (M2; R1-R3)')
    s_papel_tr.add_argument('--papel', required=True, choices=['arquiteto', 'revisor', 'execucao', 'coordenador'], help='Papel a ser alterado')
    s_papel_tr.add_argument('--para', default=None, help='Nova plataforma de destino')
    s_papel_tr.add_argument('--motivo', required=True, help='Motivo da troca')
    s_papel_tr.add_argument('--fornecedor', default=None, help='Fornecedor do destino (obrigatório se a plataforma não estiver no perfil)')
    s_papel_tr.add_argument('--modelo', default=None, help='Modelo adotado (obrigatório quando o fornecedor muda)')
    s_papel_tr.add_argument('--autor', required=True, help='Quem faz a troca (registrado no registro.json)')
    s_papel_tr.add_argument('--esforco', default=None, help='Nível de esforço (high, medium, etc.)')
    s_papel_tr.add_argument('--estado', default='ativo', choices=['ativo', 'reserva', 'espera'], help='Estado do papel (padrão: ativo)')
    s_papel_tr.add_argument('--decisao-ref', default=None, help='Referência a decisão para exceções (ex.: R3)')
    s_papel_tr.add_argument('--perfil', default=None, help='Caminho do perfil.md (opcional)')
    s_papel_tr.set_defaults(func=cmd_papel_trocar)

    a = p.parse_args(argv)
    if getattr(a, 'pasta', None) is None and getattr(a, 'cmd', None) != 'worktree':
        a.pasta = str(localizar_sociedade_canonica())
    return a.func(a)


if __name__ == '__main__':
    sys.exit(main())
