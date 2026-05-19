# El intérprete es la fase final: recibe el AST y lo ejecuta.
# Patrón usado: tree-walking interpreter — recorre el árbol nodo a nodo
# y ejecuta cada uno directamente, sin compilar a bytecode ni a otro lenguaje.

from clases import (
    Programa, CreateTable, InsertInto, Select, SetVariable,
    JoinClause, OrderBy,
    ExprBinOp, ExprUnOp, ColRef, ExprVariable, ExprLiteral,
)
from ambito import AmbitoSQL, ErrorSQL


# ─── Base de datos en memoria ──────────────────────────────────────────────────

class BaseDatos:
    """
    Almacena las tablas como diccionarios en memoria.
    Estructura: { nombre_tabla: { 'columnas': [...], 'filas': [...] } }
    Cada fila es un dict { nombre_col: valor }.
    """

    def __init__(self):
        # Diccionario principal: clave = nombre de tabla, valor = dict con columnas y filas.
        # Ej: {'empleados': {'columnas': ['id','nombre'], 'filas': [{'id':1,'nombre':'Ana'}]}}
        self.tablas = {}

    def crear_tabla(self, nombre, columnas):
        if nombre in self.tablas:
            # No se permite crear dos tablas con el mismo nombre.
            raise ErrorSQL(f"La tabla '{nombre}' ya existe")
        # Crea la entrada con lista de columnas vacía de filas.
        self.tablas[nombre] = {'columnas': list(columnas), 'filas': []}

    def insertar(self, nombre, valores):
        if nombre not in self.tablas:
            raise ErrorSQL(f"La tabla '{nombre}' no existe")
        tabla = self.tablas[nombre]
        ncols = len(tabla['columnas'])
        if len(valores) != ncols:
            # El número de valores debe coincidir exactamente con el número de columnas.
            raise ErrorSQL(
                f"INSERT en '{nombre}': se esperaban {ncols} valores, "
                f"se recibieron {len(valores)}")
        # zip empareja cada columna con su valor y dict() lo convierte en fila.
        # Ej: zip(['id','nombre'], [1,'Ana']) → {'id':1, 'nombre':'Ana'}
        fila = dict(zip(tabla['columnas'], valores))
        tabla['filas'].append(fila)

    def obtener(self, nombre):
        if nombre not in self.tablas:
            raise ErrorSQL(f"La tabla '{nombre}' no existe")
        # Devuelve el dict completo: {'columnas': [...], 'filas': [...]}
        return self.tablas[nombre]


# ─── Intérprete SQL ────────────────────────────────────────────────────────────

