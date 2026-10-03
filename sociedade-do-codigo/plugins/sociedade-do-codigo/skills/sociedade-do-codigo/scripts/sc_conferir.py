#!/usr/bin/env python3
"""Conferência da ordem verificável (Q119, RM-1b F6).

Lê o bloco ```entregas de uma ordem e marca cada entrega como feita, não feita, não
verificada ou não preenchida, sem executar testes. Uma linha por entrega:

    ID | tipo | argumento [| argumento...]

Tipos:
  commit_existe <ref>
  arquivos_em <base>..<head> | <prefixo> [| <prefixo>...]   todos os arquivos alterados começam por um prefixo
  arquivo_existe <caminho>
  atestado_aprovado <arquivo> | <commit>                     status APROVADO e commit do atestado igual ao informado
  parecer_valido <arquivo>                                   lint do parecer sem erro e com veredito
  hash_confere <arquivo> | <sha256>
  push_feito <ramo>                                          ramo remoto (origin) igual ao local; sem rede: não verificado
  delegacoes antigravity | <conversa> | <mínimo>             chamadas a invoke_subagent no log da conversa
  conversa_nova antigravity | <conversa>                     uma única ordem na conversa

Com --registrar, grava o resultado no registro.json como evento 'conferencia_registrada'.
Código de saída 0 só se todas as entregas estiverem feitas.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sc_registro import localizar_sociedade_canonica  # noqa: E402

FEITO, NAO_FEITO, NAO_VERIFICADO, NAO_PREENCHIDO = 'feito', 'não feito', 'não verificado', 'não preenchido'
BLOCO = re.compile(r'```entregas\s*\n(.*?)```', re.S)
MARCADOR = re.compile(r'<[^<>\n]+>')


def git(raiz, *args):
    r = subprocess.run(['git', '-C', str(raiz), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def ler_entregas(texto):
    m = BLOCO.search(texto)
    if not m:
        raise ValueError('A ordem não tem bloco ```entregas.')
    itens = []
    for linha in m.group(1).splitlines():
        linha = linha.strip()
        if not linha or linha.startswith('#'):
            continue
        partes = [p.strip() for p in linha.split('|')]
        if len(partes) < 2:
            raise ValueError(f'Entrega malformada: "{linha}". Use "ID | tipo | argumentos".')
        itens.append({'id': partes[0], 'tipo': partes[1], 'args': partes[2:]})
    return itens


def _sha256(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def conferir_item(item, raiz):
    tipo, args = item['tipo'], item['args']
    if any(MARCADOR.search(a) for a in args) or not args:
        return NAO_PREENCHIDO, 'argumento com marcador <...> ou vazio'
    caminho = lambda rel: (raiz / rel) if not Path(rel).is_absolute() else Path(rel)  # noqa: E731

    if tipo == 'commit_existe':
        sha = git(raiz, 'rev-parse', '--verify', f'{args[0]}^{{commit}}')
        return (FEITO, sha[:12]) if sha else (NAO_FEITO, f'commit {args[0]} não existe')

    if tipo == 'arquivos_em':
        if '..' not in args[0] or len(args) < 2:
            return NAO_PREENCHIDO, 'use "<base>..<head> | <prefixo>"'
        base, head = args[0].split('..', 1)
        saida = git(raiz, 'diff', '--name-only', '-M', base, head)
        if saida is None:
            return NAO_FEITO, f'intervalo inválido: {args[0]}'
        arquivos = [a for a in saida.splitlines() if a]
        fora = [a for a in arquivos if not any(a.startswith(p) for p in args[1:])]
        if not arquivos:
            return NAO_FEITO, 'nenhum arquivo alterado no intervalo'
        return (FEITO, f'{len(arquivos)} arquivos, todos nos prefixos') if not fora else \
               (NAO_FEITO, f'{len(fora)} fora dos prefixos: {", ".join(fora[:5])}')

    if tipo == 'arquivo_existe':
        return (FEITO, args[0]) if caminho(args[0]).exists() else (NAO_FEITO, f'{args[0]} não existe')

    if tipo == 'atestado_aprovado':
        arq = caminho(args[0])
        if not arq.is_file():
            return NAO_FEITO, f'{args[0]} não existe'
        try:
            at = json.loads(arq.read_text(encoding='utf-8'))
        except ValueError:
            return NAO_FEITO, 'atestado não é JSON válido'
        if at.get('status') != 'APROVADO':
            return NAO_FEITO, f'status {at.get("status")}'
        if len(args) > 1:
            esperado = git(raiz, 'rev-parse', '--verify', f'{args[1]}^{{commit}}') or args[1]
            if not at.get('commit'):
                return NAO_FEITO, 'atestado sem commit (versão anterior à 1.2.0)'
            if not esperado.startswith(at['commit'][:7]) and not at['commit'].startswith(esperado[:7]):
                return NAO_FEITO, f'atestado do commit {at["commit"][:12]}, esperado {esperado[:12]}'
        if not at.get('total_arquivos_inspecionados'):
            return NAO_FEITO, 'atestado aprovado sem nenhum arquivo inspecionado'
        return FEITO, f'APROVADO, {at["total_arquivos_inspecionados"]} arquivos, commit {str(at.get("commit"))[:12]}'

    if tipo == 'parecer_valido':
        arq = caminho(args[0])
        if not arq.is_file():
            return NAO_FEITO, f'{args[0]} não existe'
        lint = Path(__file__).resolve().parents[2] / 'sc-revisao' / 'scripts' / 'lint_parecer.py'
        r = subprocess.run([sys.executable, '-B', str(lint), str(arq)], capture_output=True, text=True)
        veredito = re.search(r'veredito:\s*(aceitar com ressalvas|n[ãa]o aceitar|aceitar)', arq.read_text(encoding='utf-8'), re.I)
        if r.returncode != 0:
            return NAO_FEITO, 'lint do parecer com erro: ' + (r.stdout.strip().splitlines() or [''])[0][:100]
        return (FEITO, f'veredito: {veredito.group(1)}') if veredito else (NAO_FEITO, 'sem veredito')

    if tipo == 'hash_confere':
        arq = caminho(args[0])
        if not arq.is_file() or len(args) < 2:
            return NAO_FEITO, f'{args[0]} não existe ou hash ausente'
        real = _sha256(arq)
        return (FEITO, real[:12]) if real == args[1].lower() else (NAO_FEITO, f'hash real {real[:12]}')

    if tipo == 'push_feito':
        local = git(raiz, 'rev-parse', '--verify', f'refs/heads/{args[0]}')
        if not local:
            return NAO_FEITO, f'ramo local {args[0]} não existe'
        remoto = git(raiz, 'ls-remote', 'origin', f'refs/heads/{args[0]}')
        if remoto is None:
            return NAO_VERIFICADO, 'sem acesso ao remoto'
        sha_remoto = remoto.split()[0] if remoto else ''
        return (FEITO, local[:12]) if sha_remoto == local else (NAO_FEITO, f'remoto {sha_remoto[:12] or "ausente"}, local {local[:12]}')

    if tipo in ('delegacoes', 'conversa_nova'):
        from sc_sessao import medir, ErroSessao
        if args[0] != 'antigravity' or len(args) < 2:
            return NAO_PREENCHIDO, 'use "antigravity | <conversa>"'
        try:
            m = medir('antigravity', conversa=args[1])
        except ErroSessao as e:
            return NAO_VERIFICADO, str(e)
        if tipo == 'conversa_nova':
            return (FEITO, '1 ordem na conversa') if m['conversa_nova'] else \
                   (NAO_FEITO, f'{m["ordens_na_conversa"]} ordens na mesma conversa')
        minimo = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
        return (FEITO, f'{m["delegacoes_total"]} delegações') if m['delegacoes_total'] >= minimo else \
               (NAO_FEITO, f'{m["delegacoes_total"]} delegações, mínimo {minimo}')

    return NAO_PREENCHIDO, f'tipo desconhecido: {tipo}'


def conferir(ordem, raiz=None):
    ordem = Path(ordem)
    raiz = Path(raiz) if raiz else Path(git(ordem.parent, 'rev-parse', '--show-toplevel') or ordem.parent)
    itens = ler_entregas(ordem.read_text(encoding='utf-8'))
    resultado = []
    for it in itens:
        estado, detalhe = conferir_item(it, raiz)
        resultado.append({'id': it['id'], 'tipo': it['tipo'], 'estado': estado, 'detalhe': detalhe})
    return {
        'ordem': str(ordem),
        'etapa': ordem.stem,
        'conferido_em': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'commit': git(raiz, 'rev-parse', 'HEAD'),
        'itens': resultado,
        'feitos': sum(1 for r in resultado if r['estado'] == FEITO),
        'total': len(resultado),
    }


def registrar(rel, pasta_sociedade=None, autor='conferência automática'):
    from sc_registro import Registro
    reg = Registro(pasta_sociedade or localizar_sociedade_canonica())

    def gerador(_dados):
        return [{'tipo': 'conferencia_registrada', 'dados': {
            'etapa': rel['etapa'], 'ordem': rel['ordem'], 'commit': rel['commit'],
            'feitos': rel['feitos'], 'total': rel['total'],
            'itens': [{k: i[k] for k in ('id', 'tipo', 'estado', 'detalhe')} for i in rel['itens']],
        }}]
    reg.aplicar_mutacao(gerador, autor=autor, aplicar=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ordem', required=True, help='arquivo da ordem com o bloco ```entregas')
    ap.add_argument('--raiz', help='raiz do repositório (padrão: a da ordem)')
    ap.add_argument('--registrar', action='store_true', help='grava o resultado no registro.json')
    ap.add_argument('--pasta-sociedade', help='pasta do registro (padrão: sociedade/ canônica)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        rel = conferir(a.ordem, a.raiz)
    except (OSError, ValueError) as e:
        print(f'erro: {e}', file=sys.stderr)
        return 2
    if a.registrar:
        registrar(rel, Path(a.pasta_sociedade) if a.pasta_sociedade else None)
    if a.json:
        print(json.dumps(rel, ensure_ascii=False, indent=2))
    else:
        print(f'Conferência de {rel["ordem"]}: {rel["feitos"]} de {rel["total"]} feitas')
        for r in rel['itens']:
            print(f'  [{r["estado"]:^14}] {r["id"]:<5} {r["tipo"]:<18} {r["detalhe"]}')
    return 0 if rel['feitos'] == rel['total'] else 1


if __name__ == '__main__':
    sys.exit(main())
