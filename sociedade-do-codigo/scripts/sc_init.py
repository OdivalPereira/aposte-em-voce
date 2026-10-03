#!/usr/bin/env python3
"""Ponto de entrada na raiz para inicialização guiada de novos projetos na Sociedade do Código.

Encaminha a execução para plugins/sociedade-do-codigo/skills/sociedade-do-codigo/scripts/sc_init.py.
Sem dependências externas.
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT_REAL = RAIZ / 'plugins' / 'sociedade-do-codigo' / 'skills' / 'sociedade-do-codigo' / 'scripts' / 'sc_init.py'

if not SCRIPT_REAL.is_file():
    print(f'ERRO: Script de inicialização não encontrado em {SCRIPT_REAL}', file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(SCRIPT_REAL.parent))
from sc_init import main

if __name__ == '__main__':
    sys.exit(main())
