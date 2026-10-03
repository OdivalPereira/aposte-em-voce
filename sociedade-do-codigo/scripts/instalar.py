#!/usr/bin/env python3
"""Instalador de reserva: copia as skills (e, se pedido, os agentes) para as pastas de cada ferramenta.

Use quando o plugin não puder ser instalado pelo mecanismo da ferramenta. Por padrão só SIMULA: mostra o que
faria. Com --aplicar, copia. Nunca toca em MCP, credenciais nem arquivos de configuração das ferramentas.

Destinos (relativos à pasta pessoal do usuário):
  claude              .claude/skills/<skill>            agentes: .claude/agents/<arquivo>
  codex               .agents/skills/<skill>
  antigravity         .gemini/config/skills/<skill>     agentes: .gemini/config/agents/<arquivo>
  antigravity-cli     .gemini/antigravity-cli/skills/<skill>

Segurança: só grava dentro dos destinos acima e em .sociedade-do-codigo/ (registro e cópias de segurança);
recusa caminhos que passem por link simbólico; não sobrescreve o que você alterou sem --substituir; toda
substituição ou remoção guarda antes uma cópia em .sociedade-do-codigo/backup/<data-hora>/.

Códigos de saída: 0 sucesso; 1 houve conflito ignorado ou erro; 2 uso incorreto. Sem dependências externas.
"""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REGISTRO = Path('.sociedade-do-codigo') / 'instalado.json'
BACKUPS = Path('.sociedade-do-codigo') / 'backup'
DESTINOS = {
    'claude': {'skills': '.claude/skills', 'agentes': '.claude/agents', 'adaptador': 'claude'},
    'codex': {'skills': '.agents/skills', 'agentes': None, 'adaptador': 'codex'},
    'antigravity': {'skills': '.gemini/config/skills', 'agentes': '.gemini/config/agents', 'adaptador': 'antigravity'},
    'antigravity-cli': {'skills': '.gemini/antigravity-cli/skills', 'agentes': None, 'adaptador': 'antigravity'},
}


def ignorar(p):
    return '__pycache__' in p.parts or p.suffix == '.pyc'


def arquivos(p):
    if p.is_file():
        return [p]
    return sorted(f for f in p.rglob('*') if f.is_file() and not ignorar(f))


def hash_item(p):
    h = hashlib.sha256()
    base = p.parent if p.is_file() else p
    for f in arquivos(p):
        h.update(f.relative_to(base).as_posix().encode('utf-8'))
        h.update(b'\0')
        h.update(f.read_bytes())
        h.update(b'\0')
    return h.hexdigest()


def versao_pacote():
    return (RAIZ / 'VERSION').read_text(encoding='utf-8').strip()


def descobrir_itens(alvos, com_agentes, so_skills=None):
    """Lista (rotulo, origem, destino_relativo) de tudo que será instalado."""
    itens = []
    pasta_skills = next((RAIZ / 'plugins').glob('*/skills'), None)
    if pasta_skills is None:
        raise SystemExit('erro: pasta plugins/*/skills não encontrada no pacote')
    skills = sorted(p for p in pasta_skills.iterdir() if (p / 'SKILL.md').is_file())
    if so_skills:
        desconhecidas = set(so_skills) - {s.name for s in skills}
        if desconhecidas:
            raise SystemExit(f'erro: skill(s) desconhecida(s): {", ".join(sorted(desconhecidas))}')
        skills = [s for s in skills if s.name in so_skills]
    for alvo in alvos:
        cfg = DESTINOS[alvo]
        for s in skills:
            itens.append((f'{alvo}: skill {s.name}', s, Path(cfg['skills']) / s.name))
        if com_agentes:
            if cfg['agentes'] is None:
                itens.append((f'{alvo}: agentes', None, None))
                continue
            for a in sorted((RAIZ / 'adapters' / cfg['adaptador'] / 'agents').glob('*.md')):
                itens.append((f'{alvo}: agente {a.stem}', a, Path(cfg['agentes']) / a.name))
    return itens


