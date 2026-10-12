-- ============================================================
-- OptiRoute AI - Datos DEMO para catalogos y planificacion
-- Requiere que 001_grafo_prueba.sql ya haya creado los nodos.
-- Es idempotente: usa identificadores DEMO y claves unicas existentes.
-- ============================================================

-- Clientes DEMO. identificacion no tiene una restriccion UNIQUE, por eso se
-- protege explicitamente la insercion antes de crear cada registro.
INSERT INTO operaciones.clientes (
    tipo_cliente, nombres, apellidos, identificacion, correo, telefono, activo
)
SELECT 'PERSONA', 'Cliente', 'Demo A', 'DEMO-OPT-001',
       'cliente.demo.a@optiroute.local', '0990000101', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM operaciones.clientes WHERE identificacion = 'DEMO-OPT-001'
);

INSERT INTO operaciones.clientes (
    tipo_cliente, nombres, apellidos, identificacion, correo, telefono, activo
)
SELECT 'PERSONA', 'Cliente', 'Demo B', 'DEMO-OPT-002',
       'cliente.demo.b@optiroute.local', '0990000102', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM operaciones.clientes WHERE identificacion = 'DEMO-OPT-002'
);

INSERT INTO operaciones.clientes (
    tipo_cliente, nombres, apellidos, identificacion, correo, telefono, activo
)
SELECT 'PERSONA', 'Cliente', 'Demo C', 'DEMO-OPT-003',
       'cliente.demo.c@optiroute.local', '0990000103', TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM operaciones.clientes WHERE identificacion = 'DEMO-OPT-003'
);

-- Direcciones vinculadas exclusivamente a nodos existentes del grafo.
INSERT INTO operaciones.direcciones (
    id_cliente, id_nodo, etiqueta, direccion_texto, ciudad, provincia,
    pais, latitud, longitud, referencia, es_principal, activo
)
SELECT c.id_cliente, n.id_nodo, 'DEMO-A', 'DEMO OptiRoute - Cliente A',
       'Quito', 'Pichincha', 'Ecuador', n.latitud, n.longitud,
       'Datos DEMO; nodo Cliente A', TRUE, TRUE
FROM operaciones.clientes c
JOIN logistica.nodos n ON n.nombre = 'Cliente A' AND n.activo = TRUE
WHERE c.identificacion = 'DEMO-OPT-001'
  AND NOT EXISTS (
      SELECT 1 FROM operaciones.direcciones d
      WHERE d.id_cliente = c.id_cliente AND d.etiqueta = 'DEMO-A'
  );

INSERT INTO operaciones.direcciones (
    id_cliente, id_nodo, etiqueta, direccion_texto, ciudad, provincia,
    pais, latitud, longitud, referencia, es_principal, activo
)
SELECT c.id_cliente, n.id_nodo, 'DEMO-B', 'DEMO OptiRoute - Cliente B',
       'Quito', 'Pichincha', 'Ecuador', n.latitud, n.longitud,
       'Datos DEMO; nodo Cliente B', TRUE, TRUE
FROM operaciones.clientes c
JOIN logistica.nodos n ON n.nombre = 'Cliente B' AND n.activo = TRUE
WHERE c.identificacion = 'DEMO-OPT-002'
  AND NOT EXISTS (
      SELECT 1 FROM operaciones.direcciones d
      WHERE d.id_cliente = c.id_cliente AND d.etiqueta = 'DEMO-B'
  );

INSERT INTO operaciones.direcciones (
    id_cliente, id_nodo, etiqueta, direccion_texto, ciudad, provincia,
    pais, latitud, longitud, referencia, es_principal, activo
)
SELECT c.id_cliente, n.id_nodo, 'DEMO-C', 'DEMO OptiRoute - Cliente C',
       'Quito', 'Pichincha', 'Ecuador', n.latitud, n.longitud,
       'Datos DEMO; nodo Cliente C', TRUE, TRUE
FROM operaciones.clientes c
JOIN logistica.nodos n ON n.nombre = 'Cliente C' AND n.activo = TRUE
WHERE c.identificacion = 'DEMO-OPT-003'
  AND NOT EXISTS (
      SELECT 1 FROM operaciones.direcciones d
      WHERE d.id_cliente = c.id_cliente AND d.etiqueta = 'DEMO-C'
  );

