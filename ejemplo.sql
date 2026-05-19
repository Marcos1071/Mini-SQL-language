-- ============================================================
--  MiniSQL — fichero de ejemplo
-- ============================================================

-- 1. Crear tablas
CREATE TABLE departamentos (id, nombre);
CREATE TABLE empleados (id, nombre, dept_id, salario);

-- 2. Poblar departamentos
INSERT INTO departamentos VALUES (1, 'Ingenieria');
INSERT INTO departamentos VALUES (2, 'Marketing');
INSERT INTO departamentos VALUES (3, 'RRHH');

-- 3. Poblar empleados
INSERT INTO empleados VALUES (1, 'Ana',    1, 75000);
INSERT INTO empleados VALUES (2, 'Carlos', 2, 60000);
INSERT INTO empleados VALUES (3, 'Maria',  1, 80000);
INSERT INTO empleados VALUES (4, 'Luis',   3, 55000);
INSERT INTO empleados VALUES (5, 'Elena',  1, 70000);
INSERT INTO empleados VALUES (6, 'Pedro',  2, 62000);

-- 4. SELECT simple: todos los empleados
SELECT * FROM empleados;

-- 5. Filtro con WHERE
SELECT nombre, salario FROM empleados WHERE salario > 65000;

-- 6. ORDER BY descendente
SELECT nombre, salario FROM empleados ORDER BY salario DESC;

-- 7. WHERE compuesto con AND
SELECT nombre, salario FROM empleados
    WHERE dept_id = 1 AND salario >= 75000;

-- 8. JOIN: empleados con su departamento
SELECT empleados.nombre, departamentos.nombre, empleados.salario
    FROM empleados
    JOIN departamentos ON empleados.dept_id = departamentos.id;

-- 9. JOIN + WHERE + ORDER BY
SELECT empleados.nombre, departamentos.nombre, empleados.salario
    FROM empleados
    JOIN departamentos ON empleados.dept_id = departamentos.id
    WHERE departamentos.id = 1
    ORDER BY empleados.salario DESC;

-- 10. Valores nulos y booleanos
CREATE TABLE proyectos (id, titulo, activo, presupuesto);
INSERT INTO proyectos VALUES (1, 'AlphaBot', TRUE,  120000);
INSERT INTO proyectos VALUES (2, 'BetaWeb',  FALSE, 45000);
INSERT INTO proyectos VALUES (3, 'GammaAI', TRUE,  NULL);

SELECT * FROM proyectos WHERE activo = TRUE;
