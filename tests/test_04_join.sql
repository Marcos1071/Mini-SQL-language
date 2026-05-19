-- TEST 04: JOIN
-- Verifica el INNER JOIN entre dos tablas.

CREATE TABLE departamentos (id, nombre, ciudad);
CREATE TABLE empleados (id, nombre, dept_id, salario);

INSERT INTO departamentos VALUES (1, 'Ingenieria', 'Madrid');
INSERT INTO departamentos VALUES (2, 'Marketing',  'Barcelona');
INSERT INTO departamentos VALUES (3, 'RRHH',       'Sevilla');

INSERT INTO empleados VALUES (1, 'Ana',    1, 75000);
INSERT INTO empleados VALUES (2, 'Carlos', 2, 60000);
INSERT INTO empleados VALUES (3, 'Maria',  1, 80000);
INSERT INTO empleados VALUES (4, 'Luis',   3, 55000);
INSERT INTO empleados VALUES (5, 'Elena',  1, 70000);

-- JOIN básico: empleados con su departamento
SELECT empleados.nombre, departamentos.nombre, departamentos.ciudad
    FROM empleados
    JOIN departamentos ON empleados.dept_id = departamentos.id;

-- JOIN con WHERE: solo empleados de Ingenieria
SELECT empleados.nombre, empleados.salario
    FROM empleados
    JOIN departamentos ON empleados.dept_id = departamentos.id
    WHERE departamentos.nombre = 'Ingenieria';

-- JOIN con WHERE y ORDER BY
SELECT empleados.nombre, departamentos.nombre, empleados.salario
    FROM empleados
    JOIN departamentos ON empleados.dept_id = departamentos.id
    WHERE empleados.salario > 60000
    ORDER BY empleados.salario DESC;
