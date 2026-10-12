-- ============================================================
-- OptiRoute AI - Demo completo para exposición de grafos
-- Idempotente: usa identificadores DEMO-OPT-*
-- Zona coherente: Quito (-0.19 a -0.23 lat, -78.48 a -78.52 lng)
-- ============================================================

-- NODOS adicionales (zona Quito norte-centro)
INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Cliente E', 'CLIENTE', -0.190000, -78.485000 WHERE NOT EXISTS (SELECT 1 FROM logistica.nodos WHERE nombre='Cliente E');
INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Cliente F', 'CLIENTE', -0.195000, -78.495000 WHERE NOT EXISTS (SELECT 1 FROM logistica.nodos WHERE nombre='Cliente F');
INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Cliente G', 'CLIENTE', -0.225000, -78.490000 WHERE NOT EXISTS (SELECT 1 FROM logistica.nodos WHERE nombre='Cliente G');
INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Cliente H', 'CLIENTE', -0.218000, -78.498000 WHERE NOT EXISTS (SELECT 1 FROM logistica.nodos WHERE nombre='Cliente H');
INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Interseccion Norte', 'INTERSECCION', -0.198000, -78.492000 WHERE NOT EXISTS (SELECT 1 FROM logistica.nodos WHERE nombre='Interseccion Norte');
INSERT INTO logistica.nodos (nombre, tipo_nodo, latitud, longitud)
SELECT 'Interseccion Sur', 'INTERSECCION', -0.220000, -78.498000 WHERE NOT EXISTS (SELECT 1 FROM logistica.nodos WHERE nombre='Interseccion Sur');

-- CONEXIONES para grafo conectado (idempotente via ON CONFLICT)
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT o.id_nodo, d.id_nodo, 3.5, 7.0, 1.2, TRUE FROM logistica.nodos o, logistica.nodos d WHERE o.nombre='Bodega Principal' AND d.nombre='Cliente E' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT o.id_nodo, d.id_nodo, 2.8, 5.5, 1.0, TRUE FROM logistica.nodos o, logistica.nodos d WHERE o.nombre='Bodega Principal' AND d.nombre='Interseccion Norte' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT o.id_nodo, d.id_nodo, 2.2, 4.0, 0.9, TRUE FROM logistica.nodos o, logistica.nodos d WHERE o.nombre='Interseccion Norte' AND d.nombre='Cliente E' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT o.id_nodo, d.id_nodo, 2.5, 5.0, 1.0, TRUE FROM logistica.nodos o, logistica.nodos d WHERE o.nombre='Interseccion Norte' AND d.nombre='Cliente F' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT o.id_nodo, d.id_nodo, 3.0, 6.0, 1.1, TRUE FROM logistica.nodos o, logistica.nodos d WHERE o.nombre='Cliente F' AND d.nombre='Cliente A' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT o.id_nodo, d.id_nodo, 2.0, 4.0, 0.8, TRUE FROM logistica.nodos o, logistica.nodos d WHERE o.nombre='Cliente G' AND d.nombre='Cliente D' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT o.id_nodo, d.id_nodo, 1.8, 3.5, 0.7, TRUE FROM logistica.nodos o, logistica.nodos d WHERE o.nombre='Cliente H' AND d.nombre='Cliente C' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT o.id_nodo, d.id_nodo, 2.6, 5.0, 1.0, TRUE FROM logistica.nodos o, logistica.nodos d WHERE o.nombre='Interseccion Sur' AND d.nombre='Cliente G' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT o.id_nodo, d.id_nodo, 1.5, 3.0, 0.6, TRUE FROM logistica.nodos o, logistica.nodos d WHERE o.nombre='Interseccion Sur' AND d.nombre='Cliente H' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;
INSERT INTO logistica.conexiones (id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional)
SELECT o.id_nodo, d.id_nodo, 4.5, 8.5, 1.4, TRUE FROM logistica.nodos o, logistica.nodos d WHERE o.nombre='Bodega Principal' AND d.nombre='Interseccion Sur' ON CONFLICT (id_nodo_origen, id_nodo_destino) DO NOTHING;