class InterpretadorSQL:
    """
    Intérprete de árbol (tree-walking interpreter) para MiniSQL.

    Mantiene dos estructuras de estado:
      · bd      — la base de datos en memoria (tablas y filas)
      · ambito  — ámbito de sesión (AmbitoSQL) que almacena las
                  variables @usuario declaradas con SET.

    Para cada SELECT se crea un ámbito de consulta hijo del de sesión,
    siguiendo el mismo patrón de scope chain que las prácticas del curso.
    """

    def __init__(self):
        self.bd     = BaseDatos()            # base de datos vacía en RAM
        self.ambito = AmbitoSQL(nombre='sesion')  # ámbito raíz de variables @

    def ejecutar(self, programa):
        # Recorre la lista de sentencias del nodo Programa y ejecuta cada una.
        for sent in programa.sentencias:
            self._ejecutar(sent)

    # ── Dispatcher de sentencias ───────────────────────────────────────────────

    def _ejecutar(self, sent):
        # Comprueba el tipo del nodo con 'is' (más rápido que isinstance)
        # y delega a la función correspondiente.
        t = type(sent)
        if t is CreateTable:
            self._create_table(sent)
        elif t is InsertInto:
            self._insert_into(sent)
        elif t is SetVariable:
            self._set_variable(sent)
        elif t is Select:
            self._select(sent)
        else:
            raise ErrorSQL(f"Sentencia desconocida: {t.__name__}", sent.linea)

    def _create_table(self, sent):
        self.bd.crear_tabla(sent.nombre, sent.columnas)
        cols = ', '.join(sent.columnas)
        print(f"Tabla '{sent.nombre}' creada  ({cols})")

    def _insert_into(self, sent):
        # Desenvuelve los nodos ExprLiteral para obtener los valores Python reales.
        # sent.valores es lista de ExprLiteral; .valor da el int/str/bool/None.
        valores = [v.valor for v in sent.valores]
        self.bd.insertar(sent.tabla, valores)
        print(f"1 fila insertada en '{sent.tabla}'")

    def _set_variable(self, sent):
        # Crea un ámbito hijo temporal solo para evaluar la expresión del lado derecho.
        # La fila está vacía ({}) porque SET no opera sobre filas de tabla.
        ambito_eval = AmbitoSQL(padre=self.ambito, nombre='set-expr')
        valor = self._evaluar(sent.valor, {}, ambito_eval)
        # Guarda el resultado en el ámbito de SESIÓN (no en el hijo temporal).
        self.ambito.asignar(sent.nombre, valor)
        print(f"Variable {sent.nombre} = {_fmt(valor)}")

    def _select(self, sent):
        # Crea un ámbito hijo del de sesión para esta consulta.
        # Las @variables definidas con SET son visibles aquí gracias a la cadena de ámbitos.
        ambito_consulta = AmbitoSQL(padre=self.ambito, nombre='consulta')

        # Obtiene el dict de la tabla principal: {'columnas': [...], 'filas': [...]}
        info = self.bd.obtener(sent.tabla)

        # PASO 1 — Calificar filas: añade claves 'tabla.col' junto a las claves simples 'col'.
        # Necesario para que WHERE pueda usar tanto 'nombre' como 'empleados.nombre'.
        filas = _calificar(sent.tabla, info['filas'])

        # PASO 2 — JOIN: si hay cláusula JOIN, combina las filas de las dos tablas.
        if sent.join is not None:
            filas = self._join(filas, sent.join)

        # PASO 3 — WHERE: filtra las filas evaluando la condición sobre cada una.
        # Solo pasan las filas para las que _evaluar devuelve True (o truthy).
        if sent.where is not None:
            filas = [f for f in filas
                     if self._evaluar(sent.where, f, ambito_consulta)]

        # PASO 4 — ORDER BY: ordena la lista de filas.
        if sent.order_by is not None:
            clave = _resolver_clave(sent.order_by.columna, filas)
            desc  = (sent.order_by.direccion == 'DESC')
            # La clave de orden es una tupla (es_null, valor):
            # · es_null=False < es_null=True → los no-nulos van antes en ASC.
            # · reverse=True (DESC) invierte el orden completo.
            filas.sort(
                key=lambda f: (f.get(clave) is None, f.get(clave)),
                reverse=desc,
            )

        # PASO 5 — Proyección: selecciona solo las columnas pedidas.
        cabeceras, filas_out = self._proyectar(
            sent.columnas, sent.tabla, sent.join, filas, ambito_consulta)

        # Imprime la tabla resultante con formato de cuadrícula.
        _imprimir(cabeceras, filas_out)

    # ── JOIN ───────────────────────────────────────────────────────────────────

    def _join(self, filas_izq, jc):
        # Obtiene y califica las filas de la tabla derecha.
        info_der  = self.bd.obtener(jc.tabla)
        filas_der = _calificar(jc.tabla, info_der['filas'])
        resultado = []
        # Producto cartesiano: combina cada fila izquierda con cada fila derecha.
        for fi in filas_izq:
            for fd in filas_der:
                # Evalúa los dos lados del ON para ver si las filas coinciden.
                vi = self._col(jc.on_izq, fi)
                vd = self._col(jc.on_der, fd)
                if vi == vd:
                    # Las filas coinciden: las fusiona en una sola con {**fi, **fd}.
                    # Si ambas tienen una clave igual, la de fd sobreescribe a la de fi.
                    resultado.append({**fi, **fd})
        return resultado

    # ── Proyección ─────────────────────────────────────────────────────────────

    def _proyectar(self, columnas, tabla_princ, join_clause, filas, ambito):
        if columnas == '*':
            # SELECT *: toma todas las columnas de la tabla principal.
            cols = list(self.bd.obtener(tabla_princ)['columnas'])
            if join_clause is not None:
                # Si hay JOIN, añade también las columnas de la tabla secundaria,
                # evitando duplicados (si ambas tablas tienen 'id', solo aparece una vez).
                for c in self.bd.obtener(join_clause.tabla)['columnas']:
                    if c not in cols:
                        cols.append(c)
            # Construye la lista de filas de salida con solo esas columnas.
            filas_out = [{c: f.get(c) for c in cols} for f in filas]
            return cols, filas_out

        # SELECT col1, col2, @var: construye la cabecera a partir de los items pedidos.
        cabeceras = []
        for item in columnas:
            if type(item) is ColRef:
                # 'tabla.columna' si está calificado, 'columna' si no.
                cabeceras.append(
                    f'{item.tabla}.{item.columna}' if item.tabla else item.columna)
            else:  # ExprVariable
                cabeceras.append(item.nombre)  # Ej: '@precio_min'

        # Construye las filas de salida evaluando cada item para cada fila.
        filas_out = []
        for f in filas:
            fila_out = {}
            for item, h in zip(columnas, cabeceras):
                if type(item) is ColRef:
                    # Resuelve la columna dentro de la fila.
                    fila_out[h] = self._col(item, f)
                else:  # ExprVariable — su valor es igual en todas las filas
                    fila_out[h] = self._evaluar(item, f, ambito)
            filas_out.append(fila_out)
        return cabeceras, filas_out

    # ── Evaluación de expresiones ──────────────────────────────────────────────

    def _evaluar(self, expr, fila, ambito):
        """
        Evalúa una expresión en el contexto de una fila y un ámbito.
        Es recursiva: ExprBinOp llama a _evaluar sobre sus hijos izq y der.
        La búsqueda de variables sube por la cadena de ámbitos (scope chain).
        """
        t = type(expr)

        if t is ExprLiteral:
            # Caso base: devuelve el valor Python directamente.
            # Ej: ExprLiteral(42) → 42
            return expr.valor

        if t is ColRef:
            # Busca el valor de la columna dentro del dict de la fila actual.
            return self._col(expr, fila)

        if t is ExprVariable:
            # Busca la @variable en el ámbito (sube por la cadena si hace falta).
            return ambito.obtener(expr.nombre, expr.linea)

        if t is ExprUnOp and expr.op == 'NOT':
            # Evalúa el operando y niega el resultado.
            return not self._evaluar(expr.operando, fila, ambito)

        if t is ExprBinOp:
            op = expr.op

            if op == 'AND':
                # Cortocircuito: si el izquierdo es falso, el derecho nunca se evalúa.
                return (self._evaluar(expr.izq, fila, ambito) and
                        self._evaluar(expr.der, fila, ambito))
            if op == 'OR':
                # Cortocircuito: si el izquierdo es verdadero, el derecho nunca se evalúa.
                return (self._evaluar(expr.izq, fila, ambito) or
                        self._evaluar(expr.der, fila, ambito))

            # Para el resto de operadores hay que evaluar los dos lados primero.
            izq = self._evaluar(expr.izq, fila, ambito)
            der = self._evaluar(expr.der, fila, ambito)

            # Comparaciones: devuelven True o False.
            # = y != usan == y != de Python directamente (funcionan con None).
            # El resto usan _cmp() que maneja NULL de forma segura.
            if op == '=':  return izq == der
            if op == '!=': return izq != der
            if op == '<':  return _cmp(izq, der) < 0
            if op == '<=': return _cmp(izq, der) <= 0
            if op == '>':  return _cmp(izq, der) > 0
            if op == '>=': return _cmp(izq, der) >= 0

        raise ErrorSQL(f"Expresión no soportada: {type(expr).__name__}")

    # ── Resolución de columna en una fila ──────────────────────────────────────

    def _col(self, col_ref, fila):
        # Si la columna tiene prefijo de tabla, busca primero la clave calificada.
        # Ej: col_ref.tabla='empleados', col_ref.columna='nombre' → busca 'empleados.nombre'
        if col_ref.tabla:
            key = f'{col_ref.tabla}.{col_ref.columna}'
            if key in fila:
                return fila[key]
        # Si no tiene prefijo (o no encontró la clave calificada), busca la simple.
        if col_ref.columna in fila:
            return fila[col_ref.columna]
        raise ErrorSQL(f"Columna '{col_ref.columna}' no encontrada en la fila")


