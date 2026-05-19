#!/usr/bin/env python3
# Punto de entrada del intérprete MiniSQL.
# Orquesta las tres fases: léxico → sintáctico → ejecución.
# Ofrece tres modos de uso:
#   python main.py archivo.sql         → ejecuta el fichero
#   python main.py                     → modo interactivo (REPL)
#   python main.py --ast archivo.sql   → muestra el AST sin ejecutar
"""
MiniSQL — Intérprete de SQL simplificado.

Uso:
    python main.py archivo.sql          Ejecutar un fichero SQL
    python main.py                      Modo interactivo (REPL)
    python main.py --ast archivo.sql    Mostrar el AST sin ejecutar

Sentencias soportadas:
    CREATE TABLE nombre (col1, col2, ...);
    INSERT INTO nombre VALUES (v1, v2, ...);
    SELECT * | col [, col ...]
        FROM tabla
        [JOIN tabla2 ON tabla.col = tabla2.col]
        [WHERE condicion]
        [ORDER BY col [ASC | DESC]];

Tipos de datos: entero, flotante, cadena, TRUE, FALSE, NULL
Operadores WHERE: =  !=  <  <=  >  >=  AND  OR  NOT
"""

import sys
import logging

# Silencia los avisos internos que SLY imprime sobre la gramática.
logging.getLogger('sly').setLevel(logging.ERROR)

from lexer      import SQLLexer
from parser     import SQLParser
from interprete import InterpretadorSQL, ErrorSQL


def analizar(codigo):
    # Ejecuta las dos primeras fases en una sola línea:
    # 1. SQLLexer().tokenize(codigo) → generador de tokens
    # 2. SQLParser().parse(...)      → árbol AST (nodo Programa) o None si hay error
    return SQLParser().parse(SQLLexer().tokenize(codigo))


def mostrar_ast(nodo, nivel=0):
    # Imprime el AST con indentación para que sea legible.
    # Se llama recursivamente: cada hijo aumenta el nivel en 1.
    sangria = '  ' * nivel
    nombre  = type(nodo).__name__  # nombre de la clase del nodo, Ej: 'Select'

    # Obtiene todos los atributos del nodo excepto 'linea' (no aporta visualmente).
    campos  = {k: v for k, v in nodo.__dict__.items() if k != 'linea'}

    # Separa los atributos escalares (str, int, bool, None) de los que son nodos o listas.
    # Los escalares se imprimen en la misma línea que el nombre del nodo.
    escalares = {k: v for k, v in campos.items()
                 if not isinstance(v, list) and not hasattr(v, '__dict__')}

    # Imprime el nombre del nodo y sus atributos escalares en una línea.
    # Ej:  Select tabla='empleados', columnas='*'
    print(f'{sangria}{nombre}', end='')
    if escalares:
        print(' ' + ', '.join(f'{k}={v!r}' for k, v in escalares.items()), end='')
    print()

    # Imprime los atributos que son listas o nodos hijos con más indentación.
    for k, v in campos.items():
        if isinstance(v, list):
            # Es una lista: imprime la etiqueta y cada elemento de la lista.
            print(f'{sangria}  [{k}]:')
            for item in v:
                if hasattr(item, '__dict__'):
                    # El elemento es un nodo → llamada recursiva.
                    mostrar_ast(item, nivel + 2)
                else:
                    # El elemento es un escalar (Ej: nombre de columna en CreateTable).
                    print(f'{"  " * (nivel + 2)}{item!r}')
        elif hasattr(v, '__dict__'):
            # Es un nodo hijo (Ej: where, join, order_by) → llamada recursiva.
            print(f'{sangria}  {k}:')
            mostrar_ast(v, nivel + 2)


