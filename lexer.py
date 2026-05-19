# El lexer (analizador léxico) es la primera fase del intérprete.
# Su trabajo es convertir el texto SQL crudo en una lista de tokens.
# Un token es la unidad mínima con significado: una palabra clave, un número,
# un operador, un identificador...
# Ejemplo: "SELECT nombre FROM empleados" → [SELECT, ID('nombre'), FROM, ID('empleados')]

from sly import Lexer  # importa la clase base de la librería SLY


class SQLLexer(Lexer):

    # ── Declaración de todos los tokens que puede producir este lexer ─────────
    # SLY requiere que estén todos listados aquí. Los que no estén en esta lista
    # no pueden usarse en el parser.
    tokens = {
        CREATE, TABLE, INSERT, INTO, VALUES,        # palabras clave DDL/DML
        SELECT, FROM, WHERE, JOIN, ON,              # palabras clave de consulta
        ORDER, BY, ASC, DESC,                       # palabras clave de ordenación
        SET,                                        # palabra clave de variables
        AND, OR, NOT,                               # operadores lógicos
        TRUE, FALSE, NULL,                          # literales especiales
        NEQ, LE, GE,                                # operadores de dos caracteres: != <= >=
        VARIABLE,                                   # variables de sesión: @nombre
        ID, INTEGER, FLOAT, STRING,                 # identificadores y literales de valor
    }

    # ── Caracteres de un solo carácter que son tokens por sí mismos ───────────
    # SLY los trata como tokens cuyo tipo ES el propio carácter.
    # Así en el parser se pueden usar directamente como "=" o "(" sin declararlos en tokens.
    literals = {'=', '<', '>', '(', ')', ',', ';', '.', '*', '-'}

    # ── Caracteres que se ignoran silenciosamente (no producen token) ─────────
    # Espacios, tabuladores y retorno de carro se descartan sin avisar.
    # Los saltos de línea (\n) NO están aquí porque se tratan aparte para contar líneas.
    ignore = ' \t\r'

    # ── Operadores de dos caracteres ──────────────────────────────────────────
    # DEBEN definirse ANTES que los literales de un carácter '<' y '>'.
    # Si no, el lexer vería '<' primero y nunca llegaría a reconocer '<='.
    NEQ = r'!='   # distinto
    LE  = r'<='   # menor o igual
    GE  = r'>='   # mayor o igual

    # ── Variables de sesión: @nombre ──────────────────────────────────────────
    # El @ forma parte del token y se conserva tal cual en el AST.
    # Ej: @precio_min -> token VARIABLE con value='@precio_min'
    VARIABLE = r'@[a-zA-Z_][a-zA-Z0-9_]*'

    # ── Números ───────────────────────────────────────────────────────────────
    # FLOAT debe ir ANTES que INTEGER. Si fuera al revés, "3.14" produciría
    # el token INTEGER(3) seguido de un error al ver ".14".
    FLOAT   = r'\d+\.\d+'   # uno o más dígitos, punto, uno o más dígitos
    INTEGER = r'\d+'         # uno o más dígitos

    # ── Cadenas de texto ──────────────────────────────────────────────────────
    # El decorador @_ indica que esta función ES la regla del token STRING.
    # Acepta comillas dobles o simples, y admite secuencias de escape (\n, \", etc.)
    @_(r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'')
    def STRING(self, t):
        # Elimina las comillas del principio y del final del valor.
        # Ej: '"Ana"'  ->  t.value = 'Ana'
        t.value = t.value[1:-1]
        return t

    # ── Identificadores y palabras clave ──────────────────────────────────────
    # Esta regla captura cualquier secuencia de letras/dígitos/guión_bajo.
    # Luego comprueba si es una palabra clave (SELECT, FROM, etc.) o un identificador normal.
    @_(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def ID(self, t):
        # Diccionario de palabras clave → tipo de token.
        keywords = {
            'CREATE': 'CREATE', 'TABLE': 'TABLE',
            'INSERT': 'INSERT', 'INTO':  'INTO',  'VALUES': 'VALUES',
            'SELECT': 'SELECT', 'FROM':  'FROM',  'WHERE':  'WHERE',
            'JOIN':   'JOIN',   'ON':    'ON',
            'ORDER':  'ORDER',  'BY':    'BY',
            'ASC':    'ASC',    'DESC':  'DESC',
            'SET':    'SET',
            'AND':    'AND',    'OR':    'OR',    'NOT': 'NOT',
            'TRUE':   'TRUE',   'FALSE': 'FALSE', 'NULL': 'NULL',
        }
        # .upper() hace la búsqueda insensible a mayúsculas:
        # 'select', 'SELECT' y 'Select' producen el mismo token SELECT.
        # Si no está en el diccionario, es un identificador normal (ID).
        t.type = keywords.get(t.value.upper(), 'ID')
        return t

    # ── Saltos de línea ───────────────────────────────────────────────────────
    # No produce token (no hay return), solo actualiza el contador de línea.
    # self.lineno es el atributo interno de SLY que rastrea la línea actual.
    # len(t.value) permite contar varios \n seguidos de golpe.
    @_(r'\n+')
    def NEWLINE(self, t):
        self.lineno += len(t.value)

    # ── Comentarios de una línea: -- texto ────────────────────────────────────
    # Consume todo desde '--' hasta el final de la línea y lo descarta (pass).
    # No produce token ni actualiza lineno porque el \n final lo captura NEWLINE.
    @_(r'--[^\n]*')
    def LINE_COMMENT(self, t):
        pass

    # ── Comentarios de bloque: /* texto */ ────────────────────────────────────
    # El '?' hace el '*' no codicioso: para en el primer '*/' que encuentre,
    # no en el último (sin '?' consumiría todo hasta el último '*/' del archivo).
    # Como el bloque puede tener saltos de línea dentro, hay que contarlos
    # manualmente para mantener self.lineno correcto.
    @_(r'/\*(.|\n)*?\*/')
    def BLOCK_COMMENT(self, t):
        self.lineno += t.value.count('\n')

    # ── Manejo de errores léxicos ─────────────────────────────────────────────
    # Se llama automáticamente cuando el lexer encuentra un carácter que no
    # encaja con ninguna regla. Imprime un aviso y avanza un carácter (self.index += 1)
    # para no quedarse atascado en un bucle infinito.
    def error(self, t):
        print(f'[Error léxico] línea {self.lineno}: carácter desconocido {t.value[0]!r}')
        self.index += 1
