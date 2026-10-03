#!/usr/bin/env python3
"""Registro estruturado, operacional e transacional de eventos da Sociedade do Código.

Gerencia o arquivo <pasta>/registro.json como fonte única de eventos,
com integridade atômica, revisão monotônica, trava de concorrência,
derivação de estado, projeções Markdown não destrutivas e agregação entre projetos.

Sem dependências externas: usa apenas a biblioteca padrão do Python.
"""
import contextlib
import fcntl
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

VERSAO_FORMATO = '2.1.0'
NOME_ARQUIVO_REGISTRO = 'registro.json'
NOME_ARQUIVO_LOCK = '.registro.lock'
SEVERIDADES_ACHADO = ('bloqueador', 'relevante', 'opcional')
ESTADOS_ACHADO = ('aberto', 'contestado', 'corrigido', 'excepcionado')
MAPA_SINONIMOS_ESTADO_ACHADO = {
    'resolvido': 'corrigido',
    'fechado': 'corrigido',
    'atendido': 'corrigido',
    'abrir': 'aberto',
    'novo': 'aberto',
}
ESTADOS_TAREFA = ('pendente', 'em_andamento', 'concluida', 'bloqueada', 'falhou')
VEREDITOS_PARECER = ('aceitar', 'aceitar_com_ressalvas', 'nao_aceitar')
CLASSIFICACOES_IMPACTO = ('alto', 'sem_alto', 'desconhecido')

PADRAO_PLACEHOLDER = re.compile(
    r'<\s*(?:preencher|inserir|todo|a\s+preencher|definir|seu[-_]comando|sua[-_]saida)\b[^>]*>',
    re.IGNORECASE
)
PADRAO_NAO_EXECUTADO = re.compile(
    r'\b(?:n[ãa]o\s+(?:executad[oa]|rodou|testad[oa]|iniciado)|pendente\s+de\s+execu[çc][ãa]o|dry[- ]run|skipped|prova:\s*None)\b',
    re.IGNORECASE
)
PADRAO_CONTAGEM_SKIPPED = re.compile(
    r'\(?(?:\bskipped\s*=\s*\d+|\b\d+\s+skipped\b)\)?',
    re.IGNORECASE
)
PADRAO_DECISAO_REF = re.compile(
    r'^[A-Za-z0-9]+-[A-Za-z0-9_-]+'
)


class ErroRegistro(Exception):
    """Erro base do subsistema de registro."""


class ErroRegistroCorrompido(ErroRegistro):
    """Disparado ao encontrar arquivo corrompido ou com schema violado."""


class ErroConcorrenciaRegistro(ErroRegistro):
    """Disparado quando a revisão no disco difere da revisão esperada."""


class ErroValidacaoRegistro(ErroRegistro):
    """Disparado quando uma operação viola as regras de negócio do método."""


def agora_iso():
    return datetime.now(timezone.utc).isoformat()


def calcular_hash_conteudo(texto_ou_bytes):
    if isinstance(texto_ou_bytes, str):
        texto_ou_bytes = texto_ou_bytes.encode('utf-8')
    return hashlib.sha256(texto_ou_bytes).hexdigest()


def localizar_sociedade_canonica(pasta_base=None):
    """Localiza o diretório canônico 'sociedade/' a partir do diretório comum do Git.

    Se executado dentro de um worktree ou do repositório principal, consulta o Git
    (git rev-parse --git-common-dir) para identificar a raiz do repositório canônico
    e retorna o caminho para a pasta 'sociedade' correspondente.
    Se não estiver em um repositório Git ou se o Git falhar/não estiver disponível,
    retorna (pasta_base ou Path.cwd()) / 'sociedade'.
    """
    import subprocess
    base = Path(pasta_base).resolve() if pasta_base else Path.cwd().resolve()
    if base.is_dir() and base.name == 'sociedade':
        return base
    try:
        res = subprocess.run(
            ['git', '-C', str(base), 'rev-parse', '--git-common-dir'],
            capture_output=True, text=True, check=True
        )
        caminho_git = res.stdout.strip()
        if caminho_git:
            p = Path(caminho_git)
            if not p.is_absolute():
                p = (base / p).resolve()
            else:
                p = p.resolve()
            repo_root = p.parent
            return repo_root / 'sociedade'
    except Exception:
        pass
    return (base / 'sociedade').resolve()


def caminhos_registro(pasta=None):
    if pasta is None:
        p = localizar_sociedade_canonica()
    else:
        p = Path(pasta)
    return p / NOME_ARQUIVO_REGISTRO, p / NOME_ARQUIVO_LOCK


@contextlib.contextmanager
def trava_exclusiva(lock_path):
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock_path, 'a+')
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        f.close()


def carregar_dados_registro(registro_path):
    p = Path(registro_path)
    if not (os.path.exists(str(p)) or p.is_file()):
        return None
    try:
        bruto = p.read_text(encoding='utf-8')
        dados = json.loads(bruto)
    except Exception as e:
        raise ErroRegistroCorrompido(f'Arquivo de registro corrompido ou malformado: {e}') from e

    if not isinstance(dados, dict):
        raise ErroRegistroCorrompido('Raiz do registro deve ser um objeto JSON.')
    for campo in ('versao_formato', 'projeto_id', 'revisao', 'eventos'):
        if campo not in dados:
            raise ErroRegistroCorrompido(f'Campo obrigatório ausente no registro: {campo}')
    if not isinstance(dados['eventos'], list):
        raise ErroRegistroCorrompido('Campo "eventos" deve ser uma lista.')

    # Valida integridade e monotonicidade dos eventos (REV-001, REV-014)
    ultimo_seq = 0
    for ev in dados['eventos']:
        if not isinstance(ev, dict):
            raise ErroRegistroCorrompido('Evento malformado (deve ser objeto JSON).')
        for k in ('id', 'seq', 'tipo', 'timestamp'):
            if k not in ev:
                raise ErroRegistroCorrompido(f'Evento incompleto: ausente campo "{k}".')
        if ev['seq'] <= ultimo_seq:
            raise ErroRegistroCorrompido(
                f'Monotonicidade de eventos violada: seq {ev["seq"]} <= {ultimo_seq}.'
            )
        ultimo_seq = ev['seq']

    return dados