def ejecutar_archivo(ruta, mostrar_arbol=False):
    # Lee el contenido completo del fichero .sql.
    try:
        with open(ruta, encoding='utf-8') as f:
            codigo = f.read()
    except FileNotFoundError:
        print(f'[Error] Fichero no encontrado: {ruta}')
        sys.exit(1)

    # Fase 1 y 2: lexer + parser → AST.
    ast = analizar(codigo)
    if ast is None:
        # El parser devuelve None si no pudo construir el árbol (error sintáctico).
        print('[Error] No se pudo construir el AST.')
        sys.exit(1)

    if mostrar_arbol:
        # Modo --ast: solo muestra el árbol y termina sin ejecutar.
        mostrar_ast(ast)
        return

    # Fase 3: crea el intérprete y ejecuta el AST.
    interprete = InterpretadorSQL()
    try:
        interprete.ejecutar(ast)
    except ErrorSQL as e:
        # Captura errores de ejecución (tabla no existe, columna no encontrada, etc.)
        linea = f' (línea {e.linea})' if e.linea else ''
        print(f'[Error SQL{linea}] {e}')
        sys.exit(1)


def repl():
    # REPL = Read-Eval-Print Loop: modo interactivo línea a línea.
    print('MiniSQL — Intérprete SQL simplificado')
    print('Escribe sentencias SQL (terminadas en ";").')
    print('Pulsa Enter vacío tras completar una sentencia para ejecutar.')
    print('Escribe "salir" o Ctrl+C para terminar.\n')

    # Un único intérprete persiste toda la sesión: las tablas y @variables
    # creadas en una sentencia siguen disponibles en las siguientes.
    interprete = InterpretadorSQL()
    lexer      = SQLLexer()
    parser     = SQLParser()
    buffer     = ''  # acumula texto hasta encontrar un ';'

    while True:
        try:
            # El prompt cambia según si hay texto acumulado o no.
            # 'sql> ' indica inicio de sentencia nueva.
            # '...> ' indica que la sentencia aún no está completa.
            prompt = 'sql> ' if not buffer.strip() else '...> '
            linea  = input(prompt)
        except (EOFError, KeyboardInterrupt):
            # Ctrl+D (EOF) o Ctrl+C → sale del bucle limpiamente.
            print()
            break

        # Permite salir escribiendo 'salir', 'exit' o 'quit' (con o sin ';').
        if linea.strip().lower() in ('salir', 'salir;', 'exit', 'exit;', 'quit', 'quit;'):
            break

        # Acumula la línea en el buffer para soportar sentencias multi-línea.
        buffer += linea + '\n'

        # Si no hay ';' en el buffer todavía, espera más líneas.
        if ';' not in buffer:
            continue

        # Hay al menos un ';': intenta parsear y ejecutar el buffer completo.
        ast = parser.parse(lexer.tokenize(buffer))
        buffer = ''  # limpia el buffer para la siguiente sentencia
        if ast is None:
            continue  # error sintáctico ya impreso por el parser
        try:
            interprete.ejecutar(ast)
        except ErrorSQL as e:
            sufijo = f' (línea {e.linea})' if e.linea else ''
            print(f'[Error SQL{sufijo}] {e}')


def main():
    # Lee los argumentos de línea de comandos (sys.argv[0] es el propio script).
    args = sys.argv[1:]

    if not args:
        # Sin argumentos → modo interactivo.
        repl()
        return

    if args[0] == '--ast' and len(args) == 2:
        # '--ast fichero.sql' → muestra el AST sin ejecutar.
        ejecutar_archivo(args[1], mostrar_arbol=True)
        return

    if args[0] in ('-h', '--help'):
        # '-h' o '--help' → imprime el docstring del módulo y termina.
        print(__doc__)
        return

    # Cualquier otro argumento se trata como nombre de fichero a ejecutar.
    ejecutar_archivo(args[0])


# Punto de entrada estándar de Python:
# Este bloque solo se ejecuta si el script se lanza directamente (python main.py),
# no si se importa desde otro módulo (import main).
if __name__ == '__main__':
    main()