# ─── Funciones auxiliares ──────────────────────────────────────────────────────

def _calificar(nombre_tabla, filas_raw):
    """Añade clave 'tabla.col' junto a la clave simple 'col' en cada fila."""
    resultado = []
    for fila in filas_raw:
        # Copia la fila original para no modificarla.
        nueva = dict(fila)
        # Añade una clave extra 'tabla.col' por cada columna.
        # Ej: fila {'id':1} de tabla 'empleados' → {'id':1, 'empleados.id':1}
        for col, val in fila.items():
            nueva[f'{nombre_tabla}.{col}'] = val
        resultado.append(nueva)
    return resultado


def _resolver_clave(col_ref, filas):
    # Determina qué clave del dict de fila usar para ordenar.
    # Prefiere la clave calificada ('tabla.col') si existe, si no usa la simple.
    if not filas:
        return col_ref.columna
    key_cal = f'{col_ref.tabla}.{col_ref.columna}' if col_ref.tabla else None
    if key_cal and key_cal in filas[0]:
        return key_cal
    return col_ref.columna


def _cmp(a, b):
    """Comparación segura que trata NULL como menor que todo."""
    # Necesaria porque Python no puede comparar None con int/str directamente.
    if a is None and b is None:
        return 0   # NULL = NULL
    if a is None:
        return -1  # NULL < cualquier cosa
    if b is None:
        return 1   # cualquier cosa > NULL
    # Truco Python para comparación de tres vías: da -1, 0 o 1.
    # Funciona porque True y False son 1 y 0 en Python.
    return (a > b) - (a < b)


