#!/usr/bin/env python3
"""Gerenciamento de worktrees Git da Sociedade do Código.

Local padrão: ~/.sociedade/trabalho/<projeto>/<etapa>
Permite criar, listar e remover worktrees de etapas de forma determinística
garantindo o isolamento do código do candidato sem alterar sociedade/ canônica.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sc_registro import localizar_sociedade_canonica  # noqa: E402

NOME_VALIDO = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')


class ErroWorktree(Exception):
    """Erro nas operações com worktrees Git."""


def validar_nome(valor: str, campo: str) -> str:
    """Aceita só nomes simples (letras, números, ponto, hífen e sublinhado), sem barra nem '..'."""
    v = (valor or '').strip()
    if not v or '..' in v or not NOME_VALIDO.match(v):
        raise ErroWorktree(f'{campo} inválido: "{valor}". Use letras, números, ".", "_" ou "-", sem barras.')
    return v


def obter_pasta_raiz_trabalho(pasta_raiz: Optional[Path] = None) -> Path:
    """Retorna o diretório base de trabalho (~/.sociedade/trabalho por padrão)."""
    if pasta_raiz is not None:
        return Path(pasta_raiz).resolve()
    return (Path.home() / '.sociedade' / 'trabalho').resolve()


def obter_caminho_worktree(
    etapa: str,
    projeto: Optional[str] = None,
    pasta_base: Optional[Path] = None,
    pasta_raiz: Optional[Path] = None
) -> Path:
    """Calcula o caminho padrão para o worktree de uma etapa, sempre dentro de <raiz>/<projeto>."""
    raiz = obter_pasta_raiz_trabalho(pasta_raiz)
    etapa = validar_nome(etapa, 'Identificador da etapa')
    if not projeto:
        canonica = localizar_sociedade_canonica(pasta_base)
        projeto = re.sub(r'[^A-Za-z0-9._-]+', '_', canonica.parent.name).strip('._-') or 'projeto'
    projeto = validar_nome(projeto, 'Nome do projeto')
    pasta_projeto = (raiz / projeto).resolve()
    caminho = (pasta_projeto / etapa).resolve()
    if caminho.parent != pasta_projeto:
        raise ErroWorktree(f'Caminho do worktree fora da pasta de trabalho do projeto: {caminho}')
    return caminho


def _worktrees_registrados(repo_root: Path) -> List[Dict[str, str]]:
    """Worktrees que o Git conhece para o repositório (formato --porcelain)."""
    res = subprocess.run(
        ['git', '-C', str(repo_root), 'worktree', 'list', '--porcelain'],
        capture_output=True, text=True
    )
    if res.returncode != 0:
        raise ErroWorktree(f'Falha ao listar worktrees Git: {res.stderr.strip()}')
    blocos: List[Dict[str, str]] = []
    atual: Dict[str, str] = {}
    for linha in res.stdout.splitlines() + ['']:
        linha = linha.strip()
        if not linha:
            if 'worktree' in atual:
                blocos.append(atual)
            atual = {}
            continue
        partes = linha.split(maxsplit=1)
        atual[partes[0]] = partes[1] if len(partes) > 1 else ''
    return blocos


def obter_raiz_repositorio_git(pasta_base: Optional[Path] = None) -> Path:
    """Obtém a raiz do repositório canônico Git."""
    canonica = localizar_sociedade_canonica(pasta_base)
    repo = canonica.parent
    try:
        res = subprocess.run(
            ['git', '-C', str(repo), 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, check=True
        )
        return Path(res.stdout.strip()).resolve()
    except Exception as e:
        raise ErroWorktree(f'Não foi possível determinar a raiz do repositório Git em {repo}: {e}')


def criar_worktree(
    etapa: str,
    branch: Optional[str] = None,
    base: Optional[str] = None,
    projeto: Optional[str] = None,
    pasta_base: Optional[Path] = None,
    pasta_raiz: Optional[Path] = None
) -> Dict[str, Any]:
    """Cria um worktree de etapa no local padrão."""
    etapa = validar_nome(etapa, 'Identificador da etapa')
    caminho = obter_caminho_worktree(etapa, projeto, pasta_base, pasta_raiz)
    if caminho.exists():
        raise ErroWorktree(f'Worktree ou pasta já existe em: {caminho}')

    repo_root = obter_raiz_repositorio_git(pasta_base)
    nome_branch = branch.strip() if branch and branch.strip() else f'etapa/{etapa}'
    base_ref = base.strip() if base and base.strip() else 'HEAD'

    # Cria pasta pai do destino se necessário
    caminho.parent.mkdir(parents=True, exist_ok=True)

    # Verifica se a branch já existe no repositório
    check_branch = subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--verify', f'refs/heads/{nome_branch}'],
        capture_output=True, text=True
    )

    if check_branch.returncode == 0:
        cmd = ['git', '-C', str(repo_root), 'worktree', 'add', str(caminho), nome_branch]
    else:
        cmd = ['git', '-C', str(repo_root), 'worktree', 'add', str(caminho), '-b', nome_branch, base_ref]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise ErroWorktree(f'Falha ao criar worktree Git: {res.stderr.strip() or res.stdout.strip()}')

    return {
        'sucesso': True,
        'caminho': str(caminho),
        'branch': nome_branch,
        'etapa': etapa,
        'base': base_ref,
    }


def listar_worktrees(
    projeto: Optional[str] = None,
    pasta_base: Optional[Path] = None,
    pasta_raiz: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Lista os worktrees associados ao projeto."""
    repo_root = obter_raiz_repositorio_git(pasta_base)
    raiz_trabalho = obter_pasta_raiz_trabalho(pasta_raiz)
    if not projeto:
        canonica = localizar_sociedade_canonica(pasta_base)
        projeto = canonica.parent.name
    pasta_projeto_trabalho = (raiz_trabalho / projeto).resolve()

    itens: List[Dict[str, Any]] = []
    for bloco in _worktrees_registrados(repo_root):
        caminho_wt = Path(bloco['worktree']).resolve()
        branch_wt = bloco.get('branch', '')
        if branch_wt.startswith('refs/heads/'):
            branch_wt = branch_wt[len('refs/heads/'):]
        padrao = caminho_wt.parent == pasta_projeto_trabalho
        itens.append({
            'caminho': str(caminho_wt),
            'branch': branch_wt,
            'head': bloco.get('HEAD', ''),
            'etapa': caminho_wt.name,
            'padrao': padrao,
        })
    return itens


