#!/usr/bin/env python3
"""Inventário do ambiente local para os executores do módulo `local` (somente leitura).

Mostra o que existe nesta máquina: processador, memória, disco, Ollama (binário, servidor e modelos),
bibliotecas Python usadas pelos quatro papéis, navegadores do Playwright e, se pedido, caminhos e comandos.

O que o script NÃO faz: instalar, baixar, atualizar, executar modelo, gravar arquivo ou enviar dado para fora.
Só consulta o Ollama em endereço da própria máquina (127.0.0.1, localhost ou ::1) e só com GET de leitura.
As bibliotecas são procuradas sem importá-las (nenhum código delas é executado).

Uso:
  python3 inventario_local.py
  python3 inventario_local.py --json
  python3 inventario_local.py --caminho modules/parsers --comando node
  python3 inventario_local.py --exigir ollama,servidor,modelo:qwen,py:duckdb     (sai com código 1 se faltar algo)

As bibliotecas são vistas pelo Python que roda este script. Se o projeto usa outro ambiente virtual,
rode o script com o Python dele.
"""
import argparse
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

URL_OLLAMA_PADRAO = 'http://127.0.0.1:11434'
HOSTS_LOCAIS = ('127.0.0.1', 'localhost', '::1')

# (módulo importável, nome da distribuição no pip)
GRUPOS = {
    'parsers e extração (Celebrimbor)': [
        ('docling', 'docling'), ('instructor', 'instructor'), ('pydantic', 'pydantic'),
        ('pdfplumber', 'pdfplumber'), ('pypdf', 'pypdf'), ('pandas', 'pandas'),
        ('openpyxl', 'openpyxl'), ('ofxparse', 'ofxparse'),
    ],
    'coleta web (Radagast)': [
        ('httpx', 'httpx'), ('requests', 'requests'), ('trafilatura', 'trafilatura'),
        ('crawl4ai', 'crawl4ai'), ('playwright', 'playwright'), ('bs4', 'beautifulsoup4'), ('lxml', 'lxml'),
    ],
    'auditoria (Faramir)': [
        ('duckdb', 'duckdb'), ('pandas', 'pandas'), ('numpy', 'numpy'), ('scipy', 'scipy'),
    ],
    'acervo e contexto (Bilbo)': [
        ('chromadb', 'chromadb'), ('lancedb', 'lancedb'),
        ('sentence_transformers', 'sentence-transformers'), ('faiss', 'faiss-cpu'),
    ],
}


# ---------- formatação ----------

def formatar_gib(n):
    """Bytes em GiB com vírgula decimal (padrão brasileiro)."""
    if n is None:
        return 'não informado'
    return f'{n / 1024 ** 3:.1f}'.replace('.', ',') + ' GiB'


def formatar_tamanho(n):
    if n is None:
        return 'tamanho não informado'
    if n >= 1024 ** 3:
        return formatar_gib(n)
    return f'{n / 1024 ** 2:.0f}'.replace('.', ',') + ' MiB'


# ---------- máquina ----------

def parse_meminfo(texto):
    """Lê o conteúdo de /proc/meminfo e devolve (total, disponível) em bytes; None se ausente."""
    def kb(chave):
        m = re.search(rf'^{chave}:\s+(\d+)\s*kB', texto, re.M)
        return int(m.group(1)) * 1024 if m else None
    return kb('MemTotal'), kb('MemAvailable')


def memoria():
    try:
        if sys.platform.startswith('linux'):
            return parse_meminfo(Path('/proc/meminfo').read_text(encoding='utf-8'))
        if sys.platform == 'darwin':
            out = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True, timeout=5)
            return int(out.stdout.strip()), None
        if sys.platform.startswith('win'):
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                            ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                            ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                            ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                            ('sullAvailExtendedVirtual', ctypes.c_ulonglong)]
            st = MEMORYSTATUSEX()
            st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
            return int(st.ullTotalPhys), int(st.ullAvailPhys)
    except Exception:
        pass
    return None, None


def processador():
    try:
        if sys.platform.startswith('linux'):
            m = re.search(r'^model name\s*:\s*(.+)$', Path('/proc/cpuinfo').read_text(encoding='utf-8'), re.M)
            if m:
                return m.group(1).strip()
        if sys.platform == 'darwin':
            out = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True, timeout=5)
            if out.stdout.strip():
                return out.stdout.strip()
    except Exception:
        pass
    return platform.processor() or platform.machine() or 'não informado'


def coletar_maquina(pasta):
    total, disponivel = memoria()
    try:
        livre = shutil.disk_usage(pasta).free
    except Exception:
        livre = None
    return {
        'sistema': f'{platform.system()} {platform.release()}',
        'arquitetura': platform.machine(),
        'processador': processador(),
        'nucleos_logicos': os.cpu_count(),
        'memoria_total_bytes': total,
        'memoria_disponivel_bytes': disponivel,
        'disco_livre_bytes': livre,
        'disco_livre_em': str(pasta),
        'python': platform.python_version(),
        'python_caminho': sys.executable,
    }


