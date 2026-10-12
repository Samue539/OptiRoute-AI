-- ============================================================
-- OptiRoute AI
-- Datos de prueba para Matemáticas Discretas y Grafos
-- Idempotente: se puede ejecutar varias veces sin duplicar datos.
--   - logistica.nodos no tiene UNIQUE(nombre), por lo que cada nodo se
--     protege con WHERE NOT EXISTS (SELECT ... WHERE nombre = ...).
--   - logistica.conexiones sí tiene UNIQUE(id_nodo_origen, id_nodo_destino)
--     (uq_conexiones_origen_destino), por lo que cada arista se protege con
--     ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING.
-- No se modifican pesos, conexiones ni el grafo matemático: los valores son
-- exactamente los mismos que en la versión original de este script.
-- ============================================================


-- ------------------------------------------------------------
-- VERTICES DEL GRAFO
-- ------------------------------------------------------------

INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Bodega Principal', 'BODEGA', -0.200000, -78.500000
WHERE NOT EXISTS (
    SELECT 1 FROM logistica.nodos WHERE nombre = 'Bodega Principal'
);

INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Cliente A', 'CLIENTE', -0.205000, -78.495000
WHERE NOT EXISTS (
    SELECT 1 FROM logistica.nodos WHERE nombre = 'Cliente A'
);

INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Cliente B', 'CLIENTE', -0.210000, -78.490000
WHERE NOT EXISTS (
    SELECT 1 FROM logistica.nodos WHERE nombre = 'Cliente B'
);

INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Cliente C', 'CLIENTE', -0.215000, -78.500000
WHERE NOT EXISTS (
    SELECT 1 FROM logistica.nodos WHERE nombre = 'Cliente C'
);

INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Cliente D', 'CLIENTE', -0.220000, -78.505000
WHERE NOT EXISTS (
    SELECT 1 FROM logistica.nodos WHERE nombre = 'Cliente D'
);


-- ------------------------------------------------------------
-- ARISTAS DEL GRAFO
-- Cada arista se resuelve por nombre de nodo (no por ID fijo) para que
-- funcione sin importar el orden real de inserción de los nodos.
-- ------------------------------------------------------------

INSERT INTO logistica.conexiones
    (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT origen.id_nodo, destino.id_nodo, 4.000, 8.00, 1.50, TRUE
FROM logistica.nodos origen, logistica.nodos destino
WHERE origen.nombre = 'Bodega Principal' AND destino.nombre = 'Cliente A'
ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;

INSERT INTO logistica.conexiones
    (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT origen.id_nodo, destino.id_nodo, 10.000, 18.00, 3.00, TRUE
FROM logistica.nodos origen, logistica.nodos destino
WHERE origen.nombre = 'Bodega Principal' AND destino.nombre = 'Cliente B'
ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;

INSERT INTO logistica.conexiones
    (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT origen.id_nodo, destino.id_nodo, 3.000, 6.00, 1.00, TRUE
FROM logistica.nodos origen, logistica.nodos destino
WHERE origen.nombre = 'Cliente A' AND destino.nombre = 'Cliente B'
ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;

INSERT INTO logistica.conexiones
    (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT origen.id_nodo, destino.id_nodo, 7.000, 12.00, 2.00, TRUE
FROM logistica.nodos origen, logistica.nodos destino
WHERE origen.nombre = 'Cliente A' AND destino.nombre = 'Cliente C'
ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;

INSERT INTO logistica.conexiones
    (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT origen.id_nodo, destino.id_nodo, 2.000, 4.00, 0.80, TRUE
FROM logistica.nodos origen, logistica.nodos destino
WHERE origen.nombre = 'Cliente B' AND destino.nombre = 'Cliente C'
ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;

INSERT INTO logistica.conexiones
    (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT origen.id_nodo, destino.id_nodo, 6.000, 10.00, 1.70, TRUE
FROM logistica.nodos origen, logistica.nodos destino
WHERE origen.nombre = 'Cliente B' AND destino.nombre = 'Cliente D'
ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;

INSERT INTO logistica.conexiones
    (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT origen.id_nodo, destino.id_nodo, 3.000, 5.00, 1.00, TRUE
FROM logistica.nodos origen, logistica.nodos destino
WHERE origen.nombre = 'Cliente C' AND destino.nombre = 'Cliente D'
ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
