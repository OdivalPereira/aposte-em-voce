#!/usr/bin/env python3
"""Script determinístico de verificação pré-devolução de fatia / entrega (SC-E5 / Pacote 1).

Substitui checklists verbais repetitivos por prova física executada em código:
1. Execução física de testes automatizados com conferência de código de saída zero.
2. Varredura da regra antitoken inviolável e detecção de segredos em arquivos tocados.
3. Higiene Git e bloqueio de pastas isoladas/sensíveis (ex.: credenciais, segredos, .env).
4. Compilação estática, em memória, de scripts Python alterados.
5. Disjunção de arquivos tocados contra listas proibidas ou de outras tarefas.

Emite atestado estruturado com status APROVADO (código 0) ou REPROVADO (código 1).
Sem dependências externas (Python stdlib).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sc_perfil import ErroPortao, areas_tocadas, ler_portao_por_area  # noqa: E402
from sc_registro import localizar_sociedade_canonica  # noqa: E402

# Padrões oficiais de segurança e integridade
MEDICAO = re.compile(
    r'(?:estim\w+|calcul\w+|medi\w+|conte|contar|relat\w+|registr\w+)'
    r'[^.\n]{0,40}(?:tokens|consumo|custo|gasto)',
    re.I
)
MEDICAO_OK = re.compile(
    r'\b(?:n[ãa]o|nunca|jamais|nenhum\w*|nada|sem|proib\w+|aus[êe]ncia|dispens\w+)\b',
    re.I
)
SEGREDOS = re.compile(
    r'(?:AIza[0-9A-Za-z_\-]{30,}|gh[pousr]_[0-9A-Za-z]{30,}|sk-[0-9A-Za-z_\-]{30,}|'
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[abprs]-[0-9A-Za-z-]{20,})'
)
PASTAS_PROIBIDAS_PADRAO = ['.env', '.git', 'segredos', 'private', 'credentials', 'sociedade']


def calcular_sha256(caminho: Path) -> str:
    """Calcula hash SHA-256 do arquivo."""
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _git(pasta: Path, *args: str) -> Optional[str]:
    """Executa git e devolve a saída, ou None se falhar."""
    try:
        res = subprocess.run(['git', '-C', str(pasta), *args], capture_output=True, text=True, check=False)
    except Exception:
        return None
    return res.stdout if res.returncode == 0 else None


def raiz_git(pasta: Path) -> Optional[Path]:
    """Raiz do repositório (ou worktree) que contém a pasta; None fora do Git."""
    saida = _git(pasta, 'rev-parse', '--show-toplevel')
    return Path(saida.strip()).resolve() if saida and saida.strip() else None


def _nfc(texto: str) -> str:
    """Normaliza o caminho em NFC para o atestado e as conferências (o nome no disco fica como está)."""
    return unicodedata.normalize('NFC', texto)


def _git_z(pasta: Path, *args: str) -> Optional[List[str]]:
    """Saída do git em campos separados por NUL, sem aspas nos caminhos (`core.quotepath=off`); None se falhar."""
    try:
        res = subprocess.run(['git', '-C', str(pasta), '-c', 'core.quotepath=off', *args],
                             capture_output=True, check=False)
    except Exception:
        return None
    if res.returncode != 0:
        return None
    return [os.fsdecode(c) for c in res.stdout.split(b'\0') if c]


def _em_governanca(rel: str) -> bool:
    return rel == 'sociedade' or rel.startswith('sociedade/')


def listar_arvore(top: Path) -> Optional[List[str]]:
    """Caminhos com mudança na árvore de trabalho ou no índice, rastreados ou não (ignorados pelo `.gitignore` não
    aparecem). `git status --porcelain=v1 -z`: em renomeação o destino vem antes da origem; os dois contam.
    Arquivo marcado `assume-unchanged` ou `skip-worktree` (`git ls-files -v`: letra minúscula ou `S`) também conta:
    o Git deixa de ver a mudança dele no `status`."""
    campos = _git_z(top, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    if campos is None:
        return None
    caminhos: List[str] = []
    i = 0
    while i < len(campos):
        campo = campos[i]
        i += 1
        if len(campo) < 4:
            continue
        caminhos.append(campo[3:])
        if campo[0] in 'RC' or campo[1] in 'RC':
            if i < len(campos):
                caminhos.append(campos[i])
                i += 1
    marcados = _git_z(top, 'ls-files', '-v', '-z')
    if marcados is None:
        return None
    for campo in marcados:
        if len(campo) > 2 and (campo[0].islower() or campo[0] == 'S'):
            caminhos.append(campo[2:])
    return caminhos


def obter_arquivos_candidato(pasta_projeto: Path, base: Optional[str] = None,
                             pasta_sociedade: Optional[Path] = None) -> Dict[str, Any]:
    """Arquivos do candidato: commits de base..HEAD (se houver base) mais alterações não commitadas.

    Os caminhos do Git são relativos à raiz do repositório, não à pasta do projeto (D01).
    Alterações em sociedade/ vindas de commits do candidato são sempre governança violada (Q60).
    Alterações não commitadas em sociedade/ só são ignoradas na pasta principal, onde
    sociedade/ é a canônica e recebe registros de governança em andamento.
    Caminhos lidos com `-z` e sem aspas; `caminhos` (todos fora de sociedade/) e `suja` (os que estão na árvore sem
    commit, fora de sociedade/) saem em NFC.
    """
    resultado: Dict[str, Any] = {'raiz': None, 'arquivos': [], 'removidos': [], 'governanca': [],
                                 'commit': None, 'base': None, 'erros': [], 'caminhos': [], 'suja': []}
    top = raiz_git(pasta_projeto)
    if top is None:
        return resultado
    resultado['raiz'] = top
    head = _git(top, 'rev-parse', 'HEAD')
    resultado['commit'] = head.strip() if head else None

    canonica = pasta_sociedade.resolve() if pasta_sociedade else None
    soc_local_e_canonica = canonica is not None and (top / 'sociedade').resolve() == canonica

    caminhos: Dict[str, str] = {}  # caminho relativo -> origem ('commit' | 'arvore')
    if base:
        base_sha = _git(top, 'rev-parse', '--verify', f'{base}^{{commit}}')
        if not base_sha:
            resultado['erros'].append(f'Base inválida ou inexistente: {base}')
            return resultado
        resultado['base'] = base_sha.strip()
        diff = _git_z(top, 'diff', '--name-only', '-z', '--no-renames', resultado['base'], 'HEAD')  # origem e destino
        if diff is None:
            resultado['erros'].append(f'git diff {resultado["base"][:12]}..HEAD falhou')
            return resultado
        for rel in diff:
            caminhos[rel] = 'commit'

    arvore = listar_arvore(top)
    if arvore is None:
        resultado['erros'].append('git status falhou: não consegui conferir a árvore de trabalho')
        arvore = []
    resultado['suja'] = sorted({_nfc(r) for r in arvore if not _em_governanca(r)})
    for rel in arvore:
        if rel not in caminhos:
            caminhos[rel] = 'arvore'

    resultado['caminhos'] = sorted({_nfc(r) for r in caminhos if not _em_governanca(r)})
    for rel, origem in sorted(caminhos.items()):
        if _em_governanca(rel):
            if origem == 'arvore' and soc_local_e_canonica:
                continue
            resultado['governanca'].append(_nfc(rel))
            continue
        alvo = top / rel
        if alvo.is_file():
            resultado['arquivos'].append(alvo.resolve())
        else:
            resultado['removidos'].append(_nfc(rel))
    return resultado


def resumir_testes(saida: str) -> Dict[str, Any]:
    """Extrai totais de uma saída do unittest (Ran N tests / OK / FAILED)."""
    tot: Dict[str, Any] = {}
    m = re.search(r'Ran (\d+) tests?', saida or '')
    if m:
        tot['executados'] = int(m.group(1))
    m = re.search(r'^(OK|FAILED)(?: \((.*?)\))?\s*$', saida or '', re.M)
    if m:
        tot['resultado'] = m.group(1)
        for par in (m.group(2) or '').split(','):
            if '=' in par:
                k, v = par.strip().split('=', 1)
                if v.isdigit():
                    tot[k] = int(v)
    return tot


ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]')


def contar_testes(saida: str) -> Dict[str, int]:
    """Conta os testes da saída completa de uma execução: `total`, `pulados` e `falhos`.

    Lê o unittest (`Ran N tests` e `skipped=K` da linha OK/FAILED), o Vitest (`Tests  X passed | Y skipped (Z)`) e o
    Playwright (`N passed`, `N skipped`, `N failed`...). Várias execuções no mesmo comando somam. Saída que nenhum dos
    três formatos reconhece dá total 0."""
    limpa = ANSI.sub('', saida or '')
    total = pulados = falhos = 0
    for m in re.finditer(r'^Ran (\d+) tests? in ', limpa, re.M):
        total += int(m.group(1))
    for m in re.finditer(r'^(?:OK|FAILED)(?: \((.*?)\))?\s*$', limpa, re.M):
        for par in (m.group(1) or '').split(','):
            chave, _, valor = par.strip().partition('=')
            if valor.isdigit():
                if chave == 'skipped':
                    pulados += int(valor)
                elif chave in ('failures', 'errors'):
                    falhos += int(valor)
    for m in re.finditer(r'^[ \t]*Tests[ \t]+(.+)$', limpa, re.M):
        itens = re.findall(r'(\d+)\s+(failed|passed|skipped|todo)\b', m.group(1))
        if not itens:
            continue
        parenteses = re.search(r'\((\d+)\)', m.group(1))
        total += int(parenteses.group(1)) if parenteses else sum(int(n) for n, _ in itens)
        pulados += sum(int(n) for n, t in itens if t in ('skipped', 'todo'))
        falhos += sum(int(n) for n, t in itens if t == 'failed')
    for m in re.finditer(r'^[ \t]*(\d+)[ \t]+(passed|failed|flaky|skipped|interrupted|did not run)\b', limpa, re.M):
        n, tipo = int(m.group(1)), m.group(2)
        total += n
        if tipo in ('skipped', 'did not run'):
            pulados += n
        elif tipo in ('failed', 'interrupted'):
            falhos += n
    return {'total': total, 'pulados': pulados, 'falhos': falhos}


def executar_com_timeout(comando: str, pasta: Path, timeout: int) -> Tuple[int, str, bool, float]:
    """Roda o comando num shell, em `pasta`, com tempo limite. Devolve (código, saída completa, estourou, segundos).

    No estouro, mata o grupo de processos inteiro (o shell e o que ele abriu) e devolve o que já tinha saído."""
    inicio = time.monotonic()
    try:
        proc = subprocess.Popen(comando, shell=True, cwd=pasta, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding='utf-8', errors='replace', start_new_session=True)
    except Exception as e:
        return -1, f'Erro ao executar comando: {e}', False, 0.0
    estourou = False
    try:
        saida, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        estourou = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        try:
            saida, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            saida = ''
    return proc.returncode, saida or '', estourou, round(time.monotonic() - inicio, 1)


def verificar_higiene_pastas(
    arquivos: List[Path],
    pasta_projeto: Path,
    pastas_isoladas: Optional[List[str]] = None,
    pasta_sociedade: Optional[Path] = None,
    raiz: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """Verifica se arquivos tocam pastas isoladas ou arquivos proibidos."""
    erros = []
    raiz = (raiz or pasta_projeto).resolve()
    regras_isoladas = list(PASTAS_PROIBIDAS_PADRAO)
    if pastas_isoladas:
        regras_isoladas.extend(pastas_isoladas)

    p_soc = pasta_sociedade.resolve() if pasta_sociedade else None

    for arq in arquivos:
        arq_res = arq.resolve()
        if p_soc and (arq_res == p_soc or p_soc in arq_res.parents):
            erros.append(f'Acesso violado: candidato não pode alterar arquivos na pasta de governança sociedade/: {arq}')
            continue

        try:
            rel = arq_res.relative_to(raiz).as_posix()
        except ValueError:
            erros.append(f'Arquivo fora dos limites do projeto: {arq}')
            continue

        for p_proibida in regras_isoladas:
            p_clean = p_proibida.strip().lstrip('./')
            if rel == p_clean or rel.startswith(f'{p_clean}/'):
                erros.append(f'Acesso violado à pasta/arquivo isolado proibido: {rel}')
            elif '.env' in rel.split('/'):
                erros.append(f'Arquivo sensível de configuração (.env) tocado: {rel}')
    return len(erros) == 0, erros


def verificar_compilacao(arquivos: List[Path]) -> Tuple[bool, List[str]]:
    """Compila scripts Python para verificar erros de sintaxe."""
    erros = []
    for arq in arquivos:
        if arq.suffix == '.py' and arq.is_file():
            # Compila em memória: py_compile gravaria __pycache__ dentro do projeto verificado.
            try:
                compile(arq.read_bytes(), str(arq), 'exec', dont_inherit=True)
            except SyntaxError as e:
                erros.append(f'Falha de compilação em {arq.name}: {e.msg} (linha {e.lineno})')
            except Exception as e:
                erros.append(f'Erro ao verificar compilação de {arq.name}: {e}')
    return len(erros) == 0, erros


def verificar_seguranca_antitoken(arquivos: List[Path]) -> Tuple[bool, List[str]]:
    """Varre arquivos em busca de segredos e violações da regra antitoken."""
    erros = []
    for arq in arquivos:
        if not arq.is_file():
            continue
        try:
            conteudo = arq.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        # 1. Segredos
        if SEGREDOS.search(conteudo):
            erros.append(f'Possível segredo ou chave privada detectada em {arq.name}')

        # 2. Regra antitoken em documentação e modelos
        if arq.suffix in ('.md', '.modelo'):
            for num, linha in enumerate(conteudo.splitlines(), start=1):
                if MEDICAO.search(linha) and not MEDICAO_OK.search(linha):
                    erros.append(
                        f'Violação da regra antitoken em {arq.name}:{num}: "{linha.strip()[:60]}"'
                    )
    return len(erros) == 0, erros


def executar_comando(comando: str, pasta_projeto: Path) -> Tuple[bool, str, int]:
    """Executa comando de terminal no diretório do projeto e captura resultado."""
    try:
        proc = subprocess.run(
            comando,
            shell=True,
            cwd=pasta_projeto,
            capture_output=True,
            text=True,
            check=False
        )
        sucesso = (proc.returncode == 0)
        saida_completa = (proc.stdout + '\n' + proc.stderr).strip()
        linhas = saida_completa.splitlines()
        resumo = '\n'.join(linhas[-5:]) if len(linhas) > 5 else saida_completa
        return sucesso, resumo, proc.returncode
    except Exception as e:
        return False, f'Erro ao executar comando: {e}', -1


def eh_comando_valido(cmd: Optional[str]) -> bool:
    """Verifica se uma string de comando é executável e não é placeholder ou 'nenhum'."""
    if not cmd:
        return False
    c = cmd.strip().strip('`').strip()
    if not c or c.lower() in ('nenhum', 'none', 'null', '—', '-', 'não', 'nao'):
        return False
    if c.startswith('<') and c.endswith('>'):
        return False
    return True


def ler_comandos_perfil(pasta_projeto: Path, perfil: Optional[Path] = None) -> Dict[str, Optional[str]]:
    """Lê comandos configurados em perfil.md (Build, Testes, Lint e tipos).

    `perfil` (o perfil canônico da `--pasta-sociedade`) vale antes dos candidatos da pasta do projeto."""
    candidatos = ([Path(perfil)] if perfil else []) + [
        pasta_projeto / 'docs' / 'sociedade' / 'perfil.md',
        pasta_projeto / 'perfil.md',
        pasta_projeto / 'sociedade' / 'perfil.md',
    ]
    comandos = {'build': None, 'testes': None, 'lint': None}
    perfil_arq = next((p for p in candidatos if p.is_file()), None)
    if not perfil_arq:
        return comandos

    try:
        texto = perfil_arq.read_text(encoding='utf-8')
    except Exception:
        return comandos

    m_sec = re.search(r'##\s+Comandos\b(.*?)(?=\n##|\Z)', texto, re.S | re.I)
    bloco = m_sec.group(1) if m_sec else texto

    m_build = re.search(r'[-*]?\s*\**Build\**\s*:\s*(.+)$', bloco, re.M | re.I)
    if m_build:
        v = m_build.group(1).strip().strip('`')
        if not (v.startswith('<') and v.endswith('>')):
            comandos['build'] = v

    m_testes = re.search(r'[-*]?\s*\**Testes\**\s*:\s*(.+)$', bloco, re.M | re.I)
    if m_testes:
        v = m_testes.group(1).strip().strip('`')
        if not (v.startswith('<') and v.endswith('>')):
            comandos['testes'] = v

    m_lint = re.search(r'[-*]?\s*\**(?:Lint\s+e\s+tipos|Lint|Tipos)\**\s*:\s*(.+)$', bloco, re.M | re.I)
    if m_lint:
        v = m_lint.group(1).strip().strip('`')
        if not (v.startswith('<') and v.endswith('>')):
            comandos['lint'] = v

    return comandos


def inferir_arquivos_fatia(pasta_sociedade: Path, fatia_id: str) -> List[str]:
    """Infere arquivos declarados para a fatia a partir de rodada.md ou registro.json."""
    if not pasta_sociedade or not pasta_sociedade.is_dir():
        return []

    str_f = str(fatia_id).strip()
    p_rodada = pasta_sociedade / 'rodada.md'
    if p_rodada.is_file():
        try:
            texto = p_rodada.read_text(encoding='utf-8')
            for linha in texto.splitlines():
                if f'{str_f}.' in linha or f'fatia_{str_f}' in linha or (f' {str_f} ' in linha):
                    m = re.search(r'paralela:\s*([^)]+)', linha)
                    if m:
                        return [x.strip() for x in m.group(1).split(',') if x.strip()]
        except Exception:
            pass

    p_reg = pasta_sociedade / 'registro.json'
    if p_reg.is_file():
        try:
            dados = json.loads(p_reg.read_text(encoding='utf-8'))
            for ev in reversed(dados.get('eventos', [])):
                tipo = ev.get('tipo')
                d = ev.get('dados', {})
                t_id = str(d.get('tarefa_id', ''))
                if t_id in (str_f, f'fatia_{str_f}'):
                    if tipo in ('tarefa_criada', 'tarefa_atualizada') and d.get('arquivos'):
                        return list(d['arquivos'])
                    elif tipo == 'passagem_despachada' and d.get('leia_so'):
                        return list(d['leia_so'])
        except Exception:
            pass
    return []


def obter_arquivos_outras_fatias(pasta_sociedade: Path, fatia_id: str, pasta_projeto: Path) -> Set[Path]:
    """Obtém conjunto de caminhos pertencentes a outras fatias no mesmo workspace."""
    outros = set()
    if not pasta_sociedade or not pasta_sociedade.is_dir():
        return outros

    str_fatia = str(fatia_id).strip() if fatia_id else ''

    p_rodada = pasta_sociedade / 'rodada.md'
    if p_rodada.is_file():
        try:
            texto = p_rodada.read_text(encoding='utf-8')
            for linha in texto.splitlines():
                m = re.match(r'^(\d+)\.\s+(.+?)\s+—', linha.strip())
                if m:
                    f_n = m.group(1)
                    if f_n != str_fatia and f'fatia_{f_n}' != str_fatia:
                        m_par = re.search(r'paralela:\s*([^)]+)', linha)
                        if m_par:
                            for x in m_par.group(1).split(','):
                                x = x.strip()
                                if x:
                                    outros.add((pasta_projeto / x).resolve())
        except Exception:
            pass

    p_reg = pasta_sociedade / 'registro.json'
    if p_reg.is_file():
        try:
            dados = json.loads(p_reg.read_text(encoding='utf-8'))
            for ev in dados.get('eventos', []):
                d = ev.get('dados', {})
                t_id = str(d.get('tarefa_id', ''))
                if t_id and t_id != str_fatia and t_id != f'fatia_{str_fatia}':
                    arqs = d.get('arquivos') or d.get('leia_so') or []
                    for a in arqs:
                        outros.add((pasta_projeto / a).resolve())
        except Exception:
            pass

    return outros



def verificar_disjuncao(arquivos_tocados: List[Path], arquivos_proibidos: List[str], pasta_projeto: Path) -> Tuple[bool, List[str]]:
    """Garante que nenhum arquivo tocado coincide com arquivos proibidos da disjunção."""
    erros = []
    raiz = pasta_projeto.resolve()
    tocados_rel = set()
    for a in arquivos_tocados:
        try:
            tocados_rel.add(a.resolve().relative_to(raiz).as_posix())
        except ValueError:
            pass

    for proibido in arquivos_proibidos:
        p_clean = proibido.strip().lstrip('./')
        if p_clean in tocados_rel:
            erros.append(f'Arquivo tocado viola disjunção declarada: {p_clean}')

    return len(erros) == 0, erros


class VerificadorPreDevolucao:
    """Orquestrador da verificação pré-devolução."""

    def __init__(self, pasta_projeto: Path, pasta_sociedade: Optional[Path] = None):
        self.pasta_projeto = Path(pasta_projeto).resolve()
        self.pasta_sociedade = Path(pasta_sociedade).resolve() if pasta_sociedade else localizar_sociedade_canonica(self.pasta_projeto)

    def _rodar_areas(self, areas: List[Dict[str, Any]], area: Optional[str], caminhos: List[str],
                     raiz: Optional[Path], todos_erros: List[str],
                     areas_rodadas: List[Dict[str, Any]],
                     tocadas_out: Optional[List[str]] = None) -> Tuple[bool, str, Optional[str], Dict[str, int]]:
        """Roda os testes de cada área escolhida (B11c) e acrescenta o registro de cada uma em `areas_rodadas`.

        Sem `area`: as áreas que `caminhos` (base..HEAD) toca; com `area`: só ela. O comando e o timeout vêm da tabela
        do perfil. Reprovam: saída diferente de zero, timeout, 0 testes, todos pulados e testes que falharam com
        código 0. `tocadas_out` recebe todas as áreas que base..HEAD toca, rodem ou não. Devolve
        (ok, resumo, comandos, totais)."""
        totais = {'total': 0, 'pulados': 0, 'falhos': 0}
        if not areas:
            return False, 'Portão por área indisponível: o perfil não tem áreas válidas.', None, totais
        if raiz is None:
            todos_erros.append('Portão por área: a pasta não está num repositório Git.')
            return False, 'Sem repositório Git: nenhum teste rodou.', None, totais
        tocadas = areas_tocadas(caminhos, areas)
        if tocadas_out is not None:
            tocadas_out.extend(tocadas)
        if area:
            escolhidas = [a for a in areas if a['nome'] == area]
            if not escolhidas:
                todos_erros.append(f'Área desconhecida: "{area}" (o perfil tem: {", ".join(a["nome"] for a in areas)}).')
                return False, 'Área desconhecida: nenhum teste rodou.', None, totais
        else:
            escolhidas = [a for a in areas if a['nome'] in tocadas]
            if not escolhidas:
                todos_erros.append('base..HEAD não toca nenhuma área do "Portão por área" (só sociedade/ e docs/?): '
                                   'não há teste a rodar. Use --area <nome> para rodar uma área mesmo assim.')
                return False, 'Nenhuma área tocada: nenhum teste rodou.', None, totais
        ok_geral, resumos, comandos = True, [], []
        for a in escolhidas:
            registro: Dict[str, Any] = {'area': a['nome'], 'pasta': a['pasta'], 'comando': a['comando'],
                                        'timeout_s': a['timeout']}
            areas_rodadas.append(registro)
            comandos.append(f'{a["nome"]}: {a["comando"]}')
            pasta_exec = (raiz / a['pasta']).resolve()
            try:
                pasta_exec.relative_to(raiz)
            except ValueError:
                pasta_exec = None
            if pasta_exec is None or not pasta_exec.is_dir():
                msg = f'Área {a["nome"]}: a pasta "{a["pasta"]}" não existe no repositório.'
                registro.update({'ok': False, 'motivos': [msg]})
                todos_erros.append(msg)
                ok_geral = False
                continue
            codigo, saida, estourou, duracao = executar_com_timeout(a['comando'], pasta_exec, a['timeout'])
            t = contar_testes(saida)
            motivos = []
            if estourou:
                motivos.append(f'timeout de {a["timeout"]} s estourado')
            else:
                if codigo != 0:
                    motivos.append(f'saiu com código {codigo}')
                if t['total'] == 0:
                    motivos.append('0 testes executados (ou formato de saída não reconhecido)')
                elif t['pulados'] >= t['total']:
                    motivos.append(f'todos os {t["total"]} testes foram pulados')
                if t['falhos'] > 0 and codigo == 0:
                    motivos.append(f'{t["falhos"]} teste(s) falharam, embora o comando tenha saído com código 0')
            final = '\n'.join(ANSI.sub('', saida).strip().splitlines()[-6:])
            registro.update({'ok': not motivos, 'codigo': codigo, 'duracao_s': duracao, 'timeout_estourado': estourou,
                             'testes': t, 'motivos': motivos, 'saida_final': final})
            for k in totais:
                totais[k] += t[k]
            resumos.append(f'{a["nome"]}: {t["total"]} testes, {t["pulados"]} pulados, {duracao} s'
                           + (f' — {"; ".join(motivos)}' if motivos else ''))
            if motivos:
                ok_geral = False
                todos_erros.append(f'Portão da área {a["nome"]} reprovou: {"; ".join(motivos)}. '
                                   f'Comando: {a["comando"]}. Fim da saída: {final[-300:]}')
        return ok_geral, ' | '.join(resumos), '; '.join(comandos), totais

    def executar(
        self,
        papel: str = 'Executor',
        etapa_id: str = '',
        fatia_id: str = '',
        comando_teste: Optional[str] = None,
        comando_build: Optional[str] = None,
        comando_lint: Optional[str] = None,
        ignorar_testes: bool = False,
        motivo_ignorar: str = '',
        arquivos_alvo: Optional[List[str]] = None,
        arquivos_proibidos: Optional[List[str]] = None,
        pastas_isoladas: Optional[List[str]] = None,
        ignorar_arquivos_externos: bool = False,
        base: Optional[str] = None,
        por_area: bool = False,
        area: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executa bateria determinística de verificações físicas.

        Com `por_area` (B11, B11c) o portão é o do `sc.py entregar`: o comando de testes e o timeout vêm só da seção
        "Portão por área" do perfil canônico (o da pasta de sociedade); a árvore suja, 0 testes, todos pulados e o
        timeout reprovam; roda cada área que base..HEAD toca (ou só `area`)."""
        todos_erros: List[str] = []
        areas_perfil: List[Dict[str, Any]] = []
        perfil_canonico: Optional[Path] = None
        perfil_sha256: Optional[str] = None
        if por_area:
            if comando_teste or ignorar_testes or arquivos_alvo is not None or ignorar_arquivos_externos:
                raise ValueError('o portão por área não aceita comando de teste, dispensa de testes nem lista de arquivos.')
            perfil_canonico = self.pasta_sociedade / 'perfil.md'
            try:
                bruto_perfil = perfil_canonico.read_bytes()
                perfil_sha256 = hashlib.sha256(bruto_perfil).hexdigest()
                areas_perfil = ler_portao_por_area(bruto_perfil.decode('utf-8'))
            except (OSError, UnicodeDecodeError) as e:
                todos_erros.append(f'Portão por área: não consegui ler o perfil canônico {perfil_canonico}: {e}')
            except ErroPortao as e:
                todos_erros.append(f'Portão por área: {e}')
            if not base:
                todos_erros.append('Portão por área: informe --base (a área de cada caminho vem de base..HEAD).')

        # 1. Determina arquivos a inspecionar
        arquivos_escopo = list(arquivos_alvo) if arquivos_alvo is not None else None
        if not arquivos_escopo and ignorar_arquivos_externos and fatia_id:
            inferred = inferir_arquivos_fatia(self.pasta_sociedade, fatia_id)
            if inferred:
                arquivos_escopo = inferred

        origem_arquivos = 'lista_explicita'
        raiz_higiene = None
        arquivos_removidos: List[str] = []
        top = raiz_git(self.pasta_projeto)
        commit_atual = (_git(top, 'rev-parse', 'HEAD') or '').strip() or None if top else None
        base_resolvida = None
        caminhos_candidato: List[str] = []
        arvore_suja: List[str] = []
        if arquivos_escopo is not None:
            arquivos_verificar = []
            for a in arquivos_escopo:
                p = (self.pasta_projeto / a).resolve() if not Path(a).is_absolute() else Path(a).resolve()
                if p.is_file():
                    arquivos_verificar.append(p)
                else:
                    todos_erros.append(f'Arquivo do escopo da fatia não encontrado: {a}')
        else:
            cand = obter_arquivos_candidato(self.pasta_projeto, base, self.pasta_sociedade)
            origem_arquivos = 'git'
            raiz_higiene = cand['raiz']
            commit_atual, base_resolvida = cand['commit'], cand['base']
            arquivos_removidos = cand['removidos']
            caminhos_candidato = cand['caminhos']
            arvore_suja = cand['suja']
            todos_erros.extend(cand['erros'])
            if por_area and arvore_suja:
                amostra = ', '.join(arvore_suja[:8]) + (f' e mais {len(arvore_suja) - 8}' if len(arvore_suja) > 8 else '')
                todos_erros.append(
                    f'Árvore suja: {len(arvore_suja)} caminho(s) com mudança fora de sociedade/ e sem commit '
                    f'(o portão atesta o commit, não a árvore): {amostra}')
            for rel in cand['governanca']:
                todos_erros.append(f'Acesso violado: candidato não pode alterar arquivos na pasta de governança sociedade/: {rel}')
            arquivos_verificar = cand['arquivos']
            if ignorar_arquivos_externos:
                outros = obter_arquivos_outras_fatias(self.pasta_sociedade, fatia_id, self.pasta_projeto)
                if outros:
                    arquivos_verificar = [p for p in arquivos_verificar if p not in outros]
            if not arquivos_verificar and not arquivos_removidos and not cand['governanca'] and not cand['erros']:
                todos_erros.append(
                    'Nada a inspecionar: sem alterações na árvore e sem --base. '
                    'Para um candidato já commitado, informe --base <commit de partida da etapa>.'
                    if cand['raiz'] else
                    'Nada a inspecionar: a pasta não está num repositório Git e nenhum --arquivos-alvo foi informado.'
                )

        # 2. Carrega comandos do perfil.md se disponíveis
        comandos_perfil = ler_comandos_perfil(self.pasta_projeto, perfil_canonico)

        # 3. Checagens individuais
        resultados_verificacoes = {}

        # A. Higiene e isolamento
        higiene_ok, erros_higiene = verificar_higiene_pastas(
            arquivos_verificar, self.pasta_projeto, pastas_isoladas, self.pasta_sociedade, raiz=raiz_higiene
        )
        resultados_verificacoes['higiene_pastas'] = {'ok': higiene_ok, 'erros': erros_higiene}
        todos_erros.extend(erros_higiene)

        # B. Compilação, build e checagem de tipos
        compilacao_ok = True
        erros_compilacao = []

        # B.1 Comando de build (opcional via CLI ou perfil.md)
        cmd_build = comando_build or comandos_perfil.get('build')
        build_ok = True
        if cmd_build and eh_comando_valido(cmd_build):
            build_ok, resumo_build, b_code = executar_comando(cmd_build, self.pasta_projeto)
            resultados_verificacoes['build'] = {
                'ok': build_ok,
                'comando': cmd_build,
                'detalhes': resumo_build,
                'codigo': b_code
            }
            if not build_ok:
                msg_b = f'Comando de build falhou (código de saída {b_code}): {resumo_build}'
                todos_erros.append(msg_b)
                erros_compilacao.append(msg_b)
                compilacao_ok = False

        # B.2 Compilação estática de Python, em memória
        comp_py_ok, erros_py = verificar_compilacao(arquivos_verificar)
        if not comp_py_ok:
            compilacao_ok = False
            erros_compilacao.extend(erros_py)
            todos_erros.extend(erros_py)

        # B.3 Checagem estática de tipos (TypeScript ou Lint e tipos configurado)
        tem_ts = any(a.suffix in ('.ts', '.tsx') for a in arquivos_verificar)
        tem_tsconfig = (self.pasta_projeto / 'tsconfig.json').is_file()
        cmd_lint_perfil = comando_lint or comandos_perfil.get('lint')

        tipos_ok = True
        if cmd_lint_perfil and cmd_lint_perfil.lower() == 'nenhum':
            tipos_ok = True
        elif cmd_lint_perfil and eh_comando_valido(cmd_lint_perfil):
            cmd_tipo = cmd_lint_perfil
            tipos_ok, resumo_tipos, t_code = executar_comando(cmd_tipo, self.pasta_projeto)
            resultados_verificacoes['tipos_estaticos'] = {
                'ok': tipos_ok,
                'comando': cmd_tipo,
                'detalhes': resumo_tipos,
                'codigo': t_code
            }
            if not tipos_ok:
                msg_tipo = f'Checagem estática de tipos falhou (código de saída {t_code}): {resumo_tipos}'
                todos_erros.append(msg_tipo)
                erros_compilacao.append(msg_tipo)
                compilacao_ok = False
        elif tem_ts and tem_tsconfig:
            cmd_tipo = 'npx tsc --noEmit'
            tipos_ok, resumo_tipos, t_code = executar_comando(cmd_tipo, self.pasta_projeto)
            resultados_verificacoes['tipos_estaticos'] = {
                'ok': tipos_ok,
                'comando': cmd_tipo,
                'detalhes': resumo_tipos,
                'codigo': t_code
            }
            if not tipos_ok:
                msg_tipo = f'Checagem estática de tipos falhou (código de saída {t_code}): {resumo_tipos}'
                todos_erros.append(msg_tipo)
                erros_compilacao.append(msg_tipo)
                compilacao_ok = False

        resultados_verificacoes['compilacao'] = {'ok': compilacao_ok, 'erros': erros_compilacao}

        # E. Segurança antitoken e segredos
        seg_ok, erros_seg = verificar_seguranca_antitoken(arquivos_verificar)
        resultados_verificacoes['seguranca_antitoken'] = {'ok': seg_ok, 'erros': erros_seg}
        todos_erros.extend(erros_seg)

        # F. Disjunção
        if arquivos_proibidos:
            disj_ok, erros_disj = verificar_disjuncao(arquivos_verificar, arquivos_proibidos, self.pasta_projeto)
        else:
            disj_ok, erros_disj = True, []
        resultados_verificacoes['disjuncao'] = {'ok': disj_ok, 'erros': erros_disj}
        todos_erros.extend(erros_disj)

        # G. Testes automatizados
        comando_testes_usado = None
        areas_rodadas: List[Dict[str, Any]] = []
        areas_do_candidato: List[str] = []
        if por_area:
            testes_ok, resumo_testes, comando_testes_usado, totais_testes = self._rodar_areas(
                areas_perfil, area, caminhos_candidato, raiz_higiene, todos_erros, areas_rodadas, areas_do_candidato)
            if raiz_higiene is not None:
                depois = sorted({_nfc(r) for r in (listar_arvore(raiz_higiene) or []) if not _em_governanca(r)})
                if depois != arvore_suja:
                    novos = sorted(set(depois) ^ set(arvore_suja))
                    todos_erros.append('A árvore mudou durante o portão (os testes alteraram arquivos fora de '
                                       f'sociedade/): {", ".join(novos[:8])}')
                    testes_ok = False
        elif ignorar_testes:
            if not motivo_ignorar.strip():
                todos_erros.append('Flag --ignorar-testes exige justificativa explícita (--motivo-ignorar).')
                testes_ok = False
                resumo_testes = 'Testes ignorados sem justificativa'
            else:
                testes_ok = True
                resumo_testes = f'Dispensado com justificativa: {motivo_ignorar.strip()}'
        else:
            cmd = comando_teste or comandos_perfil.get('testes') or ('python3 -m unittest discover tests' if (self.pasta_projeto / 'tests').is_dir() else None)
            if cmd and eh_comando_valido(cmd):
                comando_testes_usado = cmd
                testes_ok, resumo_testes, code = executar_comando(cmd, self.pasta_projeto)
                if not testes_ok:
                    todos_erros.append(f'Suíte de testes falhou (código de saída {code}): {resumo_testes}')
            else:
                testes_ok = False
                resumo_testes = (
                    'Nenhum teste configurado ou diretório de testes detectado no projeto. '
                    'Para dispensar testes na pré-devolução, utilize --ignorar-testes '
                    'acompanhado de justificativa explícita (--motivo-ignorar).'
                )
                todos_erros.append(resumo_testes)

        resultados_verificacoes['testes'] = {'ok': testes_ok, 'detalhes': resumo_testes,
                                             'comando': comando_testes_usado,
                                             'totais': totais_testes if por_area else resumir_testes(resumo_testes)}
        if por_area:
            resultados_verificacoes['arvore_limpa'] = {'ok': not arvore_suja, 'suja': arvore_suja}

        # 4. Mapeamento de hashes dos artefatos inspecionados
        hashes_artefatos = {}
        raiz_hash = raiz_higiene or self.pasta_projeto
        for arq in arquivos_verificar:
            try:
                rel = _nfc(arq.relative_to(raiz_hash).as_posix())
                hashes_artefatos[rel] = calcular_sha256(arq)
            except Exception:
                pass

        aprovado = len(todos_erros) == 0 and testes_ok and higiene_ok and compilacao_ok and seg_ok and disj_ok and build_ok and tipos_ok

        atestado = {
            'tipo': 'atestado_pre_devolucao',
            'versao': '1.3.0' if por_area else '1.2.0',
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
            'papel': papel,
            'etapa_id': etapa_id or 'N/A',
            'fatia_id': fatia_id or 'N/A',
            'status': 'APROVADO' if aprovado else 'REPROVADO',
            'verificacoes': resultados_verificacoes,
            'commit': commit_atual,
            'base': base_resolvida,
            'origem_arquivos': origem_arquivos,
            'total_arquivos_inspecionados': len(arquivos_verificar),
            'arquivos_removidos': arquivos_removidos,
            'python': sys.version.split()[0],
            'hashes_artefatos': hashes_artefatos,
            'arquivos_inspecionados': sorted(hashes_artefatos),
            'erros': todos_erros
        }
        if por_area:
            atestado['portao'] = {
                'modo': 'por_area',
                'perfil': 'sociedade/perfil.md',
                'perfil_sha256': perfil_sha256,
                'commit': commit_atual,
                'area_pedida': area,
                'areas_tocadas': areas_do_candidato,
                'cobertura_completa': bool(areas_do_candidato) and all(
                    any(r['area'] == nome and r.get('ok') is True for r in areas_rodadas) for nome in areas_do_candidato),
                'areas': areas_rodadas,
            }

        # Calcula hash criptográfico SHA-256 do payload do atestado (para prova física e rastreabilidade)
        payload_hash = json.dumps({
            'commit': commit_atual,
            'base': base_resolvida,
            'papel': papel,
            'etapa_id': etapa_id or 'N/A',
            'fatia_id': fatia_id or 'N/A',
            'status': atestado['status'],
            'verificacoes': resultados_verificacoes,
            'hashes_artefatos': hashes_artefatos,
            'portao': atestado.get('portao'),
            'erros': todos_erros
        }, sort_keys=True)
        atestado['atestado_hash'] = hashlib.sha256(payload_hash.encode('utf-8')).hexdigest()
        return atestado


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument('--papel', default='Executor', help='Papel do agente devolvendo a fatia (ex: Aragorn, Elrond)')
    p.add_argument('--etapa', default='', help='Identificador da etapa (ex: SC-E5)')
    p.add_argument('--fatia', default='', help='Identificador da fatia (ex: F1)')
    p.add_argument('--pasta-projeto', default='.', help='Raiz do repositório/projeto')
    p.add_argument('--pasta-sociedade', default=None, help='Pasta com registro e governança')
    p.add_argument('--comando-teste', default=None, help='Comando personalizado de testes')
    p.add_argument('--comando-build', default=None, help='Comando de build/compilação do projeto')
    p.add_argument('--comando-lint', default=None, help='Comando de lint e checagem de tipos')
    p.add_argument('--ignorar-testes', action='store_true', help='Não executa testes automatizados')
    p.add_argument('--motivo-ignorar', default='', help='Justificativa obrigatória se --ignorar-testes for usado')
    p.add_argument('--arquivos-alvo', '--arquivos', dest='arquivos', nargs='*', default=None,
                   help='Lista explícita de arquivos da fatia (escopo delimitado)')
    p.add_argument('--ignorar-arquivos-externos', action='store_true', default=False,
                   help='Ignora alterações fora do escopo delimitado da fatia')
    p.add_argument('--proibidos', nargs='*', default=None, help='Lista de arquivos proibidos por disjunção')
    p.add_argument('--pastas-isoladas', nargs='*', default=None, help='Lista de pastas ou caminhos isolados protegidos')
    p.add_argument('--base', default=None,
                   help='Commit de partida da etapa: inspeciona os arquivos de base..HEAD (candidato commitado)')
    p.add_argument('--portao-por-area', action='store_true',
                   help='Portão do `sc.py entregar`: comando e timeout só da seção "Portão por área" do perfil canônico; '
                        'reprova árvore suja, 0 testes, todos pulados e timeout (exige --base)')
    p.add_argument('--area', default=None, help='Com --portao-por-area: roda só esta área (padrão: as que base..HEAD toca)')
    p.add_argument('--saida-json', default=None, help='Caminho para salvar o atestado em arquivo JSON')
    args = p.parse_args(argv)
    if args.area and not args.portao_por_area:
        p.error('--area só vale com --portao-por-area.')
    if args.portao_por_area and (args.comando_teste or args.ignorar_testes or args.arquivos is not None
                                 or args.ignorar_arquivos_externos):
        p.error('--portao-por-area não aceita --comando-teste, --ignorar-testes, --arquivos-alvo nem '
                '--ignorar-arquivos-externos: o comando vem do perfil.')

    verificador = VerificadorPreDevolucao(
        pasta_projeto=Path(args.pasta_projeto),
        pasta_sociedade=Path(args.pasta_sociedade) if args.pasta_sociedade else None
    )

    atestado = verificador.executar(
        papel=args.papel,
        etapa_id=args.etapa,
        fatia_id=args.fatia,
        comando_teste=args.comando_teste,
        comando_build=args.comando_build,
        comando_lint=args.comando_lint,
        ignorar_testes=args.ignorar_testes,
        motivo_ignorar=args.motivo_ignorar,
        arquivos_alvo=args.arquivos,
        arquivos_proibidos=args.proibidos,
        pastas_isoladas=args.pastas_isoladas,
        ignorar_arquivos_externos=args.ignorar_arquivos_externos,
        base=args.base,
        por_area=args.portao_por_area,
        area=args.area
    )

    if args.saida_json:
        caminho_saida = Path(args.saida_json)
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        caminho_saida.write_text(json.dumps(atestado, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    # Exibição no terminal
    print(f'=== ATESTADO PRÉ-DEVOLUÇÃO: {atestado["status"]} ===')
    print(f'Papel: {atestado["papel"]} | Etapa: {atestado["etapa_id"]} | Fatia: {atestado["fatia_id"]}')
    print(f'Timestamp: {atestado["timestamp"]} | Arquivos inspecionados: {atestado["total_arquivos_inspecionados"]}')
    if atestado.get('commit'):
        print(f'Commit: {atestado["commit"][:12]} | Base: {(atestado.get("base") or "—")[:12]} | Origem: {atestado["origem_arquivos"]}')
    print('Verificações:')
    for k, v in atestado['verificacoes'].items():
        st = 'OK' if v.get('ok') else 'FALHA'
        print(f'  - {k}: [{st}]')

    for a in (atestado.get('portao') or {}).get('areas', []):
        t = a.get('testes') or {}
        print(f'  * área {a["area"]} [{"OK" if a.get("ok") else "FALHA"}] {a["comando"]} (pasta {a["pasta"]}, '
              f'timeout {a["timeout_s"]} s): {t.get("total", "?")} testes, {t.get("pulados", "?")} pulados')

    if atestado['status'] != 'APROVADO':
        print('\nPENDÊNCIAS E ERROS DETECTADOS:')
        for e in atestado['erros']:
            print(f'  [x] {e}')
        return 1

    print('\nTodos os critérios físicos de devolução foram satisfeitos com sucesso.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
