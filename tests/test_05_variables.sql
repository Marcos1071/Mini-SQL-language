-- TEST 05: Variables de sesión (gestión de ámbitos)
-- Demuestra SET @var y su uso en WHERE y SELECT.
-- Las variables persisten en el ámbito de sesión entre consultas.

CREATE TABLE productos (id, nombre, categoria, precio, stock);

INSERT INTO productos VALUES (1, 'Laptop',      'Electronica', 999.00, 20);
INSERT INTO productos VALUES (2, 'Teclado',     'Electronica',  49.99, 150);
INSERT INTO productos VALUES (3, 'Silla',       'Muebles',     199.00, 30);
INSERT INTO productos VALUES (4, 'Mesa',        'Muebles',     349.00, 15);
INSERT INTO productos VALUES (5, 'Auriculares', 'Electronica',  79.95, 80);
INSERT INTO productos VALUES (6, 'Lampara',     'Muebles',      45.00, 60);

-- Definir umbral de precio en el ámbito de sesión
SET @precio_min = 100;
SET @categoria  = 'Electronica';

-- Usar @precio_min en WHERE (se resuelve subiendo por la cadena de ámbitos)
SELECT nombre, precio FROM productos WHERE precio > @precio_min;

-- Usar @categoria en WHERE
SELECT nombre, precio FROM productos WHERE categoria = @categoria;

-- Combinar columnas y variables en el SELECT
SELECT nombre, precio, @precio_min FROM productos WHERE precio > @precio_min;

-- Reasignar la variable y repetir la consulta (el ámbito actualiza su valor)
SET @precio_min = 300;
SELECT nombre, precio FROM productos WHERE precio > @precio_min;

-- Variable booleana
SET @solo_caros = TRUE;
SELECT nombre, precio FROM productos WHERE precio > 200;
