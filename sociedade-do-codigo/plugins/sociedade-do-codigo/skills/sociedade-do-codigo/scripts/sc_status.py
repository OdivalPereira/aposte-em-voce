#!/usr/bin/env python3
"""Status `portao` e `aceite` de um PR de etapa (Q148, B05). Falha fechada.

A sessão em nuvem não publica status de commit (a integração recebe 403), então as duas
verificações rodam como jobs do GitHub Actions (.github/workflows/status.yml), que só chamam
este script. Cada job fica verde apenas se o script sair com 0.

  portao  lê, no head do PR, sociedade/pareceres/atestado-<ID>.json (ID tirado do ramo etapa/<ID>) e exige:
          atestado APROVADO da mesma etapa; commit do atestado ancestral do head; e, depois dele,
          só commits (sem merge) que tocam apenas sociedade/ (cauda de governança, Q149).
  aceite  lê, no head do PR, sociedade/registro.json e exige que a última decisão da etapa seja
          `aceitar`, com quem decidiu e com o SHA revisado (dados.commit) ancestral do head, e a
          mesma cauda só de sociedade/. Sem decisão, vermelho.

Uso:
  sc_status.py portao --ramo etapa/<ID> --head <sha> [--raiz <repo>]
  sc_status.py aceite --ramo etapa/<ID> --head <sha> [--raiz <repo>]
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sc_registro import carregar_dados_registro, derivar_estado  # noqa: E402

ID_ETAPA = re.compile(r'^[a-z0-9][a-z0-9-]{0,39}$')
SHA = re.compile(r'^[0-9a-fA-F]{7,40}$')
PASTA_GOVERNANCA = 'sociedade/'
REGISTRO = 'sociedade/registro.json'


def atestado_caminho(etapa_id):
    return f'sociedade/pareceres/atestado-{etapa_id}.json'


def etapa_do_ramo(ramo):
    """ID da etapa a partir de `etapa/<ID>` (aceita refs/heads/ na frente); None se o ramo não for de etapa."""
    m = re.fullmatch(r'(?:refs/heads/)?etapa/(.+)', str(ramo or ''))
    return m.group(1) if m and ID_ETAPA.fullmatch(m.group(1)) else None


def _git(raiz, *args):
    r = subprocess.run(['git', '-C', str(raiz), *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr.strip()


def _resolver(raiz, ref):
    if not SHA.match(str(ref or '')):
        return None
    rc, saida, _ = _git(raiz, 'rev-parse', '--verify', f'{ref}^{{commit}}')
    return saida.strip() if rc == 0 else None


def _arquivo_em(raiz, head, caminho):
    rc, saida, _ = _git(raiz, 'show', f'{head}:{caminho}')
    return saida if rc == 0 else None


def verificar_cauda(raiz, sha_revisado, head):
    """(ok, motivo): sha_revisado é ancestral do head e tudo depois dele toca só sociedade/."""
    base, topo = _resolver(raiz, sha_revisado), _resolver(raiz, head)
    if not base:
        return False, f'commit {str(sha_revisado)[:12]} não existe'
    if not topo:
        return False, f'head {str(head)[:12]} inválido'
    if _git(raiz, 'merge-base', '--is-ancestor', base, topo)[0] != 0:
        return False, f'commit {base[:12]} não é ancestral do head {topo[:12]}'
    rc, saida, erro = _git(raiz, 'rev-list', '--parents', f'{base}..{topo}')
    if rc != 0:
        return False, f'git rev-list falhou: {erro[:100]}'
    for linha in saida.splitlines():
        partes = linha.split()
        if len(partes) != 2:
            return False, f'commit {partes[0][:12]} da cauda é merge ou raiz'
        rc, arquivos, erro = _git(raiz, 'diff-tree', '--no-commit-id', '--name-only', '-r', '--no-renames', '-z', partes[1], partes[0])
        if rc != 0:
            return False, f'git diff-tree falhou: {erro[:100]}'
        fora = [a for a in arquivos.split('\0') if a and not a.startswith(PASTA_GOVERNANCA)]
        if fora:
            return False, f'commit {partes[0][:12]} depois de {base[:12]} toca fora de sociedade/: {", ".join(fora[:3])}'
    return True, f'cauda só de sociedade/ ({len(saida.splitlines())} commits)'


def verificar_portao(raiz, ramo, head):
    """Status `portao`: {'ok', 'motivo', 'atestado_sha256', 'commit'}."""
    etapa = etapa_do_ramo(ramo)
    if not etapa:
        return _res(False, f'ramo "{ramo}" não é etapa/<ID> válido')
    caminho = atestado_caminho(etapa)
    bruto = _arquivo_em(raiz, head, caminho)
    if bruto is None:
        return _res(False, f'sem {caminho} no head')
    hash_atestado = hashlib.sha256(bruto.encode('utf-8')).hexdigest()
    try:
        at = json.loads(bruto)
    except ValueError:
        return _res(False, 'atestado não é JSON válido', hash_atestado)
    if not isinstance(at, dict):
        return _res(False, 'atestado malformado', hash_atestado)
    if at.get('status') != 'APROVADO':
        return _res(False, f'atestado com status {at.get("status")}', hash_atestado)
    if at.get('etapa_id') != etapa:
        return _res(False, f'atestado da etapa {at.get("etapa_id")}, esperado {etapa}', hash_atestado)
    if not at.get('total_arquivos_inspecionados'):
        return _res(False, 'atestado sem arquivo inspecionado', hash_atestado)
    ok, motivo = verificar_cauda(raiz, at.get('commit'), head)
    return _res(ok, motivo, hash_atestado, at.get('commit'))


def _res(ok, motivo, hash_atestado=None, commit=None):
    return {'ok': bool(ok), 'motivo': motivo, 'atestado_sha256': hash_atestado, 'commit': commit}


def _registro_em(raiz, head):
    bruto = _arquivo_em(raiz, head, REGISTRO)
    if bruto is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        arq = Path(tmp) / 'registro.json'
        arq.write_text(bruto, encoding='utf-8')
        dados = carregar_dados_registro(arq)
    derivar_estado(dados)  # integridade semântica: levanta se o registro for incoerente
    return dados


def decisao_final(dados, etapa_id):
    """Última decisão registrada da etapa (dict de `decisao_registrada`) ou None."""
    ultima = None
    for ev in dados.get('eventos', []):
        d = ev.get('dados') or {}
        if ev.get('tipo') == 'decisao_registrada' and d.get('etapa_id') == etapa_id:
            ultima = d
    return ultima


def _mesmo_sha(a, b):
    a, b = str(a or '').lower(), str(b or '').lower()
    return len(a) >= 7 and len(b) >= 7 and (a.startswith(b) or b.startswith(a))


def verificar_aceite(raiz, ramo, head, registro=None):
    """Status `aceite`: a última decisão da etapa é `aceitar`, do SHA revisado, e a cauda é só de sociedade/.

    `registro` (dict) é só para teste; no uso real vem de sociedade/registro.json no head."""
    etapa = etapa_do_ramo(ramo)
    if not etapa:
        return _res(False, f'ramo "{ramo}" não é etapa/<ID> válido')
    try:
        dados = registro if registro is not None else _registro_em(raiz, head)
    except Exception as e:  # registro corrompido ou incoerente: vermelho
        return _res(False, f'registro ilegível ou incoerente: {type(e).__name__}: {str(e)[:100]}')
    if dados is None:
        return _res(False, f'sem {REGISTRO} no head')
    dec = decisao_final(dados, etapa)
    if not dec:
        return _res(False, f'sem decisão registrada da etapa {etapa}')
    if dec.get('acao') != 'aceitar':
        return _res(False, f'última decisão da etapa {etapa} é "{dec.get("acao")}", não "aceitar"')
    if not str(dec.get('quem') or '').strip():
        return _res(False, 'decisão sem a pessoa que decidiu')
    sha = dec.get('commit')
    if not sha:
        return _res(False, 'decisão sem o SHA revisado (dados.commit)')
    ok, motivo = verificar_cauda(raiz, sha, head)
    return _res(ok, f'decisão aceitar de {dec["quem"]}; {motivo}' if ok else motivo, None, sha)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('status', choices=('portao', 'aceite'))
    ap.add_argument('--ramo', required=True, help='ramo do PR (etapa/<ID>)')
    ap.add_argument('--head', required=True, help='SHA do head do PR')
    ap.add_argument('--raiz', default='.', help='repositório com o histórico completo')
    a = ap.parse_args(argv)
    try:
        r = (verificar_portao if a.status == 'portao' else verificar_aceite)(a.raiz, a.ramo, a.head)
    except Exception as e:  # falha fechada
        r = _res(False, f'erro inesperado: {type(e).__name__}: {str(e)[:150]}')
    print(f'{a.status}: {"verde" if r["ok"] else "VERMELHO"} — {r["motivo"]}')
    if r['atestado_sha256']:
        print(f'atestado sha256: {r["atestado_sha256"]}')
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
