-- TEST 01: CREATE TABLE e INSERT INTO
-- Verifica que se pueden crear tablas e insertar filas correctamente.

CREATE TABLE productos (id, nombre, precio, stock);

INSERT INTO productos VALUES (1, 'Teclado',  49.99,  150);
INSERT INTO productos VALUES (2, 'Raton',    25.50,  200);
INSERT INTO productos VALUES (3, 'Monitor', 299.00,   40);
INSERT INTO productos VALUES (4, 'Auriculares', 79.95, 80);

-- Mostrar toda la tabla
SELECT * FROM productos;