def caminho_seguro(home, rel):
    """Recusa destino fora da pasta pessoal ou que passe por link simbólico."""
    destino = home / rel
    try:
        destino.resolve(strict=False).relative_to(home.resolve())
    except ValueError:
        return False, 'fora da pasta pessoal'
    atual = home
    for parte in Path(rel).parts:
        atual = atual / parte
        if atual.is_symlink():
            return False, f'passa por link simbólico: {atual}'
    return True, ''


def ler_registro(home):
    arq = home / REGISTRO
    if arq.is_file():
        try:
            return json.loads(arq.read_text(encoding='utf-8')).get('itens', {})
        except ValueError:
            raise SystemExit(f'erro: registro corrompido em {arq}; corrija ou apague-o e rode de novo')
    return {}


def gravar_registro(home, itens):
    arq = home / REGISTRO
    arq.parent.mkdir(parents=True, exist_ok=True)
    tmp = arq.with_suffix('.tmp')
    tmp.write_text(json.dumps({'versao_registro': 1, 'itens': itens}, ensure_ascii=False, indent=2) + '\n',
                   encoding='utf-8')
    tmp.replace(arq)


def planejar(home, itens, registro, substituir, remover):
    """Cada ação: dict(tipo, rotulo, origem, destino, motivo)."""
    plano = []
    for rotulo, origem, rel in itens:
        if rel is None:
            plano.append({'tipo': 'nota', 'rotulo': rotulo, 'motivo': 'esta ferramenta não tem pasta de agentes neste pacote'})
            continue
        ok, porque = caminho_seguro(home, rel)
        chave = rel.as_posix()
        if not ok:
            plano.append({'tipo': 'erro', 'rotulo': rotulo, 'destino': rel, 'motivo': porque})
            continue
        destino = home / rel
        existe = destino.exists()
        atual = hash_item(destino) if existe else None
        rastreado = registro.get(chave, {}).get('hash')
        nosso_intacto = existe and rastreado is not None and atual == rastreado
        if remover:
            if not existe:
                plano.append({'tipo': 'ausente', 'rotulo': rotulo, 'destino': rel, 'motivo': 'nada a remover'})
            elif nosso_intacto or substituir:
                plano.append({'tipo': 'remover', 'rotulo': rotulo, 'destino': rel})
            else:
                motivo = 'foi alterado desde a instalação' if rastreado else 'não foi instalado por este script'
                plano.append({'tipo': 'conflito', 'rotulo': rotulo, 'destino': rel, 'motivo': f'{motivo}; use --substituir, que guarda uma cópia de segurança antes'})
            continue
        novo = hash_item(origem)
        if not existe:
            plano.append({'tipo': 'criar', 'rotulo': rotulo, 'origem': origem, 'destino': rel, 'hash': novo})
        elif atual == novo:
            plano.append({'tipo': 'igual', 'rotulo': rotulo, 'destino': rel, 'hash': novo})
        elif nosso_intacto or substituir:
            plano.append({'tipo': 'atualizar', 'rotulo': rotulo, 'origem': origem, 'destino': rel, 'hash': novo})
        else:
            motivo = 'foi alterado desde a instalação' if rastreado else 'já existe e não foi instalado por este script'
            plano.append({'tipo': 'conflito', 'rotulo': rotulo, 'destino': rel, 'motivo': f'{motivo}; use --substituir, que guarda uma cópia de segurança antes'})
    return plano


