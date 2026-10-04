#!/usr/bin/env python3
"""Leitor único e validador do perfil do projeto (perfil.md).

Implementa os requisitos de F3 (Q61, Q95, Q109; A2-P01, A2-P08):
- Descoberta canônica de perfil.md (incluindo worktrees);
- Leitura estruturada da tabela de papéis (papel, nome, plataforma, fornecedor, modelo, esforço, estado, desde, motivo);
- Definição de equipe ativa (Q95) com estados: ativo, reserva, espera;
- Conectores declarados por papel e ambiente (Q109);
- Resolução de fornecedor por papel/agente sem inventar padrão (A2-P01);
- Identificadores de agente e conferência estrita de auto-revisão (A2-P08).
"""
import argparse
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


class ErroPerfil(Exception):
    """Erro ao localizar, carregar ou validar o perfil do projeto."""
    pass


AGENTES_CONHECIDOS_PADRAO = {
    'gandalf', 'cirdan', 'barbarvore', 'aragorn', 'elrond',
    'galadriel', 'legolas', 'jules', 'celebrimbor', 'radagast',
    'faramir', 'bilbo'
}

# Chave funcional do papel -> rótulos aceitos na coluna "Papel" do perfil (slug exato).
PAPEIS_CANONICOS = {
    'arquiteto': {'arquiteto', 'cirdan'},
    'revisor': {'revisor', 'revisor_independente', 'barbarvore'},
    'coordenador': {'coordenador', 'coordenacao', 'coordenacao_e_execucao', 'execucao', 'gandalf'},
    'jules': {'jules', 'executor_junior_em_nuvem', 'executor_junior'},
    'executores_locais': {'executores_locais', 'executores', 'executor_local', 'celebrimbor', 'radagast', 'faramir', 'bilbo'},
}
PAPEIS_CANONICOS['execucao'] = PAPEIS_CANONICOS['coordenador']

SUFIXOS_VARIANTE = re.compile(
    r'(?:[-_]?(?:revisor|reviewer|coord|coordenador|dev|qa|ui|agent|[0-9]+))+$',
    re.IGNORECASE
)


def _remover_acentos(texto: str) -> str:
    if not texto:
        return ''
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def _slug(texto: str) -> str:
    s = _remover_acentos(texto).lower().strip()
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')


def _limpar_celula(texto: str) -> str:
    s = texto.strip()
    s = re.sub(r'^\*+|\*+$', '', s)
    s = re.sub(r'^`+|`+$', '', s)
    return s.strip()


def extrair_tabelas_markdown(texto: str) -> list[dict]:
    """Extrai todas as tabelas Markdown do texto com suas seções correspondentes."""
    linhas = texto.splitlines()
    tabelas = []
    secao_atual = ''
    i = 0
    n = len(linhas)

    while i < n:
        linha = linhas[i].strip()
        if linha.startswith('#'):
            secao_atual = linha.lstrip('#').strip()
            i += 1
            continue

        if linha.startswith('|') and linha.endswith('|'):
            # Potencial tabela
            partes_cab = [c.strip() for c in linha.strip('|').split('|')]
            if i + 1 < n:
                linha_sep = linhas[i + 1].strip()
                if (linha_sep.startswith('|') and linha_sep.endswith('|') and
                        all(re.match(r'^:?-+:?$', c.strip()) for c in linha_sep.strip('|').split('|') if c.strip())):
                    # É cabeçalho válido de tabela
                    headers = [_limpar_celula(h) for h in partes_cab]
                    linhas_dados = []
                    malformada = None
                    j = i + 2
                    while j < n:
                        l_dado = linhas[j].strip()
                        if l_dado.startswith('|') and l_dado.endswith('|'):
                            celulas = [_limpar_celula(c) for c in l_dado.strip('|').split('|')]
                            if len(celulas) != len(headers) and malformada is None:
                                malformada = (
                                    f"Perfil malformado: linha com {len(celulas)} colunas, esperava {len(headers)}: '{linhas[j]}'"
                                )
                            linhas_dados.append(celulas)
                            j += 1
                        else:
                            break
                    tabelas.append({
                        'secao': secao_atual,
                        'headers': headers,
                        'rows': linhas_dados,
                        'linha_inicio': i + 1,
                        'malformada': malformada,
                    })
                    i = j
                    continue
        i += 1

    return tabelas


def extrair_base_agente(nome_ou_id: str, conhecidos=None) -> str:
    """Extrai o identificador canônico base de um agente removendo sufixos conhecidos (A2-P08)."""
    if not nome_ou_id:
        return ''
    s = _slug(nome_ou_id)
    conhecidos = conhecidos or AGENTES_CONHECIDOS_PADRAO

    if s in conhecidos:
        return s

    # Tenta remover sufixos como _reviewer, 2, Revisor
    s_sem_sufixo = SUFIXOS_VARIANTE.sub('', s)
    if s_sem_sufixo in conhecidos:
        return s_sem_sufixo

    # Tenta casamento de prefixo com agentes conhecidos
    for c in conhecidos:
        if s.startswith(c) and (len(s) == len(c) or s[len(c):] in ('2', '3', '_reviewer', '_revisor', 'revisor', 'reviewer')):
            return c

    return s_sem_sufixo or s


