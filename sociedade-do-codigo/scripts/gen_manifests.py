#!/usr/bin/env python3
"""Gera os manifestos do plugin e dos marketplaces a partir de pacote.json e VERSION (fonte única).

Sem opções: mostra o estado (igual, diferente ou ausente). --escrever grava. --verificar sai com 1 se algum
arquivo divergir do que seria gerado (uso em CI). Sem dependências externas.

Arquivos gerados:
  plugins/<nome>/plugin.json                    padrão Agent Plugins (Antigravity é superconjunto dele)
  plugins/<nome>/.claude-plugin/plugin.json     Claude Code
  plugins/<nome>/.codex-plugin/plugin.json      Codex
  .claude-plugin/marketplace.json               marketplace do Claude Code
  .agents/plugins/marketplace.json              marketplace do Codex
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCHEMA_AGENT_PLUGINS = 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'


def carregar():
    dados = json.loads((RAIZ / 'pacote.json').read_text(encoding='utf-8'))
    versao = (RAIZ / 'VERSION').read_text(encoding='utf-8').strip()
    return dados, versao


def base_plugin(d, versao):
    return {
        'name': d['name'],
        'version': versao,
        'description': d['description'],
        'author': {'name': d['author']},
        'repository': d['repository'],
        'license': d['license'],
        'keywords': d['keywords'],
    }


def gerar(d, versao):
    nome = d['name']
    pasta = f'plugins/{nome}'
    portatil = {'$schema': SCHEMA_AGENT_PLUGINS, **base_plugin(d, versao)}
    claude = base_plugin(d, versao)
    codex = {
        **base_plugin(d, versao),
        'skills': './skills/',
        'interface': {
            'displayName': d['displayName'],
            'shortDescription': d['shortDescription'],
            'longDescription': d['description'],
            'category': 'Productivity',
        },
    }
    mkt_claude = {
        'name': d['marketplace'],
        'owner': {'name': d['author']},
        'description': f"Marketplace do {d['displayName']}",
        'plugins': [{
            'name': nome,
            'source': f'./{pasta}',
            'description': d['description'],
            'version': versao,
            'license': d['license'],
            'keywords': d['keywords'],
            'category': d['category'],
        }],
    }
    mkt_codex = {
        'name': d['marketplace'],
        'interface': {'displayName': d['displayName']},
        'plugins': [{
            'name': nome,
            'source': {'source': 'local', 'path': f'./{pasta}'},
            'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
            'category': 'Productivity',
        }],
    }
    return {
        f'{pasta}/plugin.json': portatil,
        f'{pasta}/.claude-plugin/plugin.json': claude,
        f'{pasta}/.codex-plugin/plugin.json': codex,
        '.claude-plugin/marketplace.json': mkt_claude,
        '.agents/plugins/marketplace.json': mkt_codex,
    }


def serializar(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group()
    g.add_argument('--escrever', action='store_true', help='grava os arquivos gerados')
    g.add_argument('--verificar', action='store_true', help='sai com 1 se algum arquivo divergir')
    args = p.parse_args(argv)
    dados, versao = carregar()
    divergiu = False
    for rel, obj in gerar(dados, versao).items():
        alvo = RAIZ / rel
        novo = serializar(obj)
        atual = alvo.read_text(encoding='utf-8') if alvo.is_file() else None
        estado = 'igual' if atual == novo else ('ausente' if atual is None else 'diferente')
        if estado != 'igual':
            divergiu = True
        if args.escrever and estado != 'igual':
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(novo, encoding='utf-8')
            estado += ' -> gravado'
        print(f'{rel}: {estado}')
    if args.verificar and divergiu:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