def guardar_backup(home, rel, carimbo):
    origem = home / rel
    destino = home / BACKUPS / carimbo / rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    if origem.is_dir():
        shutil.copytree(origem, destino, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    else:
        shutil.copy2(origem, destino)


def copiar(origem, destino):
    """Copia por uma pasta temporária vizinha e troca de uma vez; não deixa a temporária para trás."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + '.sc-tmp')
    limpar(tmp)
    try:
        if origem.is_dir():
            shutil.copytree(origem, tmp, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(origem, tmp)
        limpar(destino)
        tmp.rename(destino)
    finally:
        limpar(tmp)


def limpar(caminho):
    if caminho.is_dir() and not caminho.is_symlink():
        shutil.rmtree(caminho)
    elif caminho.exists() or caminho.is_symlink():
        caminho.unlink()


def executar(home, plano, registro, versao):
    carimbo = datetime.now().strftime('%Y%m%d-%H%M%S')
    feito_backup = False
    for a in plano:
        t = a['tipo']
        if t in ('criar', 'atualizar'):
            destino = home / a['destino']
            if t == 'atualizar':
                guardar_backup(home, a['destino'], carimbo)
                feito_backup = True
            copiar(a['origem'], destino)
            registro[a['destino'].as_posix()] = {
                'hash': a['hash'], 'versao': versao, 'instalado_em': datetime.now().strftime('%d/%m/%Y %H:%M'),
            }
        elif t == 'remover':
            destino = home / a['destino']
            guardar_backup(home, a['destino'], carimbo)
            feito_backup = True
            limpar(destino)
            registro.pop(a['destino'].as_posix(), None)
        elif t == 'igual':
            registro.setdefault(a['destino'].as_posix(), {
                'hash': a['hash'], 'versao': versao, 'instalado_em': datetime.now().strftime('%d/%m/%Y %H:%M'),
            })
    gravar_registro(home, registro)
    return carimbo if feito_backup else None


ROTULO_TIPO = {'criar': 'criar', 'atualizar': 'atualizar', 'igual': 'igual', 'remover': 'remover',
               'conflito': 'CONFLITO', 'erro': 'ERRO', 'ausente': 'ausente', 'nota': 'nota'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--alvo', required=True,
                   help='ferramentas, separadas por vírgula: ' + ', '.join(DESTINOS))
    p.add_argument('--agentes', action='store_true', help='instala também as definições de agentes do adaptador')
    p.add_argument('--skills', help='só estas skills, separadas por vírgula (padrão: todas)')
    p.add_argument('--home', help='pasta pessoal alternativa (padrão: a do usuário; útil para testes)')
    p.add_argument('--aplicar', action='store_true', help='executa (sem isto, apenas simula)')
    p.add_argument('--substituir', action='store_true', help='permite sobrescrever ou remover o que foi alterado (com cópia de segurança)')
    p.add_argument('--remover', action='store_true', help='remove o que este script instalou')
    args = p.parse_args(argv)

    alvos = [a.strip() for a in args.alvo.split(',') if a.strip()]
    invalidos = [a for a in alvos if a not in DESTINOS]
    if not alvos or invalidos:
        print(f'erro: alvo inválido: {", ".join(invalidos) or "(vazio)"}; use: {", ".join(DESTINOS)}', file=sys.stderr)
        return 2
    home = Path(args.home).expanduser() if args.home else Path.home()
    if not home.is_dir():
        print(f'erro: pasta pessoal não existe: {home}', file=sys.stderr)
        return 2
    so_skills = [s.strip() for s in args.skills.split(',')] if args.skills else None
    itens = descobrir_itens(alvos, args.agentes, so_skills)
    registro = ler_registro(home)
    plano = planejar(home, itens, registro, args.substituir, args.remover)

    problemas = 0
    for a in plano:
        rel = f' ~/{a["destino"].as_posix()}' if a.get('destino') else ''
        extra = f' ({a["motivo"]})' if a.get('motivo') else ''
        print(f'{ROTULO_TIPO[a["tipo"]]:9}{a["rotulo"]}{rel}{extra}')
        if a['tipo'] in ('conflito', 'erro'):
            problemas += 1
    if not args.aplicar:
        print('\nSimulação: nada foi alterado. Rode de novo com --aplicar para executar.')
        return 1 if problemas else 0
    executaveis = [a for a in plano if a['tipo'] in ('criar', 'atualizar', 'remover', 'igual')]
    if executaveis:
        backup = executar(home, executaveis, registro, versao_pacote())
        print('\nConcluído.' + (f' Cópia de segurança em ~/{(BACKUPS / backup).as_posix()}' if backup else ''))
    if problemas:
        print(f'{problemas} item(ns) ignorado(s) por conflito ou erro; nada foi sobrescrito sem permissão.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
