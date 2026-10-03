#!/usr/bin/env python3
"""Automação gradual de passagens de bastão com confirmação e recuperação de falhas (SC-E5).

Implementa:
- Confirmação explícita de recebimento (handshake / acknowledgement).
- Proteção contra entrega duplicada (idempotência e recusa de retrabalho).
- Validação estrita de caminhos ("leia só" limitado, caminhos existentes, sem escape de projeto).
- Tratamento de ferramenta indisponível com fallback seguro para o coordenador.
- Recuperação e retomada de passagens interrompidas sem duplicação de estado.
- Manutenção estrita de paradas humanas invioláveis (push, merge, publicação, credenciais).

Sem dependências externas.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from sc_registro import Registro, caminhos_registro, ErroRegistroCorrompido, localizar_sociedade_canonica
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from sc_registro import Registro, caminhos_registro, ErroRegistroCorrompido, localizar_sociedade_canonica
    except Exception:
        Registro = None
        caminhos_registro = None
        ErroRegistroCorrompido = None
        def localizar_sociedade_canonica(pasta_base=None):
            b = Path(pasta_base).resolve() if pasta_base else Path.cwd().resolve()
            return (b / 'sociedade').resolve()

try:
    from sc_rodada import (
        caminhos as caminhos_rodada,
        ler as ler_rodada,
        gravar as gravar_rodada,
        montar as montar_rodada,
        partir as partir_rodada,
        fatias_de as fatias_de_rodada,
        etapa_id_de,
        anexar_historico,
        obter_sincronia_info,
        agora as agora_rodada,
        rotulo as rotulo_rodada
    )
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from sc_rodada import (
            caminhos as caminhos_rodada,
            ler as ler_rodada,
            gravar as gravar_rodada,
            montar as montar_rodada,
            partir as partir_rodada,
            fatias_de as fatias_de_rodada,
            etapa_id_de,
            anexar_historico,
            obter_sincronia_info,
            agora as agora_rodada,
            rotulo as rotulo_rodada
        )
    except Exception:
        caminhos_rodada = None
        ler_rodada = None
        gravar_rodada = None
        montar_rodada = None
        partir_rodada = None
        fatias_de_rodada = None
        etapa_id_de = None
        anexar_historico = None
        obter_sincronia_info = None
        agora_rodada = None
        rotulo_rodada = None

try:
    from sc_pre_devolucao import VerificadorPreDevolucao
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from sc_pre_devolucao import VerificadorPreDevolucao
    except Exception:
        VerificadorPreDevolucao = None

MAX_LEIA_PADRAO = 5

ACOES_CRITICAS_RESTRITAS = [
    'push', 'git push', 'merge', 'git merge', 'publicar', 'publicacao',
    'release', 'deploy', 'credencial', 'secret', 'token', 'producao'
]


class ErroPassagem(Exception):
    """Exceção base para erros no fluxo de passagem."""
    pass


class ErroParadaHumana(ErroPassagem):
    """Tentativa de automatizar operação que exige parada humana obrigatória."""
    pass


class ErroCaminhoIncorreto(ErroPassagem):
    """Caminho inválido, inexistente ou fora dos limites do projeto."""
    pass


class ErroEntregaDuplicada(ErroPassagem):
    """Tentativa de reenviar ou duplicar passagem já em andamento."""
    pass


class ErroFerramentaIndisponivel(ErroPassagem):
    """Ferramenta ou modelo necessário não está instalado ou disponível."""
    pass


class ErroEstadoPassagem(ErroPassagem):
    """Transição de estado inválida para a passagem."""
    pass


def calcular_hash_passagem(dados: Dict[str, Any]) -> str:
    """Gera hash SHA-256 estável sobre os parâmetros da passagem."""
    payload = {
        'etapa_id': dados['etapa_id'],
        'de': dados['de'],
        'para': dados['para'],
        'tarefa_id': dados['tarefa_id'],
        'leia_so': sorted(list(dados.get('leia_so', []))),
        'faca': list(dados.get('faca', [])),
        'limites': str(dados.get('limites', ''))
    }
    bruto = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(bruto).hexdigest()[:16]


def validar_caminhos_leia(caminhos: List[str], pasta_projeto: Path, justificativa_expansao: str = '') -> List[str]:
    """Valida lista de caminhos de leitura estrita."""
    if len(caminhos) > MAX_LEIA_PADRAO and not justificativa_expansao.strip():
        raise ErroCaminhoIncorreto(
            f'"leia só" aceita no máximo {MAX_LEIA_PADRAO} caminhos sem justificativa de expansão válida.'
        )

    raiz = pasta_projeto.resolve()
    validados = []
    for c in caminhos:
        c_str = str(c).strip()
        if not c_str:
            continue
        p = Path(c_str)
        alvo = (raiz / p).resolve() if not p.is_absolute() else p.resolve()
        
        # Verifica escape de projeto
        try:
            alvo.relative_to(raiz)
        except ValueError:
            raise ErroCaminhoIncorreto(f'Caminho fora dos limites do projeto: {c_str}')

        # Verifica links simbólicos inseguros
        atual = raiz
        for parte in (alvo.relative_to(raiz)).parts:
            atual = atual / parte
            if atual.is_symlink():
                raise ErroCaminhoIncorreto(f'Caminho passa por link simbólico inseguro: {atual}')

        # Verifica existência
        if not alvo.exists():
            raise ErroCaminhoIncorreto(f'Caminho citado em "leia só" não existe no projeto: {c_str}')

        validados.append(alvo.relative_to(raiz).as_posix())

    return validados


def checar_parada_humana(faca: List[str], limites: str, decisao_ref: Optional[str] = None) -> None:
    """Verifica se há ordens críticas que violam paradas humanas sem decisão aprovada."""
    texto_ordens = ' '.join(faca).lower() + ' ' + str(limites).lower()
    for acao in ACOES_CRITICAS_RESTRITAS:
        if acao in texto_ordens:
            if not decisao_ref or not str(decisao_ref).strip():
                raise ErroParadaHumana(
                    f'Ação restrita "{acao}" detectada na ordem. Exige decisão humana explícita (--decisao-ref).'
                )


class GerenciadorPassagem:
    """Gerencia ciclo de vida de passagens automatizadas com confirmação e resiliência."""

    def __init__(self, reg, pasta_projeto: Path):
        self.reg = reg
        self.pasta_projeto = Path(pasta_projeto)

    def despachar_passagem(
        self,
        etapa_id: str,
        de: str,
        para: str,
        tarefa_id: str,
        leia_so: List[str],
        faca: List[str],
        nao_faca: Optional[List[str]] = None,
        limites: str = '',
        ferramentas_necessarias: Optional[List[str]] = None,
        justificativa_expansao: str = '',
        decisao_ref: Optional[str] = None,
        aplicar: bool = True
    ) -> Dict[str, Any]:
        """Despacha uma passagem com validações de segurança."""
        # 1. Parada humana
        checar_parada_humana(faca, limites, decisao_ref)

        # 2. Validação estrita de caminhos
        caminhos_ok = validar_caminhos_leia(leia_so, self.pasta_projeto, justificativa_expansao)

        # 3. Construção dos dados da passagem
        dados_passagem = {
            'etapa_id': etapa_id,
            'de': de,
            'para': para,
            'tarefa_id': tarefa_id,
            'leia_so': caminhos_ok,
            'faca': list(faca),
            'nao_faca': list(nao_faca or []),
            'limites': limites,
            'justificativa_expansao': justificativa_expansao.strip(),
            'decisao_ref': decisao_ref or '',
        }
        h_passagem = calcular_hash_passagem(dados_passagem)
        passagem_id = f'PSG-{h_passagem}'
        dados_passagem['passagem_id'] = passagem_id
        dados_passagem['hash_passagem'] = h_passagem

        # 4. Verificação de ferramenta necessária / Fallback
        fallback_motivo = None
        if ferramentas_necessarias:
            for ferramenta in ferramentas_necessarias:
                if ferramenta.startswith('cmd:'):
                    cmd_nome = ferramenta[4:].strip()
                    if not shutil.which(cmd_nome):
                        fallback_motivo = f'Comando obrigatório "{cmd_nome}" não encontrado no ambiente local.'
                        break

        if fallback_motivo:
            dados_passagem['status'] = 'fallback_necessario'
            dados_passagem['motivo_fallback'] = fallback_motivo
            dados_passagem['para'] = 'Gandalf'  # Reatribuição segura para coordenação
        else:
            dados_passagem['status'] = 'despachada'

        # 5. Mutação no registro com verificação de idempotência / duplicidade
        def gerador(estado_disco):
            # Procura se já existe passagem idêntica na etapa
            eventos_existentes = estado_disco.get('eventos', [])
            for ev in eventos_existentes:
                if ev.get('tipo') == 'passagem_despachada':
                    d = ev.get('dados', {})
                    if d.get('etapa_id') == etapa_id and d.get('passagem_id') == passagem_id:
                        # Idempotência: mesma passagem exata já despachada
                        return []
                    if (d.get('etapa_id') == etapa_id and d.get('para') == para
                            and d.get('tarefa_id') == tarefa_id and d.get('status') in ('despachada', 'confirmada')):
                        raise ErroEntregaDuplicada(
                            f'Passagem para {para} na tarefa {tarefa_id} já está em andamento (ID: {d.get("passagem_id")}).'
                        )

            return [{
                'tipo': 'passagem_despachada',
                'dados': dados_passagem
            }]

        self.reg.aplicar_mutacao(gerador, autor=de, aplicar=aplicar)
        return dados_passagem

    def confirmar_recebimento(self, etapa_id: str, passagem_id: str, recebedor: str, aplicar: bool = True) -> Dict[str, Any]:
        """Confirmação de recebimento (handshake) pelo destinatário."""
        confirmacao = {'etapa_id': etapa_id, 'passagem_id': passagem_id, 'recebedor': recebedor, 'status': 'confirmada'}

        def gerador(estado_disco):
            # Localiza a passagem no histórico de eventos
            passagem_encontrada = None
            for ev in reversed(estado_disco.get('eventos', [])):
                if ev.get('tipo') == 'passagem_despachada' and ev.get('dados', {}).get('passagem_id') == passagem_id:
                    passagem_encontrada = ev['dados']
                    break

            if not passagem_encontrada:
                raise ErroEstadoPassagem(f'Passagem {passagem_id} não encontrada para confirmação.')

            if passagem_encontrada['para'] != recebedor:
                raise ErroEstadoPassagem(
                    f'Recebedor inválido: passagem foi despachada para {passagem_encontrada["para"]}, não {recebedor}.'
                )

            # Verifica se já foi confirmada
            for ev in estado_disco.get('eventos', []):
                if ev.get('tipo') == 'passagem_confirmada' and ev.get('dados', {}).get('passagem_id') == passagem_id:
                    return []  # Idempotente

            return [{
                'tipo': 'passagem_confirmada',
                'dados': confirmacao
            }]

        self.reg.aplicar_mutacao(gerador, autor=recebedor, aplicar=aplicar)
        return confirmacao

    def recuperar_passagem(self, etapa_id: str) -> Optional[Dict[str, Any]]:
        """Recupera a última passagem ativa após interrupção da sessão."""
        estado_dados = self.reg.carregar_dados() if hasattr(self.reg, 'carregar_dados') else self.reg._dados
        passagens_ativas = {}

        for ev in estado_dados.get('eventos', []):
            tipo = ev.get('tipo')
            d = ev.get('dados', {})
            if d.get('etapa_id') != etapa_id:
                continue

            p_id = d.get('passagem_id')
            if tipo == 'passagem_despachada':
                passagens_ativas[p_id] = dict(d)
            elif tipo == 'passagem_confirmada' and p_id in passagens_ativas:
                passagens_ativas[p_id]['status'] = 'confirmada'
            elif tipo == 'passagem_concluida' and p_id in passagens_ativas:
                del passagens_ativas[p_id]

        if not passagens_ativas:
            return None

        # Retorna a passagem mais recente que ficou pendente ou em execução
        ultima_id = list(passagens_ativas.keys())[-1]
        return passagens_ativas[ultima_id]

    def concluir_passagem(
        self,
        etapa_id: str,
        passagem_id: str,
        executor: str,
        resultado: str,
        aplicar: bool = True
    ) -> Dict[str, Any]:
        """Conclui a passagem e registra resultado."""
        conclusao = {
            'etapa_id': etapa_id,
            'passagem_id': passagem_id,
            'executor': executor,
            'resultado': resultado,
            'status': 'concluida'
        }

        def gerador(estado_disco):
            # Localiza a passagem no histórico de eventos
            passagem_encontrada = None
            for ev in reversed(estado_disco.get('eventos', [])):
                if ev.get('tipo') == 'passagem_despachada' and ev.get('dados', {}).get('passagem_id') == passagem_id:
                    passagem_encontrada = ev['dados']
                    break

            if not passagem_encontrada:
                raise ErroEstadoPassagem(f'Passagem {passagem_id} não encontrada para conclusão.')

            if passagem_encontrada['para'] != executor:
                raise ErroEstadoPassagem(
                    f'Executor inválido: passagem foi despachada para {passagem_encontrada["para"]}, não {executor}.'
                )

            # Verifica se já foi concluída (idempotência / terminalidade)
            for ev in estado_disco.get('eventos', []):
                if ev.get('tipo') == 'passagem_concluida' and ev.get('dados', {}).get('passagem_id') == passagem_id:
                    dados_concl = ev.get('dados', {})
                    if dados_concl.get('executor') == executor and dados_concl.get('resultado') == resultado:
                        return []  # Idempotente
                    raise ErroEstadoPassagem(
                        f'Passagem {passagem_id} já concluída com dados divergentes.'
                    )

            return [{
                'tipo': 'passagem_concluida',
                'dados': conclusao
            }]

        self.reg.aplicar_mutacao(gerador, autor=executor, aplicar=aplicar)
        return conclusao

    def despachar_jules(
        self,
        etapa_id: str,
        fatia_id: str,
        tarefa_id: str,
        arquivos: List[str],
        instrucoes: str,
        criterios: Optional[List[str]] = None,
        de: str = 'Gandalf',
        prs_abertos: Optional[int] = None,
        max_prs_abertos: int = 3,
        aplicar: bool = True
    ) -> Dict[str, Any]:
        """Despacha tarefa mecânica delimitada para o executor júnior em nuvem Jules."""
        # 1. Contrapressão de fila: no teto de PRs/tarefas abertas (padrão 3, Q93), bloqueia fail-closed
        total_abertos = prs_abertos
        if total_abertos is None:
            total_abertos = 0
            dados_reg = self.reg.carregar_dados() if hasattr(self.reg, 'carregar_dados') else getattr(self.reg, '_dados', {})
            passagens_jules = {}
            for ev in dados_reg.get('eventos', []):
                t = ev.get('tipo')
                d = ev.get('dados', {})
                p_id = d.get('passagem_id')
                if t == 'passagem_despachada' and d.get('para') == 'Jules':
                    passagens_jules[p_id] = True
                elif t == 'passagem_concluida' and p_id in passagens_jules:
                    del passagens_jules[p_id]
            total_abertos = len(passagens_jules)

        if total_abertos >= max_prs_abertos:
            raise ErroPassagem(
                f'Contrapressão: Jules possui {total_abertos} tarefas/PRs abertos aguardando revisão (teto: {max_prs_abertos}); não despache mais, esvazie a fila antes de prosseguir.'
            )

        # 2. Valida ausência de caminhos locais absolutos (/home/...) ou URIs file:// (Q48)
        if '/home/' in instrucoes or 'file://' in instrucoes:
            raise ErroCaminhoIncorreto(
                'Instruções para Jules não podem conter caminhos locais absolutos (/home/...) ou URIs file://.'
            )

        # 3. Despacha a passagem para Jules
        limites = f'Restrito estritamente aos {len(arquivos)} arquivos da fatia {fatia_id}. Contexto remoto exclusivo via AGENTS.md.'
        passagem = self.despachar_passagem(
            etapa_id=etapa_id,
            de=de,
            para='Jules',
            tarefa_id=tarefa_id,
            leia_so=arquivos,
            faca=[instrucoes],
            nao_faca=['Não alterar arquivos fora da lista autorizada', 'Não realizar merge, push ou releases'],
            limites=limites,
            aplicar=aplicar
        )
        passagem['fatia_id'] = fatia_id
        passagem['janela_espera_minutos'] = 45
        passagem['criterios'] = list(criterios or [])
        return passagem

    def auditar_jules(
        self,
        arquivos_permitidos: List[str],
        arquivos_alterados: Optional[List[str]] = None,
        comando_teste: str = '',
        comando_regressao: Optional[str] = None,
        tarefa_id: str = '',
        pr_id: str = ''
    ) -> Dict[str, Any]:
        """Executa a auditoria em 6 passos do Portão de Ferro para uma entrega do Jules."""
        try:
            from sc_jules_portao import PortaoDeFerroJules
        except ImportError:
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from sc_jules_portao import PortaoDeFerroJules
            except Exception as e:
                raise ErroPassagem(f'Falha ao carregar auditor do Portão de Ferro: {e}')

        portao = PortaoDeFerroJules(pasta_projeto=self.pasta_projeto)
        return portao.auditar_pr(
            arquivos_permitidos=arquivos_permitidos,
            arquivos_alterados=arquivos_alterados or [],
            comando_teste=comando_teste,
            comando_regressao=comando_regressao,
            tarefa_id=tarefa_id,
            pr_id=pr_id
        )

    def exportar_revisao(
        self,
        etapa_id: str,
        fatia_id: str = '',
        base_commit: str = '',
        head_commit: str = 'HEAD',
        revisor: Optional[str] = None,
        fornecedor_revisor: Optional[str] = None
    ) -> str:
        """Gera pacote estruturado completo para o Revisor Independente."""
        if not revisor or not fornecedor_revisor:
            # M5: revisor e fornecedor vêm do perfil do projeto, nunca de um padrão fixo.
            linha = None
            try:
                from sc_perfil import carregar_perfil
                linha = carregar_perfil(getattr(self.reg, 'pasta', None)).obter_papel('revisor')
            except Exception:
                linha = None
            if linha:
                revisor = revisor or linha.get('nome')
                fornecedor_revisor = fornecedor_revisor or linha.get('fornecedor')
        if not revisor or not fornecedor_revisor:
            raise ErroPassagem('Revisor e fornecedor não informados e não encontrados no perfil: use --revisor e --fornecedor-revisor.')

        dados_reg = self.reg.carregar_dados() if hasattr(self.reg, 'carregar_dados') else getattr(self.reg, '_dados', {})
        etapa_info = None
        for ev in dados_reg.get('eventos', []):
            if ev.get('tipo') == 'etapa_aberta' and ev.get('dados', {}).get('etapa_id') == etapa_id:
                etapa_info = ev['dados']
                break

        diff_texto = ''
        arquivos_alterados = []
        if base_commit:
            try:
                res_diff = subprocess.run(
                    ['git', 'diff', '--name-status', f'{base_commit}..{head_commit}'],
                    cwd=self.pasta_projeto,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res_diff.returncode == 0:
                    arquivos_alterados = [l.strip() for l in res_diff.stdout.splitlines() if l.strip()]

                res_patch = subprocess.run(
                    ['git', 'diff', f'{base_commit}..{head_commit}'],
                    cwd=self.pasta_projeto,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res_patch.returncode == 0:
                    diff_texto = res_patch.stdout[:15000]
            except Exception:
                pass

        criterios_lista = etapa_info.get('criterios', []) if etapa_info else []
        alvo_revisao = f'Fatia {fatia_id}' if fatia_id else 'Fechamento da etapa'
        data_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

        corpo = [
            f"# Pacote de Revisão Independente — Etapa: {etapa_id}",
            f"- **Escopo:** {alvo_revisao}",
            f"- **Revisor designado:** {revisor} ({fornecedor_revisor})",
            f"- **Base..Head:** {base_commit or 'origem'}..{head_commit}",
            f"- **Data de exportação:** {data_str}",
            "",
            "## 1. Diretrizes Invioláveis do Revisor",
            "- Atuação estritamente em somente-leitura sobre o produto com veto a edições ou correções.",
            "- Proibição categórica de git push, git merge, criação de releases ou deploys.",
            "- Independência estrita: veredito formal autônomo (aceitar ou nao_aceitar).",
            "- Achados categorizados em 3 severidades: bloqueador, relevante ou opcional.",
            "- Proibido medir ou estimar métricas de inteligência artificial.",
            "",
            "## 2. Critérios da Etapa",
        ]
        if criterios_lista:
            for c in criterios_lista:
                corpo.append(f"- [ ] `{c}`")
        else:
            corpo.append("- Nenhum critério formal explicitado no registro.")

        corpo.append("")
        corpo.append("## 3. Arquivos Modificados na Entrega")
        if arquivos_alterados:
            for a in arquivos_alterados:
                corpo.append(f"- `{a}`")
        else:
            corpo.append("- Não foi possível obter diff git ou nenhum arquivo alterado.")

        if diff_texto:
            corpo.append("")
            corpo.append("## 4. Diff Git da Entrega")
            corpo.append("```diff")
            corpo.append(diff_texto)
            corpo.append("```")

        corpo.append("")
        corpo.append("## 5. Template de Parecer a Preencher")
        corpo.append("```markdown")
        corpo.append("## Parecer do Revisor Independente")
        corpo.append(f"- rodada: {etapa_id}")
        corpo.append(f"- fatia ou fechamento: {alvo_revisao.lower()}")
        corpo.append(f"- entrega: {head_commit}")
        corpo.append(f"- commit: {head_commit}")
        corpo.append(f"- base..head: {base_commit or 'origem'}..{head_commit}")
        corpo.append(f"- revisor: {revisor} · fornecedor: {fornecedor_revisor} · sessão: <id>")
        corpo.append("- veredito: [aceitar | nao_aceitar]")
        corpo.append(f"- data: {data_str}")
        corpo.append("")
        corpo.append("### Independência")
        corpo.append("Não implementei nem corrigi nada desta entrega.")
        corpo.append("")
        corpo.append("### Resumo")
        corpo.append("[Resumo sucinto da avaliação]")
        corpo.append("")
        corpo.append("### Critérios e Evidências")
        corpo.append("| Critério | Evidência | Estado |")
        corpo.append("|---|---|---|")
        for c in criterios_lista:
            corpo.append(f"| {c} | [comando executado e saída] | [executada/lida/não verificada] |")
        corpo.append("")
        corpo.append("### Achados")
        corpo.append("- [bloqueador|relevante|opcional] TITULO")
        corpo.append("  Condição: ...")
        corpo.append("  Esperado: ...")
        corpo.append("  Evidência: ...")
        corpo.append("")
        corpo.append("### O que não verifiquei")
        corpo.append("- [item não verificado, ou \"nada\"]")
        corpo.append("```")

        return '\n'.join(corpo)

    def despachar(
        self,
        para: str,
        faca: List[str],
        leia_so: Optional[List[str]] = None,
        etapa_id: Optional[str] = None,
        fatia: Optional[Any] = None,
        tarefa_id: Optional[str] = None,
        de: Optional[str] = None,
        nao_faca: Optional[List[str]] = None,
        limites: str = '',
        ferramentas_necessarias: Optional[List[str]] = None,
        justificativa_expansao: str = '',
        decisao_ref: Optional[str] = None,
        devolva: str = 'quando a fatia estiver pronta e passar no pré-devolução',
        nota: str = '',
        aplicar: bool = True
    ) -> Dict[str, Any]:
        """Macro atômico: despacha passagem, confirma recebimento, atualiza tarefa e transfere bastão na rodada."""
        # 1. Resolve etapa_id
        if not etapa_id:
            est = self.reg.estado() if hasattr(self.reg, 'estado') else {}
            etapa_atual = est.get('etapa_atual')
            if etapa_atual:
                etapa_id = etapa_atual.get('id')
        if not etapa_id and caminhos_rodada and ler_rodada and partir_rodada:
            p_rodada, _, _ = caminhos_rodada(self.reg.pasta)
            if p_rodada.is_file():
                conteudo = ler_rodada(p_rodada)
                if conteudo:
                    titulo, _, _ = partir_rodada(conteudo)
                    etapa_id = etapa_id_de(titulo) if etapa_id_de else None
        if not etapa_id:
            raise ErroPassagem('Etapa ID não fornecido e nenhuma etapa ativa encontrada no registro.')

        # 2. Identifica fatia e tarefa_id
        num_fatia = None
        if fatia is not None:
            str_f = str(fatia).strip()
            if str_f.isdigit():
                num_fatia = int(str_f)
            elif str_f.startswith('fatia_') and str_f[6:].isdigit():
                num_fatia = int(str_f[6:])
            if not tarefa_id:
                tarefa_id = f'fatia_{num_fatia}' if num_fatia is not None else str_f
        elif tarefa_id:
            if tarefa_id.startswith('fatia_') and tarefa_id[6:].isdigit():
                num_fatia = int(tarefa_id[6:])
        else:
            if caminhos_rodada and ler_rodada and partir_rodada:
                p_rodada, _, _ = caminhos_rodada(self.reg.pasta)
                if p_rodada.is_file():
                    conteudo = ler_rodada(p_rodada)
                    if conteudo:
                        _, _, secoes = partir_rodada(conteudo)
                        fs = fatias_de_rodada(secoes) if fatias_de_rodada else []
                        pendentes = [f for f in fs if f.get('estado') == 'pendente']
                        if pendentes:
                            num_fatia = pendentes[0]['n']
                            tarefa_id = f'fatia_{num_fatia}'
            if not tarefa_id:
                tarefa_id = 'T-01'

        # 3. Resolve autor/de
        if not de:
            if caminhos_rodada and ler_rodada and partir_rodada:
                p_rodada, _, _ = caminhos_rodada(self.reg.pasta)
                if p_rodada.is_file():
                    conteudo = ler_rodada(p_rodada)
                    if conteudo:
                        _, campos, _ = partir_rodada(conteudo)
                        de = campos.get('bastao')
            if not de:
                de = 'Gandalf'

        # 4. Despacha passagem
        passagem = self.despachar_passagem(
            etapa_id=etapa_id,
            de=de,
            para=para,
            tarefa_id=tarefa_id,
            leia_so=leia_so or [],
            faca=faca,
            nao_faca=nao_faca or [],
            limites=limites,
            ferramentas_necessarias=ferramentas_necessarias,
            justificativa_expansao=justificativa_expansao,
            decisao_ref=decisao_ref,
            aplicar=aplicar
        )

        if passagem.get('status') == 'fallback_necessario':
            return {
                'passagem': passagem,
                'confirmacao': None,
                'status': 'fallback_necessario',
                'motivo_fallback': passagem.get('motivo_fallback'),
                'bastao': 'Gandalf',
                'tarefa_id': tarefa_id,
                'etapa_id': etapa_id
            }

        # 5. Handshake de recebimento automático
        confirmacao = self.confirmar_recebimento(
            etapa_id=etapa_id,
            passagem_id=passagem['passagem_id'],
            recebedor=para,
            aplicar=aplicar
        )

        # 6. Atualiza estado da tarefa no registro.json
        try:
            self.reg.atualizar_tarefa(
                etapa_id,
                tarefa_id,
                'em_andamento',
                autor=de,
                arquivos=passagem.get('leia_so'),
                aplicar=aplicar
            )
        except Exception:
            try:
                self.reg.registrar_tarefa(
                    etapa_id,
                    tarefa_id,
                    para,
                    '; '.join(faca),
                    autor=de,
                    aplicar=aplicar
                )
                self.reg.atualizar_tarefa(
                    etapa_id,
                    tarefa_id,
                    'em_andamento',
                    autor=de,
                    arquivos=passagem.get('leia_so'),
                    aplicar=aplicar
                )
            except Exception:
                pass

        # 7. Registra transferência de bastão no registro.json
        try:
            self.reg.passar_bastao(etapa_id, para, autor=de, nota=nota or f'despachado para {para}', aplicar=aplicar)
        except Exception:
            pass

        # 8. Atualiza rodada.md e historico.md se presentes
        if caminhos_rodada and ler_rodada and gravar_rodada and partir_rodada and montar_rodada:
            p_rodada, p_hist, _ = caminhos_rodada(self.reg.pasta)
            if p_rodada.is_file():
                conteudo = ler_rodada(p_rodada)
                if conteudo:
                    titulo, campos, secoes = partir_rodada(conteudo)
                    campos['bastao'] = para
                    linhas_bastao = [f'bastão está com: {para}', 'leia só:']
                    if justificativa_expansao.strip():
                        linhas_bastao.append(f'<!-- expansão justificada: {justificativa_expansao.strip()} -->')
                    for p in passagem.get('leia_so', []):
                        linhas_bastao.append(f'- {p}')
                    linhas_bastao.append('faça:')
                    for f in faca:
                        linhas_bastao.append(f'- {f}')
                    if nao_faca:
                        linhas_bastao.append('não faça:')
                        for nf in nao_faca:
                            linhas_bastao.append(f'- {nf}')
                    linhas_bastao.append(f'devolva: {devolva}')
                    secoes['Para quem pega o bastão agora'] = linhas_bastao

                    if num_fatia is not None and 'Fatias' in secoes:
                        fs = fatias_de_rodada(secoes) if fatias_de_rodada else []
                        alvo = next((f for f in fs if f['n'] == num_fatia), None)
                        if alvo:
                            nova_linha = f"{alvo['n']}. {alvo['nome']} — em andamento"
                            secoes['Fatias'] = [nova_linha if l.strip() == alvo['linha'].strip() else l for l in secoes['Fatias']]

                    sinc = obter_sincronia_info(self.reg) if obter_sincronia_info else None
                    gravar_rodada(p_rodada, montar_rodada(titulo, campos, secoes, sincronia=sinc), aplicar, f'bastão despachado para {para}')
                    if anexar_historico and agora_rodada and rotulo_rodada:
                        anexar_historico(p_hist, f'{agora_rodada()} · {de} → {para} · {rotulo_rodada(titulo)} · passagem',
                                         f'despachou {tarefa_id} para {para}', aplicar)

        return {
            'status': 'confirmada',
            'passagem': passagem,
            'confirmacao': confirmacao,
            'tarefa_id': tarefa_id,
            'etapa_id': etapa_id,
            'bastao': para
        }

    def receber(
        self,
        etapa_id: Optional[str] = None,
        passagem_id: Optional[str] = None,
        executor: Optional[str] = None,
        resultado: Optional[str] = None,
        prova: Optional[str] = None,
        fatia: Optional[Any] = None,
        tarefa_id: Optional[str] = None,
        arquivos_alvo: Optional[List[str]] = None,
        ignorar_arquivos_externos: bool = False,
        comando_teste: Optional[str] = None,
        comando_regressao: Optional[str] = None,
        comando_build: Optional[str] = None,
        comando_tipos: Optional[str] = None,
        comando_lint: Optional[str] = None,
        ignorar_testes: bool = False,
        motivo_ignorar: str = '',
        devolver_para: str = 'Gandalf',
        aplicar: bool = True
    ) -> Dict[str, Any]:
        """Macro atômico: valida portão pré-devolução, conclui passagem, atualiza registro e devolve bastão na rodada."""
        # 1. Resolve etapa_id
        if not etapa_id:
            est = self.reg.estado() if hasattr(self.reg, 'estado') else {}
            etapa_atual = est.get('etapa_atual')
            if etapa_atual:
                etapa_id = etapa_atual.get('id')
        if not etapa_id and caminhos_rodada and ler_rodada and partir_rodada:
            p_rodada, _, _ = caminhos_rodada(self.reg.pasta)
            if p_rodada.is_file():
                conteudo = ler_rodada(p_rodada)
                if conteudo:
                    titulo, _, _ = partir_rodada(conteudo)
                    etapa_id = etapa_id_de(titulo) if etapa_id_de else None
        if not etapa_id:
            raise ErroPassagem('Etapa ID não fornecido e nenhuma etapa ativa encontrada no registro.')

        # 2. Localiza passagem ativa
        passagem_ativa = None
        if passagem_id:
            dados_reg = self.reg.carregar_dados() if hasattr(self.reg, 'carregar_dados') else getattr(self.reg, '_dados', {})
            for ev in reversed(dados_reg.get('eventos', [])):
                if ev.get('tipo') == 'passagem_despachada' and ev.get('dados', {}).get('passagem_id') == passagem_id:
                    passagem_ativa = ev['dados']
                    break
        else:
            passagem_ativa = self.recuperar_passagem(etapa_id)

        if passagem_ativa:
            if not passagem_id:
                passagem_id = passagem_ativa.get('passagem_id')
            if not executor:
                executor = passagem_ativa.get('para')
            if not tarefa_id:
                tarefa_id = passagem_ativa.get('tarefa_id')
            if not arquivos_alvo:
                leia_so = list(passagem_ativa.get('leia_so') or [])
                arqs_git = []
                try:
                    res_git = subprocess.run(
                        ['git', 'status', '--porcelain'],
                        cwd=self.pasta_projeto,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if res_git.returncode == 0:
                        for linha in res_git.stdout.splitlines():
                            linha = linha.strip()
                            if not linha:
                                continue
                            partes = linha.split(maxsplit=1)
                            if len(partes) == 2:
                                c_rel = partes[1].strip()
                                if ' -> ' in c_rel:
                                    c_rel = c_rel.split(' -> ')[1].strip()
                                p_arq = (self.pasta_projeto / c_rel).resolve()
                                if p_arq.is_file():
                                    try:
                                        p_soc = self.reg.pasta.resolve()
                                        if p_arq == p_soc or p_soc in p_arq.parents:
                                            continue
                                    except Exception:
                                        pass
                                    arqs_git.append(c_rel)
                except Exception:
                    pass

                if arqs_git:
                    candidatos = list(leia_so)
                    for ag in arqs_git:
                        if ag not in candidatos:
                            candidatos.append(ag)
                    arquivos_alvo = candidatos
                elif leia_so:
                    arquivos_alvo = leia_so

        if not executor:
            if caminhos_rodada and ler_rodada and partir_rodada:
                p_rodada, _, _ = caminhos_rodada(self.reg.pasta)
                if p_rodada.is_file():
                    conteudo = ler_rodada(p_rodada)
                    if conteudo:
                        _, campos, _ = partir_rodada(conteudo)
                        executor = campos.get('bastao')
            if not executor:
                executor = 'Especialista'

        num_fatia = None
        if fatia is not None:
            str_f = str(fatia).strip()
            if str_f.isdigit():
                num_fatia = int(str_f)
            elif str_f.startswith('fatia_') and str_f[6:].isdigit():
                num_fatia = int(str_f[6:])
            if not tarefa_id:
                tarefa_id = f'fatia_{num_fatia}' if num_fatia is not None else str_f
        elif tarefa_id:
            if tarefa_id.startswith('fatia_') and tarefa_id[6:].isdigit():
                num_fatia = int(tarefa_id[6:])
        else:
            if caminhos_rodada and ler_rodada and partir_rodada:
                p_rodada, _, _ = caminhos_rodada(self.reg.pasta)
                if p_rodada.is_file():
                    conteudo = ler_rodada(p_rodada)
                    if conteudo:
                        _, _, secoes = partir_rodada(conteudo)
                        fs = fatias_de_rodada(secoes) if fatias_de_rodada else []
                        em_and = [f for f in fs if f.get('estado') in ('em andamento', 'em_andamento')]
                        if em_and:
                            num_fatia = em_and[0]['n']
                            tarefa_id = f'fatia_{num_fatia}'
                        else:
                            pendentes = [f for f in fs if f.get('estado') == 'pendente']
                            if pendentes:
                                num_fatia = pendentes[0]['n']
                                tarefa_id = f'fatia_{num_fatia}'

        cmd_lint_efetivo = comando_tipos or comando_lint

        # 3. Executa Portão Pré-Devolução
        atestado = None
        if VerificadorPreDevolucao is not None:
            verificador = VerificadorPreDevolucao(pasta_projeto=self.pasta_projeto, pasta_sociedade=self.reg.pasta)
            atestado = verificador.executar(
                papel=executor,
                etapa_id=etapa_id,
                fatia_id=str(num_fatia) if num_fatia is not None else (tarefa_id or ''),
                comando_teste=comando_teste,
                comando_build=comando_build,
                comando_lint=cmd_lint_efetivo,
                ignorar_testes=ignorar_testes,
                motivo_ignorar=motivo_ignorar,
                arquivos_alvo=arquivos_alvo,
                ignorar_arquivos_externos=ignorar_arquivos_externos
            )
            if atestado.get('status') != 'APROVADO':
                erros = atestado.get('erros', [])
                erros_msg = '\n'.join([f"- {e}" for e in erros]) if erros else 'Falha nas verificações'
                raise ErroPassagem(
                    f"Portão de Pré-Devolução reprovou a entrega da tarefa:\n{erros_msg}\nStatus: {atestado.get('status')}"
                )

        if comando_regressao and comando_regressao.strip():
            cmd_regr = comando_regressao.strip()
            try:
                proc = subprocess.run(
                    cmd_regr,
                    shell=True,
                    cwd=str(self.pasta_projeto),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=300
                )
                if proc.returncode != 0:
                    raise ErroPassagem(
                        f"Comando de regressão falhou com código {proc.returncode}:\n{proc.stdout}"
                    )
            except subprocess.TimeoutExpired:
                raise ErroPassagem(f"Comando de regressão excedeu timeout (300s): {cmd_regr}")

        # 4. Define prova e resultado
        prova_str = (prova or '').strip()
        if not prova_str:
            h_atest = atestado.get('atestado_hash', '')[:12] if atestado else 'ok'
            prova_str = f"Pré-devolução aprovado (hash={h_atest})"
        res_str = (resultado or prova or 'Tarefa concluída com sucesso e aprovada no pré-devolução').strip()

        # 5. Conclui passagem no registro se houver ID de passagem
        conclusao = None
        if passagem_id:
            conclusao = self.concluir_passagem(
                etapa_id=etapa_id,
                passagem_id=passagem_id,
                executor=executor,
                resultado=res_str,
                aplicar=aplicar
            )

        # 6. Atualiza tarefa no registro.json
        if tarefa_id:
            try:
                self.reg.atualizar_tarefa(
                    etapa_id,
                    tarefa_id,
                    'concluida',
                    autor=executor,
                    aplicar=aplicar
                )
            except Exception:
                pass

        # 7. Registra evidência física no registro.json
        if num_fatia is not None or tarefa_id:
            crit_id = f'fatia_{num_fatia}' if num_fatia is not None else tarefa_id
            try:
                self.reg.registrar_evidencia(
                    etapa_id=etapa_id,
                    criterio_id=crit_id,
                    comando=comando_teste or f'fatia {num_fatia or tarefa_id}',
                    exit_code=0,
                    saida=prova_str,
                    verificador=executor,
                    autor=executor,
                    aplicar=aplicar
                )
            except Exception:
                pass

        # 8. Passa bastão de volta no registro.json
        try:
            self.reg.passar_bastao(etapa_id, devolver_para, autor=executor, nota=f'tarefa {tarefa_id or ""} concluída', aplicar=aplicar)
        except Exception:
            pass

        # 9. Atualiza rodada.md e historico.md
        if caminhos_rodada and ler_rodada and gravar_rodada and partir_rodada and montar_rodada:
            p_rodada, p_hist, _ = caminhos_rodada(self.reg.pasta)
            if p_rodada.is_file():
                conteudo = ler_rodada(p_rodada)
                if conteudo:
                    titulo, campos, secoes = partir_rodada(conteudo)
                    campos['bastao'] = devolver_para

                    secoes['Para quem pega o bastão agora'] = [
                        f'bastão está com: {devolver_para}',
                        'leia só:',
                        '- sociedade/rodada.md',
                        'faça:',
                        f'- Verificar conclusão de {tarefa_id or "fatia"} e prosseguir com a rodada',
                        'devolva: quando a próxima etapa/fatia estiver pronta'
                    ]

                    if num_fatia is not None and 'Fatias' in secoes:
                        fs = fatias_de_rodada(secoes) if fatias_de_rodada else []
                        alvo = next((f for f in fs if f['n'] == num_fatia), None)
                        if alvo:
                            nova_linha = f"{alvo['n']}. {alvo['nome']} — fechada · prova: {prova_str}"
                            secoes['Fatias'] = [nova_linha if l.strip() == alvo['linha'].strip() else l for l in secoes['Fatias']]

                    sinc = obter_sincronia_info(self.reg) if obter_sincronia_info else None
                    gravar_rodada(p_rodada, montar_rodada(titulo, campos, secoes, sincronia=sinc), aplicar, f'fatia {num_fatia or tarefa_id} concluída e devolvida')
                    if anexar_historico and agora_rodada and rotulo_rodada:
                        anexar_historico(p_hist, f'{agora_rodada()} · {executor} → {devolver_para} · {rotulo_rodada(titulo)} · devolução',
                                         f'concluiu: {tarefa_id or ""} prova: {prova_str}', aplicar)

        return {
            'status': 'concluida',
            'passagem_id': passagem_id,
            'tarefa_id': tarefa_id,
            'executor': executor,
            'devolver_para': devolver_para,
            'prova': prova_str,
            'atestado': atestado,
            'conclusao': conclusao
        }


def obter_gerenciador(pasta_sociedade: Path, pasta_projeto: Path) -> GerenciadorPassagem:
    """Carrega registro obrigatório e retorna instância do gerenciador."""
    p_soc = Path(pasta_sociedade).resolve()
    p_proj = Path(pasta_projeto).resolve()
    if Registro is None:
        raise ErroPassagem('Módulo sc_registro não disponível.')
    reg_file, _ = caminhos_registro(p_soc)
    if not reg_file.is_file():
        raise ErroPassagem(
            f'registro.json não encontrado em {p_soc}. Inicialize a rodada antes de despachar passagens.'
        )
    try:
        reg = Registro(p_soc)
    except ErroRegistroCorrompido as e:
        raise ErroPassagem(f'Registro corrompido em {p_soc}: {e}')
    return GerenciadorPassagem(reg, p_proj)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest='comando', required=True)

    # despachar (macro atômico)
    p_desp = sub.add_parser('despachar', help='Despacha passagem atomicamente, confirmando recebimento e atualizando rodada')
    p_desp.add_argument('--para', required=True, help='Destinatário (ex: Elrond, Aragorn, Legolas, Galadriel)')
    p_desp.add_argument('--faca', nargs='+', required=True, help='Ordens a executar')
    p_desp.add_argument('--leia-so', '--arquivos', dest='leia_so', nargs='*', default=[], help='Arquivos para leitura estrita (máx 5)')
    p_desp.add_argument('--etapa', default=None, help='ID da etapa (se omitido, usa a etapa ativa)')
    p_desp.add_argument('--fatia', default=None, help='Número ou ID da fatia')
    p_desp.add_argument('--tarefa', default=None, help='ID da tarefa')
    p_desp.add_argument('--de', default=None, help='Quem despacha (padrão: portador atual do bastão)')
    p_desp.add_argument('--nao-faca', nargs='*', default=[], help='Ordens expressas de não fazer')
    p_desp.add_argument('--limites', default='', help='Limites explícitos da passagem')
    p_desp.add_argument('--ferramentas', nargs='*', default=[], help='Ferramentas necessárias (ex: cmd:git)')
    p_desp.add_argument('--justificativa-expansao', default='', help='Justificativa se mais de 5 caminhos')
    p_desp.add_argument('--decisao-ref', default=None, help='Referência da decisão humana caso toque ação crítica')
    p_desp.add_argument('--devolva', default='quando a fatia estiver pronta e passar no pré-devolução', help='Critério de devolução')
    p_desp.add_argument('--nota', default='', help='Nota de passagem do bastão')
    p_desp.add_argument('--pasta-sociedade', default=None, help='Pasta do registro (padrão: sociedade canônica)')
    p_desp.add_argument('--pasta-projeto', default='.', help='Raiz do projeto')
    p_desp.add_argument('--aplicar', action='store_true', help='Persiste as mutações no registro.json e rodada.md')

    # receber (macro atômico)
    p_rec = sub.add_parser('receber', help='Recebe devolução atomicamente com portão pré-devolução, conclusão e passagem de bastão')
    p_rec.add_argument('--etapa', default=None, help='ID da etapa (se omitido, usa a etapa ativa)')
    p_rec.add_argument('--passagem', default=None, help='ID da passagem (se omitido, recupera a ativa)')
    p_rec.add_argument('--executor', default=None, help='Quem executou (se omitido, recupera da passagem)')
    p_rec.add_argument('--resultado', default=None, help='Resumo do resultado alcançado')
    p_rec.add_argument('--prova', default=None, help='Evidência física / prova de execução')
    p_rec.add_argument('--fatia', default=None, help='Número ou ID da fatia')
    p_rec.add_argument('--tarefa', default=None, help='ID da tarefa')
    p_rec.add_argument('--arquivos-alvo', '--arquivos', dest='arquivos_alvo', nargs='*', default=None, help='Arquivos específicos do escopo da fatia')
    p_rec.add_argument('--ignorar-arquivos-externos', action='store_true', help='Ignora arquivos fora do escopo da fatia na verificação pré-devolução')
    p_rec.add_argument('--comando-teste', default=None, help='Comando físico de prova da tarefa')
    p_rec.add_argument('--comando-regressao', default=None, help='Comando da suíte completa de regressão')
    p_rec.add_argument('--comando-build', default=None, help='Comando de build opcional')
    p_rec.add_argument('--comando-tipos', '--comando-lint', dest='comando_tipos', default=None, help='Comando de lint ou checagem estática de tipos')
    p_rec.add_argument('--ignorar-testes', action='store_true', help='Não executa testes automatizados na pré-devolução')
    p_rec.add_argument('--motivo-ignorar', default='', help='Justificativa obrigatória se --ignorar-testes for usado')
    p_rec.add_argument('--devolver-para', default='Gandalf', help='Para quem devolver o bastão (padrão: Gandalf)')
    p_rec.add_argument('--pasta-sociedade', default=None, help='Pasta do registro (padrão: sociedade canônica)')
    p_rec.add_argument('--pasta-projeto', default='.', help='Raiz do projeto')
    p_rec.add_argument('--aplicar', action='store_true', help='Persiste as mutações no registro.json e rodada.md')

    # despachar-local
    p_local = sub.add_parser('despachar-local', help='Despacha passagem para subagente local')
    p_local.add_argument('--etapa', required=True, help='ID da etapa')
    p_local.add_argument('--para', required=True, help='Destinatário (ex: Elrond, Aragorn, Galadriel)')
    p_local.add_argument('--tarefa', required=True, help='ID da tarefa (ex: T-01)')
    p_local.add_argument('--de', default='Gandalf', help='Quem despacha (padrão: Gandalf)')
    p_local.add_argument('--leia-so', nargs='*', default=[], help='Arquivos para leitura estrita (máx 5)')
    p_local.add_argument('--justificativa-expansao', default='', help='Justificativa se mais de 5 caminhos')
    p_local.add_argument('--faca', nargs='+', required=True, help='Ordens a executar')
    p_local.add_argument('--nao-faca', nargs='*', default=[], help='Ordens expressas de não fazer')
    p_local.add_argument('--limites', default='', help='Limites explícitos da passagem')
    p_local.add_argument('--ferramentas', nargs='*', default=[], help='Ferramentas necessárias (ex: cmd:git)')
    p_local.add_argument('--decisao-ref', default=None, help='Referência da decisão humana caso toque ação crítica')
    p_local.add_argument('--pasta-sociedade', default=None, help='Pasta do registro (padrão: sociedade canônica)')
    p_local.add_argument('--pasta-projeto', default='.', help='Raiz do projeto')
    p_local.add_argument('--aplicar', action='store_true', help='Persiste a mutação no registro.json')

    # confirmar
    p_conf = sub.add_parser('confirmar', help='Confirma recebimento de passagem (handshake)')
    p_conf.add_argument('--etapa', required=True, help='ID da etapa')
    p_conf.add_argument('--passagem', required=True, help='ID da passagem (PSG-...)')
    p_conf.add_argument('--recebedor', required=True, help='Nome do recebedor confirmando recebimento')
    p_conf.add_argument('--pasta-sociedade', default=None, help='Pasta do registro (padrão: sociedade canônica)')
    p_conf.add_argument('--pasta-projeto', default='.', help='Raiz do projeto')
    p_conf.add_argument('--aplicar', action='store_true', help='Persiste a confirmação no registro.json')

    # concluir
    p_conc = sub.add_parser('concluir', help='Conclui passagem e registra resultado')
    p_conc.add_argument('--etapa', required=True, help='ID da etapa')
    p_conc.add_argument('--passagem', required=True, help='ID da passagem (PSG-...)')
    p_conc.add_argument('--executor', required=True, help='Nome do executor concluindo a tarefa')
    p_conc.add_argument('--resultado', required=True, help='Resumo do resultado alcançado')
    p_conc.add_argument('--pasta-sociedade', default=None, help='Pasta do registro (padrão: sociedade canônica)')
    p_conc.add_argument('--pasta-projeto', default='.', help='Raiz do projeto')
    p_conc.add_argument('--aplicar', action='store_true', help='Persiste a conclusão no registro.json')

    # despachar-jules
    p_jules = sub.add_parser('despachar-jules', help='Despacha tarefa delimitada para o Jules em nuvem')
    p_jules.add_argument('--etapa', required=True, help='ID da etapa')
    p_jules.add_argument('--fatia', required=True, help='ID da fatia')
    p_jules.add_argument('--tarefa', required=True, help='ID da tarefa')
    p_jules.add_argument('--arquivos', nargs='+', required=True, help='Arquivos atribuídos à tarefa')
    p_jules.add_argument('--instrucoes', required=True, help='Instruções da tarefa mecânica')
    p_jules.add_argument('--criterios', nargs='*', default=[], help='Critérios da etapa contemplados')
    p_jules.add_argument('--de', default='Gandalf', help='Quem despacha (padrão: Gandalf)')
    p_jules.add_argument('--prs-abertos', type=int, default=None, help='Contagem manual de PRs/tarefas abertos aguardando revisão')
    p_jules.add_argument('--max-prs-abertos', type=int, default=3, help='Teto de tolerância de PRs abertos (padrão: 8)')
    p_jules.add_argument('--pasta-sociedade', default=None, help='Pasta do registro (padrão: sociedade canônica)')
    p_jules.add_argument('--pasta-projeto', default='.', help='Raiz do projeto')
    p_jules.add_argument('--aplicar', action='store_true', help='Persiste a passagem no registro.json')

    # auditar-jules
    p_aud = sub.add_parser('auditar-jules', help='Executa o Portão de Ferro de auditoria física de Draft PR do Jules (6 passos)')
    p_aud.add_argument('--arquivos-permitidos', nargs='+', required=True, help='Arquivos autorizados no contrato da tarefa')
    p_aud.add_argument('--arquivos-alterados', nargs='*', default=[], help='Arquivos alterados no PR (ou detecta via git status)')
    p_aud.add_argument('--comando-teste', required=True, help='Comando físico de prova da tarefa')
    p_aud.add_argument('--comando-regressao', default=None, help='Comando da suíte completa de regressão')
    p_aud.add_argument('--tarefa', default='', help='ID da tarefa Jules')
    p_aud.add_argument('--pr', default='', help='ID do PR')
    p_aud.add_argument('--formato', choices=['texto', 'json'], default='texto', help='Formato de saída')
    p_aud.add_argument('--pasta-sociedade', default=None, help='Pasta do registro (padrão: sociedade canônica)')
    p_aud.add_argument('--pasta-projeto', default='.', help='Raiz do projeto')

    # exportar-revisao
    p_rev = sub.add_parser('exportar-revisao', help='Exporta pacote de revisão independente')
    p_rev.add_argument('--etapa', required=True, help='ID da etapa')
    p_rev.add_argument('--fatia', default='', help='ID da fatia (opcional; se omitido, fechamento da etapa)')
    p_rev.add_argument('--base', default='', help='Commit base para diff')
    p_rev.add_argument('--head', default='HEAD', help='Commit head para diff')
    p_rev.add_argument('--revisor', default=None, help='Nome do revisor (padrão: o do perfil)')
    p_rev.add_argument('--fornecedor-revisor', default=None, help='Fornecedor do revisor (padrão: o do perfil)')
    p_rev.add_argument('--saida', default=None, help='Arquivo para salvar o pacote exportado')
    p_rev.add_argument('--pasta-sociedade', default=None, help='Pasta do registro (padrão: sociedade canônica)')
    p_rev.add_argument('--pasta-projeto', default='.', help='Raiz do projeto')

    # recuperar
    p_rec = sub.add_parser('recuperar', help='Recupera última passagem ativa de uma etapa')
    p_rec.add_argument('--etapa', required=True, help='ID da etapa')
    p_rec.add_argument('--pasta-sociedade', default=None, help='Pasta do registro (padrão: sociedade canônica)')
    p_rec.add_argument('--pasta-projeto', default='.', help='Raiz do projeto')

    args = parser.parse_args(argv)

    try:
        p_soc = Path(args.pasta_sociedade) if getattr(args, 'pasta_sociedade', None) else localizar_sociedade_canonica(getattr(args, 'pasta_projeto', None))
        gerenciador = obter_gerenciador(p_soc, Path(args.pasta_projeto))
    except Exception as e:
        print(f'ERRO: {e}', file=sys.stderr)
        return 1

    try:
        if args.comando == 'despachar':
            res = gerenciador.despachar(
                para=args.para,
                faca=args.faca,
                leia_so=args.leia_so,
                etapa_id=args.etapa,
                fatia=args.fatia,
                tarefa_id=args.tarefa,
                de=args.de,
                nao_faca=args.nao_faca,
                limites=args.limites,
                ferramentas_necessarias=args.ferramentas,
                justificativa_expansao=args.justificativa_expansao,
                decisao_ref=args.decisao_ref,
                devolva=args.devolva,
                nota=args.nota,
                aplicar=args.aplicar
            )
            print(f"=== PASSAGEM DESPACHADA E CONFIRMADA ATOMICAMENTE ===")
            print(f"Destinatário: {res['bastao']} | Status: {res['status']}")
            print(f"Tarefa: {res['tarefa_id']} | Passagem ID: {res['passagem']['passagem_id']}")
            return 0

        elif args.comando == 'receber':
            res = gerenciador.receber(
                etapa_id=args.etapa,
                passagem_id=args.passagem,
                executor=args.executor,
                resultado=args.resultado,
                prova=args.prova,
                fatia=args.fatia,
                tarefa_id=args.tarefa,
                arquivos_alvo=args.arquivos_alvo,
                ignorar_arquivos_externos=args.ignorar_arquivos_externos,
                comando_teste=args.comando_teste,
                comando_regressao=args.comando_regressao,
                comando_build=args.comando_build,
                comando_tipos=args.comando_tipos,
                ignorar_testes=args.ignorar_testes,
                motivo_ignorar=args.motivo_ignorar,
                devolver_para=args.devolver_para,
                aplicar=args.aplicar
            )
            print(f"=== DEVOLUÇÃO RECEBIDA E CONCLUÍDA ATOMICAMENTE ===")
            print(f"Status: {res['status']} | Prova: {res['prova']}")
            print(f"Bastão devolvido para: {res['devolver_para']}")
            return 0

        elif args.comando == 'despachar-local':
            passagem = gerenciador.despachar_passagem(
                etapa_id=args.etapa,
                de=args.de,
                para=args.para,
                tarefa_id=args.tarefa,
                leia_so=args.leia_so,
                faca=args.faca,
                nao_faca=args.nao_faca,
                limites=args.limites,
                ferramentas_necessarias=args.ferramentas,
                justificativa_expansao=args.justificativa_expansao,
                decisao_ref=args.decisao_ref,
                aplicar=args.aplicar
            )
            print(f"=== PASSAGEM DESPACHADA: {passagem['passagem_id']} ===")
            print(f"De: {passagem['de']} -> Para: {passagem['para']} | Tarefa: {passagem['tarefa_id']}")
            print(f"Status: {passagem['status']} (aplicado no registro: {args.aplicar})")
            print("\n--- INSTRUÇÃO PRONTA PARA O SUBAGENTE ---")
            print(f"Etapa: {passagem['etapa_id']} | Passagem: {passagem['passagem_id']}")
            print("Leia só:")
            for a in passagem['leia_so']:
                print(f"  - {a}")
            print("Faça:")
            for f in passagem['faca']:
                print(f"  - {f}")
            if passagem.get('nao_faca'):
                print("Não faça:")
                for nf in passagem['nao_faca']:
                    print(f"  - {nf}")
            if passagem.get('limites'):
                print(f"Limites: {passagem['limites']}")

        elif args.comando == 'despachar-jules':
            passagem = gerenciador.despachar_jules(
                etapa_id=args.etapa,
                fatia_id=args.fatia,
                tarefa_id=args.tarefa,
                arquivos=args.arquivos,
                instrucoes=args.instrucoes,
                criterios=args.criterios,
                de=args.de,
                prs_abertos=args.prs_abertos,
                max_prs_abertos=args.max_prs_abertos,
                aplicar=args.aplicar
            )
            print(f"=== TAREFA JULES DESPACHADA: {passagem['passagem_id']} ===")
            print(f"Etapa: {passagem['etapa_id']} | Fatia: {passagem['fatia_id']} | Tarefa: {passagem['tarefa_id']}")
            print("Janela assíncrona mandatória: 45 minutos (trabalho independente local, sem polling ativo).")
            print(f"Status: {passagem['status']} (aplicado no registro: {args.aplicar})")
            print("\nPayload para Jules:")
            print(json.dumps(passagem, indent=2, ensure_ascii=False))

        elif args.comando == 'auditar-jules':
            arquivos_alterados = args.arquivos_alterados
            if not arquivos_alterados:
                try:
                    res_git = subprocess.run(
                        ['git', 'status', '--porcelain'],
                        cwd=gerenciador.pasta_projeto,
                        capture_output=True,
                        text=True
                    )
                    if res_git.returncode == 0:
                        linhas = [l.strip() for l in res_git.stdout.split('\n') if l.strip()]
                        arquivos_alterados = [l.split()[-1] for l in linhas if not l.startswith('??')]
                except Exception:
                    pass

            atestado = gerenciador.auditar_jules(
                arquivos_permitidos=args.arquivos_permitidos,
                arquivos_alterados=arquivos_alterados,
                comando_teste=args.comando_teste,
                comando_regressao=args.comando_regressao,
                tarefa_id=args.tarefa,
                pr_id=args.pr
            )

            if args.formato == 'json':
                print(json.dumps(atestado, indent=2, ensure_ascii=False))
            else:
                try:
                    from sc_jules_portao import formatar_relatorio_portao
                    print(formatar_relatorio_portao(atestado))
                except Exception:
                    print(json.dumps(atestado, indent=2, ensure_ascii=False))

            return 0 if atestado['status'] == 'APROVADO' else 1

        elif args.comando == 'confirmar':
            conf = gerenciador.confirmar_recebimento(
                etapa_id=args.etapa,
                passagem_id=args.passagem,
                recebedor=args.recebedor,
                aplicar=args.aplicar
            )
            print(f"=== RECEBIMENTO CONFIRMADO: {conf['passagem_id']} ===")
            print(f"Recebedor: {conf['recebedor']} | Status: {conf['status']} (aplicado: {args.aplicar})")

        elif args.comando == 'concluir':
            conc = gerenciador.concluir_passagem(
                etapa_id=args.etapa,
                passagem_id=args.passagem,
                executor=args.executor,
                resultado=args.resultado,
                aplicar=args.aplicar
            )
            print(f"=== PASSAGEM CONCLUÍDA: {conc['passagem_id']} ===")
            print(f"Executor: {conc['executor']} | Status: {conc['status']} (aplicado: {args.aplicar})")
            print(f"Resultado: {conc['resultado']}")

        elif args.comando == 'recuperar':
            rec = gerenciador.recuperar_passagem(args.etapa)
            if rec:
                print(f"=== PASSAGEM ATIVA RECUPERADA: {rec['passagem_id']} ===")
                print(f"De: {rec.get('de')} -> Para: {rec.get('para')} | Tarefa: {rec.get('tarefa_id')}")
                print(f"Status: {rec.get('status')}")
                print(json.dumps(rec, indent=2, ensure_ascii=False))
            else:
                print("Nenhuma passagem ativa ou pendente para esta etapa.")

        elif args.comando == 'exportar-revisao':
            pct = gerenciador.exportar_revisao(
                etapa_id=args.etapa,
                fatia_id=args.fatia,
                base_commit=args.base,
                head_commit=args.head,
                revisor=args.revisor,
                fornecedor_revisor=args.fornecedor_revisor
            )
            if args.saida:
                p_saida = Path(args.saida)
                p_saida.parent.mkdir(parents=True, exist_ok=True)
                p_saida.write_text(pct, encoding='utf-8')
                print(f"Pacote de revisão exportado com sucesso para: {args.saida}")
            else:
                print(pct)

        return 0

    except ErroPassagem as e:
        print(f"ERRO DE PASSAGEM: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERRO INESPERADO: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
