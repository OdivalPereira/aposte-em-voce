#!/usr/bin/env python3
"""Status `portao` e `aceite` de um PR de etapa (Q148, B05). Falha fechada.

A sessão em nuvem não publica status de commit (a integração recebe 403), então as duas
verificações rodam como jobs do GitHub Actions (.github/workflows/status.yml), que só chamam
este script. Cada job fica verde apenas se o script sair com 0.

  portao  lê, no head do PR, sociedade/pareceres/atestado-<ID>.json (ID tirado do ramo etapa/<ID>) e exige:
          atestado APROVADO da mesma etapa, na forma do portão por área (1.3.0: `portao` do `sc.py entregar`, com
          todas as áreas tocadas rodadas e ok, e o SHA-256 do perfil igual ao de sociedade/perfil.md no head);
          commit do atestado ancestral do head; e, depois dele, só commits (sem merge) que tocam apenas
          sociedade/ (cauda de governança, Q149).
  aceite  lê, no head do PR, sociedade/registro.json e exige que a última decisão da etapa seja
          `aceitar`, com quem decidiu e com o SHA revisado (dados.commit) ancestral do head, e a
          mesma cauda só de sociedade/. Sem decisão, vermelho. Confere ainda (B15): o atestado do head é o do
          `sc.py entregar` (forma 1.3.0 e `atestado_hash` refeito) e é o que a decisão registrou (`atestado_hash`);
          e, se o PR altera `.github/workflows/`, a ordem da abertura (hash conferido) lista o caminho no escreva-só.

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
PERFIL = 'sociedade/perfil.md'


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


def sha256_do_perfil_em(raiz, head):
    """SHA-256 dos bytes de sociedade/perfil.md no commit `head`; None se o perfil não existir lá."""
    r = subprocess.run(['git', '-C', str(raiz), 'show', f'{head}:{PERFIL}'], capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None


def forma_do_atestado(at, sha256_perfil_atual):
    """(ok, motivo): o atestado é o do `sc.py entregar` (portão por área, versão 1.3.0), completo e do perfil de hoje.

    Exige `portao.modo == 'por_area'`, `portao.commit` igual ao `commit` do atestado, áreas rodadas não vazias e todas
    ok, `areas_tocadas` todas rodadas e ok (`cobertura_completa`: `--area` sozinho não basta) e `portao.perfil_sha256`
    igual ao SHA-256 do perfil que está sendo julgado (`sha256_perfil_atual`). Um atestado avulso (`sc_pre_devolucao.py`
    com `--comando-teste`) não passa."""
    portao = at.get('portao') if isinstance(at, dict) else None
    if not isinstance(portao, dict) or portao.get('modo') != 'por_area':
        return False, 'atestado sem o portão por área (forma 1.3.0): só vale o gerado por `sc.py entregar`'
    if not at.get('commit') or portao.get('commit') != at.get('commit'):
        return False, 'o commit do portão não é o commit do atestado'
    areas = portao.get('areas')
    if not isinstance(areas, list) or not areas or not all(isinstance(a, dict) for a in areas):
        return False, 'atestado sem nenhuma área rodada'
    ruins = [str(a.get('area')) for a in areas if a.get('ok') is not True]
    if ruins:
        return False, f'área(s) que não passaram no portão: {", ".join(ruins)}'
    tocadas = portao.get('areas_tocadas')
    if not isinstance(tocadas, list) or not tocadas:
        return False, 'atestado sem as áreas que base..HEAD toca'
    rodadas = {a.get('area') for a in areas}
    faltam = [str(t) for t in tocadas if t not in rodadas]
    if faltam or portao.get('cobertura_completa') is not True:
        return False, ('o atestado não cobre todas as áreas tocadas' + (f' (faltam: {", ".join(faltam)})' if faltam else '')
                       + ': rode `sc.py entregar` sem --area')
    sha = portao.get('perfil_sha256')
    if not sha or not sha256_perfil_atual:
        return False, 'sem como conferir o perfil: o atestado ou o commit julgado não tem o SHA-256 do perfil'
    if sha != sha256_perfil_atual:
        return False, 'o perfil mudou depois do portão (SHA-256 do atestado diferente do de sociedade/perfil.md)'
    return True, 'portão por área completo e do perfil atual'


CAMPOS_DO_HASH = ('commit', 'base', 'papel', 'etapa_id', 'fatia_id', 'status', 'verificacoes', 'hashes_artefatos', 'portao', 'erros')


def hash_do_atestado(at):
    """SHA-256 que o `sc_pre_devolucao` grava em `atestado_hash`: o JSON canônico dos campos de `CAMPOS_DO_HASH`."""
    return hashlib.sha256(json.dumps({k: at.get(k) for k in CAMPOS_DO_HASH}, sort_keys=True).encode('utf-8')).hexdigest()


def hash_do_atestado_confere(at):
    """(ok, motivo) B15: o atestado traz o `atestado_hash` e ele é o dos campos que o `entregar` gravou.

    O hash não cobre `total_arquivos_inspecionados`; por isso ele tem de ser o nº de arquivos com hash em
    `hashes_artefatos`, e `arquivos_inspecionados` a lista deles (o `entregar` grava os três juntos)."""
    if not isinstance(at, dict) or not at.get('atestado_hash'):
        return False, 'atestado sem atestado_hash: só vale o gerado por `sc.py entregar`'
    if at['atestado_hash'] != hash_do_atestado(at):
        return False, 'atestado adulterado: o atestado_hash não é o dos campos do atestado'
    hashes = at.get('hashes_artefatos')
    if not isinstance(hashes, dict) or at.get('arquivos_inspecionados') != sorted(hashes) \
            or at.get('total_arquivos_inspecionados') != len(hashes):
        return False, 'atestado adulterado: o total de arquivos inspecionados não é o dos hashes gravados'
    return True, 'atestado_hash confere'


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
    ok, motivo = forma_do_atestado(at, sha256_do_perfil_em(raiz, head))
    if not ok:
        return _res(False, motivo, hash_atestado, at.get('commit'))
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
    if ok and registro is None:  # `registro=` é só para teste; no uso real as provas saem do head do PR
        ok, motivo = _provas_no_head(raiz, head, etapa, dec, dados)
    return _res(ok, f'decisão aceitar de {dec["quem"]}; {motivo}' if ok else motivo, None, sha)


def _provas_no_head(raiz, head, etapa, dec, dados):
    """(ok, motivo) B15: atestado oficial e íntegro no head, o mesmo da decisão; workflow só se a ordem o lista."""
    caminho = atestado_caminho(etapa)
    bruto = _arquivo_em(raiz, head, caminho)
    if bruto is None:
        return False, f'sem {caminho} no head: decisão sem o atestado do `sc.py entregar`'
    try:
        at = json.loads(bruto)
    except ValueError:
        return False, 'atestado não é JSON válido'
    ok, motivo = hash_do_atestado_confere(at)
    if not ok:
        return False, motivo
    ok, motivo = forma_do_atestado(at, sha256_do_perfil_em(raiz, head))
    if not ok:
        return False, motivo
    if at.get('status') != 'APROVADO' or at.get('etapa_id') != etapa or not _mesmo_sha(at.get('commit'), dec.get('commit')):
        return False, 'o atestado do head não é APROVADO, desta etapa e do SHA que a decisão revisou'
    if dec.get('atestado_hash') != at['atestado_hash']:
        return False, 'o atestado do head não é o que a decisão registrou (atestado_hash): alterado depois da decisão'
    return verificar_workflows(raiz, head, etapa, dados)


def _ordem_da_abertura(dados, etapa):
    for ev in dados.get('eventos', []):
        d = ev.get('dados') or {}
        if ev.get('tipo') == 'etapa_aberta' and d.get('etapa_id') == etapa:
            return d.get('base_efetiva'), str(d.get('autorizacao_ref') or '')
    return None, ''


def _escreva_so(texto):
    """Caminhos entre crases das linhas de escreva-só da ordem, sem o que vem depois de "Proibido"."""
    achados = []
    for linha in texto.splitlines():
        m = re.search(r'escreva[\s-]*s[óo]\b', linha, re.I)
        if m:
            resto = re.split(r'proibid', linha[m.end():], maxsplit=1, flags=re.I)[0]
            achados += re.findall(r'`([^`]+)`', resto)
    return achados


def verificar_workflows(raiz, head, etapa, dados):
    """(ok, motivo) B15 (c): o PR (base da abertura..head) só altera `.github/workflows/` se a ordem o lista no
    escreva-só; a ordem lida no head tem de ser a da abertura (`autorizacao_ref` = ordem_sha256:<16 hex>)."""
    base, ref = _ordem_da_abertura(dados, etapa)
    base = _resolver(raiz, base)
    if not base:
        return False, 'a base da abertura da etapa não resolve a um commit: não dá para conferir o que o PR altera'
    rc, saida, erro = _git(raiz, '-c', 'core.quotepath=off', 'diff', '--name-only', '-z', '--no-renames', base, head)
    if rc != 0:
        return False, f'git diff falhou: {erro[:100]}'
    tocados = [c for c in saida.split('\0') if c.startswith('.github/workflows/')]
    if not tocados:
        return True, 'o PR não altera .github/workflows/'
    ordem = _arquivo_em(raiz, head, f'sociedade/ordens/{etapa}.md')
    m = re.fullmatch(r'ordem_sha256:([0-9a-f]{16})', ref)
    if ordem is None or not m:
        return False, f'o PR altera {tocados[0]} e a ordem da etapa não está no head com o hash da abertura'
    if hashlib.sha256(ordem.encode('utf-8')).hexdigest()[:16] != m.group(1):
        return False, f'o PR altera {tocados[0]} e a ordem foi editada depois da abertura (hash diferente)'
    listados = [t.strip() for t in _escreva_so(ordem)]
    fora = [c for c in tocados if not any(c == t or (t.endswith('/') and c.startswith(t)) for t in listados)]
    if fora:
        return False, f'o PR altera {", ".join(fora[:3])} sem que a ordem o liste no escreva-só (.github/workflows/)'
    return True, 'workflows alterados estão no escreva-só da ordem'


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
