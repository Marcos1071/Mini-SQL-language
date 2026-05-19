# Gestión de ámbitos (scope) para MiniSQL.
#
# Un ámbito es un diccionario de variables con una referencia a su padre.
# Cuando buscas una variable, miras en el diccionario local y si no está
# subes al padre, y así hasta llegar a la raíz.
#
# En MiniSQL hay dos niveles:
#   sesion   → ámbito raíz, vive todo el programa, guarda las @variables de SET
#   consulta → hijo de sesion, creado por cada SELECT, destruido al terminar


class ErrorSQL(Exception):
    # Excepción personalizada para errores en tiempo de ejecución de MiniSQL.
    def __init__(self, mensaje, linea=0):
        super().__init__(mensaje)  # pasa el mensaje a Exception para que str(e) lo devuelva
        # Guarda la línea donde ocurrió el error, para mostrársela al usuario.
        self.linea = linea


class AmbitoSQL:
    """
    Entorno de variables de sesión SQL.

    Implementa la misma arquitectura de cadena de ámbitos (scope chain)
    usada en intérpretes imperativos: cada ámbito tiene una referencia
    a su padre y la búsqueda de variables sube por la cadena.

    En MiniSQL existen dos niveles:
      · sesion  — ámbito raíz; contiene las variables @usuario declaradas
                  con SET a lo largo de toda la sesión interactiva.
      · consulta — hijo del ámbito de sesión; creado para cada SELECT y
                   destruido al terminar la consulta.  Permite que futuras
                   extensiones (sub-consultas, CTEs) tengan su propio espacio
                   sin contaminar la sesión.

    La interfaz (definir / obtener / asignar / existe) es idéntica a la
    del Ambito del intérprete imperativo visto en las prácticas, lo que
    demuestra que el patrón es independiente del paradigma del lenguaje.
    """

    def __init__(self, padre=None, nombre='sesion'):
        self._vars  = {}      # diccionario local de este ámbito: { '@nombre': valor }
        self.padre  = padre   # referencia al ámbito padre, o None si es la raíz
        self.nombre = nombre  # nombre descriptivo para depuración ('sesion', 'consulta')

    # ── definir: siempre crea la variable en el ámbito ACTUAL ─────────────────

    def definir(self, nombre, valor):
        # Escribe directamente en el diccionario local, sin mirar al padre.
        # Se usa cuando queremos forzar que la variable viva en este nivel.
        self._vars[nombre] = valor

    # ── obtener: busca subiendo por la cadena hasta encontrar la variable ──────

    def obtener(self, nombre, linea=0):
        if nombre in self._vars:
            # La encontró en este ámbito -> la devuelve directamente.
            return self._vars[nombre]
        if self.padre is not None:
            # No está aquí -> sube al padre y repite la búsqueda (recursión).
            return self.padre.obtener(nombre, linea)
        # Llegó a la raíz (padre=None) y no la encontró en ningún lado -> error.
        raise ErrorSQL(
            f"Variable '{nombre}' no definida — usa SET para inicializarla",
            linea)

    # ── asignar: modifica donde fue definida, o crea en el ámbito actual ──────

    def asignar(self, nombre, valor, linea=0):
        if nombre in self._vars:
            # Existe en este ámbito -> la modifica aquí mismo.
            self._vars[nombre] = valor
            return
        if self.padre is not None and self.padre.existe(nombre):
            # No está aquí pero sí en algún padre -> delega la modificación al padre.
            # Así SET @x = 200 actualiza @x donde fue creada, no crea una copia local.
            self.padre.asignar(nombre, valor, linea)
            return
        # No existe en ningún lado -> la crea en el ámbito actual.
        # Esta es la semántica de SQL: SET crea la variable si no existía.
        self._vars[nombre] = valor

    # ── existe: comprueba si una variable es visible desde este ámbito ────────

    def existe(self, nombre):
        if nombre in self._vars:
            return True
        if self.padre is not None:
            # Busca recursivamente hacia arriba.
            return self.padre.existe(nombre)
        # Llegó a la raíz y no la encontró.
        return False

    # ── variables: devuelve todas las variables visibles (para depuración) ────

    def variables(self):
        # Empieza por las del padre (o dict vacío si es raíz) y luego
        # sobreescribe con las locales, igual que como funciona el scope chain:
        # las variables locales tapan a las del padre si tienen el mismo nombre.
        resultado = {} if self.padre is None else self.padre.variables()
        resultado.update(self._vars)
        return resultado

    def __repr__(self):
        # Representación útil para depuración: muestra el nombre y las claves locales.
        return f'AmbitoSQL({self.nombre}, vars={list(self._vars.keys())})'
