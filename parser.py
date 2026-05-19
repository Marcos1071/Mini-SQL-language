# El parser (analizador sintáctico) es la segunda fase del intérprete.
# Recibe la lista de tokens que produce el lexer y construye el AST.
# Usa el algoritmo LALR(1): lee los tokens de izquierda a derecha y decide
# qué regla gramatical aplicar mirando solo el token actual (1 token de lookahead).
# Cada regla de producción crea un nodo de clases.py y lo devuelve.

import logging
# SLY imprime advertencias de la gramática por defecto. Esto las silencia
# para que no ensucien la salida cuando se ejecuta el intérprete.
logging.getLogger('sly').setLevel(logging.ERROR)

from sly import Parser
from lexer import SQLLexer
from clases import *  # importa todos los nodos del AST (Programa, Select, ColRef, etc.)


class SQLParser(Parser):
    # Le dice a SLY qué tokens puede recibir (los mismos que produce SQLLexer).
    tokens = SQLLexer.tokens
    # Redirige los mensajes internos de SLY al logger silenciado arriba.
    log    = logging.getLogger('sly')

    # NOTA SOBRE PRECEDENCIA:
    # No hay tabla 'precedence = (...)' como en otros parsers.
    # La precedencia se codifica directamente en la jerarquía de no-terminales:
    #   expr → or_expr → and_expr → not_expr → cmp_expr → atom
    # Cuanto más abajo en la cadena, mayor prioridad de evaluación.
    # Este es el mismo patrón usado en las prácticas del curso.

    # NOTA SOBRE p.lineno:
    # En cada función de producción, 'p' es el objeto que SLY pasa con los valores
    # de los símbolos de la regla. p.lineno contiene el número de línea del primer
    # token de esa regla en el archivo fuente.
    # Se pasa al constructor del nodo AST (linea=p.lineno) para que los mensajes
    # de error puedan indicar exactamente en qué línea del .sql ocurrió el problema.
    # Ej: [Error SQL (línea 7)] La tabla 'productos' ya existe

    # ── Programa ───────────────────────────────────────────────────────────────
    # El símbolo inicial de la gramática es el primero que se define.

    @_('sent_lista')
    def programa(self, p):
        # El programa completo es simplemente la lista de sentencias.
        return Programa(p.sent_lista, linea=1)

    # Regla recursiva por la izquierda para acumular sentencias en una lista.
    @_('sent_lista sentencia')
    def sent_lista(self, p):
        # Ya teníamos una lista; le añadimos la nueva sentencia al final.
        return p.sent_lista + [p.sentencia]

    # Caso base: una sola sentencia arranca la lista.
    @_('sentencia')
    def sent_lista(self, p):
        return [p.sentencia]

    # ── Sentencias ─────────────────────────────────────────────────────────────

    @_('CREATE TABLE ID "(" col_def_lista ")" ";"')
    def sentencia(self, p):
        # p.ID es el nombre de la tabla, p.col_def_lista es la lista de columnas.
        return CreateTable(p.ID, p.col_def_lista, linea=p.lineno)

    @_('INSERT INTO ID VALUES "(" val_lista ")" ";"')
    def sentencia(self, p):
        # p.ID es el nombre de la tabla, p.val_lista es la lista de ExprLiteral.
        return InsertInto(p.ID, p.val_lista, linea=p.lineno)

    @_('SET VARIABLE "=" expr ";"')
    def sentencia(self, p):
        # p.VARIABLE incluye el '@'. Ej: '@precio_min'
        return SetVariable(p.VARIABLE, p.expr, linea=p.lineno)

    # SELECT * FROM tabla ...
    @_('SELECT "*" FROM ID opt_join opt_where opt_order ";"')
    def sentencia(self, p):
        # El '*' es un literal de un carácter, por eso va entre comillas dobles.
        # Se pasa la string '*' como valor de columnas para que el intérprete
        # sepa que tiene que proyectar todas las columnas.
        return Select('*', p.ID,
                      join=p.opt_join, where=p.opt_where, order_by=p.opt_order,
                      linea=p.lineno)

    # SELECT col, col FROM tabla ...
    @_('SELECT sel_cols FROM ID opt_join opt_where opt_order ";"')
    def sentencia(self, p):
        # p.sel_cols es una lista de ColRef / ExprVariable.
        return Select(p.sel_cols, p.ID,
                      join=p.opt_join, where=p.opt_where, order_by=p.opt_order,
                      linea=p.lineno)

    # ── Columnas para CREATE TABLE ─────────────────────────────────────────────
    # Solo son nombres (strings), sin tipo.

    @_('col_def_lista "," ID')
    def col_def_lista(self, p):
        # Acumula columnas: ya teníamos la lista, añadimos el nuevo ID al final.
        return p.col_def_lista + [p.ID]

    @_('ID')
    def col_def_lista(self, p):
        # Caso base: la primera (o única) columna arranca la lista.
        return [p.ID]

    # ── Columnas para SELECT ───────────────────────────────────────────────────
    # Pueden ser referencias a columnas (ColRef) o variables de sesión (@var).

    @_('sel_cols "," proj_item')
    def sel_cols(self, p):
        return p.sel_cols + [p.proj_item]

    @_('proj_item')
    def sel_cols(self, p):
        return [p.proj_item]

    # Un ítem de proyección puede ser una columna o una variable de sesión.
    @_('col_ref')
    def proj_item(self, p):
        return p.col_ref

    @_('VARIABLE')
    def proj_item(self, p):
        # Ej: SELECT nombre, @precio_min FROM ...
        return ExprVariable(p.VARIABLE, linea=p.lineno)

    # ── Referencia de columna ──────────────────────────────────────────────────

    @_('ID "." ID')
    def col_ref(self, p):
        # Columna calificada: tabla.columna
        # SLY numera los símbolos repetidos: p.ID0 = tabla, p.ID1 = columna.
        return ColRef(p.ID1, tabla=p.ID0, linea=p.lineno)

    @_('ID')
    def col_ref(self, p):
        # Columna simple: solo el nombre, sin prefijo de tabla.
        return ColRef(p.ID, linea=p.lineno)

    # ── Valores para INSERT ────────────────────────────────────────────────────
    # Admite negativos porque en SQL se puede escribir INSERT ... VALUES (-5, ...).

    @_('val_lista "," literal')
    def val_lista(self, p):
        return p.val_lista + [p.literal]

    @_('literal')
    def val_lista(self, p):
        return [p.literal]

    @_('INTEGER')
    def literal(self, p):
        # Convierte el string del token a int de Python.
        return ExprLiteral(int(p.INTEGER), linea=p.lineno)

    @_('"-" INTEGER')
    def literal(self, p):
        # El '-' es un literal de un carácter (está en literals del lexer).
        # Así se soportan valores negativos: INSERT ... VALUES (-5)
        return ExprLiteral(-int(p.INTEGER), linea=p.lineno)

    @_('FLOAT')
    def literal(self, p):
        return ExprLiteral(float(p.FLOAT), linea=p.lineno)

    @_('"-" FLOAT')
    def literal(self, p):
        return ExprLiteral(-float(p.FLOAT), linea=p.lineno)

    @_('STRING')
    def literal(self, p):
        # p.STRING ya viene sin las comillas (el lexer las eliminó).
        return ExprLiteral(p.STRING, linea=p.lineno)

    @_('TRUE')
    def literal(self, p):
        # TRUE en SQL → True en Python (bool).
        return ExprLiteral(True, linea=p.lineno)

    @_('FALSE')
    def literal(self, p):
        # FALSE en SQL → False en Python (bool).
        return ExprLiteral(False, linea=p.lineno)

    @_('NULL')
    def literal(self, p):
        # NULL en SQL → None en Python.
        return ExprLiteral(None, linea=p.lineno)

    # ── JOIN opcional ──────────────────────────────────────────────────────────

    @_('JOIN ID ON col_ref "=" col_ref')
    def opt_join(self, p):
        # p.col_ref0 = lado izquierdo del ON, p.col_ref1 = lado derecho.
        return JoinClause(p.ID, p.col_ref0, p.col_ref1, linea=p.lineno)

    @_('')
    def opt_join(self, p):
        # Producción vacía (epsilon): no hay JOIN → devuelve None.
        return None

    # ── WHERE opcional ─────────────────────────────────────────────────────────

    @_('WHERE expr')
    def opt_where(self, p):
        # Devuelve directamente el nodo de expresión.
        return p.expr

    @_('')
    def opt_where(self, p):
        # No hay WHERE → None.
        return None

    # ── ORDER BY opcional ──────────────────────────────────────────────────────

    @_('ORDER BY col_ref ASC')
    def opt_order(self, p):
        return OrderBy(p.col_ref, 'ASC', linea=p.lineno)

    @_('ORDER BY col_ref DESC')
    def opt_order(self, p):
        return OrderBy(p.col_ref, 'DESC', linea=p.lineno)

    @_('ORDER BY col_ref')
    def opt_order(self, p):
        # Sin ASC ni DESC → ascendente por defecto (igual que SQL estándar).
        return OrderBy(p.col_ref, 'ASC', linea=p.lineno)

    @_('')
    def opt_order(self, p):
        # No hay ORDER BY → None.
        return None

    # ── Expresiones WHERE — jerarquía explícita de precedencia ────────────────
    #
    # La cadena de no-terminales codifica la precedencia SIN tabla de precedencia:
    #
    #   expr → or_expr → and_expr → not_expr → cmp_expr → atom
    #
    # Leer de abajo a arriba: atom tiene más prioridad, or_expr la menor.
    # Esto garantiza que  a = 1 AND b = 2 OR c = 3
    # se interprete como  (a=1 AND b=2) OR (c=3)  y no de otra forma.

    # 1. OR — menor prioridad de todos los operadores lógicos
    @_('or_expr OR and_expr')
    def or_expr(self, p):
        return ExprBinOp('OR', p.or_expr, p.and_expr, linea=p.lineno)

    # Si no hay OR, or_expr es simplemente un and_expr (pasa hacia arriba).
    @_('and_expr')
    def or_expr(self, p):
        return p.and_expr

    # expr es el punto de entrada público de las expresiones.
    @_('or_expr')
    def expr(self, p):
        return p.or_expr

    # 2. AND — mayor prioridad que OR
    @_('and_expr AND not_expr')
    def and_expr(self, p):
        return ExprBinOp('AND', p.and_expr, p.not_expr, linea=p.lineno)

    @_('not_expr')
    def and_expr(self, p):
        return p.not_expr

    # 3. NOT — mayor prioridad que AND
    @_('NOT not_expr')
    def not_expr(self, p):
        # NOT es recursivo: NOT NOT x es válido.
        return ExprUnOp('NOT', p.not_expr, linea=p.lineno)

    @_('cmp_expr')
    def not_expr(self, p):
        return p.cmp_expr

    # 4. Comparaciones — no asociativas (no se puede escribir a < b < c)
    # Cada operador va en su propia regla, todas al mismo nivel.
    @_('atom "=" atom')
    def cmp_expr(self, p):
        return ExprBinOp('=', p.atom0, p.atom1, linea=p.lineno)

    @_('atom NEQ atom')
    def cmp_expr(self, p):
        return ExprBinOp('!=', p.atom0, p.atom1, linea=p.lineno)

    @_('atom "<" atom')
    def cmp_expr(self, p):
        return ExprBinOp('<', p.atom0, p.atom1, linea=p.lineno)

    @_('atom LE atom')
    def cmp_expr(self, p):
        return ExprBinOp('<=', p.atom0, p.atom1, linea=p.lineno)

    @_('atom ">" atom')
    def cmp_expr(self, p):
        return ExprBinOp('>', p.atom0, p.atom1, linea=p.lineno)

    @_('atom GE atom')
    def cmp_expr(self, p):
        return ExprBinOp('>=', p.atom0, p.atom1, linea=p.lineno)

    # Si no hay comparación, cmp_expr es directamente un atom.
    @_('atom')
    def cmp_expr(self, p):
        return p.atom

    # 5. Átomos — mayor prioridad, los valores individuales
    @_('col_ref')
    def atom(self, p):
        # Una columna: nombre  o  tabla.columna
        return p.col_ref

    @_('VARIABLE')
    def atom(self, p):
        # Una variable de sesión: @precio_min
        return ExprVariable(p.VARIABLE, linea=p.lineno)

    @_('literal')
    def atom(self, p):
        # Un valor literal: 42, 'Ana', TRUE, NULL...
        return p.literal

    @_('"(" expr ")"')
    def atom(self, p):
        # Expresión entre paréntesis: fuerza prioridad manualmente.
        # Los paréntesis no generan nodo propio, simplemente devuelven la expr interior.
        return p.expr

    # ── Errores sintácticos ────────────────────────────────────────────────────

    def error(self, p):
        if p:
            # p existe: hay un token inesperado en la posición p.lineno.
            print(f'[Error sintáctico] línea {p.lineno}: '
                  f'token inesperado {p.type!r} ({p.value!r})')
        else:
            # p es None: el archivo terminó antes de lo esperado.
            print('[Error sintáctico] fin de archivo inesperado')