def sao_mesmo_agente(agente1: str, agente2: str, perfil=None) -> bool:
    """Verifica se dois identificadores/nomes referem-se ao mesmo agente (A2-P08)."""
    if not agente1 or not agente2:
        return False
    if perfil is not None:
        return perfil.sao_mesmo_agente(agente1, agente2)

    b1 = extrair_base_agente(agente1)
    b2 = extrair_base_agente(agente2)
    if b1 and b2 and b1 == b2:
        return True

    # Comparação estrita de slug
    s1 = _slug(agente1)
    s2 = _slug(agente2)
    return bool(s1 and s2 and s1 == s2)


def nome_de_agente(nome: str, perfil=None) -> bool:
    """True se o nome é de agente (identificador ou variante do perfil, lista mínima embutida) ou "Claude".

    Sem distinção de caixa e de acento. Perfil ausente: vale só a lista embutida (falha fechada).
    """
    s = _slug(nome)
    if not s:
        return False
    if s == 'claude' or s.startswith('claude_'):
        return True
    conhecidos = set(AGENTES_CONHECIDOS_PADRAO)
    if perfil is not None:
        conhecidos |= set(perfil.identificadores) | set(perfil.identificadores.values())
    candidatos = {s, extrair_base_agente(s, conhecidos)}
    if perfil is not None:
        candidatos.add(perfil.obter_id_agente(nome))
    return bool(candidatos & conhecidos)


_TITULO_MD = re.compile(r'^\s{0,3}#{1,6}\s*(.+?)\s*#*\s*$')
_LINHA_EMULACAO = re.compile(r'^[-*+]\s*\*\*emulacao\s*:?\*\*\s*:?\s*(.*?)\s*$')
_VALOR_UNICO = re.compile(r'^([a-z]+)(?:\.(?:\s.*)?)?$')  # uma palavra; só ponto final e, depois dele, texto livre
_COMENTARIO_HTML = re.compile(r'<!--.*?(?:-->|\Z)', re.S)  # comentário sem fechamento vale até o fim (falha fechada)


def valor_chave_emulacao(texto: str) -> str | None:
    """Valor da linha `- **Emulação:** <valor>` na seção "Modo emulação" (B02, Q147).

    Devolve o valor único, sem acento e em minúsculas ('sim', 'nao', ...); valor que não é uma palavra só
    ('sim | não', 'sim ou não', 'sim/não') ou linhas em conflito devolvem o texto bruto (nunca 'sim'). None se a
    seção ou a linha não existirem. Só conta a seção cujo título é "Modo emulação" (com sufixo entre parênteses);
    comentário HTML, bloco de código com cerca e bloco indentado (4 espaços ou tab) são ignorados.
    """
    dentro, cerca, valores = False, False, []
    for linha in _COMENTARIO_HTML.sub('', texto or '').splitlines():
        if linha.strip().startswith('```'):
            cerca = not cerca
            continue
        if cerca or linha.startswith(('    ', '\t')):
            continue
        t = _TITULO_MD.match(linha)
        if t:
            titulo = re.sub(r'\s*\([^)]*\)$', '', _remover_acentos(t.group(1)).lower().strip())
            dentro = titulo == 'modo emulacao'
            continue
        if dentro:
            m = _LINHA_EMULACAO.match(_remover_acentos(linha).lower().strip())
            if m:
                u = _VALOR_UNICO.match(m.group(1))
                valores.append(u.group(1) if u else (m.group(1) or '?'))
    if not valores:
        return None
    return valores[0] if len(set(valores)) == 1 else ' / '.join(valores)


def _texto_do_perfil(fonte) -> str:
    if hasattr(fonte, 'texto'):
        return fonte.texto or ''
    if isinstance(fonte, Path) or (isinstance(fonte, str) and fonte.strip() and '\n' not in fonte):
        caminho = Path(fonte)
        if caminho.is_file() or caminho.is_dir():
            return localizar_perfil(caminho).read_text(encoding='utf-8')
    return fonte if isinstance(fonte, str) else ''


def emulacao_ligada(perfil=None) -> bool:
    """True só se o perfil traz `- **Emulação:** sim` na seção "Modo emulação" (B02, Q147).

    Aceita um PerfilProjeto, o caminho do perfil.md (ou da pasta) ou o texto do perfil.
    Chave ausente, valor diferente de "sim", perfil ilegível ou None: False (falha fechada).
    """
    try:
        return valor_chave_emulacao(_texto_do_perfil(perfil)) == 'sim'
    except Exception:
        return False


