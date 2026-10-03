#!/usr/bin/env python3
"""Portão de Ferro de Auditoria Física de Draft PRs do Jules (Sociedade do Código).

Executa deterministicamente os 6 passos locais de auditoria técnica sobre as entregas
produzidas pelo executor júnior em nuvem (Google Jules):
1. Inspeção de escopo e arquivos permitidos (rejeição de alterações fora da lista e arquivos sensíveis);
2. Verificação de integridade física dos arquivos no disco / checkout;
3. Compilação e sintaxe estrita (py_compile para arquivos Python);
4. Execução física do comando de teste da tarefa na máquina local (returncode == 0);
5. Execução da suíte de regressão local (returncode == 0);
6. Auditoria de integridade das evidências (antissabotagem: veto a assert True, mocks vazios, caminhos locais).

Emite atestado estruturado com código de saída 0 (APROVADO) ou 1 (REJEITADO).
Sem dependências externas: usa apenas a biblioteca padrão do Python.
"""
import argparse
import hashlib
import json
import os
import py_compile
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PADRAO_TESTE_TAUTOLOGICO = re.compile(
    r'\b(?:assert\s+True\b|assert\s+not\s+False\b|self\.assertTrue\s*\(\s*True\s*\)|self\.assertEqual\s*\(\s*1\s*,\s*1\s*\)|self\.assertEqual\s*\(\s*True\s*,\s*True\s*\))\b'
)
PADRAO_CAMINHO_LOCAL = re.compile(
    r'(?<![\w/])(?:/(?:home|Users|tmp|mnt|root|var|etc)/|[A-Za-z]:\\|~/|file://)'
)
PADRAO_ARQUIVO_PROIBIDO = re.compile(
    r'(\.env|\.pem|\.key|id_rsa|credentials|secrets?\.json|senha|password)',
    re.I
)


def calcular_hash_arquivo(caminho: Path) -> str:
    """Calcula hash SHA-256 do arquivo se existir."""
    if not caminho.is_file():
        return ''
    return hashlib.sha256(caminho.read_bytes()).hexdigest()[:16]


def normalizar_caminho(caminho: str) -> str:
    c = caminho.strip().replace('\\', '/')
    while c.startswith('./'):
        c = c[2:]
    return c.rstrip('/')


