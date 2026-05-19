#!/usr/bin/env python3
"""
Ejecuta todos los tests de MiniSQL y reporta resultados.
Uso: python tests/run_tests.py
"""

import os
import sys
import subprocess

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN      = os.path.join(TESTS_DIR, '..', 'main.py')
PYTHON    = sys.executable

VERDE  = '\033[92m'
ROJO   = '\033[91m'
AMARILLO = '\033[93m'
RESET  = '\033[0m'

tests = sorted(f for f in os.listdir(TESTS_DIR) if f.endswith('.sql'))

ok = err = 0

SEP = '-' * 55
print(SEP)
print('  MiniSQL -- Suite de tests')
print(SEP)

for test in tests:
    ruta = os.path.join(TESTS_DIR, test)
    result = subprocess.run(
        [PYTHON, MAIN, ruta],
        capture_output=True, text=True, timeout=10
    )
    tiene_error = (
        '[Error' in result.stdout or
        '[Error' in result.stderr or
        result.returncode != 0
    )
    if tiene_error:
        print(f'  FALLO  {test}')
        if result.stdout:
            for linea in result.stdout.strip().split('\n'):
                if '[Error' in linea:
                    print(f'         {linea}')
        if result.stderr:
            print(f'         {result.stderr.strip()[:120]}')
        err += 1
    else:
        print(f'  OK     {test}')
        ok += 1

print(SEP)
print(f'  Pasados: {ok}  |  Fallados: {err}  |  Total: {ok + err}')
print(SEP)

sys.exit(0 if err == 0 else 1)
