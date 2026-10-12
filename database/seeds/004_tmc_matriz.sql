-- TMC Grupo Tramaco - Matriz Central Quito
-- Actualiza bodega principal y reubica clientes demo en Quito (Carcelén, Ponceano, etc.)
-- Coordenada ajustada visualmente sobre el predio TMC/Tramaco Express mostrado por OpenStreetMap. Referencial intersección Manuel Najas / Joaquín Mancheno, Carcelén Industrial, Quito
-- TMC Matriz: lat -0.09668, lon -78.47537 (referencial intersección, verificada vía Nominatim OSM con curl para Manuel Najas y Joaquin Mancheno)
-- Clientes demo: sectores públicos Quito, claramente DEMO, sin datos personales
-- Pesos del grafo: distancias geográficas estimadas (haversine) entre nodos para demostración académica

UPDATE logistica.nodos
SET nombre = 'TMC Grupo Tramaco - Matriz Quito',
    latitud = -0.09668,
    longitud = -78.47537,
    tipo_nodo = 'BODEGA'
WHERE id_nodo = 1 OR nombre = 'Bodega Principal';

-- Clientes demo - coordenadas coherentes Quito (ultima milla desde TMC)
UPDATE logistica.nodos SET latitud = -0.1150, longitud = -78.4900 WHERE nombre = 'Cliente A'; -- Ponceano
UPDATE logistica.nodos SET latitud = -0.1100, longitud = -78.4950 WHERE nombre = 'Cliente B'; -- Cotocollao
UPDATE logistica.nodos SET latitud = -0.1050, longitud = -78.5000 WHERE nombre = 'Cliente C'; -- El Condado
UPDATE logistica.nodos SET latitud = -0.1120, longitud = -78.4850 WHERE nombre = 'Cliente D'; -- La Ofelia
UPDATE logistica.nodos SET latitud = -0.0900, longitud = -78.4800 WHERE nombre = 'Cliente E'; -- Carcelén cercano
UPDATE logistica.nodos SET latitud = -0.1200, longitud = -78.4700 WHERE nombre = 'Cliente F'; -- Comité del Pueblo
UPDATE logistica.nodos SET latitud = -0.1750, longitud = -78.4800 WHERE nombre = 'Cliente G'; -- Iñaquito
UPDATE logistica.nodos SET latitud = -0.1800, longitud = -78.4850 WHERE nombre = 'Cliente H'; -- La Carolina

-- Intersecciones también cerca
UPDATE logistica.nodos SET latitud = -0.1000, longitud = -78.4900 WHERE nombre = 'Interseccion Norte';
UPDATE logistica.nodos SET latitud = -0.1500, longitud = -78.4900 WHERE nombre = 'Interseccion Sur';

-- Sincronizar direcciones demo con coordenadas de nodos (para que pedidos muestren destino correcto)
UPDATE operaciones.direcciones d
SET latitud = n.latitud, longitud = n.longitud
FROM logistica.nodos n
WHERE d.id_nodo = n.id_nodo;

-- Recalcular TODAS las aristas donde TMC (id 1) participa usando haversine (distancia geográfica estimada)
-- Valores calculados con haversine para TMC -0.0966838,-78.4753787:
-- TMC->Cliente E (Carcelén -0.09,-78.48) = 0.904 km
-- TMC->Interseccion Norte (-0.10,-78.49) = 1.667 km
-- TMC->Interseccion Sur (-0.15,-78.49) = 6.147 km
-- TMC->Cliente A (Ponceano -0.115,-78.49) = 2.606 km
-- TMC->Cliente B (Cotocollao -0.11,-78.495) = 2.637 km
UPDATE logistica.conexiones SET distancia_km = 0.904, tiempo_minutos = 2.0 WHERE (id_nodo_origen=1 AND id_nodo_destino IN (SELECT id_nodo FROM logistica.nodos WHERE nombre='Cliente E')) OR (id_nodo_origen IN (SELECT id_nodo FROM logistica.nodos WHERE nombre='Cliente E') AND id_nodo_destino=1);
UPDATE logistica.conexiones SET distancia_km = 1.667, tiempo_minutos = 3.7 WHERE (id_nodo_origen=1 AND id_nodo_destino IN (SELECT id_nodo FROM logistica.nodos WHERE nombre='Interseccion Norte')) OR (id_nodo_origen IN (SELECT id_nodo FROM logistica.nodos WHERE nombre='Interseccion Norte') AND id_nodo_destino=1);
UPDATE logistica.conexiones SET distancia_km = 6.147, tiempo_minutos = 13.5 WHERE (id_nodo_origen=1 AND id_nodo_destino IN (SELECT id_nodo FROM logistica.nodos WHERE nombre='Interseccion Sur')) OR (id_nodo_origen IN (SELECT id_nodo FROM logistica.nodos WHERE nombre='Interseccion Sur') AND id_nodo_destino=1);
UPDATE logistica.conexiones SET distancia_km = 2.606, tiempo_minutos = 5.7 WHERE (id_nodo_origen=1 AND id_nodo_destino IN (SELECT id_nodo FROM logistica.nodos WHERE nombre='Cliente A')) OR (id_nodo_origen IN (SELECT id_nodo FROM logistica.nodos WHERE nombre='Cliente A') AND id_nodo_destino=1);
UPDATE logistica.conexiones SET distancia_km = 2.637, tiempo_minutos = 5.8 WHERE (id_nodo_origen=1 AND id_nodo_destino IN (SELECT id_nodo FROM logistica.nodos WHERE nombre='Cliente B')) OR (id_nodo_origen IN (SELECT id_nodo FROM logistica.nodos WHERE nombre='Cliente B') AND id_nodo_destino=1);

-- Asegurar aristas TMC existen (idempotente) - si faltara alguna, crear con distancia haversine
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT 1, n.id_nodo, 2.606, 5.7, 1.0, TRUE FROM logistica.nodos n WHERE n.nombre='Cliente A' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT n.id_nodo, 1, 2.606, 5.7, 1.0, TRUE FROM logistica.nodos n WHERE n.nombre='Cliente A' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