-- CLIENTES 4-8
INSERT INTO operaciones.clientes (tipo_cliente, nombres, apellidos, identificacion, correo, telefono, activo)
SELECT 'PERSONA','Cliente','Demo D','DEMO-OPT-004','cliente.demo.d@optiroute.local','0990000104',TRUE WHERE NOT EXISTS (SELECT 1 FROM operaciones.clientes WHERE identificacion='DEMO-OPT-004');
INSERT INTO operaciones.clientes (tipo_cliente, nombres, apellidos, identificacion, correo, telefono, activo)
SELECT 'PERSONA','Cliente','Demo E','DEMO-OPT-005','cliente.demo.e@optiroute.local','0990000105',TRUE WHERE NOT EXISTS (SELECT 1 FROM operaciones.clientes WHERE identificacion='DEMO-OPT-005');
INSERT INTO operaciones.clientes (tipo_cliente, nombres, apellidos, razon_social, identificacion, correo, telefono, activo)
SELECT 'EMPRESA',NULL,NULL,'Empresa Demo F S.A.','DEMO-OPT-006','empresa.demo.f@optiroute.local','0990000106',TRUE WHERE NOT EXISTS (SELECT 1 FROM operaciones.clientes WHERE identificacion='DEMO-OPT-006');
INSERT INTO operaciones.clientes (tipo_cliente, nombres, apellidos, identificacion, correo, telefono, activo)
SELECT 'PERSONA','Cliente','Demo G','DEMO-OPT-007','cliente.demo.g@optiroute.local','0990000107',TRUE WHERE NOT EXISTS (SELECT 1 FROM operaciones.clientes WHERE identificacion='DEMO-OPT-007');
INSERT INTO operaciones.clientes (tipo_cliente, nombres, apellidos, identificacion, correo, telefono, activo)
SELECT 'PERSONA','Cliente','Demo H','DEMO-OPT-008','cliente.demo.h@optiroute.local','0990000108',TRUE WHERE NOT EXISTS (SELECT 1 FROM operaciones.clientes WHERE identificacion='DEMO-OPT-008');