def marcar_motivo_emulacao(motivo: str = '') -> str:
    """Motivo gravado numa troca de papel em modo emulação (R4): começa sempre por "emulação"."""
    m = (motivo or '').strip()
    return m if m.lower().startswith('emulação') else (f'emulação: {m}' if m else 'emulação')


class PerfilProjeto:
    """Leitor e validador central do perfil do projeto."""

    def __init__(self, caminho_ou_pasta=None, conteudo=None):
        self.caminho = None
        self.texto = ''
        self.papeis = []
        self.equipe_ativa_papeis = []
        self.identificadores = {}  # alias -> canonical_id
        self.conectores = []
        self._nomes_conhecidos = set(AGENTES_CONHECIDOS_PADRAO)

        if conteudo is not None:
            self.texto = conteudo
        else:
            self.caminho = localizar_perfil(caminho_ou_pasta)
            try:
                self.texto = self.caminho.read_text(encoding='utf-8')
            except Exception as e:
                raise ErroPerfil(f'Erro ao ler perfil em {self.caminho}: {e}')

        self._processar()

    def _processar(self):
        if not self.texto or not self.texto.strip():
            raise ErroPerfil('Perfil malformado: arquivo vazio ou sem conteúdo.')

        tabelas = extrair_tabelas_markdown(self.texto)
        if not tabelas:
            raise ErroPerfil('Perfil malformado: nenhuma tabela encontrada no perfil.')

        candidatas_papeis = []
        tabela_ids = None
        tabela_conectores = None

        for tab in tabelas:
            headers_norm = [_slug(h) for h in tab['headers']]
            if 'papel' in headers_norm and any(h in headers_norm for h in ('fornecedor', 'plataforma', 'modelo')):
                candidatas_papeis.append(tab)
            elif 'identificador' in headers_norm or ('variantes' in headers_norm or 'variantes_reconhecidas' in headers_norm):
                if not tab['malformada']:
                    tabela_ids = tab
            elif 'conectores_autorizados' in headers_norm or 'conectores' in headers_norm:
                if not tab['malformada']:
                    tabela_conectores = tab

        if not candidatas_papeis:
            raise ErroPerfil('Perfil malformado: tabela de papéis não encontrada.')
        na_secao = [t for t in candidatas_papeis if 'papel' in _slug(t['secao'])]
        tabela_papeis = (na_secao or candidatas_papeis)[0]
        if tabela_papeis['malformada']:
            raise ErroPerfil(tabela_papeis['malformada'])

        # Processa tabela de papéis
        headers_norm = [_slug(h) for h in tabela_papeis['headers']]
        col_map = {}
        for idx, h in enumerate(headers_norm):
            if h == 'papel':
                col_map['papel'] = idx
            elif h == 'nome':
                col_map['nome'] = idx
            elif h in ('plataforma', 'ferramenta'):
                col_map['plataforma'] = idx
            elif h == 'fornecedor':
                col_map['fornecedor'] = idx
            elif h == 'modelo':
                col_map['modelo'] = idx
            elif h in ('esforco', 'esforço'):
                col_map['esforco'] = idx
            elif 'estado' in h:
                col_map['estado'] = idx
            elif h == 'desde':
                col_map['desde'] = idx
            elif h in ('motivo', 'observacao', 'observacoes'):
                col_map['motivo'] = idx

        minimos = ['papel', 'fornecedor']
        for m in minimos:
            if m not in col_map:
                raise ErroPerfil(f'Perfil malformado: coluna obrigatória "{m}" ausente na tabela de papéis.')

        for linha in tabela_papeis['rows']:
            papel = linha[col_map['papel']] if 'papel' in col_map else ''
            nome = linha[col_map['nome']] if 'nome' in col_map else papel
            plataforma = linha[col_map['plataforma']] if 'plataforma' in col_map else ''
            fornecedor = linha[col_map['fornecedor']] if 'fornecedor' in col_map else ''
            modelo = linha[col_map['modelo']] if 'modelo' in col_map else ''
            esforco = linha[col_map['esforco']] if 'esforco' in col_map else 'padrão'
            estado = linha[col_map['estado']].lower() if 'estado' in col_map else 'ativo'
            desde = linha[col_map['desde']] if 'desde' in col_map else ''
            motivo = linha[col_map['motivo']] if 'motivo' in col_map else ''

            if estado and estado not in ('ativo', 'reserva', 'espera'):
                raise ErroPerfil(
                    f"Perfil malformado: estado inválido '{estado}' para o papel '{papel}'. Estados válidos: ativo, reserva, espera."
                )

            item = {
                'papel': papel,
                'nome': nome,
                'plataforma': plataforma,
                'fornecedor': fornecedor,
                'modelo': modelo,
                'esforco': esforco,
                'estado': estado or 'ativo',
                'desde': desde,
                'motivo': motivo
            }
            self.papeis.append(item)
            if item['estado'] == 'ativo':
                self.equipe_ativa_papeis.append(item)

            # Registra nomes conhecidos
            if nome:
                base_n = _slug(nome)
                self._nomes_conhecidos.add(base_n)
                self.identificadores[base_n] = base_n
            if papel:
                base_p = _slug(papel)
                self._nomes_conhecidos.add(base_p)
                if nome:
                    self.identificadores[base_p] = _slug(nome)

        # Processa identificadores explícitos (A2-P08)
        if tabela_ids:
            h_ids = [_slug(h) for h in tabela_ids['headers']]
            idx_id = h_ids.index('identificador') if 'identificador' in h_ids else 0
            idx_var = -1
            for k in ('variantes_reconhecidas', 'variantes'):
                if k in h_ids:
                    idx_var = h_ids.index(k)
                    break

            for linha in tabela_ids['rows']:
                cid = _slug(linha[idx_id])
                if not cid:
                    continue
                self.identificadores[cid] = cid
                self._nomes_conhecidos.add(cid)
                if idx_var >= 0 and idx_var < len(linha):
                    vars_str = linha[idx_var]
                    for v in vars_str.split(','):
                        v_slug = _slug(v)
                        if v_slug:
                            self.identificadores[v_slug] = cid

        # Processa conectores por papel (Q109)
        if tabela_conectores:
            h_con = [_slug(h) for h in tabela_conectores['headers']]
            idx_p = h_con.index('papel') if 'papel' in h_con else 0
            idx_c = -1
            for k in ('conectores_autorizados', 'conectores'):
                if k in h_con:
                    idx_c = h_con.index(k)
                    break
            idx_a = h_con.index('ambiente') if 'ambiente' in h_con else -1

            for linha in tabela_conectores['rows']:
                self.conectores.append({
                    'papel': linha[idx_p] if idx_p >= 0 else '',
                    'conectores': linha[idx_c] if idx_c >= 0 else '',
                    'ambiente': linha[idx_a] if idx_a >= 0 else ''
                })

    @property
    def emulacao(self) -> bool:
        """Chave `emulacao` do perfil (B02): True só com `- **Emulação:** sim`."""
        return emulacao_ligada(self)

    def obter_papel(self, nome_ou_papel: str) -> dict | None:
        """Obtém a linha do papel por chave funcional, rótulo do papel ou nome do agente (casamento exato)."""
        if not nome_ou_papel:
            return None
        s = _slug(nome_ou_papel)
        rotulos = PAPEIS_CANONICOS.get(s, {s})
        cid = self.obter_id_agente(nome_ou_papel)
        encontrados = []
        for p in self.papeis:
            p_papel = _slug(p['papel'])
            nomes = {_slug(x) for x in re.split(r',|\se\s', p['nome']) if _slug(x)}
            nomes.add(_slug(p['nome']))
            if p_papel in rotulos or s in nomes or (cid and cid in nomes) or any(r in nomes for r in rotulos):
                encontrados.append(p)
        if len(encontrados) > 1:
            if s == 'execucao':
                por_coord = [p for p in encontrados if _slug(p['papel']) in PAPEIS_CANONICOS['coordenador']]
                if por_coord:
                    return por_coord[0]
            por_papel = [p for p in encontrados if _slug(p['papel']) in rotulos]
            if len(por_papel) == 1:
                return por_papel[0]
            raise ErroPerfil(f'Papel ambíguo no perfil: "{nome_ou_papel}" casa com {len(encontrados)} linhas.')
        return encontrados[0] if encontrados else None

    def listar_papeis(self, estado: str = None) -> list[dict]:
        """Lista os papéis do perfil, opcionalmente filtrando por estado."""
        if estado:
            e_norm = estado.strip().lower()
            return [p for p in self.papeis if p['estado'] == e_norm]
        return list(self.papeis)

    def equipe_ativa(self) -> list[dict]:
        """Retorna os papéis em estado 'ativo' (Q95)."""
        return list(self.equipe_ativa_papeis)

    def obter_fornecedor(self, agente_ou_papel: str) -> str | None:
        """Obtém o fornecedor de um agente ou papel.

        NUNCA inventa um fornecedor padrão. Devolve None se não encontrado.
        """
        p = self.obter_papel(agente_ou_papel)
        if p and p.get('fornecedor'):
            forn = p['fornecedor'].strip()
            # Ignora marcadores de modelo não preenchidos ou 'desconhecido'
            if forn.startswith('<') and forn.endswith('>'):
                return None
            if forn.lower() in ('desconhecido', ''):
                return None
            return forn
        return None

    def obter_id_agente(self, agente: str) -> str:
        """Determina o identificador canônico de um agente (A2-P08)."""
        if not agente:
            return ''
        s = _slug(agente)
        if s in self.identificadores:
            return self.identificadores[s]

        # Decomposição por sufixo de variante
        base = extrair_base_agente(s, self._nomes_conhecidos)
        if base in self.identificadores:
            return self.identificadores[base]
        if base in self._nomes_conhecidos:
            return base

        return s

    def sao_mesmo_agente(self, agente1: str, agente2: str) -> bool:
        """Verifica se agente1 e agente2 são a mesma entidade (A2-P08)."""
        if not agente1 or not agente2:
            return False
        id1 = self.obter_id_agente(agente1)
        id2 = self.obter_id_agente(agente2)
        if id1 and id2 and id1 == id2:
            return True

        # Fallback genérico para sufixos
        return sao_mesmo_agente(agente1, agente2)

    def obter_conectores(self, papel_ou_nome: str) -> dict | None:
        """Retorna a configuração de conectores para o papel."""
        if not papel_ou_nome:
            return None
        s = _slug(papel_ou_nome)
        for c in self.conectores:
            if s in _slug(c['papel']):
                return c
        return None


