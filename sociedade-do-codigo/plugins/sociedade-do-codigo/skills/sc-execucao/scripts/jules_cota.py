#!/usr/bin/env python3
"""Conta quantas tarefas do Jules foram criadas nas últimas 24 horas (janela móvel) e quanto ainda cabe.

Somente leitura. Não grava relatório nem histórico. Fontes das datas:
  --arquivo ARQ   JSON com lista de datas ISO 8601 ou de objetos com "createTime" (use "-" para ler da entrada padrão);
                  também aceita a resposta da API ({"sessions": [...]}).
  --api           consulta GET /sessions da API alfa do Jules; usa a variável de ambiente JULES_API_KEY
                  (a chave nunca é impressa nem gravada).

Suposição declarada na saída: uma sessão criada = uma tarefa (a documentação oficial não define "tarefa").
Sem dependências externas.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE_API = 'https://jules.googleapis.com/v1alpha'
# Limites da página oficial em 19/09/2026 (https://jules.google/docs/usage-limits/). Confirme o plano.
LIMITES = {'free': (15, 3), 'gratuito': (15, 3), 'pro': (100, 15), 'ultra': (300, 60)}
JANELA = timedelta(hours=24)


def obter_fuso(nome):
    """Fuso para exibir horários: --fuso (nome IANA) ou o fuso local da máquina."""
    if not nome:
        return None  # None = fuso local do sistema
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(nome)
    except Exception as e:  # nome inexistente ou base de fusos ausente
        raise ValueError(f'fuso desconhecido ou indisponível: {nome} ({e.__class__.__name__})') from None


def parse_data(texto):
    """Lê ISO 8601 (com Z ou deslocamento). Sem fuso, assume UTC."""
    t = str(texto).strip()
    if t.endswith('Z') or t.endswith('z'):
        t = t[:-1] + '+00:00'
    if '.' in t:  # fração de segundo com mais de 6 dígitos
        cabeca, _, resto = t.partition('.')
        digitos = ''
        for c in resto:
            if c.isdigit():
                digitos += c
            else:
                break
        cauda = resto[len(digitos):]
        t = f'{cabeca}.{digitos[:6].ljust(6, "0")}{cauda}'
    d = datetime.fromisoformat(t)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def extrair_datas(dados):
    if isinstance(dados, dict):
        dados = dados.get('sessions', dados.get('sessoes', []))
    if not isinstance(dados, list):
        raise ValueError('esperava uma lista de datas ou de objetos com "createTime"')
    datas = []
    for item in dados:
        bruto = item.get('createTime') if isinstance(item, dict) else item
        if bruto:
            datas.append(parse_data(bruto))
    return datas


def ler_api(max_paginas, tamanho_pagina=100):
    chave = os.environ.get('JULES_API_KEY', '').strip()
    if not chave:
        raise RuntimeError('variável de ambiente JULES_API_KEY não definida (a chave nunca vai para arquivo nem argumento)')
    datas, token, cortou = [], '', False
    for pagina in range(max_paginas):
        url = f'{BASE_API}/sessions?pageSize={tamanho_pagina}'
        if token:
            url += f'&pageToken={token}'
        req = urllib.request.Request(url, headers={'X-Goog-Api-Key': chave})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                corpo = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'API respondeu HTTP {e.code}; confira a chave, o acesso e o plano') from None
        except urllib.error.URLError as e:
            raise RuntimeError(f'falha de rede ao consultar a API: {e.reason}') from None
        datas.extend(extrair_datas(corpo))
        token = corpo.get('nextPageToken', '')
        if not token:
            break
    else:
        cortou = bool(token)
    return datas, cortou


def calcular(datas, agora, limite, simultaneas=None, ativas=None, reserva=0):
    dentro = sorted(d for d in datas if agora - JANELA < d <= agora)
    usadas = len(dentro)
    restam = max(limite - usadas, 0)
    utilizavel = max(restam - reserva, 0)
    resultado = {
        'usadas_24h': usadas,
        'limite_diario': limite,
        'restam': restam,
        'reserva': reserva,
        'pode_despachar': utilizavel,
        'proxima_liberacao': None,
    }
    if dentro:
        # uma vaga volta quando a sessão mais antiga da janela completa 24 horas
        resultado['proxima_liberacao'] = dentro[0] + JANELA
    if simultaneas is not None and ativas is not None:
        livres = max(simultaneas - ativas, 0)
        resultado['simultaneas'] = simultaneas
        resultado['ativas'] = ativas
        resultado['simultaneas_livres'] = livres
        resultado['pode_despachar'] = min(utilizavel, livres)
    return resultado


def formatar(dt, fuso=None):
    local = dt.astimezone(fuso) if fuso else dt.astimezone()
    deslocamento = local.strftime('%z')
    return f"{local.strftime('%d/%m/%Y %H:%M')} (UTC{deslocamento[:3]}:{deslocamento[3:]})"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    origem = p.add_mutually_exclusive_group(required=True)
    origem.add_argument('--arquivo', help='JSON com datas ("-" para a entrada padrão)')
    origem.add_argument('--api', action='store_true', help='consulta a API do Jules (usa JULES_API_KEY)')
    p.add_argument('--plano', choices=sorted(LIMITES), help='plano contratado (define limites padrão)')
    p.add_argument('--limite', type=int, help='limite diário informado pelo usuário (sobrepõe o plano)')
    p.add_argument('--simultaneas', type=int, help='teto de tarefas simultâneas (perfil do projeto ou plano)')
    p.add_argument('--ativas', type=int, help='tarefas ativas agora (informe; a API não documenta estados)')
    p.add_argument('--reserva', type=int, default=0, help='cota a deixar de reserva (padrão 0)')
    p.add_argument('--max-paginas', type=int, default=5, help='páginas da API a ler (padrão 5)')
    p.add_argument('--agora', help='instante de referência ISO 8601 (para testes)')
    p.add_argument('--fuso', help='fuso para exibir horários, nome IANA (padrão: fuso local da máquina)')
    p.add_argument('--json', action='store_true', help='saída em JSON')
    args = p.parse_args(argv)

    limite, sim_plano = (None, None)
    if args.plano:
        limite, sim_plano = LIMITES[args.plano]
    if args.limite is not None:
        limite = args.limite
    if limite is None:
        print('erro: informe --plano ou --limite (o plano do usuário não é presumido)', file=sys.stderr)
        return 2
    simultaneas = args.simultaneas if args.simultaneas is not None else sim_plano
    cortou = False
    try:
        if args.api:
            datas, cortou = ler_api(args.max_paginas)
        else:
            texto = sys.stdin.read() if args.arquivo == '-' else open(args.arquivo, encoding='utf-8').read()
            datas = extrair_datas(json.loads(texto))
        agora = parse_data(args.agora) if args.agora else datetime.now(timezone.utc)
        fuso = obter_fuso(args.fuso)
    except (OSError, ValueError, RuntimeError) as e:
        print(f'erro: {e}', file=sys.stderr)
        return 2

    r = calcular(datas, agora, limite, simultaneas, args.ativas, args.reserva)
    r['assuncao'] = 'uma sessão criada = uma tarefa; a documentação oficial não define "tarefa"'
    r['limites_conferidos_em'] = '19/09/2026'
    if cortou:
        r['aviso'] = 'a listagem foi cortada em --max-paginas; a contagem pode estar subestimada'
    if args.json:
        saida = dict(r)
        if saida['proxima_liberacao']:
            saida['proxima_liberacao'] = formatar(saida['proxima_liberacao'], fuso)
        print(json.dumps(saida, ensure_ascii=False, indent=2))
        return 0
    print(f"Tarefas criadas nas últimas 24 h: {r['usadas_24h']} de {r['limite_diario']}")
    print(f"Restam na janela: {r['restam']}" + (f" (reserva de {r['reserva']})" if r['reserva'] else ''))
    if 'simultaneas_livres' in r:
        print(f"Simultâneas: {r['ativas']} ativas de {r['simultaneas']}; livres: {r['simultaneas_livres']}")
    print(f"Pode despachar agora: {r['pode_despachar']}")
    if r['proxima_liberacao']:
        print(f"Próxima vaga na cota: {formatar(r['proxima_liberacao'], fuso)}")
    print(f"Suposição: {r['assuncao']}. Limites conferidos em {r['limites_conferidos_em']}; confirme o plano.")
    if cortou:
        print(f"Aviso: {r['aviso']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