# ---------- Ollama ----------

def host_local(url):
    """True se a URL é http e aponta para a própria máquina."""
    try:
        p = urlparse(url)
    except ValueError:
        return False
    return p.scheme == 'http' and (p.hostname or '') in HOSTS_LOCAIS


def _get_json(url, timeout=2.0):
    with urllib.request.urlopen(url, timeout=timeout) as r:  # GET de leitura em endereço local
        return json.loads(r.read().decode('utf-8'))


def _modelo(m):
    d = m.get('details') or {}
    return {'nome': m.get('name') or m.get('model'), 'tamanho_bytes': m.get('size'),
            'parametros': d.get('parameter_size'), 'quantizacao': d.get('quantization_level'),
            'familia': d.get('family')}


def coletar_ollama(url=URL_OLLAMA_PADRAO, timeout=2.0):
    info = {'url': url, 'binario': shutil.which('ollama'), 'versao': None, 'servidor': 'sem resposta',
            'modelos': [], 'carregados': []}
    if not host_local(url):
        info['servidor'] = 'não consultado: o endereço não é da própria máquina'
        return info
    try:
        info['versao'] = _get_json(url.rstrip('/') + '/api/version', timeout).get('version')
        info['servidor'] = 'respondendo'
        info['modelos'] = [_modelo(m) for m in _get_json(url.rstrip('/') + '/api/tags', timeout).get('models', [])]
        try:
            info['carregados'] = [_modelo(m) for m in _get_json(url.rstrip('/') + '/api/ps', timeout).get('models', [])]
        except Exception:
            info['carregados'] = []
    except Exception:
        pass  # servidor desligado ou inacessível: fica como "sem resposta"
    if info['versao'] is None and info['binario']:
        try:
            out = subprocess.run([info['binario'], '--version'], capture_output=True, text=True, timeout=5)
            m = re.search(r'(\d+\.\d+\.\d+\S*)', (out.stdout or '') + (out.stderr or ''))
            info['versao'] = m.group(1) if m else None
        except Exception:
            pass
    return info


# ---------- bibliotecas, navegadores, caminhos, comandos ----------

def biblioteca(modulo, distribuicao):
    try:
        presente = importlib.util.find_spec(modulo) is not None
    except (ImportError, ValueError):
        presente = False
    versao = None
    if presente:
        try:
            versao = importlib.metadata.version(distribuicao)
        except Exception:
            versao = None
    return {'presente': presente, 'versao': versao}


def coletar_bibliotecas():
    return {grupo: {mod: biblioteca(mod, dist) for mod, dist in itens} for grupo, itens in GRUPOS.items()}


def navegadores_playwright():
    var = os.environ.get('PLAYWRIGHT_BROWSERS_PATH')
    home = Path.home()
    candidatos = []
    if var and var != '0':
        candidatos.append(Path(var))
    candidatos += [home / '.cache' / 'ms-playwright', home / 'Library' / 'Caches' / 'ms-playwright']
    local = os.environ.get('LOCALAPPDATA')
    if local:
        candidatos.append(Path(local) / 'ms-playwright')
    achados = []
    for c in candidatos:
        try:
            if c.is_dir():
                achados += sorted(p.name for p in c.iterdir()
                                  if p.is_dir() and re.match(r'(chromium|firefox|webkit)', p.name))
        except OSError:
            continue
    return achados


def coletar_caminhos(caminhos):
    r = {}
    for c in caminhos:
        p = Path(c)
        r[c] = 'pasta' if p.is_dir() else 'arquivo' if p.is_file() else 'não existe'
    return r


def coletar_comandos(comandos):
    return {c: shutil.which(c) for c in comandos}


# ---------- exigências ----------

def avaliar_exigencias(exigencias, inv):
    """Devolve a lista do que faltou. Itens: ollama, servidor, modelo:<trecho>, py:<módulo>, comando:<nome>."""
    faltando = []
    for e in exigencias:
        e = e.strip()
        if not e:
            continue
        if e == 'ollama':
            if not inv['ollama']['binario'] and inv['ollama']['servidor'] != 'respondendo':
                faltando.append(e)
        elif e == 'servidor':
            if inv['ollama']['servidor'] != 'respondendo':
                faltando.append(e)
        elif e.startswith('modelo:'):
            trecho = e.split(':', 1)[1].lower()
            if not any(trecho in (m['nome'] or '').lower() for m in inv['ollama']['modelos']):
                faltando.append(e)
        elif e.startswith('py:'):
            mod = e.split(':', 1)[1]
            if not biblioteca(mod, mod)['presente']:
                faltando.append(e)
        elif e.startswith('comando:'):
            if not shutil.which(e.split(':', 1)[1]):
                faltando.append(e)
        else:
            faltando.append(e + ' (item desconhecido)')
    return faltando


