-- TEST 06: Valores NULL
-- Verifica el manejo de NULL en datos y en comparaciones.

CREATE TABLE proyectos (id, nombre, responsable, presupuesto, completado);

INSERT INTO proyectos VALUES (1, 'AlphaBot',  'Ana',   120000, TRUE);
INSERT INTO proyectos VALUES (2, 'BetaWeb',   'Carlos', 45000, FALSE);
INSERT INTO proyectos VALUES (3, 'GammaAI',   NULL,    200000, FALSE);
INSERT INTO proyectos VALUES (4, 'DeltaApp',  'Maria',   NULL, TRUE);
INSERT INTO proyectos VALUES (5, 'EpsilonDB', NULL,     80000, TRUE);

-- Ver todos los proyectos (NULL se muestra como NULL)
SELECT * FROM proyectos;

-- Filtrar proyectos completados
SELECT nombre, responsable FROM proyectos WHERE completado = TRUE;

-- Filtrar los que tienen presupuesto definido (no NULL)
-- NULL > 0 devuelve false, por lo que estos se excluyen correctamente
SELECT nombre, presupuesto FROM proyectos WHERE presupuesto > 0;

-- ORDER BY con NULL: los NULL van primero (menor que todo)
SELECT nombre, presupuesto FROM proyectos ORDER BY presupuesto;
SELECT nombre, presupuesto FROM proyectos ORDER BY presupuesto DESC;
