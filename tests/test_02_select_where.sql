-- TEST 02: SELECT con WHERE
-- Verifica filtros simples y compuestos con AND/OR/NOT.

CREATE TABLE empleados (id, nombre, departamento, salario, activo);

INSERT INTO empleados VALUES (1, 'Ana',    'IT',      75000, TRUE);
INSERT INTO empleados VALUES (2, 'Carlos', 'Ventas',  60000, TRUE);
INSERT INTO empleados VALUES (3, 'Maria',  'IT',      80000, TRUE);
INSERT INTO empleados VALUES (4, 'Luis',   'RRHH',    55000, FALSE);
INSERT INTO empleados VALUES (5, 'Elena',  'IT',      70000, TRUE);
INSERT INTO empleados VALUES (6, 'Pedro',  'Ventas',  62000, FALSE);

-- Filtro simple
SELECT nombre, salario FROM empleados WHERE salario > 65000;

-- Filtro compuesto con AND
SELECT nombre, departamento FROM empleados WHERE departamento = 'IT' AND salario >= 75000;

-- Filtro con OR
SELECT nombre, salario FROM empleados WHERE salario < 60000 OR salario > 78000;

-- Filtro con NOT
SELECT nombre, activo FROM empleados WHERE NOT activo = TRUE;