def salvar_dados_registro_atomico(registro_path, dados):
    """Gravação atômica com arquivo temporário e fsync (REV-001, REV-016)."""
    p = Path(registro_path)
    pasta = p.parent
    pasta.mkdir(parents=True, exist_ok=True)

    dados_serializados = json.dumps(dados, indent=2, ensure_ascii=False, sort_keys=True)
    tmp_path = pasta / f'{p.name}.tmp.{os.getpid()}'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(dados_serializados)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, p)
        # Sincroniza o diretório pai em POSIX para garantir persistência no storage
        try:
            dir_fd = os.open(str(pasta), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def derivar_estado(registro_dados):
    """Calcula o estado operacional do projeto a partir do log ordenado de eventos."""
    eventos = registro_dados.get('eventos', [])
    estado = {
        'etapa_atual': None,
        'etapas_concluidas': [],
        'etapas_excepcionadas': [],
        'etapas_simuladas': [],
        'contagem_concluidas': 0,
        'resumos_externos': dict(registro_dados.get('resumos_externos', {})),
        'contagem_agregada_total': 0,
        'aviso_cota_recente': None,
        'versao_inicial': registro_dados.get('versao_inicial'),
    }

    etapas = {}

    for ev in eventos:
        tipo = ev.get('tipo')
        d = ev.get('dados', {})
        e_id = d.get('etapa_id')

        # Se o evento visa uma etapa já encerrada, isso viola a integridade (REV-014)
        if e_id and e_id in etapas and etapas[e_id]['estado'] == 'encerrada' and tipo not in ('etapa_aberta', 'resumo_importado'):
            raise ErroValidacaoRegistro(f'Etapa {e_id} já está encerrada; não aceita novos eventos do tipo {tipo}.')

        # Rejeita eventos órfãos que referenciam etapas inexistentes (N6)
        if tipo in (
            'bastao_passado', 'versao_atualizada', 'tarefa_criada', 'tarefa_atualizada',
            'evidencia_registrada', 'achado_registrado', 'achado_atualizado',
            'parecer_registrado', 'decisao_registrada', 'excecao_registrada', 'etapa_encerrada'
        ):
            if not e_id or e_id not in etapas:
                raise ErroValidacaoRegistro(f'Evento órfão do tipo "{tipo}" referenciando etapa inexistente "{e_id}".')

        if tipo == 'etapa_aberta':
            if e_id not in etapas:
                # Regra: uma rodada ativa por vez
                ativas = [e for e in etapas.values() if e['estado'] != 'encerrada']
                if ativas:
                    raise ErroValidacaoRegistro(
                        f'Já existe etapa ativa ({ativas[-1]["id"]}). Encerre-a antes de abrir {e_id}.'
                    )

                is_sim = ev.get('simulacao', False) or d.get('origem') == 'simulacao'
                criterios_iniciais = d.get('criterios', [])
                if not criterios_iniciais and not is_sim:
                    raise ErroValidacaoRegistro('Abertura de etapa exige ao menos um critério de aceite.')

                etapas[e_id] = {
                    'id': e_id,
                    'nivel': str(d.get('nivel', '2')),
                    'objetivo': d.get('objetivo', ''),
                    'plano_ref': d.get('plano_ref', ''),
                    'autorizacao_ref': d.get('autorizacao_ref', ''),
                    'base_efetiva': d.get('base_efetiva', ''),
                    'versao_atual': d.get('base_efetiva', ''),
                    'criterios': {c: {'id': c, 'atendido': False, 'evidencias': []} for c in criterios_iniciais},
                    'tarefas': {},
                    'achados': {},
                    'pareceres': [],
                    'decisoes': [],
                    'excecoes': [],
                    'estado': 'aberta',
                    'aberta_em': ev.get('timestamp'),
                    'encerrada_em': None,
                    'resumo_encerramento': None,
                    'elegivel_publicacao': False,
                    'origem': d.get('origem', 'real'),
                    'simulacao': is_sim,
                    'exigir_revisao': d.get('exigir_revisao', True),
                    'responsavel': d.get('responsavel', 'Coordenador'),
                    'classificacao_impacto': None,
                }
            else:
                if etapas[e_id]['estado'] == 'encerrada':
                    raise ErroValidacaoRegistro(f'Etapa {e_id} já foi encerrada e não pode ser reaberta.')
                # Reabertura/manutenção de identidade da etapa ativa
                etapas[e_id]['responsavel'] = d.get('responsavel', etapas[e_id]['responsavel'])

        elif tipo == 'bastao_passado':
            etapas[e_id]['responsavel'] = d.get('para', etapas[e_id]['responsavel'])

        elif tipo == 'versao_atualizada':
            v_nova = d.get('versao', etapas[e_id]['versao_atual'])
            imp_novo = d.get('impacto', 'desconhecido')
            etapas[e_id]['versao_atual'] = v_nova
            if etapas[e_id].get('base_efetiva') in ('<preencher>', '', None) or (
                PADRAO_PLACEHOLDER and PADRAO_PLACEHOLDER.search(str(etapas[e_id].get('base_efetiva', '')))
            ):
                etapas[e_id]['base_efetiva'] = v_nova
            imp_ant = etapas[e_id].get('classificacao_impacto')
            if imp_ant == 'alto':
                # Impacto alto permanece fixado (sticky) até nova revisão examinada (N3)
                pass
            elif imp_novo == 'alto':
                etapas[e_id]['classificacao_impacto'] = 'alto'
            elif imp_ant == 'desconhecido' and imp_novo == 'sem_alto':
                etapas[e_id]['classificacao_impacto'] = 'sem_alto'
            else:
                etapas[e_id]['classificacao_impacto'] = imp_novo

        elif tipo == 'tarefa_criada':
            t_id = d.get('tarefa_id')
            if t_id in etapas[e_id]['tarefas']:
                raise ErroValidacaoRegistro(f'Tarefa com ID {t_id} já existe na etapa {e_id}.')
            etapas[e_id]['tarefas'][t_id] = {
                'id': t_id,
                'especialista': d.get('especialista'),
                'fornecedor': d.get('fornecedor') or 'desconhecido',
                'tipo': d.get('tipo', 'geral'),
                'ferramenta': d.get('ferramenta', 'local'),
                'job_id_remoto': d.get('job_id_remoto'),
                'estado': d.get('estado', 'pendente'),
                'descricao': d.get('descricao', ''),
                'dependencias': d.get('dependencias', []),
                'arquivos': list(d.get('arquivos') or []),
            }

        elif tipo == 'tarefa_atualizada':
            t_id = d.get('tarefa_id')
            if t_id not in etapas[e_id]['tarefas']:
                raise ErroValidacaoRegistro(f'Tarefa {t_id} não encontrada na etapa {e_id}.')
            etapas[e_id]['tarefas'][t_id]['estado'] = d.get('estado', etapas[e_id]['tarefas'][t_id]['estado'])
            if 'nota' in d:
                etapas[e_id]['tarefas'][t_id]['nota'] = d['nota']
            if 'arquivos' in d and d['arquivos'] is not None:
                etapas[e_id]['tarefas'][t_id]['arquivos'] = list(d['arquivos'])

        elif tipo == 'evidencia_registrada':
            c_id = d.get('criterio_id')
            if c_id not in etapas[e_id]['criterios']:
                raise ErroValidacaoRegistro(f'Critério {c_id} não pertence à etapa {e_id}.')

            ev_item = {
                'id': d.get('evidencia_id'),
                'criterio_id': c_id,
                'comando': d.get('comando', ''),
                'exit_code': d.get('exit_code', 0),
                'saida_resumo': d.get('saida_resumo', ''),
                'saida_hash': d.get('saida_hash', ''),
                'valida': d.get('valida', True),
                'motivo_invalida': d.get('motivo_invalida'),
                'verificador': d.get('verificador', ev.get('autor')),
                'ambiente': d.get('ambiente', 'local'),
                'versao_entrega': d.get('versao_entrega', ''),
                'timestamp': ev.get('timestamp'),
            }
            etapas[e_id]['criterios'][c_id]['evidencias'].append(ev_item)
            # Recomputação não-acumulativa do critério: o resultado da última evidência define o status (REV-012)
            if ev_item['valida'] and ev_item['exit_code'] == 0:
                etapas[e_id]['criterios'][c_id]['atendido'] = True
            else:
                etapas[e_id]['criterios'][c_id]['atendido'] = False

        elif tipo == 'achado_registrado':
            a_id = d.get('achado_id')
            if a_id in etapas[e_id]['achados']:
                raise ErroValidacaoRegistro(f'Achado com ID {a_id} já existe na etapa {e_id}. Reuso de ID é proibido.')
            etapas[e_id]['achados'][a_id] = {
                'id': a_id,
                'severidade': d.get('severidade', 'relevante'),
                'onde': d.get('onde', ''),
                'descricao': d.get('descricao', ''),
                'estado': 'aberto',
                'autor': ev.get('autor'),
                'historico': [{'estado': 'aberto', 'autor': ev.get('autor'), 'ts': ev.get('timestamp')}],
            }

        elif tipo == 'achado_atualizado':
            a_id = d.get('achado_id')
            if a_id not in etapas[e_id]['achados']:
                raise ErroValidacaoRegistro(f'Achado {a_id} não encontrado na etapa {e_id}.')
            novo_est = d.get('novo_estado')
            if novo_est == 'excepcionado':
                # Só pode ser excepcionado se houver exceção registrada para o achado (REV-004)
                tem_exc = any(e['regra'] in (f'achado:{a_id}', 'achados_bloqueadores') for e in etapas[e_id]['excecoes'])
                if not tem_exc:
                    raise ErroValidacaoRegistro(
                        f'Achado {a_id} não pode transicionar para "excepcionado" sem exceção estruturada correspondente.'
                    )
            etapas[e_id]['achados'][a_id]['estado'] = novo_est
            etapas[e_id]['achados'][a_id]['historico'].append({
                'estado': novo_est,
                'justificativa': d.get('justificativa', ''),
                'autor': ev.get('autor'),
                'ts': ev.get('timestamp'),
            })

        elif tipo == 'parecer_registrado':
            p_item = {
                'id': d.get('parecer_id'),
                'revisor': d.get('revisor'),
                'fornecedor_revisor': d.get('fornecedor_revisor'),
                'implementadores': d.get('implementadores', []),
                'versao_examinada': d.get('versao_examinada'),
                'veredito': d.get('veredito'),
                'criterios_verificados': d.get('criterios_verificados', {}),
                'achados_referenciados': d.get('achados_referenciados', []),
                'lacunas': d.get('lacunas', []),
                'nivel_independencia': d.get('nivel_independencia', 'A'),
                'justificativa_independencia': d.get('justificativa_independencia', ''),
                'aceite_em_emulacao': bool(d.get('aceite_em_emulacao')),
                # B02: aceite em emulação nunca é revisão independente (D-RT-001)
                'independencia': d.get('independencia') or ('sim' if d.get('nivel_independencia', 'A') == 'A' else 'não'),
                'commit': d.get('commit'),
                'timestamp': ev.get('timestamp'),
            }
            etapas[e_id]['pareceres'].append(p_item)
            if etapas[e_id].get('versao_atual') in ('<preencher>', '', None) or (
                PADRAO_PLACEHOLDER and PADRAO_PLACEHOLDER.search(str(etapas[e_id].get('versao_atual', '')))
            ):
                etapas[e_id]['versao_atual'] = p_item.get('versao_examinada')
            if etapas[e_id].get('base_efetiva') in ('<preencher>', '', None) or (
                PADRAO_PLACEHOLDER and PADRAO_PLACEHOLDER.search(str(etapas[e_id].get('base_efetiva', '')))
            ):
                etapas[e_id]['base_efetiva'] = p_item.get('versao_examinada')
            if p_item.get('versao_examinada') == etapas[e_id].get('versao_atual') and p_item.get('veredito') in ('aceitar', 'aceitar_com_ressalvas'):
                etapas[e_id]['classificacao_impacto'] = None

        elif tipo == 'decisao_registrada':
            etapas[e_id]['decisoes'].append({
                'id': d.get('decisao_id'),
                'quem': d.get('quem'),
                'referencia': d.get('referencia'),
                'acao': d.get('acao'),
                'alcance': d.get('alcance'),
                'aceite_em_emulacao': bool(d.get('aceite_em_emulacao')),
                'independencia': d.get('independencia'),
                'commit': d.get('commit'),
                'timestamp': ev.get('timestamp'),
            })

        elif tipo == 'excecao_registrada':
            etapas[e_id]['excecoes'].append({
                'id': d.get('excecao_id'),
                'regra': d.get('regra'),
                'motivo': d.get('motivo'),
                'referencia_humana': d.get('referencia_humana'),
                'alcance': d.get('alcance'),
                'timestamp': ev.get('timestamp'),
            })

        elif tipo == 'aviso_cota_registrado':
            estado['aviso_cota_recente'] = {
                'autor': d.get('autor'),
                'percentual': d.get('percentual'),
                'janela': d.get('janela'),
                'data': d.get('data'),
                'timestamp': ev.get('timestamp'),
            }

        elif tipo == 'resumo_importado':
            chave = d.get('chave')
            res = d.get('resumo')
            if chave and res:
                estado['resumos_externos'][chave] = res

        elif tipo == 'etapa_encerrada':
            etapas[e_id]['estado'] = 'encerrada'
            etapas[e_id]['encerrada_em'] = ev.get('timestamp')
            etapas[e_id]['resumo_encerramento'] = d.get('resumo', '')
            etapas[e_id]['elegivel_publicacao'] = d.get('elegivel_publicacao', False)
            etapas[e_id]['desfecho'] = d.get('desfecho')

    for e in etapas.values():
        # B02: marca de emulação da etapa = parecer que decide (Q144) ou alguma decisão marcada.
        ps = e.get('pareceres', [])
        idx_a = [i for i, p in enumerate(ps) if p.get('nivel_independencia', 'A') == 'A']
        decide = ps[idx_a[-1]] if idx_a else (ps[-1] if ps else None)
        marcada = bool((decide or {}).get('aceite_em_emulacao')) or any(
            x.get('aceite_em_emulacao') for x in e.get('decisoes', []))
        e['aceite_em_emulacao'] = marcada
        e['independencia'] = 'não' if marcada else ((decide or {}).get('independencia'))

    ativas = [e for e in etapas.values() if e['estado'] != 'encerrada']
    todas_encerradas = [e for e in etapas.values() if e['estado'] == 'encerrada']

    concluidas_elegiveis = [e for e in todas_encerradas if not e.get('simulacao') and e.get('elegivel_publicacao')]
    concluidas_excepcionadas = [e for e in todas_encerradas if not e.get('simulacao') and not e.get('elegivel_publicacao')]
    simuladas = [e for e in todas_encerradas if e.get('simulacao')]

    estado['etapa_atual'] = ativas[-1] if ativas else None
    estado['etapas_concluidas'] = [e['id'] for e in concluidas_elegiveis]
    estado['etapas_excepcionadas'] = [e['id'] for e in concluidas_excepcionadas]
    estado['etapas_simuladas'] = [e['id'] for e in simuladas]
    estado['contagem_concluidas'] = len(concluidas_elegiveis)

    # Contagem agregada (locais reais elegíveis + resumos externos válidos não simulados e elegíveis)
    externas_validas = sum(1 for r in estado['resumos_externos'].values()
                           if r.get('concluida') and not r.get('simulacao') and r.get('elegivel_publicacao', True))
    estado['contagem_agregada_total'] = estado['contagem_concluidas'] + externas_validas
    estado['etapas'] = etapas

    return estado


def verificar_condicoes_encerramento_estado(estado, etapa_id):
    """Verifica sobre uma estrutura de estado derivada se a etapa pode ser encerrada."""
    etapa = estado['etapa_atual']
    if not etapa or etapa['id'] != etapa_id:
        return False, [f'Etapa {etapa_id} não é a etapa ativa no registro.'], False

    bloqueios = []
    tem_excecao_essencial = False

    # 0. Critérios de aceite devem existir (N6)
    if not etapa.get('criterios'):
        bloqueios.append('Etapa não possui critérios de aceite definidos.')

    # 1. Critérios obrigatórios e evidências (N3, N8)
    for c_id, c_info in etapa['criterios'].items():
        c_id_norm = c_id.lower().replace('-', '_')
        if not c_info['atendido']:
            excepcionado = any(
                e['regra'].lower().replace('-', '_') in (f'criterio:{c_id_norm}', 'criterios_gerais', 'fatias_pendentes')
                for e in etapa['excecoes']
            )
            if not excepcionado:
                bloqueios.append(f'Critério obrigatório {c_id} sem evidência válida executada.')
            else:
                tem_excecao_essencial = True
        else:
            # Validar versão da evidência atendida contra versão atual se houve impacto alto (N3)
            ult_ev = c_info['evidencias'][-1] if c_info['evidencias'] else None
            if ult_ev and ult_ev.get('versao_entrega') and etapa.get('versao_atual'):
                if ult_ev['versao_entrega'] != etapa['versao_atual'] and etapa.get('classificacao_impacto') == 'alto':
                    bloqueios.append(
                        f'Critério {c_id} foi comprovado na versão {ult_ev["versao_entrega"]}, '
                        f'mas versão atual é {etapa["versao_atual"]} com alterações de alto impacto pendentes de revalidação.'
                    )

    # 2. Achados bloqueadores abertos ou contestados
    for a_id, a_info in etapa['achados'].items():
        if a_info['severidade'] == 'bloqueador' and a_info['estado'] in ('aberto', 'contestado'):
            excepcionado = any(e['regra'] in (f'achado:{a_id}', 'achados_bloqueadores') for e in etapa['excecoes'])
            if not excepcionado:
                bloqueios.append(f'Achado bloqueador {a_id} está {a_info["estado"]}.')
            else:
                tem_excecao_essencial = True

    # 3. Revisão independente obrigatória (N2)
    exigir_revisao = etapa.get('exigir_revisao', True)
    if exigir_revisao and not etapa['pareceres']:
        excepcionado = any(e['regra'] == 'revisao_independente' for e in etapa['excecoes'])
        if not excepcionado:
            bloqueios.append('Revisão independente obrigatória ainda não registrada.')
        else:
            tem_excecao_essencial = True
    elif etapa['pareceres']:
        # Q144 (A2-P02): decide o parecer independente (nível A) mais recente. Parecer interno
        # posterior fica registrado e só pesa se rejeitar. Sem parecer A, decide o último (e ele,
        # sendo interno, deixa a etapa como exceção essencial, fora da elegibilidade: D-RT-001).
        pareceres = etapa['pareceres']
        indices_a = [i for i, p in enumerate(pareceres) if p.get('nivel_independencia', 'A') == 'A']
        if indices_a:
            ultimo_parecer = pareceres[indices_a[-1]]
            for p_interno in pareceres[indices_a[-1] + 1:]:
                if p_interno.get('veredito') == 'nao_aceitar':
                    bloqueios.append('Parecer interno posterior ao independente rejeitou a entrega (Q144).')
        else:
            ultimo_parecer = pareceres[-1]
        if ultimo_parecer['veredito'] == 'nao_aceitar':
            bloqueios.append('Último parecer do revisor rejeitou a entrega (veredito: não aceitar).')
        else:
            # Escala Tripartite de Independência: etapa de nível 3 não aceita Nível C
            if str(etapa.get('nivel', '2')) == '3' and ultimo_parecer.get('nivel_independencia') == 'C':
                bloqueios.append(
                    'Etapa de nível 3 exige revisão independente de Nível A (fornecedor externo) '
                    'ou Nível B (modelo/sessão distinta com justificativa); Nível C não é aceito para homologação de nível 3.'
                )

            # D-RT-001: Pareceres com nível diferente de 'A' (ex: B ou C) são revisões internas de mesmo fornecedor
            # que não habilitam encerramento normal ou publicação por si sós; devem ser tratados como exceção essencial.
            if ultimo_parecer.get('nivel_independencia') != 'A':
                tem_excecao_essencial = True

            # 4. Vínculo de versão e impacto de correções (C07, N3)
            versao_revisada = ultimo_parecer.get('versao_examinada')
            versao_atual = etapa.get('versao_atual') or etapa.get('base_efetiva')
            if versao_atual in ('<preencher>', '', None) or (
                PADRAO_PLACEHOLDER and PADRAO_PLACEHOLDER.search(str(versao_atual))
            ):
                versao_atual = versao_revisada
            if versao_revisada in ('<preencher>', '', None) or (
                PADRAO_PLACEHOLDER and PADRAO_PLACEHOLDER.search(str(versao_revisada))
            ):
                versao_revisada = versao_atual
            if versao_revisada and versao_atual and versao_revisada != versao_atual:
                impacto = etapa.get('classificacao_impacto')
                if not impacto or impacto == 'desconhecido':
                    bloqueios.append(
                        f'Versão examinada no parecer ({versao_revisada}) difere da versão atual ({versao_atual}) '
                        'sem classificação formal de impacto (correção pós-revisão com impacto desconhecido).'
                    )
                elif impacto == 'alto':
                    bloqueios.append(
                        f'Correção de alto impacto pós-revisão ({versao_revisada} -> {versao_atual}) '
                        'exige nova revisão independente.'
                    )

    # 5. Tarefas em aberto/em andamento (N8)
    tarefas_pendentes = [
        t_id for t_id, t in etapa.get('tarefas', {}).items()
        if t.get('estado') in ('pendente', 'em_andamento')
    ]
    if tarefas_pendentes:
        excepcionado = any(
            e['regra'] in ('fatias_pendentes', 'tarefas_pendentes')
            for e in etapa['excecoes']
        )
        if not excepcionado:
            bloqueios.append(f'Tarefas não finalizadas na etapa: {", ".join(sorted(tarefas_pendentes))}.')
        else:
            tem_excecao_essencial = True

    elegivel_publicacao = (len(bloqueios) == 0) and (not tem_excecao_essencial)
    return len(bloqueios) == 0, bloqueios, elegivel_publicacao


def _etapa_existe_no_registro(dados, etapa_id):
    return any(
        ev.get('tipo') == 'etapa_aberta' and ev.get('dados', {}).get('etapa_id') == etapa_id
        for ev in dados.get('eventos', [])
    )


class Registro:
    """Interface operacional do arquivo registro.json com transações atômicas."""

    def __init__(self, pasta=None, dados=None):
        if pasta is None:
            self.pasta = localizar_sociedade_canonica()
        else:
            self.pasta = Path(pasta)
        self.registro_path, self.lock_path = caminhos_registro(self.pasta)
        if dados is not None:
            self._dados = dados
        else:
            carregado = carregar_dados_registro(self.registro_path)
            if carregado is None:
                raise ErroRegistro(f'Registro inexistente em {self.registro_path}. Inicialize-o primeiro.')
            self._dados = carregado

    @property
    def revisao(self):
        return self._dados['revisao']

    @property
    def dados(self):
        return self._dados

    @property
    def eventos(self):
        return self._dados['eventos']

    def estado(self):
        return derivar_estado(self._dados)

    @property
    def versao_inicial(self):
        return self._dados.get('versao_inicial')

    @property
    def perfil(self):
        if not hasattr(self, '_perfil_cache'):
            self._perfil_cache = None
            try:
                from sc_perfil import carregar_perfil, localizar_perfil
                try:
                    caminho = localizar_perfil(self.pasta)
                except Exception:
                    caminho = None
                if caminho and caminho.is_file():
                    self._perfil_cache = carregar_perfil(caminho)
            except Exception:
                raise
        return self._perfil_cache

    def carregar_dados(self):
        """Recarrega dados frescos do disco se o registro já existir fisicamente."""
        carregado = carregar_dados_registro(self.registro_path)
        if carregado is not None:
            self._dados = carregado
        return self._dados

    @classmethod
    def inicializar(cls, pasta, projeto_id, caminho_canonico, aplicar=True, versao_inicial=None, **kwargs):
        """Inicializa registro.json atomicamente dentro de lock exclusivo (elimina TOCTOU)."""
        if versao_inicial is None and 'versao_inicial' in kwargs:
            versao_inicial = kwargs['versao_inicial']
        pasta = Path(pasta)
        reg_path, lock_path = caminhos_registro(pasta)
        if not aplicar:
            # Em simulação (aplicar=False), NENHUM efeito colateral em disco (N5 / C13)
            novos_dados = {
                'versao_formato': VERSAO_FORMATO,
                'projeto_id': projeto_id,
                'caminho_canonico': str(caminho_canonico),
                'revisao': 1,
                'criado_em': agora_iso(),
                'atualizado_em': agora_iso(),
                'eventos': [],
                'resumos_externos': {},
            }
            if versao_inicial:
                novos_dados['versao_inicial'] = str(versao_inicial).strip()
            return cls(pasta, novos_dados)

        pasta.mkdir(parents=True, exist_ok=True)

        with trava_exclusiva(lock_path):
            if os.path.exists(str(reg_path)) or reg_path.is_file():
                existente = carregar_dados_registro(reg_path)
                return cls(pasta, existente)

            novos_dados = {
                'versao_formato': VERSAO_FORMATO,
                'projeto_id': projeto_id,
                'caminho_canonico': str(caminho_canonico),
                'revisao': 1,
                'criado_em': agora_iso(),
                'atualizado_em': agora_iso(),
                'eventos': [],
                'resumos_externos': {},
            }
            if versao_inicial:
                novos_dados['versao_inicial'] = str(versao_inicial).strip()
            salvar_dados_registro_atomico(reg_path, novos_dados)
            return cls(pasta, novos_dados)

    @classmethod
    def carregar_ou_nenhum(cls, pasta):
        pasta = Path(pasta)
        reg_path, _ = caminhos_registro(pasta)
        if not reg_path.is_file():
            return None
        return cls(pasta)

    def aplicar_mutacao(self, fn_geradora_eventos, autor, aplicar=True, revisao_esperada=None):
        """Executa mutação sob lock com optimistic locking e escrita atômica."""
        if not aplicar:
            # Simulação: zero I/O de disco (sem lock file, sem escrita)
            disco = dict(self._dados)
            if revisao_esperada is not None and disco['revisao'] != revisao_esperada:
                raise ErroConcorrenciaRegistro(
                    f'Conflito de revisão: esperada {revisao_esperada}, mas disco possui {disco["revisao"]}.'
                )

            novos_eventos = fn_geradora_eventos(disco)
            if not novos_eventos:
                return disco, []

            prox_seq = len(disco['eventos']) + 1
            eventos_formatados = []
            for ev in novos_eventos:
                if 'id' not in ev:
                    ev['id'] = f'EVT-{prox_seq:06d}'
                ev['seq'] = prox_seq
                ev['timestamp'] = ev.get('timestamp') or agora_iso()
                ev['autor'] = ev.get('autor') or autor
                ev['simulacao'] = True
                eventos_formatados.append(ev)
                prox_seq += 1

            disco_atualizado = dict(disco)
            disco_atualizado['eventos'] = list(disco['eventos']) + eventos_formatados
            disco_atualizado['revisao'] = disco['revisao'] + 1
            disco_atualizado['atualizado_em'] = agora_iso()

            derivar_estado(disco_atualizado)
            # Atualiza self._dados em memória para que mutações subsequentes na mesma instância vejam a simulação!
            self._dados = disco_atualizado
            return disco_atualizado, eventos_formatados

        with trava_exclusiva(self.lock_path):
            disco = carregar_dados_registro(self.registro_path)
            if disco is None:
                disco = self._dados

            if revisao_esperada is not None and disco['revisao'] != revisao_esperada:
                raise ErroConcorrenciaRegistro(
                    f'Conflito de revisão: esperada {revisao_esperada}, mas disco possui {disco["revisao"]}.'
                )

            novos_eventos = fn_geradora_eventos(disco)
            if not novos_eventos:
                return disco, []

            prox_seq = len(disco['eventos']) + 1
            eventos_formatados = []
            for ev in novos_eventos:
                if 'id' not in ev:
                    ev['id'] = f'EVT-{prox_seq:06d}'
                ev['seq'] = prox_seq
                ev['timestamp'] = ev.get('timestamp') or agora_iso()
                ev['autor'] = ev.get('autor') or autor
                ev['simulacao'] = False
                eventos_formatados.append(ev)
                prox_seq += 1

            disco_atualizado = dict(disco)
            disco_atualizado['eventos'] = list(disco['eventos']) + eventos_formatados
            disco_atualizado['revisao'] = disco['revisao'] + 1
            disco_atualizado['atualizado_em'] = agora_iso()

            # Valida estado resultante rigorosamente (lança ErroValidacaoRegistro se inválido)
            derivar_estado(disco_atualizado)

            salvar_dados_registro_atomico(self.registro_path, disco_atualizado)
            self._dados = disco_atualizado
            return disco_atualizado, eventos_formatados

    # ---------- Operações de Domínio ----------

    def abrir_etapa(self, etapa_id, objetivo, plano_ref, autorizacao_ref, base_efetiva, criterios,
                    responsavel='Coordenador', limites='—', origem='real', exigir_revisao=True, autor='Gandalf', aplicar=True, nivel='2'):
        if not criterios:
            raise ErroValidacaoRegistro('Abertura de etapa exige ao menos um critério de aceite.')
        if (not base_efetiva or base_efetiva == '<preencher>') and self._dados.get('versao_inicial'):
            base_efetiva = self._dados['versao_inicial']

        def gerador(dados):
            est = derivar_estado(dados)
            encerradas = [e if isinstance(e, str) else e.get('id') for e in est['etapas_concluidas']] + [e if isinstance(e, str) else e.get('id') for e in est['etapas_excepcionadas']]
            if etapa_id in encerradas:
                raise ErroValidacaoRegistro(f'Etapa {etapa_id} já foi encerrada e não pode ser reaberta.')

            if est['etapa_atual'] and est['etapa_atual']['id'] == etapa_id:
                return []  # No-op idempotente
            ev = {
                'tipo': 'etapa_aberta',
                'dados': {
                    'etapa_id': etapa_id,
                    'nivel': str(nivel),
                    'objetivo': objetivo,
                    'plano_ref': plano_ref,
                    'autorizacao_ref': autorizacao_ref,
                    'base_efetiva': base_efetiva,
                    'criterios': list(criterios),
                    'responsavel': responsavel,
                    'limites': limites,
                    'origem': origem,
                    'exigir_revisao': exigir_revisao,
                },
            }
            return [ev]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def passar_bastao(self, etapa_id, para, autor, nota='', aplicar=True):
        def gerador(dados):
            if not _etapa_existe_no_registro(dados, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            return [{
                'tipo': 'bastao_passado',
                'dados': {'etapa_id': etapa_id, 'para': para, 'nota': nota},
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def registrar_versao(self, etapa_id, versao, impacto='desconhecido', autor='Gandalf', aplicar=True):
        if impacto not in CLASSIFICACOES_IMPACTO:
            raise ErroValidacaoRegistro(f'Impacto inválido: {impacto}')

        def gerador(dados):
            if not _etapa_existe_no_registro(dados, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            return [{
                'tipo': 'versao_atualizada',
                'dados': {'etapa_id': etapa_id, 'versao': versao, 'impacto': impacto},
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def sincronizar_versao(self, etapa_id, versao, impacto='desconhecido', autor='Gandalf', aplicar=True):
        """Atualiza a versão atual no registro de forma atômica sob lock."""
        return self.registrar_versao(etapa_id, versao, impacto=impacto, autor=autor, aplicar=aplicar)

    def registrar_tarefa(self, etapa_id, tarefa_id, especialista, descricao, tipo='implementacao',
                         ferramenta='local', fornecedor='desconhecido', job_id_remoto=None, dependencias=None,
                         arquivos=None, autor='Gandalf', aplicar=True):
        if (not fornecedor or fornecedor == 'desconhecido') and self.perfil:
            forn_p = self.perfil.obter_fornecedor(especialista)
            if forn_p:
                fornecedor = forn_p

        def gerador(dados):
            if not _etapa_existe_no_registro(dados, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            return [{
                'tipo': 'tarefa_criada',
                'dados': {
                    'etapa_id': etapa_id,
                    'tarefa_id': tarefa_id,
                    'especialista': especialista,
                    'fornecedor': fornecedor or 'desconhecido',
                    'descricao': descricao,
                    'tipo': tipo,
                    'ferramenta': ferramenta,
                    'job_id_remoto': job_id_remoto,
                    'dependencias': list(dependencias or []),
                    'arquivos': list(arquivos or []),
                    'estado': 'pendente',
                },
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def atualizar_tarefa(self, etapa_id, tarefa_id, estado, nota='', autor='Gandalf', arquivos=None, aplicar=True):
        if estado not in ESTADOS_TAREFA:
            raise ErroValidacaoRegistro(f'Estado de tarefa inválido: {estado}')

        def gerador(dados):
            if not _etapa_existe_no_registro(dados, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            payload = {'etapa_id': etapa_id, 'tarefa_id': tarefa_id, 'estado': estado, 'nota': nota}
            if arquivos is not None:
                payload['arquivos'] = list(arquivos)
            return [{
                'tipo': 'tarefa_atualizada',
                'dados': payload,
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def registrar_evidencia(self, etapa_id, criterio_id, comando, exit_code, saida,
                            verificador='Gandalf', ambiente='local', versao_entrega='',
                            autor='Gandalf', aplicar=True):
        if not comando or not str(comando).strip():
            raise ErroValidacaoRegistro('Comando de evidência não pode ser vazio.')

        valida = True
        motivo_invalida = []

        if saida is None or not isinstance(saida, str):
            valida = False
            motivo_invalida.append('saída nula ou não textual')
            saida_limpa = ''
        else:
            saida_limpa = saida.strip()

        if not saida_limpa and valida:
            valida = False
            motivo_invalida.append('saída vazia')

        # Validação semântica de placeholders (permite classes <class ...> e tipos genéricos)
        if PADRAO_PLACEHOLDER.search(saida_limpa):
            valida = False
            motivo_invalida.append('placeholder não preenchido')

        # Rejeição ampla de declarações de não execução, ignorando contagens legítimas de skipped (ex: (skipped=2))
        saida_sem_contagem = PADRAO_CONTAGEM_SKIPPED.sub('', saida_limpa)
        if PADRAO_NAO_EXECUTADO.search(saida_sem_contagem):
            valida = False
            motivo_invalida.append('declarado não executado')

        if exit_code != 0:
            valida = False
            motivo_invalida.append(f'código de retorno {exit_code}')

        saida_hash = calcular_hash_conteudo(saida or '')
        amostra = saida_limpa[:300]

        def gerador(dados):
            if not _etapa_existe_no_registro(dados, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            prox_num = len(dados['eventos']) + 1
            ev_id = f"EVD-{criterio_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}_{prox_num:04d}"
            return [{
                'tipo': 'evidencia_registrada',
                'dados': {
                    'etapa_id': etapa_id,
                    'criterio_id': criterio_id,
                    'evidencia_id': ev_id,
                    'comando': comando,
                    'exit_code': exit_code,
                    'saida_resumo': amostra,
                    'saida_hash': saida_hash,
                    'valida': valida,
                    'motivo_invalida': '; '.join(motivo_invalida) if motivo_invalida else None,
                    'verificador': verificador,
                    'ambiente': ambiente,
                    'versao_entrega': versao_entrega,
                },
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def registrar_achado(self, etapa_id, achado_id, severidade, onde, descricao, autor, aplicar=True):
        if severidade not in SEVERIDADES_ACHADO:
            raise ErroValidacaoRegistro(f'Severidade de achado inválida: {severidade}')

        def gerador(dados):
            if not _etapa_existe_no_registro(dados, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            return [{
                'tipo': 'achado_registrado',
                'dados': {
                    'etapa_id': etapa_id,
                    'achado_id': achado_id,
                    'severidade': severidade,
                    'onde': onde,
                    'descricao': descricao,
                },
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def atualizar_achado(self, etapa_id, achado_id, novo_estado, justificativa='', autor='Gandalf', aplicar=True):
        if novo_estado:
            novo_estado = MAPA_SINONIMOS_ESTADO_ACHADO.get(str(novo_estado).lower().strip(), novo_estado)
        if novo_estado not in ESTADOS_ACHADO:
            raise ErroValidacaoRegistro(f'Estado de achado inválido: {novo_estado}')

        def gerador(dados):
            if not _etapa_existe_no_registro(dados, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            return [{
                'tipo': 'achado_atualizado',
                'dados': {
                    'etapa_id': etapa_id,
                    'achado_id': achado_id,
                    'novo_estado': novo_estado,
                    'justificativa': justificativa,
                },
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def implementadores_da_etapa(self, etapa_id, perfil=None):
        """Implementadores registrados da etapa (D03/D08): o responsável na abertura e os especialistas
        das tarefas que não são de revisão. Fornecedor vem da tarefa ou do perfil; None se desconhecido."""
        perfil_ativo = perfil if perfil is not None else self.perfil
        vistos = {}
        for ev in self._dados.get('eventos', []):
            d = ev.get('dados', {})
            if d.get('etapa_id') != etapa_id:
                continue
            if ev.get('tipo') == 'etapa_aberta':
                agente, forn = d.get('responsavel', 'Coordenador'), None
            elif ev.get('tipo') == 'tarefa_criada' and str(d.get('tipo', 'implementacao')) != 'revisao':
                agente, forn = d.get('especialista'), d.get('fornecedor')
            else:
                continue
            if not agente:
                continue
            if forn in (None, '', 'desconhecido') and perfil_ativo is not None:
                try:
                    forn = perfil_ativo.obter_fornecedor(agente)
                except Exception:
                    forn = None
            if forn in ('', 'desconhecido'):
                forn = None
            if agente not in vistos or (vistos[agente] is None and forn):
                vistos[agente] = forn
        return [{'agente': a, 'fornecedor': f} for a, f in vistos.items()]

    def _emulacao_ligada(self, perfil=None):
        """Chave `emulacao` do perfil (B02, Q147); sem perfil legível, desligada (falha fechada)."""
        from sc_perfil import emulacao_ligada
        return emulacao_ligada(perfil if perfil is not None else self.perfil)

    def registrar_parecer(self, etapa_id, parecer_id, revisor, fornecedor_revisor, implementadores,
                          versao_examinada, veredito, criterios_verificados, achados_referenciados=None,
                          lacunas=None, autor='Revisor', aplicar=True,
                          nivel_independencia='A', justificativa_independencia='',
                          perfil=None, aceite_em_emulacao=None, commit=None):
        if veredito not in VEREDITOS_PARECER:
            raise ErroValidacaoRegistro(f'Veredito de parecer inválido: {veredito}')

        if not implementadores:
            raise ErroValidacaoRegistro('Lista de implementadores não pode ser vazia para registro de parecer.')

        if not versao_examinada or not versao_examinada.strip():
            raise ErroValidacaoRegistro('Versão examinada é obrigatória para registro de parecer.')

        if not fornecedor_revisor or fornecedor_revisor.strip().lower() in ('', 'desconhecido'):
            raise ErroValidacaoRegistro('Revisor independente deve declarar fornecedor válido (não pode ser vazio ou desconhecido).')

        nivel_ind = str(nivel_independencia or 'A').strip().upper()
        if nivel_ind not in ('A', 'B', 'C'):
            raise ErroValidacaoRegistro(f'Nível de independência inválido: "{nivel_independencia}". Use "A", "B" ou "C".')

        justif_ind = str(justificativa_independencia or '').strip()
        if nivel_ind in ('B', 'C') and not justif_ind:
            raise ErroValidacaoRegistro(
                f'Nível {nivel_ind} de independência exige justificativa formal declarando a distinção de modelo e sessão.'
            )

        revisor_norm = revisor.strip().lower()
        forn_rev_norm = fornecedor_revisor.strip().lower()

        perfil_ativo = perfil or self.perfil
        if isinstance(perfil_ativo, (str, Path)):
            from sc_perfil import carregar_perfil
            perfil_ativo = carregar_perfil(perfil_ativo)

        # B02: aceite em emulação. None = automático (só se o perfil liga a chave e o fornecedor coincide);
        # True = declarado (exige a chave ligada); False = comportamento antigo.
        emul_ligada = self._emulacao_ligada(perfil_ativo)
        if aceite_em_emulacao and not emul_ligada:
            raise ErroValidacaoRegistro('Aceite em emulação exige a chave "Emulação: sim" na seção "Modo emulação" do perfil.')
        marcar_emulacao = bool(aceite_em_emulacao)
        permite_auto = emul_ligada and aceite_em_emulacao is None and nivel_ind == 'A'

        implementadores_processados = []

        # D08: os implementadores registrados na etapa entram sempre, além dos declarados.
        # Mesmo agente com nomes diferentes (ex.: "Coordenador" e "Gandalf") é reconhecido pela linha do perfil.
        def _linha(nome):
            try:
                return id(perfil_ativo.obter_papel(nome)) if perfil_ativo is not None and perfil_ativo.obter_papel(nome) else None
            except Exception:
                return None
        declarados_nomes, declarados_linhas = set(), set()
        for impl in implementadores:
            nome = impl.split(':', 1)[0] if isinstance(impl, str) else (impl.get('agente', '') if isinstance(impl, dict) else str(impl))
            declarados_nomes.add(str(nome).strip().lower())
            linha = _linha(str(nome).strip())
            if linha:
                declarados_linhas.add(linha)
        implementadores = list(implementadores)
        for reg_impl in self.implementadores_da_etapa(etapa_id, perfil=perfil_ativo):
            if reg_impl['agente'].strip().lower() in declarados_nomes or _linha(reg_impl['agente']) in declarados_linhas:
                continue
            # Com perfil, fornecedor desconhecido é lacuna real e trava o nível A (A2-P01).
            # Sem perfil, só entram os de fornecedor conhecido pela própria tarefa.
            if reg_impl['fornecedor'] or perfil_ativo is not None:
                implementadores.append({'agente': reg_impl['agente'], 'fornecedor': reg_impl['fornecedor'] or ''})

        # Segregação estrita: revisor não pode ser implementador e fornecedor deve ser diferente
        for impl in implementadores:
            if isinstance(impl, str):
                if ':' in impl:
                    p_ag, p_fo = impl.split(':', 1)
                    impl_agente = p_ag.strip()
                    impl_forn = p_fo.strip()
                else:
                    impl_agente = impl.strip()
                    impl_forn = ''
            elif isinstance(impl, dict):
                impl_agente = str(impl.get('agente', '')).strip()
                impl_forn = str(impl.get('fornecedor', '')).strip()
            else:
                impl_agente = str(impl).strip()
                impl_forn = ''

            # Preenchimento de fornecedor pelo perfil se não fornecido
            if (not impl_forn or impl_forn.strip().lower() in ('', 'desconhecido')) and perfil_ativo:
                forn_p = perfil_ativo.obter_fornecedor(impl_agente)
                if forn_p:
                    impl_forn = forn_p

            implementadores_processados.append({
                'agente': impl_agente,
                'fornecedor': impl_forn or 'desconhecido'
            })

            agente_norm = impl_agente.lower()
            forn_impl_norm = (impl_forn or '').strip().lower()

            # Checagem de auto-revisão com identificador de agente (A2-P08)
            coincide = False
            if perfil_ativo:
                coincide = perfil_ativo.sao_mesmo_agente(revisor, impl_agente)
            else:
                from sc_perfil import sao_mesmo_agente
                coincide = sao_mesmo_agente(revisor, impl_agente)

            if not coincide:
                if agente_norm and revisor_norm:
                    if agente_norm == revisor_norm:
                        coincide = True
                    elif re.search(rf'\b{re.escape(agente_norm)}\b', revisor_norm):
                        coincide = True
                    elif re.search(rf'\b{re.escape(revisor_norm)}\b', agente_norm):
                        coincide = True

            if coincide:
                raise ErroValidacaoRegistro(
                    f'Auto-revisão rejeitada: revisor "{revisor}" coincide com o implementador "{impl_agente}".'
                )

            # Nível A exige fornecedor estritamente conhecido e distinto (A2-P01)
            if nivel_ind == 'A':
                if not forn_impl_norm or forn_impl_norm == 'desconhecido':
                    raise ErroValidacaoRegistro(
                        f'Nível A exige que todo implementador declare fornecedor conhecido (A2-P01). '
                        f'Implementador "{impl_agente}" tem fornecedor desconhecido.'
                    )
                if forn_impl_norm == forn_rev_norm:
                    if permite_auto:
                        marcar_emulacao = True
                        continue
                    raise ErroValidacaoRegistro(
                        f'Independência violada: fornecedor do revisor "{fornecedor_revisor}" coincide com o do implementador "{impl_forn}".'
                    )

        if marcar_emulacao:
            # Nunca revisão independente (D-RT-001): nível próprio "E", fora da elegibilidade de publicação.
            nivel_ind = 'E'
            justif_ind = justif_ind or 'aceite em emulação: mesmo fornecedor do implementador (Q147)'

        def gerador(dados):
            if not _etapa_existe_no_registro(dados, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            return [{
                'tipo': 'parecer_registrado',
                'dados': {
                    'etapa_id': etapa_id,
                    'parecer_id': parecer_id,
                    'revisor': revisor,
                    'fornecedor_revisor': fornecedor_revisor,
                    'implementadores': list(implementadores_processados),
                    'versao_examinada': versao_examinada,
                    'veredito': veredito,
                    'criterios_verificados': dict(criterios_verificados),
                    'achados_referenciados': list(achados_referenciados or []),
                    'lacunas': list(lacunas or []),
                    'nivel_independencia': nivel_ind,
                    'justificativa_independencia': justif_ind,
                    **({'commit': commit} if commit else {}),
                    **({'aceite_em_emulacao': True, 'independencia': 'não'} if marcar_emulacao else {}),
                },
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def registrar_troca_papel(self, papel, plataforma, fornecedor, modelo=None, esforco=None,
                              estado='ativo', motivo='', decisao_ref=None, autor='Gandalf', aplicar=True,
                              emulacao=False, perfil=None):
        if emulacao:
            # B02/R4: em emulação o motivo gravado começa por "emulação"; a chave precisa estar ligada.
            if not self._emulacao_ligada(perfil):
                raise ErroValidacaoRegistro('Troca em emulação exige a chave "Emulação: sim" na seção "Modo emulação" do perfil.')
            from sc_perfil import marcar_motivo_emulacao
            motivo = marcar_motivo_emulacao(motivo)

        def gerador(dados):
            return [{
                'tipo': 'papel_trocado',
                'dados': {
                    'papel': papel,
                    'plataforma': plataforma,
                    'fornecedor': fornecedor,
                    'modelo': modelo,
                    'esforco': esforco,
                    'estado': estado,
                    'motivo': motivo,
                    'decisao_ref': decisao_ref,
                    'desde': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                    **({'emulacao': True} if emulacao else {}),
                }
            }]
        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def registrar_decisao(self, etapa_id, decisao_id, quem, referencia, acao, alcance='etapa',
                          autor='Gandalf', aplicar=True, aceite_em_emulacao=False, independencia=None,
                          perfil=None, commit=None):
        extra = {'commit': commit} if commit else {}
        if independencia is not None:
            indep = str(independencia).strip().lower().replace('nao', 'não')
            if indep not in ('sim', 'não'):
                raise ErroValidacaoRegistro(f'Independência inválida: "{independencia}". Use "sim" ou "não".')
            extra['independencia'] = indep
        if aceite_em_emulacao:
            # B02: marca "aceite em emulação" exige a chave ligada e nunca é revisão independente.
            if not self._emulacao_ligada(perfil):
                raise ErroValidacaoRegistro('Aceite em emulação exige a chave "Emulação: sim" na seção "Modo emulação" do perfil.')
            if extra.get('independencia', 'não') != 'não':
                raise ErroValidacaoRegistro('Aceite em emulação tem independência "não"; "sim" é contraditório.')
            extra.update({'aceite_em_emulacao': True, 'independencia': 'não'})

        def gerador(dados):
            if not _etapa_existe_no_registro(dados, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            return [{
                'tipo': 'decisao_registrada',
                'dados': {
                    'etapa_id': etapa_id,
                    'decisao_id': decisao_id,
                    'quem': quem,
                    'referencia': referencia,
                    'acao': acao,
                    'alcance': alcance,
                    **extra,
                },
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def registrar_excecao(self, etapa_id, excecao_id, regra, motivo, referencia_humana, alcance='etapa',
                          autor='Gandalf', aplicar=True):
        if not motivo or len(motivo.strip()) < 10:
            raise ErroValidacaoRegistro('Exceção exige motivo substantivo (mínimo de 10 caracteres).')
        ref_limpa = (referencia_humana or '').strip()
        if not ref_limpa or ref_limpa == 'autorizacao_cli' or len(ref_limpa) < 5 or not PADRAO_DECISAO_REF.match(ref_limpa):
            raise ErroValidacaoRegistro('Exceção exige referência humana explícita a decisão ou autorização de Odival (ex: A-SC-E1-001, DEC-123).')

        regras_validas = ('revisao_independente', 'criterios_gerais', 'achados_bloqueadores', 'fatias_pendentes')
        if regra not in regras_validas and not regra.lower().startswith('criterio:') and not regra.lower().startswith('achado:'):
            raise ErroValidacaoRegistro(f'Regra de exceção não reconhecida: {regra}')

        def gerador(dados):
            if not _etapa_existe_no_registro(dados, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            return [{
                'tipo': 'excecao_registrada',
                'dados': {
                    'etapa_id': etapa_id,
                    'excecao_id': excecao_id,
                    'regra': regra,
                    'motivo': motivo.strip(),
                    'referencia_humana': referencia_humana.strip(),
                    'alcance': alcance,
                },
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def registrar_aviso_cota(self, autor, percentual, janela, data, aplicar=True):
        def gerador(dados):
            return [{
                'tipo': 'aviso_cota_registrado',
                'dados': {
                    'autor': autor,
                    'percentual': percentual,
                    'janela': janela,
                    'data': data,
                },
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar)

    def verificar_condicoes_encerramento(self, etapa_id, dados=None):
        """Avalia se uma etapa atende a todos os requisitos para encerramento."""
        base_dados = dados if dados is not None else self._dados
        est = derivar_estado(base_dados)
        ok, bloqueios, elegivel_pub = verificar_condicoes_encerramento_estado(est, etapa_id)
        return ok, bloqueios

    def encerrar_etapa(self, etapa_id, resumo, autor='Gandalf', aplicar=True, revisao_esperada=None, desfecho=None):
        """Encerra a etapa validando as condições sob trava diretamente sobre o snapshot do disco (REV-009).

        `desfecho` ('rejeitar' ou 'sem-aceite', decididos por pessoa em `sc.py decidir`) encerra sem aceite:
        não há o que condicionar, e a etapa nunca fica elegível à publicação."""
        if desfecho not in (None, 'rejeitar', 'sem-aceite'):
            raise ErroValidacaoRegistro(f'Desfecho inválido: {desfecho}')

        def gerador(disco):
            if not _etapa_existe_no_registro(disco, etapa_id):
                raise ErroValidacaoRegistro(f'Etapa "{etapa_id}" não encontrada no registro.')
            est = derivar_estado(disco)
            if desfecho:
                if not est['etapa_atual'] or est['etapa_atual']['id'] != etapa_id:
                    raise ErroValidacaoRegistro(f'Etapa {etapa_id} não é a etapa ativa no registro.')
                ok, elegivel_pub = True, False
            else:
                ok, bloqueios, elegivel_pub = verificar_condicoes_encerramento_estado(est, etapa_id)
            if not ok:
                raise ErroValidacaoRegistro(f'Encerramento bloqueado: {"; ".join(bloqueios)}')

            return [{
                'tipo': 'etapa_encerrada',
                'dados': {
                    'etapa_id': etapa_id,
                    'resumo': resumo,
                    'elegivel_publicacao': elegivel_pub,
                    **({'desfecho': desfecho} if desfecho else {}),
                },
            }]

        return self.aplicar_mutacao(gerador, autor=autor, aplicar=aplicar, revisao_esperada=revisao_esperada)

    # ---------- Agregação entre Projetos (C10) ----------

    def exportar_resumo_etapa(self, etapa_id):
        est = self.estado()
        aberturas = [ev for ev in self.eventos if ev.get('tipo') == 'etapa_aberta' and ev.get('dados', {}).get('etapa_id') == etapa_id]
        if not aberturas:
            raise ErroValidacaoRegistro(f'Etapa {etapa_id} inexistente para exportação.')

        encerradas = [ev for ev in self.eventos if ev.get('tipo') == 'etapa_encerrada' and ev.get('dados', {}).get('etapa_id') == etapa_id]
        if not encerradas:
            raise ErroValidacaoRegistro(f'Etapa {etapa_id} não está encerrada para exportação.')

        ev_abertura = aberturas[0]
        ev_encerramento = encerradas[0]
        d_abertura = ev_abertura.get('dados', {})
        d_encerramento = ev_encerramento.get('dados', {})

        is_simulacao = ev_abertura.get('simulacao', False) or d_abertura.get('origem') == 'simulacao'

        # Conteúdo semântico estável para cálculo de hash (excluindo timestamp_exportacao) (N4)
        conteudo_semantico = {
            'projeto_origem_id': self._dados['projeto_id'],
            'etapa_id': etapa_id,
            'revisao_origem': self._dados['revisao'],
            'concluida': True,
            'simulacao': is_simulacao,
            'elegivel_publicacao': d_encerramento.get('elegivel_publicacao', False),
            'criterios_total': len(d_abertura.get('criterios', [])),
            'resumo_encerramento': d_encerramento.get('resumo', ''),
        }
        resumo_hash = calcular_hash_conteudo(json.dumps(conteudo_semantico, sort_keys=True))
        payload = dict(conteudo_semantico)
        payload['resumo_hash'] = resumo_hash
        payload['timestamp_exportacao'] = agora_iso()
        return payload

    def importar_resumo_projeto(self, resumo_externo, autor='Gandalf', aplicar=True):
        proj = resumo_externo.get('projeto_origem_id')
        e_id = resumo_externo.get('etapa_id')
        rev = resumo_externo.get('revisao_origem')
        chave = f'{proj}:{e_id}'

        if not proj or not e_id or rev is None:
            raise ErroValidacaoRegistro('Resumo externo incompleto.')

        # Recusa auto-importação do próprio projeto (REV-007)
        if proj == self._dados['projeto_id']:
            raise ErroValidacaoRegistro('Auto-importação recusada: não é permitido importar resumo do próprio projeto.')

        # Recalcular e validar hash do conteúdo semântico (N4)
        hash_esperado = resumo_externo.get('resumo_hash')
        if not hash_esperado:
            raise ErroValidacaoRegistro('Resumo externo sem resumo_hash.')

        conteudo_semantico = {
            k: v for k, v in resumo_externo.items()
            if k not in ('timestamp_exportacao', 'resumo_hash')
        }
        hash_calculado = calcular_hash_conteudo(json.dumps(conteudo_semantico, sort_keys=True))
        if hash_calculado != hash_esperado:
            raise ErroValidacaoRegistro(
                f'Integridade comprometida no resumo externo: hash {hash_esperado} não confere com conteúdo recalculado {hash_calculado}.'
            )

        if not aplicar:
            return True

        with trava_exclusiva(self.lock_path):
            disco = carregar_dados_registro(self.registro_path) or self._dados
            atuais = disco.get('resumos_externos', {})

            if chave in atuais:
                existente = atuais[chave]
                if existente.get('revisao_origem') == rev:
                    if existente.get('resumo_hash') == hash_esperado:
                        return False  # No-op idempotente
                    raise ErroValidacaoRegistro(
                        f'Conflito: chave {chave} já existe com mesma revisão mas conteúdo divergente.'
                    )
                if existente.get('revisao_origem') > rev:
                    return False  # Revisão mais antiga não sobrescreve mais nova

            disco_atualizado = dict(disco)
            disco_atualizado.setdefault('resumos_externos', {})[chave] = dict(resumo_externo)
            disco_atualizado['revisao'] = disco['revisao'] + 1
            disco_atualizado['atualizado_em'] = agora_iso()

            prox_seq = len(disco['eventos']) + 1
            ev = {
                'id': f'EVT-{prox_seq:06d}',
                'seq': prox_seq,
                'tipo': 'resumo_importado',
                'timestamp': agora_iso(),
                'autor': autor,
                'simulacao': False,
                'dados': {'chave': chave, 'resumo': resumo_externo},
            }
            disco_atualizado['eventos'] = list(disco['eventos']) + [ev]

            salvar_dados_registro_atomico(self.registro_path, disco_atualizado)
            self._dados = disco_atualizado
            return True

    # ---------- Projeções Markdown Preservativas (C03) ----------

    def projetar_andamento(self, andamento_md_path, bloco_conteudo_gandalf=None, aplicar=True):
        """Atualiza a seção gerenciada de andamento.md com delimitadores formais preservando texto externo."""
        p = Path(andamento_md_path)
        texto_anterior = p.read_text(encoding='utf-8') if p.is_file() else ''

        est = self.estado()
        etapa = est['etapa_atual']
        etapa_id = etapa['id'] if etapa else 'GERAL'
        rev = self.revisao
        eventos = self._dados.get('eventos', [])
        sha = calcular_hash_conteudo(json.dumps(eventos[-1], sort_keys=True))[:16] if eventos else ('0' * 16)

        marcador_inicio = f'<!-- bloco_gandalf_inicio: {etapa_id} -->'
        marcador_fim = f'<!-- bloco_gandalf_fim: {etapa_id} -->'
        marcador_revisao = f'<!-- registro_revisao: {rev} -->'
        marcador_sincronia = f'<!-- registro_sincronia: rev={rev} sha={sha} -->'
        marcadores_cabecalho = f'{marcador_revisao}\n{marcador_sincronia}'

        if bloco_conteudo_gandalf is None:
            if etapa:
                linhas = [
                    f'## Retorno de Gandalf — {etapa["id"]}',
                    '',
                    marcadores_cabecalho,
                    '',
                    f'Estado: {etapa["estado"]} · Bastão: {etapa["responsavel"]}',
                    f'Objetivo: {etapa["objetivo"]}',
                    f'Base efetiva: {etapa["base_efetiva"]}',
                    '',
                    '### Critérios e Evidências',
                ]
                for c_id, c in etapa['criterios'].items():
                    st = 'atendido' if c['atendido'] else 'pendente'
                    linhas.append(f'- [{st}] {c_id}')
                corpo = '\n'.join(linhas) + '\n'
            else:
                corpo = f'## Retorno de Gandalf — Nenhuma etapa ativa\n\n{marcadores_cabecalho}\n'
        else:
            corpo = bloco_conteudo_gandalf.strip() + '\n'
            if marcador_sincronia not in corpo and marcador_revisao not in corpo:
                corpo = marcadores_cabecalho + '\n\n' + corpo
            elif marcador_sincronia not in corpo:
                corpo = marcador_sincronia + '\n' + corpo

        bloco_novo = f'{marcador_inicio}\n{corpo.rstrip()}\n{marcador_fim}\n'

        if marcador_inicio in texto_anterior and marcador_fim in texto_anterior:
            idx_ini = texto_anterior.index(marcador_inicio)
            idx_fim = texto_anterior.index(marcador_fim) + len(marcador_fim)
            novo_texto = texto_anterior[:idx_ini] + bloco_novo + texto_anterior[idx_fim:]
        else:
            # NUNCA truncar! Sem marcadores desta etapa específica, anexa ao final (N1 / S-C)
            if texto_anterior.strip():
                novo_texto = texto_anterior.rstrip('\n') + '\n\n' + bloco_novo
            else:
                novo_texto = bloco_novo

        if not aplicar:
            return novo_texto

        # Escrita atômica da projeção
        pasta = p.parent
        pasta.mkdir(parents=True, exist_ok=True)
        tmp = pasta / f'{p.name}.tmp.{os.getpid()}'
        tmp.write_text(novo_texto, encoding='utf-8')
        os.replace(tmp, p)
        return novo_texto

    def projetar_historico(self, historico_md_path, entrada_doc=None, aplicar=True):
        """Acrescenta marcos de histórico de forma idempotente e atômica."""
        p = Path(historico_md_path)
        texto_anterior = p.read_text(encoding='utf-8') if p.is_file() else ''

        if not entrada_doc:
            return texto_anterior

        linhas_entrada = entrada_doc.strip().splitlines()
        linha_titulo = linhas_entrada[0] if linhas_entrada else ''

        # Idempotência: se o título do marco já estiver no histórico, não duplica (REV-011)
        if linha_titulo and linha_titulo in texto_anterior:
            return texto_anterior

        novo_texto = (texto_anterior.rstrip('\n') + '\n\n' if texto_anterior.strip() else '') + entrada_doc.strip() + '\n'
        if not aplicar:
            return novo_texto

        pasta = p.parent
        pasta.mkdir(parents=True, exist_ok=True)
        tmp = pasta / f'{p.name}.tmp.{os.getpid()}'
        tmp.write_text(novo_texto, encoding='utf-8')
        os.replace(tmp, p)
        return novo_texto

    def verificar_sincronia_projecao(self, caminho_md):
        sinc, rev_md, rev_reg = verificar_sincronia_projecao(caminho_md, self)
        p = Path(caminho_md)
        sha_md = 'sem-sha'
        if p.is_file():
            m = re.search(r'<!-- registro_sincronia:\s*rev=\d+\s+sha=([a-f0-9]+)\s*-->', p.read_text(encoding='utf-8'))
            if m:
                sha_md = m.group(1)
        eventos = self._dados.get('eventos', [])
        sha_reg = calcular_hash_conteudo(json.dumps(eventos[-1], sort_keys=True))[:16] if eventos else ('0' * 16)
        if sha_md != 'sem-sha' or sha_reg != ('0' * 16):
            msg = f'projeção: rev {rev_md} (sha {sha_md}), registro: rev {rev_reg} (sha {sha_reg})'
        else:
            msg = f'projeção: rev {rev_md}, registro: rev {rev_reg}'
        return sinc, msg


def verificar_sincronia_projecao(caminho_md, registro):
    """Verifica se um arquivo Markdown reflete a revisão atual e o hash do registro."""
    p = Path(caminho_md)
    if not p.is_file():
        return False, None, registro.revisao
    texto = p.read_text(encoding='utf-8')
    m_sinc = re.search(r'<!-- registro_sincronia:\s*rev=(\d+)\s+sha=([a-f0-9]+)\s*-->', texto)
    m_rev = re.search(r'<!-- registro_revisao:\s*(\d+)\s*-->', texto)
    if not m_sinc and not m_rev:
        return False, None, registro.revisao

    eventos = registro._dados.get('eventos', [])
    sha_esperado = calcular_hash_conteudo(json.dumps(eventos[-1], sort_keys=True))[:16] if eventos else ('0' * 16)

    if m_sinc:
        rev_md = int(m_sinc.group(1))
        sha_md = m_sinc.group(2)
        sinc = (rev_md == registro.revisao) and (sha_md == sha_esperado[:len(sha_md)])
        return sinc, rev_md, registro.revisao

    rev_md = int(m_rev.group(1))
    return rev_md == registro.revisao, rev_md, registro.revisao


# ---------- Migração do Formato Legado rodada.md (C11) ----------

def inspecionar_legado_rodada(rodada_md_path):
    p = Path(rodada_md_path)
    if not p.is_file():
        return None
    texto = p.read_text(encoding='utf-8')
    linhas = texto.splitlines()
    titulo = linhas[0] if linhas else ''
    m = re.match(r'^#\s+Rodada\s+([A-Za-z0-9_-]+)\s*—\s*(.*)$', titulo)
    r_id = m.group(1) if m else 'LEGADO'
    meta = m.group(2) if m else 'Rodada legada'

    fatias = []
    for l in linhas:
        m_f = re.match(r'^(\d+)\.\s+(.+?)\s+—\s+(fechada|em andamento|pendente)\b(.*)$', l.strip())
        if m_f:
            fatias.append({
                'n': int(m_f.group(1)),
                'nome': m_f.group(2),
                'estado': m_f.group(3),
                'resto': m_f.group(4).strip(),
            })
    return {'id': r_id, 'meta': meta, 'fatias': fatias, 'texto_original': texto}


def migrar_legado_para_registro(registro, rodada_md_path, autor='Gandalf', aplicar=True):
    legado = inspecionar_legado_rodada(rodada_md_path)
    if not legado:
        return None

    # Idempotência: se a etapa já existe no registro, retorna sem duplicar eventos
    est = registro.estado()
    todas_etapas = list(est['etapas_concluidas']) + list(est['etapas_excepcionadas']) + list(est['etapas_simuladas'])
    if est['etapa_atual']:
        todas_etapas.append(est['etapa_atual']['id'])
    if legado['id'] in todas_etapas:
        return legado

    criterios = [f'FATIA-{f["n"]}' for f in legado['fatias']] or ['FATIA-1']
    registro.abrir_etapa(
        etapa_id=legado['id'],
        objetivo=legado['meta'],
        plano_ref='legado:rodada.md',
        autorizacao_ref='legado:migracao',
        base_efetiva='legado',
        criterios=criterios,
        origem='legado_migrado',
        autor=autor,
        aplicar=aplicar,
    )

    for f in legado['fatias']:
        prova_texto = f['resto'].replace('· prova:', '').strip()
        # Conforme C11 e REV-006: provas textuais antigas tornam-se declaracao_legada_nao_verificada,
        # registradas com exit_code=1 e valida=False, garantindo que o critério NÃO seja marcado como atendido.
        registro.registrar_evidencia(
            etapa_id=legado['id'],
            criterio_id=f'FATIA-{f["n"]}',
            comando='legado',
            exit_code=1,
            saida=f'declaracao_legada_nao_verificada: {prova_texto}' if prova_texto else 'nao executado',
            verificador='migracao_legado',
            ambiente='legado',
            versao_entrega='legado',
            autor=autor,
            aplicar=aplicar,
        )
    return legado