def _fmt(val):
    # Convierte un valor Python al string que se muestra en la tabla de resultados.
    if val is None:
        return 'NULL'
    if isinstance(val, bool):
        # bool debe ir ANTES que int porque en Python bool es subclase de int.
        # Si no, True se mostraría como '1' en vez de 'TRUE'.
        return 'TRUE' if val else 'FALSE'
    return str(val)


def _imprimir(cabeceras, filas):
    # Imprime los resultados en formato de tabla con bordes: +-----+-----+
    if not cabeceras:
        print('(sin columnas)')
        return

    # Calcula el ancho máximo de cada columna (el mayor entre el header y los datos).
    anchos = {c: len(c) for c in cabeceras}
    for fila in filas:
        for c in cabeceras:
            anchos[c] = max(anchos[c], len(_fmt(fila.get(c))))

    # Línea separadora: +-------+-------+
    sep    = '+' + '+'.join('-' * (anchos[c] + 2) for c in cabeceras) + '+'
    # Línea de cabecera: | col1  | col2  |
    header = '|' + '|'.join(f' {c:<{anchos[c]}} ' for c in cabeceras) + '|'

    print(sep)
    print(header)
    print(sep)
    for fila in filas:
        # Cada fila de datos: | valor1 | valor2 |
        # :<{ancho} alinea el texto a la izquierda con el ancho calculado.
        row = '|' + '|'.join(
            f' {_fmt(fila.get(c)):<{anchos[c]}} ' for c in cabeceras) + '|'
        print(row)
    print(sep)
    # Resumen final: (3 filas) o (1 fila)
    n = len(filas)
    print(f'({n} fila{"s" if n != 1 else ""})\n')