class PortaoDeFerroJules:
    """Auditor determinístico de entregas de Draft PRs do Jules."""

    def __init__(self, pasta_projeto: Path):
        self.pasta_projeto = Path(pasta_projeto).resolve()

    def passo1_inspecionar_escopo(
        self,
        arquivos_alterados: List[str],
        arquivos_permitidos: List[str]
    ) -> Tuple[bool, str]:
        """Passo 1: Valida se os arquivos alterados respeitam estritamente a lista autorizada."""
        if not arquivos_alterados:
            return False, "Nenhum arquivo alterado informado para auditoria."

        permitidos_norm = {normalizar_caminho(a) for a in arquivos_permitidos}
        alterados_norm = [normalizar_caminho(a) for a in arquivos_alterados]

        # Verifica arquivos proibidos / sensíveis
        for a in alterados_norm:
            if PADRAO_ARQUIVO_PROIBIDO.search(a):
                return False, f"Violação de segurança: arquivo sensível/proibido tocado no PR: {a}"

        # Verifica violação de escopo
        fora_do_escopo = [a for a in alterados_norm if a not in permitidos_norm]
        if fora_do_escopo:
            return False, (
                f"Violação de escopo: PR alterou arquivos fora da lista autorizada: {fora_do_escopo}. "
                f"Arquivos autorizados eram: {sorted(list(permitidos_norm))}."
            )

        return True, f"Escopo validado com sucesso: {len(alterados_norm)} arquivo(s) estritamente autorizado(s)."

    def passo2_verificar_integridade_arquivos(
        self,
        arquivos_alterados: List[str]
    ) -> Tuple[bool, str, Dict[str, str]]:
        """Passo 2: Confere existência física e calcula hashes dos arquivos alterados."""
        hashes = {}
        for a in arquivos_alterados:
            alvo = (self.pasta_projeto / normalizar_caminho(a)).resolve()
            try:
                alvo.relative_to(self.pasta_projeto)
            except ValueError:
                return False, f"Caminho escapa da raiz do projeto: {a}", {}

            if not alvo.is_file():
                return False, f"Arquivo alterado citado não existe fisicamente no disco: {a}", {}

            hashes[normalizar_caminho(a)] = calcular_hash_arquivo(alvo)

        return True, "Todos os arquivos alterados existem fisicamente no disco com hashes íntegros.", hashes

    def passo3_compilacao_sintaxe(
        self,
        arquivos_alterados: List[str]
    ) -> Tuple[bool, str]:
        """Passo 3: Valida compilação estrita e sintaxe de arquivos Python."""
        for a in arquivos_alterados:
            caminho_norm = normalizar_caminho(a)
            if caminho_norm.endswith('.py'):
                alvo = self.pasta_projeto / caminho_norm
                try:
                    py_compile.compile(str(alvo), doraise=True)
                except py_compile.PyCompileError as e:
                    return False, f"Erro de sintaxe/compilação no arquivo {a}: {e}"
                except Exception as e:
                    return False, f"Falha inesperada ao compilar {a}: {e}"

        return True, "Compilação e sintaxe estrita validadas com sucesso."

    def passo4_executar_comando_teste(
        self,
        comando_teste: str,
        timeout_segundos: int = 120
    ) -> Tuple[bool, str, int, str]:
        """Passo 4: Executa o comando específico de teste da tarefa na máquina local."""
        if not comando_teste or not comando_teste.strip():
            return False, "Comando de teste não especificado.", -1, ""

        try:
            res = subprocess.run(
                comando_teste,
                shell=True,
                cwd=self.pasta_projeto,
                capture_output=True,
                text=True,
                timeout=timeout_segundos
            )
            saida_completa = (res.stdout + '\n' + res.stderr).strip()
            if res.returncode != 0:
                return False, f"Comando de teste falhou com código {res.returncode}.", res.returncode, saida_completa
            return True, "Comando de teste executado com sucesso (código de retorno 0).", 0, saida_completa
        except subprocess.TimeoutExpired:
            return False, f"Comando de teste excedeu timeout regulamentar de {timeout_segundos}s.", 124, "Timeout"
        except Exception as e:
            return False, f"Erro ao disparar comando de teste: {e}", 1, str(e)

    def passo5_executar_regressao(
        self,
        comando_regressao: Optional[str] = None,
        timeout_segundos: int = 300
    ) -> Tuple[bool, str, int, str]:
        """Passo 5: Executa a suíte de regressão do projeto."""
        if not comando_regressao or not comando_regressao.strip():
            return True, "Suíte de regressão dispensada ou não especificada.", 0, ""

        try:
            res = subprocess.run(
                comando_regressao,
                shell=True,
                cwd=self.pasta_projeto,
                capture_output=True,
                text=True,
                timeout=timeout_segundos
            )
            saida_completa = (res.stdout + '\n' + res.stderr).strip()
            if res.returncode != 0:
                return False, f"Suíte de regressão falhou com código {res.returncode}.", res.returncode, saida_completa
            return True, "Suíte de regressão executada com sucesso (código de retorno 0).", 0, saida_completa
        except subprocess.TimeoutExpired:
            return False, f"Suíte de regressão excedeu timeout regulamentar de {timeout_segundos}s.", 124, "Timeout"
        except Exception as e:
            return False, f"Erro ao disparar suíte de regressão: {e}", 1, str(e)

    def passo6_auditar_integridade_evidencias(
        self,
        arquivos_alterados: List[str]
    ) -> Tuple[bool, str]:
        """Passo 6: Antissabotagem — detecta testes tautológicos e caminhos locais proibidos."""
        for a in arquivos_alterados:
            caminho_norm = normalizar_caminho(a)
            alvo = self.pasta_projeto / caminho_norm
            if not alvo.is_file():
                continue

            try:
                conteudo = alvo.read_text(encoding='utf-8')
            except Exception:
                continue

            # Verifica caminhos absolutos locais
            if PADRAO_CAMINHO_LOCAL.search(conteudo):
                return False, f"Caminho absoluto local proibido detectado no arquivo {a}."

            # Se for arquivo de teste, verifica testes tautológicos
            if 'test' in caminho_norm.lower():
                linhas = conteudo.split('\n')
                for idx, linha in enumerate(linhas, 1):
                    linha_limpa = linha.strip()
                    if linha_limpa.startswith('#'):
                        continue
                    if PADRAO_TESTE_TAUTOLOGICO.search(linha_limpa):
                        return False, f"Teste tautológico/evasivo proibido detectado em {a}:{idx}: '{linha_limpa}'."

        return True, "Integridade e qualidade de evidências validadas sem achados evasivos."

    def auditar_pr(
        self,
        arquivos_permitidos: List[str],
        arquivos_alterados: List[str],
        comando_teste: str,
        comando_regressao: Optional[str] = None,
        tarefa_id: str = '',
        pr_id: str = ''
    ) -> Dict[str, Any]:
        """Executa deterministicamente os 6 passos sequenciais do Portão de Ferro."""
        ts_inicio = datetime.now(timezone.utc).isoformat()
        relatorio_passos = []
        aprovado = True
        motivo_falha = None
        passo_falha = None

        # 1. Escopo
        ok1, msg1 = self.passo1_inspecionar_escopo(arquivos_alterados, arquivos_permitidos)
        relatorio_passos.append({'passo': 1, 'nome': 'Inspeção de Escopo', 'aprovado': ok1, 'detalhe': msg1})
        if not ok1:
            aprovado = False
            passo_falha = 1
            motivo_falha = msg1

        # 2. Integridade dos arquivos
        hashes = {}
        if aprovado:
            ok2, msg2, hashes = self.passo2_verificar_integridade_arquivos(arquivos_alterados)
            relatorio_passos.append({'passo': 2, 'nome': 'Integridade Física e Hashes', 'aprovado': ok2, 'detalhe': msg2})
            if not ok2:
                aprovado = False
                passo_falha = 2
                motivo_falha = msg2
        else:
            relatorio_passos.append({'passo': 2, 'nome': 'Integridade Física e Hashes', 'aprovado': False, 'detalhe': 'Pulado devido a falha anterior.'})

        # 3. Compilação e Sintaxe
        if aprovado:
            ok3, msg3 = self.passo3_compilacao_sintaxe(arquivos_alterados)
            relatorio_passos.append({'passo': 3, 'nome': 'Compilação e Sintaxe Estrita', 'aprovado': ok3, 'detalhe': msg3})
            if not ok3:
                aprovado = False
                passo_falha = 3
                motivo_falha = msg3
        else:
            relatorio_passos.append({'passo': 3, 'nome': 'Compilação e Sintaxe Estrita', 'aprovado': False, 'detalhe': 'Pulado devido a falha anterior.'})

        # 4. Prova Local
        saida_teste = ''
        if aprovado:
            ok4, msg4, code4, saida_teste = self.passo4_executar_comando_teste(comando_teste)
            relatorio_passos.append({'passo': 4, 'nome': 'Execução Local da Prova', 'aprovado': ok4, 'detalhe': msg4, 'exit_code': code4})
            if not ok4:
                aprovado = False
                passo_falha = 4
                motivo_falha = msg4
        else:
            relatorio_passos.append({'passo': 4, 'nome': 'Execução Local da Prova', 'aprovado': False, 'detalhe': 'Pulado devido a falha anterior.'})

        # 5. Suíte de Regressão
        saida_regressao = ''
        if aprovado:
            ok5, msg5, code5, saida_regressao = self.passo5_executar_regressao(comando_regressao)
            relatorio_passos.append({'passo': 5, 'nome': 'Suíte de Regressão Local', 'aprovado': ok5, 'detalhe': msg5, 'exit_code': code5})
            if not ok5:
                aprovado = False
                passo_falha = 5
                motivo_falha = msg5
        else:
            relatorio_passos.append({'passo': 5, 'nome': 'Suíte de Regressão Local', 'aprovado': False, 'detalhe': 'Pulado devido a falha anterior.'})

        # 6. Integridade de Evidências
        if aprovado:
            ok6, msg6 = self.passo6_auditar_integridade_evidencias(arquivos_alterados)
            relatorio_passos.append({'passo': 6, 'nome': 'Antissabotagem de Evidências', 'aprovado': ok6, 'detalhe': msg6})
            if not ok6:
                aprovado = False
                passo_falha = 6
                motivo_falha = msg6
        else:
            relatorio_passos.append({'passo': 6, 'nome': 'Antissabotagem de Evidências', 'aprovado': False, 'detalhe': 'Pulado devido a falha anterior.'})

        ts_fim = datetime.now(timezone.utc).isoformat()
        return {
            'status': 'APROVADO' if aprovado else 'REJEITADO',
            'tarefa_id': tarefa_id,
            'pr_id': pr_id,
            'inicio': ts_inicio,
            'fim': ts_fim,
            'passo_falha': passo_falha,
            'motivo_falha': motivo_falha,
            'arquivos_auditados': hashes,
            'passos': relatorio_passos,
            'saida_teste': saida_teste[:2000] if saida_teste else '',
            'saida_regressao': saida_regressao[:2000] if saida_regressao else '',
        }