# ---------- saída ----------

def formatar_texto(inv):
    m, o = inv['maquina'], inv['ollama']
    L = [f'Inventário do ambiente local (somente leitura) · {inv["gerado_em"]}',
         'Nada foi instalado, baixado, executado nem alterado.', '',
         'Máquina',
         f'  sistema: {m["sistema"]} ({m["arquitetura"]})',
         f'  processador: {m["processador"]} ({m["nucleos_logicos"]} núcleos lógicos)',
         f'  memória: {formatar_gib(m["memoria_total_bytes"])} no total, {formatar_gib(m["memoria_disponivel_bytes"])} disponíveis',
         f'  disco livre em {m["disco_livre_em"]}: {formatar_gib(m["disco_livre_bytes"])}',
         f'  Python: {m["python"]} em {m["python_caminho"]}', '',
         'Ollama',
         f'  binário: {o["binario"] or "não encontrado no PATH"}' + (f' (versão {o["versao"]})' if o['versao'] else ''),
         f'  servidor em {o["url"]}: {o["servidor"]}']
    if o['servidor'] == 'respondendo':
        L.append(f'  modelos instalados ({len(o["modelos"])}):' if o['modelos'] else '  modelos instalados: nenhum')
        for x in o['modelos']:
            extra = ', '.join(str(v) for v in (x['parametros'], x['quantizacao']) if v)
            L.append(f'    {x["nome"]}  {formatar_tamanho(x["tamanho_bytes"])}' + (f'  ({extra})' if extra else ''))
        L.append('  carregados agora: ' + (', '.join(x['nome'] for x in o['carregados']) if o['carregados'] else 'nenhum'))
    L += ['', 'Bibliotecas Python (vistas por este Python)']
    for grupo, mods in inv['bibliotecas'].items():
        ok = [f'{k} {v["versao"]}' if v['versao'] else k for k, v in mods.items() if v['presente']]
        falta = [k for k, v in mods.items() if not v['presente']]
        L.append(f'  {grupo}:')
        L.append(f'    presentes: {", ".join(ok) if ok else "nenhuma"}')
        L.append(f'    ausentes: {", ".join(falta) if falta else "nenhuma"}')
    L += ['', 'Navegadores do Playwright: ' + (', '.join(inv['playwright_navegadores']) or 'nenhum encontrado')]
    if inv['caminhos']:
        L += ['', 'Caminhos']
        L += [f'  {k}: {v}' for k, v in inv['caminhos'].items()]
    if inv['comandos']:
        L += ['', 'Comandos']
        L += [f'  {k}: {v or "não encontrado"}' for k, v in inv['comandos'].items()]
    if inv['faltando']:
        L += ['', 'Exigências não atendidas: ' + ', '.join(inv['faltando'])]
    L += ['', 'Lembrete: instalar biblioteca ou baixar modelo é parada humana. Este relatório só informa o que existe.']
    return '\n'.join(L)


def coletar(caminhos=(), comandos=(), url_ollama=URL_OLLAMA_PADRAO, exigencias=(), pasta=None):
    pasta = Path(pasta) if pasta else Path.cwd()
    inv = {
        'gerado_em': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'maquina': coletar_maquina(pasta),
        'ollama': coletar_ollama(url_ollama),
        'bibliotecas': coletar_bibliotecas(),
        'playwright_navegadores': navegadores_playwright(),
        'caminhos': coletar_caminhos(caminhos),
        'comandos': coletar_comandos(comandos),
    }
    inv['faltando'] = avaliar_exigencias(exigencias, inv)
    return inv


def main(argv=None):
    p = argparse.ArgumentParser(description='Inventário do ambiente local (somente leitura).')
    p.add_argument('--json', action='store_true', help='saída em JSON')
    p.add_argument('--caminho', action='append', default=[], help='caminho a conferir (repetível)')
    p.add_argument('--comando', action='append', default=[], help='comando a procurar no PATH (repetível)')
    p.add_argument('--ollama-url', default=URL_OLLAMA_PADRAO, help='só endereços da própria máquina')
    p.add_argument('--exigir', default='', help='lista separada por vírgula: ollama, servidor, modelo:<trecho>, py:<módulo>, comando:<nome>')
    a = p.parse_args(argv)
    if not host_local(a.ollama_url):
        print('erro: --ollama-url deve ser http e apontar para 127.0.0.1, localhost ou ::1', file=sys.stderr)
        return 2
    inv = coletar(a.caminho, a.comando, a.ollama_url, [x for x in a.exigir.split(',')])
    print(json.dumps(inv, ensure_ascii=False, indent=2) if a.json else formatar_texto(inv))
    return 1 if inv['faltando'] else 0


if __name__ == '__main__':
    sys.exit(main())