def localizar_perfil(pasta_base=None) -> Path:
    """Localiza o arquivo perfil.md no projeto ou na sociedade canônica."""
    if pasta_base:
        p = Path(pasta_base)
        if p.is_file():
            return p

    # 1. Tenta via localizar_sociedade_canonica se disponível
    try:
        from sc_registro import localizar_sociedade_canonica
        soc = localizar_sociedade_canonica(pasta_base)
        if (soc / 'perfil.md').is_file():
            return soc / 'perfil.md'
    except Exception:
        pass

    base = Path(pasta_base) if pasta_base else Path.cwd()
    candidatos = [
        base / 'sociedade' / 'perfil.md',
        base / 'docs' / 'sociedade' / 'perfil.md',
        base / 'perfil.md'
    ]
    for c in candidatos:
        if c.is_file():
            return c

    raise ErroPerfil(f"Perfil do projeto não encontrado em '{base}'.")


def carregar_perfil(caminho_ou_pasta=None, conteudo=None) -> PerfilProjeto:
    """Função utilitária para instanciar PerfilProjeto."""
    return PerfilProjeto(caminho_ou_pasta=caminho_ou_pasta, conteudo=conteudo)


def atualizar_papel_no_texto(texto_md: str, papel: str, plataforma=None, fornecedor=None,
                             modelo=None, esforco=None, estado=None, motivo=None, desde=None) -> str:
    """Atualiza a linha do papel na tabela Markdown de perfil.md."""
    linhas = texto_md.splitlines()
    nova_linhas = []
    papel_norm = _slug(papel)
    rotulos = PAPEIS_CANONICOS.get(papel_norm, {papel_norm})
    casados = 0
    linhas_alteradas = 0
    desde_str = desde or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    tabela_ativa = False
    col_map = {}

    for linha in linhas:
        l_strip = linha.strip()
        if l_strip.startswith('|') and l_strip.endswith('|'):
            celulas = [_limpar_celula(c) for c in l_strip.strip('|').split('|')]
            headers_norm = [_slug(c) for c in celulas]
            if 'papel' in headers_norm and ('fornecedor' in headers_norm or 'plataforma' in headers_norm):
                tabela_ativa = True
                col_map = {h: idx for idx, h in enumerate(headers_norm)}
                nova_linhas.append(linha)
                continue
            elif tabela_ativa:
                if all(re.match(r'^:?-+:?$', c.strip()) for c in celulas if c.strip()):
                    nova_linhas.append(linha)
                    continue
                # Linha de dados da tabela de papéis
                if 'papel' in col_map and col_map['papel'] < len(celulas):
                    p_atual = _slug(celulas[col_map['papel']])
                    st_atual = _slug(celulas[col_map['estado']]) if 'estado' in col_map and col_map['estado'] < len(celulas) else 'ativo'
                    nomes_atual = set()
                    if 'nome' in col_map and col_map['nome'] < len(celulas):
                        nomes_atual = {_slug(x) for x in re.split(r',|\se\s', celulas[col_map['nome']]) if _slug(x)}

                    eh_alvo = False
                    if papel_norm == 'execucao':
                        # Altera coordenador e todos os especialistas ativos
                        if p_atual in PAPEIS_CANONICOS['coordenador']:
                            eh_alvo = True
                        elif st_atual == 'ativo' and p_atual not in ('arquiteto', 'cirdan', 'revisor', 'revisor_independente', 'barbarvore', 'jules', 'executor_junior_em_nuvem', 'executores_locais', 'executores'):
                            eh_alvo = True
                    else:
                        if p_atual in rotulos or any(n in rotulos for n in nomes_atual) or papel_norm in nomes_atual:
                            eh_alvo = True

                    if eh_alvo:
                        casados += 1
                        substancial = False
                        if plataforma and 'plataforma' in col_map and _slug(celulas[col_map['plataforma']]) != _slug(plataforma):
                            substancial = True
                        if fornecedor and 'fornecedor' in col_map and _slug(celulas[col_map['fornecedor']]) != _slug(fornecedor):
                            substancial = True
                        if modelo and 'modelo' in col_map and _slug(celulas[col_map['modelo']]) != _slug(modelo):
                            substancial = True
                        if esforco:
                            for k in ('esforco', 'esforço'):
                                if k in col_map and _slug(celulas[col_map[k]]) != _slug(esforco):
                                    substancial = True
                        if estado:
                            for k in col_map:
                                if 'estado' in k and _slug(celulas[col_map[k]]) != _slug(estado):
                                    substancial = True
                        if motivo:
                            for k in ('motivo', 'observacao', 'observacoes'):
                                if k in col_map and celulas[col_map[k]].strip() != motivo.strip():
                                    substancial = True

                        if substancial:
                            if plataforma and 'plataforma' in col_map:
                                celulas[col_map['plataforma']] = plataforma
                            if fornecedor and 'fornecedor' in col_map:
                                celulas[col_map['fornecedor']] = fornecedor
                            if modelo and 'modelo' in col_map:
                                celulas[col_map['modelo']] = modelo
                            if esforco:
                                for k in ('esforco', 'esforço'):
                                    if k in col_map:
                                        celulas[col_map[k]] = esforco
                            if estado:
                                for k in col_map:
                                    if 'estado' in k:
                                        celulas[col_map[k]] = estado
                            if 'desde' in col_map:
                                celulas[col_map['desde']] = desde_str
                            if motivo:
                                for k in ('motivo', 'observacao', 'observacoes'):
                                    if k in col_map:
                                        celulas[col_map[k]] = motivo
                            linhas_alteradas += 1

                        linha_recriada = '| ' + ' | '.join(celulas) + ' |'
                        nova_linhas.append(linha_recriada)
                        continue
        else:
            tabela_ativa = False
        nova_linhas.append(linha)

    if casados == 0:
        raise ErroPerfil(f'Papel "{papel}" não encontrado na tabela de papéis.')
    if papel_norm != 'execucao' and casados > 1:
        raise ErroPerfil(
            f'Troca recusada: o papel "{papel}" casa com {casados} linhas da tabela de papéis (esperado: exatamente 1).'
        )
    if linhas_alteradas == 0:
        raise ErroPerfil(
            f'Troca recusada: nenhuma linha do perfil foi alterada (valores já eram idênticos ou nenhuma modificação).'
        )
    return '\n'.join(nova_linhas) + ('\n' if texto_md.endswith('\n') else '')