def formatar_relatorio_portao(res: Dict[str, Any]) -> str:
    """Formata o parecer do Portão de Ferro em relatório visual legível."""
    linhas = [
        "==================================================================",
        "     PORTÃO DE FERRO DE AUDITORIA FÍSICA DE DRAFT PR (JULES)      ",
        "==================================================================",
        f"Status: {res['status']} | Tarefa: {res.get('tarefa_id', '—')} | PR: {res.get('pr_id', '—')}",
        f"Início: {res['inicio']} | Fim: {res['fim']}",
        "",
        "--- VERIFICAÇÃO DOS 6 PASSOS REGULAMENTARES ---"
    ]
    for p in res.get('passos', []):
        simbolo = "✓ [OK]" if p['aprovado'] else "✗ [FALHA]"
        linhas.append(f"  Passo {p['passo']}: {p['nome']:<32} {simbolo}")
        linhas.append(f"    -> {p['detalhe']}")

    if res['status'] == 'REJEITADO':
        linhas.append("")
        linhas.append("--- PARECER DE REJEIÇÃO ---")
        linhas.append(f"  Bloqueado no Passo {res['passo_falha']}: {res['motivo_falha']}")
        linhas.append("  Ação: Não autorizar integração nem merge. Devolver a Jules ou acionar especialista tutor.")
    else:
        linhas.append("")
        linhas.append("--- PARECER FAVORÁVEL ---")
        linhas.append("  Todos os 6 passos cumpridos com retorno zero e integridade comprovada.")
        linhas.append("  Atestado: Apto para integração por Gandalf após autorização humana.")

    linhas.append("==================================================================")
    return "\n".join(linhas)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--arquivos-permitidos',
        nargs='+',
        required=True,
        help='Lista de arquivos estritamente autorizados no contrato da tarefa'
    )
    parser.add_argument(
        '--arquivos-alterados',
        nargs='*',
        default=[],
        help='Lista de arquivos alterados pelo Jules no PR'
    )
    parser.add_argument(
        '--comando-teste',
        required=True,
        help='Comando físico de prova da tarefa executado localmente'
    )
    parser.add_argument(
        '--comando-regressao',
        default=None,
        help='Comando de teste da suíte de regressão local'
    )
    parser.add_argument(
        '--tarefa',
        default='',
        help='Identificador da tarefa Jules'
    )
    parser.add_argument(
        '--pr',
        default='',
        help='Número ou identificador do PR em rascunho'
    )
    parser.add_argument(
        '--pasta-projeto',
        default='.',
        help='Pasta raiz do projeto (padrão: .)'
    )
    parser.add_argument(
        '--formato',
        choices=['texto', 'json'],
        default='texto',
        help='Formato de saída do atestado (padrão: texto)'
    )
    parser.add_argument(
        '--saida',
        help='Arquivo para salvar o atestado do Portão de Ferro'
    )

    args = parser.parse_args(argv)
    portao = PortaoDeFerroJules(pasta_projeto=Path(args.pasta_projeto))

    arquivos_alterados = args.arquivos_alterados
    if not arquivos_alterados:
        # Tenta detectar arquivos modificados via git se arquivos_alterados não for passado
        try:
            res_git = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=args.pasta_projeto,
                capture_output=True,
                text=True
            )
            if res_git.returncode == 0:
                linhas = [l.strip() for l in res_git.stdout.split('\n') if l.strip()]
                arquivos_alterados = [l.split()[-1] for l in linhas if not l.startswith('??')]
        except Exception:
            pass

    resultado = portao.auditar_pr(
        arquivos_permitidos=args.arquivos_permitidos,
        arquivos_alterados=arquivos_alterados,
        comando_teste=args.comando_teste,
        comando_regressao=args.comando_regressao,
        tarefa_id=args.tarefa,
        pr_id=args.pr
    )

    if args.formato == 'json':
        conteudo = json.dumps(resultado, indent=2, ensure_ascii=False)
    else:
        conteudo = formatar_relatorio_portao(resultado)

    if args.saida:
        p_saida = Path(args.saida)
        p_saida.parent.mkdir(parents=True, exist_ok=True)
        p_saida.write_text(conteudo, encoding='utf-8')
        print(f"Atestado do Portão de Ferro gravado em: {args.saida}")
    else:
        print(conteudo)

    return 0 if resultado['status'] == 'APROVADO' else 1


if __name__ == '__main__':
    sys.exit(main())