-- Recurso de conductor DEMO. No representa una credencial utilizable.
INSERT INTO seguridad.usuarios (
    nombres, apellidos, correo, password_hash, tipo_usuario, activo
)
VALUES (
    'Ana', 'Conductora Demo', 'conductora.demo@optiroute.local',
    'DEMO_NO_LOGIN', 'CONDUCTOR', TRUE
)
ON CONFLICT (correo) DO UPDATE
SET nombres = EXCLUDED.nombres,
    apellidos = EXCLUDED.apellidos,
    tipo_usuario = EXCLUDED.tipo_usuario,
    activo = EXCLUDED.activo;

INSERT INTO logistica.conductores (
    id_usuario, numero_licencia, tipo_licencia, telefono, disponible, activo
)
SELECT id_usuario, 'LIC-DEMO-OPT-001', 'B', '0990000201', TRUE, TRUE
FROM seguridad.usuarios
WHERE correo = 'conductora.demo@optiroute.local'
ON CONFLICT (id_usuario) DO UPDATE
SET numero_licencia = EXCLUDED.numero_licencia,
    tipo_licencia = EXCLUDED.tipo_licencia,
    telefono = EXCLUDED.telefono,
    disponible = EXCLUDED.disponible,
    activo = EXCLUDED.activo;

-- Vehiculo DEMO con capacidad suficiente para los tres pedidos.
INSERT INTO logistica.vehiculos (
    placa, marca, modelo, anio, tipo_vehiculo, capacidad_kg,
    capacidad_volumen_m3, estado, activo
)
VALUES (
    'DEM-OR-001', 'OptiRoute', 'Demo Cargo', 2024, 'CAMIONETA', 500.00,
    5.000, 'DISPONIBLE', TRUE
)
ON CONFLICT (placa) DO UPDATE
SET marca = EXCLUDED.marca,
    modelo = EXCLUDED.modelo,
    anio = EXCLUDED.anio,
    tipo_vehiculo = EXCLUDED.tipo_vehiculo,
    capacidad_kg = EXCLUDED.capacidad_kg,
    capacidad_volumen_m3 = EXCLUDED.capacidad_volumen_m3,
    estado = EXCLUDED.estado,
    activo = EXCLUDED.activo;

-- Pedidos DEMO: destinos distintos, uno de prioridad URGENTE.
INSERT INTO operaciones.pedidos (
    codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg,
    volumen_m3, prioridad, estado, fecha_solicitada
)
SELECT 'PED-DEMO-001', c.id_cliente, d.id_direccion,
       'DEMO: insumos prioritarios para Cliente A', 80.00, 0.800,
       'URGENTE', 'PENDIENTE', CURRENT_DATE
FROM operaciones.clientes c
JOIN operaciones.direcciones d ON d.id_cliente = c.id_cliente AND d.etiqueta = 'DEMO-A'
WHERE c.identificacion = 'DEMO-OPT-001'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO operaciones.pedidos (
    codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg,
    volumen_m3, prioridad, estado, fecha_solicitada
)
SELECT 'PED-DEMO-002', c.id_cliente, d.id_direccion,
       'DEMO: reposicion programada para Cliente B', 120.00, 1.100,
       'ALTA', 'PENDIENTE', CURRENT_DATE
FROM operaciones.clientes c
JOIN operaciones.direcciones d ON d.id_cliente = c.id_cliente AND d.etiqueta = 'DEMO-B'
WHERE c.identificacion = 'DEMO-OPT-002'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO operaciones.pedidos (
    codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg,
    volumen_m3, prioridad, estado, fecha_solicitada
)
SELECT 'PED-DEMO-003', c.id_cliente, d.id_direccion,
       'DEMO: entrega regular para Cliente C', 70.00, 0.600,
       'NORMAL', 'PENDIENTE', CURRENT_DATE
FROM operaciones.clientes c
JOIN operaciones.direcciones d ON d.id_cliente = c.id_cliente AND d.etiqueta = 'DEMO-C'
WHERE c.identificacion = 'DEMO-OPT-003'
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO operaciones.entregas (id_pedido, estado, nombre_receptor, observaciones)
SELECT id_pedido, 'PENDIENTE', 'Receptor DEMO', 'Registro DEMO para pruebas end-to-end'
FROM operaciones.pedidos
WHERE codigo IN ('PED-DEMO-001', 'PED-DEMO-002', 'PED-DEMO-003')
ON CONFLICT (id_pedido) DO NOTHING;
