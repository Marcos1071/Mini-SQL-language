# Nodos del AST (Abstract Syntax Tree) para MiniSQL.
# Cada clase representa un tipo de construcción del lenguaje SQL.
# Estas clases son contenedores de datos puros — no tienen lógica de ejecución,
# eso está en interprete.py. El parser (parser.py) crea estos objetos,
# y el intérprete (interprete.py) los recorre para ejecutarlos.


class Nodo:
    # Clase base de la que heredan TODOS los nodos del árbol.
    def __init__(self, linea=0):
        # Guarda el número de línea del código fuente donde aparece este nodo.
        # Se usa para mostrar mensajes de error con ubicación exacta.
        # Por defecto es 0 porque en tests o nodos creados manualmente no hay línea real.
        self.linea = linea


class Programa(Nodo):
    # Nodo raíz del árbol. Representa el archivo SQL completo.
    def __init__(self, sentencias, linea=0):
        super().__init__(linea)  # llama al constructor de Nodo para guardar self.linea
        # Lista de nodos-sentencia en orden de aparición en el fichero.
        # Puede contener: CreateTable, InsertInto, Select, SetVariable.
        # Ejemplo: un .sql con 3 sentencias → self.sentencias tiene 3 elementos.
        self.sentencias = sentencias


# ═══ Sentencias SQL ════════════════════════════════════════════════════════════

class CreateTable(Nodo):
    """CREATE TABLE nombre (col1, col2, ...);"""
    def __init__(self, nombre, columnas, linea=0):
        super().__init__(linea)
        # Nombre de la tabla a crear. Ej: 'empleados'
        self.nombre   = nombre
        # Lista de strings con los nombres de columna. Ej: ['id', 'nombre', 'salario']
        # En MiniSQL las columnas NO tienen tipo (no hay INTEGER, VARCHAR...), solo nombre.
        self.columnas = columnas     # list[str]


class InsertInto(Nodo):
    """INSERT INTO nombre VALUES (v1, v2, ...);"""
    def __init__(self, tabla, valores, linea=0):
        super().__init__(linea)
        # Nombre de la tabla donde se inserta. Ej: 'empleados'
        self.tabla   = tabla
        # Lista de nodos ExprLiteral con los valores a insertar.
        # Son nodos del AST, no valores Python directos — el intérprete los
        # desenvuelve con v.valor cuando los necesita.
        # Ej: INSERT INTO t VALUES (1, 'Ana') → [ExprLiteral(1), ExprLiteral('Ana')]
        self.valores = valores       # list[ExprLiteral]


class Select(Nodo):
    """SELECT cols FROM tabla [JOIN ...] [WHERE expr] [ORDER BY col [ASC|DESC]];"""
    def __init__(self, columnas, tabla, join=None, where=None, order_by=None, linea=0):
        super().__init__(linea)
        # Columnas a proyectar. Hay dos casos posibles:
        #   · La string '*'                    → SELECT *
        #   · Lista de ColRef / ExprVariable   → SELECT nombre, salario, @var
        self.columnas  = columnas    # list[ColRef | ExprVariable]  o  la cadena '*'
        # Nombre de la tabla principal (la que va después del FROM).
        self.tabla     = tabla       # str
        # Cláusula JOIN opcional. Es un nodo JoinClause o None si no hay JOIN.
        self.join      = join        # JoinClause | None
        # Condición WHERE opcional. Es un nodo de expresión (ExprBinOp, etc.) o None.
        self.where     = where       # Expr | None
        # Cláusula ORDER BY opcional. Es un nodo OrderBy o None si no hay ordenación.
        self.order_by  = order_by    # OrderBy | None


class SetVariable(Nodo):
    """SET @nombre = expr;"""
    def __init__(self, nombre, valor, linea=0):
        super().__init__(linea)
        # Nombre de la variable de sesión, incluyendo el '@'.
        # Ej: SET @precio_min = 100  →  self.nombre = '@precio_min'
        # El '@' viaja así desde el lexer hasta el ámbito sin eliminarse nunca.
        self.nombre = nombre         # str  (incluye el '@')
        # Expresión del lado derecho. Para SET @x = 100 es ExprLiteral(100).
        self.valor  = valor          # Expr