-- DIRECCIONES para nuevos clientes (vinculadas a nodos E-H)
INSERT INTO operaciones.direcciones (id_cliente, id_nodo, etiqueta, direccion_texto, ciudad, provincia, pais, latitud, longitud, referencia, es_principal, activo)
SELECT c.id_cliente, n.id_nodo, 'DEMO-D','Av. Demo D 123 - Quito','Quito','Pichincha','Ecuador', n.latitud, n.longitud,'Nodo Cliente D',TRUE,TRUE FROM operaciones.clientes c JOIN logistica.nodos n ON n.nombre='Cliente D' WHERE c.identificacion='DEMO-OPT-004' AND NOT EXISTS (SELECT 1 FROM operaciones.direcciones d WHERE d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-D');
INSERT INTO operaciones.direcciones (id_cliente, id_nodo, etiqueta, direccion_texto, ciudad, provincia, pais, latitud, longitud, referencia, es_principal, activo)
SELECT c.id_cliente, n.id_nodo, 'DEMO-E','Av. Demo E 456 - Quito','Quito','Pichincha','Ecuador', n.latitud, n.longitud,'Nodo Cliente E',TRUE,TRUE FROM operaciones.clientes c JOIN logistica.nodos n ON n.nombre='Cliente E' WHERE c.identificacion='DEMO-OPT-005' AND NOT EXISTS (SELECT 1 FROM operaciones.direcciones d WHERE d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-E');
INSERT INTO operaciones.direcciones (id_cliente, id_nodo, etiqueta, direccion_texto, ciudad, provincia, pais, latitud, longitud, referencia, es_principal, activo)
SELECT c.id_cliente, n.id_nodo, 'DEMO-F','Parque Industrial Demo F - Quito','Quito','Pichincha','Ecuador', n.latitud, n.longitud,'Nodo Cliente F',TRUE,TRUE FROM operaciones.clientes c JOIN logistica.nodos n ON n.nombre='Cliente F' WHERE c.identificacion='DEMO-OPT-006' AND NOT EXISTS (SELECT 1 FROM operaciones.direcciones d WHERE d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-F');
INSERT INTO operaciones.direcciones (id_cliente, id_nodo, etiqueta, direccion_texto, ciudad, provincia, pais, latitud, longitud, referencia, es_principal, activo)
SELECT c.id_cliente, n.id_nodo, 'DEMO-G','Calle Demo G 789 - Quito','Quito','Pichincha','Ecuador', n.latitud, n.longitud,'Nodo Cliente G',TRUE,TRUE FROM operaciones.clientes c JOIN logistica.nodos n ON n.nombre='Cliente G' WHERE c.identificacion='DEMO-OPT-007' AND NOT EXISTS (SELECT 1 FROM operaciones.direcciones d WHERE d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-G');
INSERT INTO operaciones.direcciones (id_cliente, id_nodo, etiqueta, direccion_texto, ciudad, provincia, pais, latitud, longitud, referencia, es_principal, activo)
SELECT c.id_cliente, n.id_nodo, 'DEMO-H','Av. Demo H 321 - Quito','Quito','Pichincha','Ecuador', n.latitud, n.longitud,'Nodo Cliente H',TRUE,TRUE FROM operaciones.clientes c JOIN logistica.nodos n ON n.nombre='Cliente H' WHERE c.identificacion='DEMO-OPT-008' AND NOT EXISTS (SELECT 1 FROM operaciones.direcciones d WHERE d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-H');

-- USUARIOS/CONDUCTORES adicionales
INSERT INTO seguridad.usuarios (nombres, apellidos, correo, password_hash, tipo_usuario, activo)
VALUES ('Carlos','Conductor Demo','conductor.demo2@optiroute.local','DEMO_NO_LOGIN','CONDUCTOR',TRUE) ON CONFLICT (correo) DO NOTHING;
INSERT INTO seguridad.usuarios (nombres, apellidos, correo, password_hash, tipo_usuario, activo)
VALUES ('Maria','Conductora Demo 2','conductora.demo3@optiroute.local','DEMO_NO_LOGIN','CONDUCTOR',TRUE) ON CONFLICT (correo) DO NOTHING;
INSERT INTO logistica.conductores (id_usuario, numero_licencia, tipo_licencia, telefono, disponible, activo)
SELECT id_usuario,'LIC-DEMO-OPT-002','C','0990000202',TRUE,TRUE FROM seguridad.usuarios WHERE correo='conductor.demo2@optiroute.local' ON CONFLICT (id_usuario) DO UPDATE SET disponible=TRUE, activo=TRUE;
INSERT INTO logistica.conductores (id_usuario, numero_licencia, tipo_licencia, telefono, disponible, activo)
SELECT id_usuario,'LIC-DEMO-OPT-003','B','0990000203',TRUE,TRUE FROM seguridad.usuarios WHERE correo='conductora.demo3@optiroute.local' ON CONFLICT (id_usuario) DO UPDATE SET disponible=TRUE, activo=TRUE;

-- ADMIN demo
INSERT INTO seguridad.usuarios (nombres, apellidos, correo, password_hash, tipo_usuario, activo)
VALUES ('Admin','OptiRoute','admin@optiroute.local','$2b$12$DEMO_HASH_NO_LOGIN','ADMINISTRADOR',TRUE) ON CONFLICT (correo) DO NOTHING;

-- VEHICULOS adicionales
INSERT INTO logistica.vehiculos (placa, marca, modelo, anio, tipo_vehiculo, capacidad_kg, capacidad_volumen_m3, estado, activo)
VALUES ('DEM-OR-002','OptiRoute','Demo Van',2023,'CAMIONETA',800.00,8.000,'DISPONIBLE',TRUE) ON CONFLICT (placa) DO UPDATE SET capacidad_kg=800.00, capacidad_volumen_m3=8.000, estado='DISPONIBLE';
INSERT INTO logistica.vehiculos (placa, marca, modelo, anio, tipo_vehiculo, capacidad_kg, capacidad_volumen_m3, estado, activo)
VALUES ('DEM-OR-003','OptiRoute','Moto Cargo',2024,'MOTO',150.00,1.200,'DISPONIBLE',TRUE) ON CONFLICT (placa) DO UPDATE SET capacidad_kg=150.00, capacidad_volumen_m3=1.200, estado='DISPONIBLE';

-- PEDIDOS 004-015 (12 total, mix pendientes/completados)
INSERT INTO operaciones.pedidos (codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg, volumen_m3, prioridad, estado, fecha_solicitada)
SELECT 'PED-DEMO-004', c.id_cliente, d.id_direccion,'DEMO: Cliente D - materiales',60.00,0.500,'NORMAL','PENDIENTE', CURRENT_DATE FROM operaciones.clientes c JOIN operaciones.direcciones d ON d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-D' WHERE c.identificacion='DEMO-OPT-004' ON CONFLICT (codigo) DO NOTHING;
INSERT INTO operaciones.pedidos (codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg, volumen_m3, prioridad, estado, fecha_solicitada)
SELECT 'PED-DEMO-005', c.id_cliente, d.id_direccion,'DEMO: Cliente E - electronica urgente',45.00,0.400,'URGENTE','PENDIENTE', CURRENT_DATE FROM operaciones.clientes c JOIN operaciones.direcciones d ON d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-E' WHERE c.identificacion='DEMO-OPT-005' ON CONFLICT (codigo) DO NOTHING;
INSERT INTO operaciones.pedidos (codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg, volumen_m3, prioridad, estado, fecha_solicitada)
SELECT 'PED-DEMO-006', c.id_cliente, d.id_direccion,'DEMO: Empresa F - repuestos',200.00,2.000,'ALTA','PENDIENTE', CURRENT_DATE FROM operaciones.clientes c JOIN operaciones.direcciones d ON d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-F' WHERE c.identificacion='DEMO-OPT-006' ON CONFLICT (codigo) DO NOTHING;
INSERT INTO operaciones.pedidos (codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg, volumen_m3, prioridad, estado, fecha_solicitada)
SELECT 'PED-DEMO-007', c.id_cliente, d.id_direccion,'DEMO: Cliente G - alimentos',90.00,0.900,'NORMAL','PENDIENTE', CURRENT_DATE FROM operaciones.clientes c JOIN operaciones.direcciones d ON d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-G' WHERE c.identificacion='DEMO-OPT-007' ON CONFLICT (codigo) DO NOTHING;
INSERT INTO operaciones.pedidos (codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg, volumen_m3, prioridad, estado, fecha_solicitada)
SELECT 'PED-DEMO-008', c.id_cliente, d.id_direccion,'DEMO: Cliente H - farmacia',30.00,0.300,'ALTA','PENDIENTE', CURRENT_DATE FROM operaciones.clientes c JOIN operaciones.direcciones d ON d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-H' WHERE c.identificacion='DEMO-OPT-008' ON CONFLICT (codigo) DO NOTHING;
INSERT INTO operaciones.pedidos (codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg, volumen_m3, prioridad, estado, fecha_solicitada)
SELECT 'PED-DEMO-009', c.id_cliente, d.id_direccion,'DEMO: Cliente A - segunda entrega',50.00,0.450,'BAJA','PENDIENTE', CURRENT_DATE FROM operaciones.clientes c JOIN operaciones.direcciones d ON d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-A' WHERE c.identificacion='DEMO-OPT-001' ON CONFLICT (codigo) DO NOTHING;
INSERT INTO operaciones.pedidos (codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg, volumen_m3, prioridad, estado, fecha_solicitada)
SELECT 'PED-DEMO-010', c.id_cliente, d.id_direccion,'DEMO: Cliente B - completado',110.00,1.000,'NORMAL','ENTREGADO', CURRENT_DATE-2 FROM operaciones.clientes c JOIN operaciones.direcciones d ON d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-B' WHERE c.identificacion='DEMO-OPT-002' ON CONFLICT (codigo) DO NOTHING;
INSERT INTO operaciones.pedidos (codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg, volumen_m3, prioridad, estado, fecha_solicitada)
SELECT 'PED-DEMO-011', c.id_cliente, d.id_direccion,'DEMO: Cliente C - completado',75.00,0.700,'ALTA','ENTREGADO', CURRENT_DATE-1 FROM operaciones.clientes c JOIN operaciones.direcciones d ON d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-C' WHERE c.identificacion='DEMO-OPT-003' ON CONFLICT (codigo) DO NOTHING;
INSERT INTO operaciones.pedidos (codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg, volumen_m3, prioridad, estado, fecha_solicitada)
SELECT 'PED-DEMO-012', c.id_cliente, d.id_direccion,'DEMO: Cliente E - pendiente voluminoso',130.00,1.300,'NORMAL','PENDIENTE', CURRENT_DATE FROM operaciones.clientes c JOIN operaciones.direcciones d ON d.id_cliente=c.id_cliente AND d.etiqueta='DEMO-E' WHERE c.identificacion='DEMO-OPT-005' ON CONFLICT (codigo) DO NOTHING;

INSERT INTO operaciones.entregas (id_pedido, estado, nombre_receptor, observaciones)
SELECT id_pedido, CASE WHEN codigo IN ('PED-DEMO-010','PED-DEMO-011') THEN 'ENTREGADO' ELSE 'PENDIENTE' END, 'Receptor DEMO','Demo completo' FROM operaciones.pedidos WHERE codigo LIKE 'PED-DEMO-%' ON CONFLICT (id_pedido) DO NOTHING;
UPDATE operaciones.entregas SET estado='ENTREGADO', fecha_entrega=CURRENT_TIMESTAMP WHERE id_pedido IN (SELECT id_pedido FROM operaciones.pedidos WHERE codigo IN ('PED-DEMO-010','PED-DEMO-011'));

-- RUTA HISTORICA COMPLETADA (para dashboard)
DO $$
DECLARE v_bodega BIGINT; v_cliB BIGINT; v_ruta BIGINT; v_dist NUMERIC;
BEGIN
  SELECT id_nodo INTO v_bodega FROM logistica.nodos WHERE nombre='Bodega Principal';
  SELECT id_nodo INTO v_cliB FROM logistica.nodos WHERE nombre='Cliente B';
  SELECT id_vehiculo INTO v_dist FROM logistica.vehiculos WHERE placa='DEM-OR-002';
  IF v_bodega IS NOT NULL AND v_cliB IS NOT NULL AND NOT EXISTS (SELECT 1 FROM logistica.rutas WHERE codigo='RUT-DEMO-HIST001') THEN
    INSERT INTO logistica.rutas (codigo, id_nodo_origen, id_nodo_destino, estado, distancia_total_km, tiempo_estimado_min, id_vehiculo, fecha_planificada, fecha_inicio, fecha_fin)
    VALUES ('RUT-DEMO-HIST001', v_bodega, v_cliB, 'COMPLETADA', 7.5, 16.0, v_dist, CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '1 hour') RETURNING id_ruta INTO v_ruta;
    INSERT INTO logistica.ruta_puntos (id_ruta, id_nodo, orden, distancia_acumulada_km) VALUES (v_ruta, v_bodega, 1, 0) ON CONFLICT DO NOTHING;
    INSERT INTO logistica.ruta_puntos (id_ruta, id_nodo, orden, distancia_acumulada_km) VALUES (v_ruta, v_cliB, 2, 7.5) ON CONFLICT DO NOTHING;
  END IF;
END $$;
