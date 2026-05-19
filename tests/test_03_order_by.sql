-- TEST 03: ORDER BY
-- Verifica el ordenamiento ascendente y descendente.

CREATE TABLE libros (id, titulo, autor, anio, precio);

INSERT INTO libros VALUES (1, 'Don Quijote',       'Cervantes',    1605, 12.50);
INSERT INTO libros VALUES (2, 'Cien anios de soledad', 'Garcia Marquez', 1967, 15.00);
INSERT INTO libros VALUES (3, 'La Odisea',          'Homero',      -800, 10.00);
INSERT INTO libros VALUES (4, '1984',               'Orwell',      1949, 11.00);
INSERT INTO libros VALUES (5, 'El Principito',      'Saint Exupery', 1943, 9.50);

-- Ordenar por precio ascendente (por defecto)
SELECT titulo, precio FROM libros ORDER BY precio;

-- Ordenar por año descendente
SELECT titulo, anio FROM libros ORDER BY anio DESC;

-- WHERE + ORDER BY combinados
SELECT titulo, autor, precio FROM libros WHERE precio >= 11.00 ORDER BY precio DESC;