def atualizar_papel(caminho_ou_pasta, papel, plataforma=None, fornecedor=None,
                    modelo=None, esforco=None, estado=None, motivo=None, desde=None) -> Path:
    """Atualiza o perfil.md em disco gravando as alterações no papel."""
    caminho = localizar_perfil(caminho_ou_pasta)
    texto = caminho.read_text(encoding='utf-8')
    novo_texto = atualizar_papel_no_texto(
        texto, papel, plataforma=plataforma, fornecedor=fornecedor,
        modelo=modelo, esforco=esforco, estado=estado, motivo=motivo, desde=desde
    )
    tmp = caminho.with_name(caminho.name + '.tmp')
    tmp.write_text(novo_texto, encoding='utf-8')
    os.replace(tmp, caminho)
    return caminho


def atualizar_emulacao_no_texto(texto_md: str, ligar: bool, motivo: str = '') -> str:
    """Atualiza a linha do modo emulação na seção '## Modo emulação' do perfil.md."""
    linhas = texto_md.splitlines()
    novas_linhas = []
    dentro_secao = False
    alterou = False

    val_str = 'sim' if ligar else 'não'
    motivo_limpo = (motivo or '').strip()
    nova_linha = f"- **Emulação:** {val_str}. {motivo_limpo}" if motivo_limpo else f"- **Emulação:** {val_str}."

    for linha in linhas:
        t = _TITULO_MD.match(linha)
        if t:
            titulo = re.sub(r'\s*\([^)]*\)$', '', _remover_acentos(t.group(1)).lower().strip())
            dentro_secao = (titulo == 'modo emulacao')
            novas_linhas.append(linha)
            continue
        if dentro_secao:
            m = _LINHA_EMULACAO.match(_remover_acentos(linha).lower().strip())
            if m:
                novas_linhas.append(nova_linha)
                alterou = True
                dentro_secao = False
                continue
        novas_linhas.append(linha)

    if not alterou:
        raise ErroPerfil('Não foi possível encontrar a linha "- **Emulação:**" na seção "Modo emulação" do perfil.')

    return '\n'.join(novas_linhas) + ('\n' if texto_md.endswith('\n') else '')


