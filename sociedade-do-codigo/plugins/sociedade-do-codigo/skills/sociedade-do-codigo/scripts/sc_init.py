#!/usr/bin/env python3
"""Inicialização guiada e onboarding determinístico de novos projetos na Sociedade do Código.

Cria o perfil do projeto (perfil.md), o bloco no AGENTS.md, e a pasta sociedade/ com
registro.json virgem e historico.md inicial, validando todos os artefatos com zero
dependências externas.

Uso:
  python3 sc_init.py --nome "Meu Projeto" --missao "Propósito do projeto" --aplicar
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def obter_commit_git_head(pasta_projeto):
    """Captura commit Git inicial se o projeto for um repositório git."""
    try:
        p = Path(pasta_projeto).resolve()
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

# Importa módulos auxiliares do núcleo
try:
    from validar_perfil import validar as validar_perfil_func
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from validar_perfil import validar as validar_perfil_func
    except Exception:
        validar_perfil_func = None

try:
    from sc_sync_agents_md import sincronizar as sincronizar_agents_md
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from sc_sync_agents_md import sincronizar as sincronizar_agents_md
    except Exception:
        sincronizar_agents_md = None

try:
    from sc_registro import Registro
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from sc_registro import Registro
    except Exception:
        Registro = None


def gerar_conteudo_perfil(nome, missao, autoridade, stack, comando_build, comando_teste, comando_lint, com_jules):
    """Perfil a partir do modelo único (assets/perfil-modelo.md), com os dados do projeto preenchidos."""
    modelo = (Path(__file__).resolve().parent.parent / 'assets' / 'perfil-modelo.md').read_text(encoding='utf-8')
    texto = modelo.replace('# Perfil de <Projeto>', f'# Perfil de {nome}')
    texto = texto.replace(' Apague as linhas em itálico ao preencher.', '')
    texto = re.sub(r'## Missão\n\*[^\n]*\*', f'## Missão\n{missao}', texto)
    texto = texto.replace('<pessoa>', autoridade)
    texto = re.sub(r'## Regras de domínio\n\*[^\n]*\*', f'## Regras de domínio\nStack: {stack}.', texto)
    texto = texto.replace('- Build: `<comando>`', f'- Build: `{comando_build or "nenhum"}`')
    texto = texto.replace('- Testes: `<comando>`', f'- Testes: `{comando_teste or "python3 -m unittest discover tests"}`')
    texto = texto.replace('- Lint e tipos: `<comando>`', f'- Lint e tipos: `{comando_lint or "nenhum"}`')
    if not com_jules:
        texto = texto.replace('| Executor júnior em nuvem | Jules | <plataforma> | <fornecedor> | <modelo> | <esforço> | reserva |',
                              '| Executor júnior em nuvem | Jules | não usado | — | — | — | espera |')
    # Sem marcadores residuais: campos neutros. Fornecedor "desconhecido" faz R2 e o parecer de
    # nível A recusarem até o perfil ser preenchido (A2-P01): falha fechada, de propósito.
    from datetime import date
    neutros = {
        '<nome do papel e ferramenta>': 'Círdan (ver tabela abaixo)', '<plataforma>': 'a definir',
        '<fornecedor>': 'desconhecido', '<modelo>': 'a definir', '<esforço>': 'padrão',
        '<data>': date.today().isoformat(), '<nomes>': 'Celebrimbor, Radagast, Faramir, Bilbo',
        '<papéis ativos no projeto>': 'Círdan, Barbárvore, Gandalf, Aragorn, Elrond, Galadriel, Legolas',
        '<papéis em reserva, ex.: Jules>': 'Jules', '<papéis em espera, ex.: executores locais>': 'executores locais',
        '<resultado de `inventario_local.py`>': 'a definir (rode inventario_local.py)',
        '<tag, ou "nenhum">': 'nenhum', '<threads e memória>': 'padrão', '<3 por padrão>': '3',
        '<50 linhas ou 2.000 tokens, por padrão>': '50 linhas', '`<comando>`': '`nenhum`',
        '`<pasta>`': '`sociedade/saida`', '`<pasta autorizada ou "não">`': 'não',
    }
    for marcador, valor in neutros.items():
        texto = texto.replace(marcador, valor)
    return re.sub(r'<[^<>\n]{1,60}>', 'a definir', texto)


def slugificar(nome):
    s = re.sub(r'[^a-zA-Z0-9_\-]+', '-', nome.lower()).strip('-')
    return s if s else 'projeto'


class DummyArgs:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def inicializar_projeto(destino='.', nome=None, missao=None, autoridade='o usuário', stack='Python 3.12, stdlib',
                        comando_build='nenhum', comando_teste='python3 -m unittest discover tests',
                        comando_lint='nenhum', com_jules=False, aplicar=False, forcar=False):
    p_raiz = Path(destino).resolve()
    nome_proj = nome or p_raiz.name or 'Novo Projeto'
    missao_proj = missao or 'Desenvolvimento de software de alta confiabilidade com a Sociedade do Código.'
    autoridade_proj = autoridade or 'o usuário'
    slug_proj = slugificar(nome_proj)

    relatorio = []
    relatorio.append(f'=== Inicializando Projeto na Sociedade do Código ===')
    relatorio.append(f'Destino: {p_raiz}')
    relatorio.append(f'Nome: {nome_proj} ({slug_proj})')
    relatorio.append(f'Modo: {"GRAVAÇÃO (--aplicar)" if aplicar else "SIMULAÇÃO (dry-run)"}')
    relatorio.append('')

    # 1. Gerar e validar perfil.md
    pasta_docs_soc = p_raiz / 'sociedade'  # Q31: pasta única da Sociedade no projeto
    perfil_path = pasta_docs_soc / 'perfil.md'
    conteudo_perfil = gerar_conteudo_perfil(
        nome=nome_proj,
        missao=missao_proj,
        autoridade=autoridade_proj,
        stack=stack,
        comando_build=comando_build,
        comando_teste=comando_teste,
        comando_lint=comando_lint,
        com_jules=com_jules,
    )

    # Validação do perfil em memória antes de tocar o disco
    if validar_perfil_func is not None:
        import tempfile
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.md', delete=False) as tf:
            tf.write(conteudo_perfil)
            tf_nome = tf.name
        try:
            faltam, avisos = validar_perfil_func(tf_nome)
        finally:
            if os.path.exists(tf_nome):
                os.unlink(tf_nome)

        if faltam:
            raise SystemExit(f'erro na validação do perfil: campos obrigatórios ausentes: {", ".join(faltam)}')
        relatorio.append(f'[VALIDADO] Perfil aprovado por validar_perfil.py (campos mínimos e recomendados íntegros).')

    if perfil_path.is_file() and not forcar:
        relatorio.append(f'[IGNORADO] {perfil_path.relative_to(p_raiz)} já existe (use --forcar para sobrescrever).')
    else:
        if aplicar:
            pasta_docs_soc.mkdir(parents=True, exist_ok=True)
            perfil_path.write_text(conteudo_perfil, encoding='utf-8')
            relatorio.append(f'[OK] {perfil_path.relative_to(p_raiz)} gerado.')
        else:
            relatorio.append(f'[SIMULAÇÃO] {perfil_path.relative_to(p_raiz)} seria gerado.')

    # 2. Sincronizar bloco no AGENTS.md
    if sincronizar_agents_md is not None:
        args_sync = DummyArgs(
            projeto=str(p_raiz),
            perfil='sociedade/perfil.md',
            pasta='sociedade',
            jules=com_jules,
            criar=True,
            nucleo=None,
            posicao='fim',
            verificar=False,
            aplicar=aplicar,
            forcar=forcar,
        )
        try:
            sincronizar_agents_md(args_sync)
            prefixo = '[OK]' if aplicar else '[SIMULAÇÃO]'
            verbo = 'sincronizado com bloco oficial da Sociedade.' if aplicar else 'seria sincronizado com bloco oficial da Sociedade.'
            relatorio.append(f'{prefixo} AGENTS.md {verbo}')
        except SystemExit as e:
            relatorio.append(f'[AVISO] Sincronização de AGENTS.md finalizou com código {e.code}.')
        except Exception as e:
            relatorio.append(f'[ERRO] Falha ao sincronizar AGENTS.md: {e}')

    # 3. Inicializar pasta sociedade/ com registro.json
    pasta_soc = p_raiz / 'sociedade'
    p_reg = pasta_soc / 'registro.json'
    commit_inicial = obter_commit_git_head(p_raiz)
    if p_reg.is_file() and not forcar:
        relatorio.append(f'[IGNORADO] {p_reg.relative_to(p_raiz)} já existe.')
    else:
        if Registro is not None:
            Registro.inicializar(pasta_soc, projeto_id=slug_proj, caminho_canonico=str(p_raiz), aplicar=aplicar, versao_inicial=commit_inicial)
            msg_versao = f' (versão git: {commit_inicial[:7]})' if commit_inicial else ''
            prefixo = '[OK]' if aplicar else '[SIMULAÇÃO]'
            verbo = 'inicializado com sucesso' if aplicar else 'seria inicializado'
            relatorio.append(f'{prefixo} sociedade/registro.json {verbo} (revisão 1{msg_versao}).')
        else:
            relatorio.append(f'[AVISO] sc_registro indisponível para inicializar registro.json.')

    # 4. Inicializar sociedade/historico.md
    p_hist = pasta_soc / 'historico.md'
    if p_hist.is_file() and not forcar:
        relatorio.append(f'[IGNORADO] {p_hist.relative_to(p_raiz)} já existe.')
    else:
        agora_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        conteudo_hist = f"# Histórico — {nome_proj}\n\n## {agora_str} · Gandalf · adoção da Sociedade do Código\nAdoção inicial da Sociedade do Código v2.0.0 via sc_init.\n"
        if aplicar:
            pasta_soc.mkdir(parents=True, exist_ok=True)
            p_hist.write_text(conteudo_hist, encoding='utf-8')
            relatorio.append(f'[OK] sociedade/historico.md inicializado com marco de adoção.')
        else:
            relatorio.append(f'[SIMULAÇÃO] sociedade/historico.md seria inicializado com marco de adoção.')

    relatorio.append('')
    relatorio.append('Próximos passos recomendados:')
    relatorio.append(f'  1. Preencha a tabela "Papel × ferramenta" de sociedade/perfil.md.')
    relatorio.append(f'  2. Crie a primeira ordem: python3 <pasta-da-skill>/scripts/sc.py ordem --etapa E1')
    relatorio.append(f'  3. Veja o estado: python3 <pasta-da-skill>/scripts/sc.py estado')

    return '\n'.join(relatorio)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--destino', '--projeto', dest='destino', default='.',
                   help='Diretório raiz do projeto a inicializar (padrão: atual)')
    p.add_argument('--nome', help='Nome amigável do projeto')
    p.add_argument('--missao', help='Missão do projeto em uma ou duas frases')
    p.add_argument('--autoridade', default='o usuário', help='Pessoa que decide escopo e publicação (padrão: o usuário)')
    p.add_argument('--stack', default='Python 3.12, stdlib', help='Descrição da stack técnica do projeto')
    p.add_argument('--comando-build', default='nenhum', help='Comando de compilação/build')
    p.add_argument('--comando-teste', default='python3 -m unittest discover tests', help='Comando de execução de testes')
    p.add_argument('--comando-lint', default='nenhum', help='Comando de checagem e lint')
    p.add_argument('--com-jules', action='store_true', help='Configura suporte ao executor júnior em nuvem Jules')
    p.add_argument('--aplicar', action='store_true', help='Grava as alterações em disco (sem esta flag, apenas simula)')
    p.add_argument('--forcar', action='store_true', help='Sobrescreve arquivos existentes se já presentes')

    args = p.parse_args(argv)

    # Modo interativo se executado em TTY interativo e sem argumentos de nome/missão
    if sys.stdin.isatty() and not args.nome and not args.missao:
        print('=== Sociedade do Código v2.0.0 — Inicializador de Projeto ===\n')
        try:
            nome_padrao = Path(args.destino).resolve().name
            args.nome = input(f'Nome do projeto [{nome_padrao}]: ').strip() or nome_padrao
            args.missao = input('Missão do projeto: ').strip() or 'Desenvolvimento de software confiável.'
            resp_aut = input(f'Autoridade técnica [{args.autoridade}]: ').strip()
            if resp_aut:
                args.autoridade = resp_aut
            resp_stack = input(f'Stack técnica [{args.stack}]: ').strip()
            if resp_stack:
                args.stack = resp_stack
            resp_teste = input(f'Comando de teste [{args.comando_teste}]: ').strip()
            if resp_teste:
                args.comando_teste = resp_teste
            resp_jules = input('Usará o executor em nuvem Jules? (s/N): ').strip().lower()
            args.com_jules = resp_jules in ('s', 'sim', 'y', 'yes')
            resp_aplicar = input('Gravar arquivos em disco agora? (S/n): ').strip().lower()
            if resp_aplicar not in ('n', 'nao', 'não', 'no'):
                args.aplicar = True
        except (KeyboardInterrupt, EOFError):
            print('\nInicialização cancelada pelo usuário.')
            return 1

    saida = inicializar_projeto(
        destino=args.destino,
        nome=args.nome,
        missao=args.missao,
        autoridade=args.autoridade,
        stack=args.stack,
        comando_build=args.comando_build,
        comando_teste=args.comando_teste,
        comando_lint=args.comando_lint,
        com_jules=args.com_jules,
        aplicar=args.aplicar,
        forcar=args.forcar,
    )
    print(saida)
    return 0


if __name__ == '__main__':
    sys.exit(main())
