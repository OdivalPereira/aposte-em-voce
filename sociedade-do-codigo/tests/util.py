"""Apoio comum aos testes (somente biblioteca padrão)."""
import importlib.util
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLUGIN = RAIZ / 'plugins' / 'sociedade-do-codigo'
SKILLS = PLUGIN / 'skills'
NUCLEO = SKILLS / 'sociedade-do-codigo'


def rodar(script, *args, entrada=None, cwd=None, env=None):
    return subprocess.run([sys.executable, str(script), *map(str, args)], input=entrada, cwd=cwd, env=env,
                          capture_output=True, text=True, encoding='utf-8')


def carregar(caminho, nome):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