def atualizar_emulacao(caminho_ou_pasta, ligar: bool, motivo: str = '') -> Path:
    """Atualiza a linha de modo emulação no arquivo perfil.md em disco."""
    caminho = localizar_perfil(caminho_ou_pasta)
    texto = caminho.read_text(encoding='utf-8')
    novo_texto = atualizar_emulacao_no_texto(texto, ligar=ligar, motivo=motivo)
    tmp = caminho.with_name(caminho.name + '.tmp')
    tmp.write_text(novo_texto, encoding='utf-8')
    os.replace(tmp, caminho)
    return caminho


# ---------- Portão por área (B11, B11c) ----------

class ErroPortao(ErroPerfil):
    """Seção "Portão por área" ausente, malformada ou com comando vazio."""


SECAO_PORTAO = re.compile(r'^#{1,6}[ \t]*Port[ãa]o por [áa]rea[ \t]*#*[ \t]*$', re.I | re.M)
PASTAS_SEM_AREA = ('sociedade', 'docs')
PASTA_PARA_TODAS = '.github'
CORINGA = '*'


def _nfc(texto: str) -> str:
    return unicodedata.normalize('NFC', texto)


def _sem_crases(celula: str) -> str:
    c = celula.strip()
    m = re.fullmatch(r'`([^`]*)`', c)
    return (m.group(1) if m else c).strip()


