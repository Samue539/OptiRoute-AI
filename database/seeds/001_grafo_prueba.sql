-- ============================================================
-- OptiRoute AI
-- Datos de prueba para Matemáticas Discretas y Grafos
-- ============================================================


-- ------------------------------------------------------------
-- VERTICES DEL GRAFO
-- ------------------------------------------------------------

INSERT INTO logistica.nodos
(nombre, tipo_nodo, latitud, longitud)
VALUES
('Bodega Principal', 'BODEGA', -0.200000, -78.500000),
('Cliente A', 'CLIENTE', -0.205000, -78.495000),
('Cliente B', 'CLIENTE', -0.210000, -78.490000),
('Cliente C', 'CLIENTE', -0.215000, -78.500000),
('Cliente D', 'CLIENTE', -0.220000, -78.505000);


-- ------------------------------------------------------------
-- ARISTAS DEL GRAFO
-- ------------------------------------------------------------

INSERT INTO logistica.conexiones
(
    id_nodo_origen,
    id_nodo_destino,
    distancia_km,
    tiempo_minutos,
    costo,
    bidireccional
)
VALUES
(1, 2, 4.000, 8.00, 1.50, TRUE),
(1, 3, 10.000, 18.00, 3.00, TRUE),
(2, 3, 3.000, 6.00, 1.00, TRUE),
(2, 4, 7.000, 12.00, 2.00, TRUE),
(3, 4, 2.000, 4.00, 0.80, TRUE),
(3, 5, 6.000, 10.00, 1.70, TRUE),
(4, 5, 3.000, 5.00, 1.00, TRUE);