class JoinClause(Nodo):
    """JOIN tabla ON izq = der"""
    # No es una sentencia independiente: siempre vive dentro de Select.join.
    def __init__(self, tabla, on_izq, on_der, linea=0):
        super().__init__(linea)
        # Nombre de la segunda tabla que se une. Ej: 'departamentos'
        self.tabla   = tabla         # str
        # ColRef del lado izquierdo del ON. Ej: empleados.dept_id
        self.on_izq  = on_izq        # ColRef
        # ColRef del lado derecho del ON. Ej: departamentos.id
        self.on_der  = on_der        # ColRef


class OrderBy(Nodo):
    # No es una sentencia independiente: siempre vive dentro de Select.order_by.
    def __init__(self, columna, direccion='ASC', linea=0):
        super().__init__(linea)
        # La columna por la que se ordena, como nodo ColRef.
        self.columna   = columna     # ColRef
        # Dirección del orden: 'ASC' (ascendente) o 'DESC' (descendente).
        # El valor por defecto es 'ASC' porque en SQL si no escribes nada el orden
        # es ascendente: ORDER BY salario  ≡  ORDER BY salario ASC
        self.direccion = direccion   # 'ASC' | 'DESC'


# ═══ Expresiones ══════════════════════════════════════════════════════════════
# Las expresiones son nodos que producen un valor cuando el intérprete los evalúa.
# Aparecen en WHERE, en el lado derecho de SET, y como columnas en SELECT.
# Se forman en árbol: ExprBinOp puede contener otros ExprBinOp como hijos.

class ExprBinOp(Nodo):
    """Operador binario: AND, OR, =, !=, <, <=, >, >="""
    # Un único nodo sirve para TODOS los operadores binarios; el campo op distingue cuál es.
    def __init__(self, op, izq, der, linea=0):
        super().__init__(linea)
        # String con el operador. Valores posibles: 'AND','OR','=','!=','<','<=','>','>='
        self.op  = op
        # Nodo del operando izquierdo. Puede ser cualquier expresión (incluso otro ExprBinOp).
        self.izq = izq
        # Nodo del operando derecho. Igual que izq.
        self.der = der
        # Ejemplo: salario > 65000 AND dept_id = 1  se representa como:
        #   ExprBinOp('AND',
        #       izq = ExprBinOp('>', ColRef('salario'), ExprLiteral(65000)),
        #       der = ExprBinOp('=', ColRef('dept_id'), ExprLiteral(1))
        #   )
        # El intérprete lo evalúa de forma recursiva.


class ExprUnOp(Nodo):
    """Operador unario: NOT"""
    # Operador con un solo operando. En MiniSQL solo existe NOT.
    def __init__(self, op, operando, linea=0):
        super().__init__(linea)
        # String con el operador. En MiniSQL solo puede ser 'NOT'.
        self.op       = op
        # Nodo sobre el que se aplica el NOT.
        # Ej: NOT activo = TRUE  →  ExprUnOp('NOT', ExprBinOp('=', ColRef('activo'), ExprLiteral(True)))
        self.operando = operando


class ColRef(Nodo):
    """Referencia a columna de tabla: [tabla.]columna"""
    # Representa mencionar el nombre de una columna en el SQL.
    # Puede ser simple (nombre) o calificada con tabla (empleados.nombre).
    def __init__(self, columna, tabla=None, linea=0):
        super().__init__(linea)
        # Prefijo de tabla, o None si no se escribió.
        # Ej: 'nombre'            →  tabla=None
        # Ej: 'empleados.nombre'  →  tabla='empleados'
        self.tabla   = tabla         # str | None
        # Nombre de la columna, siempre presente.
        self.columna = columna       # str


class ExprVariable(Nodo):
    """Variable de sesión: @nombre"""
    # Representa el USO de una variable @var en una expresión.
    # Cuando el intérprete encuentra este nodo busca el nombre en el ámbito SQL.
    def __init__(self, nombre, linea=0):
        super().__init__(linea)
        # Nombre de la variable incluyendo el '@'.
        # Ej: WHERE precio > @precio_min  →  ExprVariable(nombre='@precio_min')
        self.nombre = nombre         # str  (incluye el '@')


class ExprLiteral(Nodo):
    """Valor literal: entero, flotante, cadena, booleano o NULL"""
    # Es el caso base de la recursión del intérprete: cuando llega aquí
    # simplemente devuelve self.valor sin evaluar nada más.
    def __init__(self, valor, linea=0):
        super().__init__(linea)
        # El valor Python correspondiente al literal SQL:
        #   42      →  int
        #   3.14    →  float
        #   'Ana'   →  str
        #   TRUE    →  True  (bool)
        #   FALSE   →  False (bool)
        #   NULL    →  None
        self.valor = valor