def _prefixos_da_celula(celula: str) -> list[str]:
    """Prefixos de uma célula: tokens entre crases ou separados por vírgula; o texto entre parênteses é comentário."""
    sem_comentario = re.sub(r'\([^)]*\)', ' ', celula)
    entre_crases = re.findall(r'`([^`]+)`', sem_comentario)
    itens = entre_crases if entre_crases else [t for t in re.split(r'[,\s]+', sem_comentario) if t]
    return [_nfc(i.strip()) for i in itens if i.strip()]


def ler_portao_por_area(texto: str) -> list[dict]:
    """Lê a tabela "Portão por área" do perfil: colunas Área, Pasta, Testes, Timeout (s), Prefixos.

    Devolve uma lista de dicts {nome, pasta, comando, timeout, prefixos, coringa}, na ordem do perfil.
    ErroPortao se a seção ou a tabela faltar, se o comando ou o timeout vier vazio ou inválido, ou se duas áreas
    declararem o mesmo prefixo (ou duas pegarem o coringa `*`)."""
    m = SECAO_PORTAO.search(texto or '')
    if not m:
        raise ErroPortao('o perfil não tem a seção "Portão por área" (tabela Área, Pasta, Testes, Timeout (s), Prefixos).')
    resto = texto[m.end():]
    prox = re.search(r'^#{1,6}[ \t]', resto, re.M)
    corpo = resto[:prox.start()] if prox else resto
    linhas = [l.strip() for l in corpo.splitlines() if l.strip().startswith('|')]
    if len(linhas) < 3:
        raise ErroPortao('a seção "Portão por área" não tem tabela com ao menos uma área.')

    def celulas(linha):
        return linha.strip().strip('|').split('|')

    cab = [_slug(_sem_crases(c)) for c in celulas(linhas[0])]
    exigidas = {'area': ('area',), 'pasta': ('pasta',), 'testes': ('testes', 'comando'),
                'timeout': ('timeout_s', 'timeout'), 'prefixos': ('prefixos', 'prefixo')}
    indice = {}
    for chave, nomes in exigidas.items():
        pos = next((i for i, c in enumerate(cab) if c in nomes), None)
        if pos is None:
            raise ErroPortao(f'a tabela "Portão por área" não tem a coluna "{chave}".')
        indice[chave] = pos
    if not re.fullmatch(r'[\s|:\-]+', linhas[1]):
        raise ErroPortao('a tabela "Portão por área" não tem a linha separadora do cabeçalho.')

    areas, vistos, coringas = [], {}, 0
    for linha in linhas[2:]:
        cel = celulas(linha)
        if len(cel) != len(cab):
            raise ErroPortao(f'linha da tabela "Portão por área" com {len(cel)} colunas, esperava {len(cab)}: "{linha}"')
        nome = _sem_crases(cel[indice['area']])
        if not nome:
            raise ErroPortao('área sem nome na tabela "Portão por área".')
        comando = _sem_crases(cel[indice['testes']])
        if not comando or comando.lower() in ('nenhum', 'none', 'null', '—', '-', 'n/a') or (
                comando.startswith('<') and comando.endswith('>')):
            raise ErroPortao(f'a área "{nome}" não tem comando de testes (coluna Testes vazia ou "nenhum").')
        bruto_timeout = _sem_crases(cel[indice['timeout']])
        if not re.fullmatch(r'\d+', bruto_timeout) or int(bruto_timeout) <= 0:
            raise ErroPortao(f'a área "{nome}" tem timeout inválido: "{bruto_timeout}" (use segundos inteiros maiores que 0).')
        pasta = _sem_crases(cel[indice['pasta']]) or '.'
        pasta_norm = Path(pasta.replace('\\', '/'))
        if pasta_norm.is_absolute() or '..' in pasta_norm.parts:
            raise ErroPortao(f'a área "{nome}" tem pasta fora do repositório: "{pasta}".')
        prefixos = _prefixos_da_celula(cel[indice['prefixos']])
        if not prefixos:
            raise ErroPortao(f'a área "{nome}" não tem prefixos.')
        coringa = CORINGA in prefixos
        coringas += 1 if coringa else 0
        explicitos = [p.rstrip('/') for p in prefixos if p != CORINGA]
        for p in explicitos:
            if p in vistos and vistos[p] != nome:
                raise ErroPortao(f'o prefixo "{p}" está nas áreas "{vistos[p]}" e "{nome}".')
            vistos[p] = nome
        if any(a['nome'] == nome for a in areas):
            raise ErroPortao(f'área "{nome}" repetida na tabela "Portão por área".')
        areas.append({'nome': nome, 'pasta': pasta_norm.as_posix(), 'comando': comando,
                      'timeout': int(bruto_timeout), 'prefixos': explicitos, 'coringa': coringa})
    if coringas > 1:
        raise ErroPortao('mais de uma área pega o coringa "*" na tabela "Portão por área".')
    return areas