def remover_worktree(
    etapa: str,
    forcar: bool = False,
    projeto: Optional[str] = None,
    pasta_base: Optional[Path] = None,
    pasta_raiz: Optional[Path] = None
) -> Dict[str, Any]:
    """Remove um worktree de etapa, recusando se houver alterações sem commit (a menos que forcar=True)."""
    etapa = validar_nome(etapa, 'Identificador da etapa')
    caminho = obter_caminho_worktree(etapa, projeto, pasta_base, pasta_raiz)
    if not caminho.exists():
        raise ErroWorktree(f'Worktree não encontrado em: {caminho}')

    repo_root = obter_raiz_repositorio_git(pasta_base)
    registrados = {Path(b['worktree']).resolve() for b in _worktrees_registrados(repo_root)}
    if caminho not in registrados:
        raise ErroWorktree(
            f'{caminho} não é um worktree registrado deste repositório. Nada foi removido.'
        )

    # Recusa alterações sem commit, a menos que --forcar
    status_res = subprocess.run(
        ['git', '-C', str(caminho), 'status', '--porcelain'],
        capture_output=True, text=True
    )
    if status_res.returncode != 0:
        raise ErroWorktree(f'Não foi possível ler o estado do worktree {caminho}: {status_res.stderr.strip()}')
    if status_res.stdout.strip() and not forcar:
        raise ErroWorktree(
            f'Worktree em {caminho} possui alterações não commitadas. Use --forcar para remover.'
        )

    cmd = ['git', '-C', str(repo_root), 'worktree', 'remove']
    if forcar:
        cmd.append('--force')
    cmd.append(str(caminho))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise ErroWorktree(f'Falha ao remover worktree Git: {res.stderr.strip() or res.stdout.strip()}')

    return {
        'sucesso': True,
        'caminho': str(caminho),
        'etapa': etapa,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--projeto', default=None, help='Nome do projeto (padrão: nome do repositório)')
    parser.add_argument('--raiz', default=None, help='Diretório raiz de trabalho (padrão: ~/.sociedade/trabalho)')
    parser.add_argument('--pasta-base', default=None, help='Pasta base para localização do Git')

    sub = parser.add_subparsers(dest='subcmd', required=True)

    p_criar = sub.add_parser('criar', help='Cria um novo worktree para a etapa')
    p_criar.add_argument('--etapa', required=True, help='Nome ou identificador da etapa')
    p_criar.add_argument('--branch', default=None, help='Nome da branch (padrão: etapa/<etapa>)')
    p_criar.add_argument('--base', default=None, help='Ponto de partida/commit base (padrão: HEAD)')

    sub.add_parser('listar', help='Lista worktrees do projeto')

    p_rem = sub.add_parser('remover', help='Remove o worktree da etapa')
    p_rem.add_argument('--etapa', required=True, help='Nome ou identificador da etapa')
    p_rem.add_argument('--forcar', action='store_true', help='Força remoção mesmo com alterações não commitadas')

    args = parser.parse_args(argv)
    p_base = Path(args.pasta_base) if args.pasta_base else None
    p_raiz = Path(args.raiz) if args.raiz else None

    try:
        if args.subcmd == 'criar':
            res = criar_worktree(
                etapa=args.etapa,
                branch=args.branch,
                base=args.base,
                projeto=args.projeto,
                pasta_base=p_base,
                pasta_raiz=p_raiz
            )
            print(f"Worktree criado com sucesso em: {res['caminho']} (branch: {res['branch']})")
            return 0
        elif args.subcmd == 'listar':
            wts = listar_worktrees(projeto=args.projeto, pasta_base=p_base, pasta_raiz=p_raiz)
            if not wts:
                print("Nenhum worktree encontrado.")
                return 0
            print("Worktrees encontrados:")
            for w in wts:
                padrao_tag = " [padrão]" if w.get('padrao') else ""
                print(f"  - Etapa: {w['etapa']} | Branch: {w['branch']} | Caminho: {w['caminho']}{padrao_tag}")
            return 0
        elif args.subcmd == 'remover':
            res = remover_worktree(
                etapa=args.etapa,
                forcar=args.forcar,
                projeto=args.projeto,
                pasta_base=p_base,
                pasta_raiz=p_raiz
            )
            print(f"Worktree da etapa '{res['etapa']}' removido com sucesso: {res['caminho']}")
            return 0
    except ErroWorktree as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERRO inesperado: {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == '__main__':
    sys.exit(main())