def _casa_prefixo(rel: str, prefixo: str) -> bool:
    return rel == prefixo or rel.startswith(prefixo + '/')


def areas_do_caminho(rel: str, areas: list[dict]) -> list[str]:
    """Nomes das áreas de um caminho (relativo à raiz do repositório): a do prefixo mais longo da tabela.

    `.github/` conta para todas as áreas; `sociedade/` e `docs/` não são de área nenhuma; o coringa `*` pega o que
    sobra fora dessas pastas. Caminho comparado em NFC."""
    r = _nfc(rel)
    if r.startswith('./'):
        r = r[2:]
    if _casa_prefixo(r, PASTA_PARA_TODAS):
        return [a['nome'] for a in areas]
    melhor, tam = None, -1
    for a in areas:
        for p in a['prefixos']:
            if _casa_prefixo(r, p) and len(p) > tam:
                melhor, tam = a['nome'], len(p)
    if melhor:
        return [melhor]
    if any(_casa_prefixo(r, p) for p in PASTAS_SEM_AREA):
        return []
    return [a['nome'] for a in areas if a['coringa']]


def areas_tocadas(caminhos, areas: list[dict]) -> list[str]:
    """Áreas tocadas por uma lista de caminhos, na ordem da tabela do perfil."""
    tocadas = set()
    for rel in caminhos:
        tocadas.update(areas_do_caminho(rel, areas))
    return [a['nome'] for a in areas if a['nome'] in tocadas]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('perfil', nargs='?', help='caminho do perfil.md ou pasta do projeto')
    p.add_argument('--validar', action='store_true', help='valida a estrutura do perfil')
    p.add_argument('--papeis', action='store_true', help='lista todos os papéis e estados')
    p.add_argument('--equipe-ativa', action='store_true', help='lista apenas papéis ativos')
    p.add_argument('--fornecedor', help='consulta o fornecedor de um agente ou papel')
    p.add_argument('--emulacao', action='store_true', help='mostra se o modo emulação está ligado (sim/não)')
    p.add_argument('--mesmo-agente', nargs=2, metavar=('AGENTE1', 'AGENTE2'),
                   help='testa se dois nomes referem-se ao mesmo agente')

    args = p.parse_args(argv)

    if args.mesmo_agente:
        ag1, ag2 = args.mesmo_agente
        perfil = None
        if args.perfil:
            try:
                perfil = carregar_perfil(args.perfil)
            except Exception:
                pass
        mesmo = sao_mesmo_agente(ag1, ag2, perfil=perfil)
        print(f"'{ag1}' e '{ag2}': {'MESMO AGENTE' if mesmo else 'AGENTES DISTINTOS'}")
        return 0 if mesmo else 1

    try:
        perfil = carregar_perfil(args.perfil)
    except ErroPerfil as e:
        print(f'erro: {e}', file=sys.stderr)
        return 2

    if args.emulacao:
        print('sim' if perfil.emulacao else 'não')
        return 0

    if args.fornecedor:
        forn = perfil.obter_fornecedor(args.fornecedor)
        if forn:
            print(forn)
            return 0
        else:
            print(f"Fornecedor não encontrado para '{args.fornecedor}'.", file=sys.stderr)
            return 1

    if args.equipe_ativa:
        print('=== EQUIPE ATIVA (Q95) ===')
        for papel in perfil.equipe_ativa():
            print(f"- {papel['papel']}: {papel['nome']} ({papel['plataforma']}, {papel['fornecedor']})")
        return 0

    if args.papeis:
        print('=== PAPÉIS DO PROJETO ===')
        for papel in perfil.listar_papeis():
            print(f"- [{papel['estado'].upper()}] {papel['papel']}: {papel['nome']} | Fornecedor: {papel['fornecedor']} | Modelo: {papel['modelo']}")
        return 0

    if args.validar or not any([args.papeis, args.equipe_ativa, args.fornecedor]):
        print(f"Perfil válido: {perfil.caminho or 'em memória'}")
        print(f"Papéis cadastrados: {len(perfil.papeis)} (Ativos: {len(perfil.equipe_ativa_papeis)})")
        print(f"Conectores cadastrados: {len(perfil.conectores)}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
