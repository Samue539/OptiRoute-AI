-- ============================================================
-- OptiRoute AI - Seed DEMO 005 (solo desarrollo aislado)
-- Centro de Distribucion y Entregas: zonas de Quito, nombres de ruta
-- y guias generadas desde los pedidos existentes.
--
-- PRECONDICIONES: 007 y 008 aplicadas. JAMAS en produccion.
-- IDEMPOTENTE: WHERE NOT EXISTS / ON CONFLICT.
--
-- NO crea membresias, vinculos ni asignaciones: eso lo hace el
-- ADMINISTRADOR desde el modulo Distribucion (POST /api/distribucion/
-- asignaciones). Sin asignaciones rige la regla legada (quien ve todas
-- ve todas; el conductor ve las propias); al asignar, el acceso se
-- restringe a lo asignado.
-- El mapeo nodo -> zona es de demostracion y se documenta abajo.
-- ============================================================

-- Empresa demo para asignar desde la UI (no asigna a nadie por si sola).
INSERT INTO plataforma.empresas (id_empresa, codigo, nombre)
VALUES ('22222222-2222-2222-2222-222222222222', 'DIST-UIO', 'Distribucion Quito Demo')
ON CONFLICT (codigo) DO NOTHING;

-- Zonas de reparto de Quito (norte -> sur).
INSERT INTO operaciones.zonas (codigo, nombre, ciudad, provincia, pais)
SELECT 'ZONA-CAROLINA', 'La Carolina', 'Quito', 'Pichincha', 'Ecuador'
WHERE NOT EXISTS (SELECT 1 FROM operaciones.zonas WHERE codigo = 'ZONA-CAROLINA');
INSERT INTO operaciones.zonas (codigo, nombre, ciudad, provincia, pais)
SELECT 'ZONA-PRADERA', 'La Pradera', 'Quito', 'Pichincha', 'Ecuador'
WHERE NOT EXISTS (SELECT 1 FROM operaciones.zonas WHERE codigo = 'ZONA-PRADERA');
INSERT INTO operaciones.zonas (codigo, nombre, ciudad, provincia, pais)
SELECT 'ZONA-CALDERON', 'Calderon', 'Quito', 'Pichincha', 'Ecuador'
WHERE NOT EXISTS (SELECT 1 FROM operaciones.zonas WHERE codigo = 'ZONA-CALDERON');
INSERT INTO operaciones.zonas (codigo, nombre, ciudad, provincia, pais)
SELECT 'ZONA-QUITUMBE', 'Quitumbe', 'Quito', 'Pichincha', 'Ecuador'
WHERE NOT EXISTS (SELECT 1 FROM operaciones.zonas WHERE codigo = 'ZONA-QUITUMBE');
INSERT INTO operaciones.zonas (codigo, nombre, ciudad, provincia, pais)
SELECT 'ZONA-TUMBACO', 'Tumbaco', 'Quito', 'Pichincha', 'Ecuador'
WHERE NOT EXISTS (SELECT 1 FROM operaciones.zonas WHERE codigo = 'ZONA-TUMBACO');

-- Nombre comercial a las rutas que aun no lo tienen.
UPDATE logistica.rutas
SET nombre_ruta = 'Ruta ' || codigo
WHERE nombre_ruta IS NULL;

-- Mapeo DEMO nodo destino -> zona (documentado, solo desarrollo):
-- Cliente A/B -> La Carolina, C/D -> La Pradera,
-- E/F -> Calderon, G/H -> Quitumbe, resto -> Tumbaco.
UPDATE logistica.rutas r
SET id_zona = (SELECT id_zona FROM operaciones.zonas WHERE codigo = 'ZONA-CAROLINA')
WHERE r.id_zona IS NULL
  AND r.id_nodo_destino IN (SELECT id_nodo FROM logistica.nodos WHERE nombre IN ('Cliente A', 'Cliente B'));

UPDATE logistica.rutas r
SET id_zona = (SELECT id_zona FROM operaciones.zonas WHERE codigo = 'ZONA-PRADERA')
WHERE r.id_zona IS NULL
  AND r.id_nodo_destino IN (SELECT id_nodo FROM logistica.nodos WHERE nombre IN ('Cliente C', 'Cliente D'));

UPDATE logistica.rutas r
SET id_zona = (SELECT id_zona FROM operaciones.zonas WHERE codigo = 'ZONA-CALDERON')
WHERE r.id_zona IS NULL
  AND r.id_nodo_destino IN (SELECT id_nodo FROM logistica.nodos WHERE nombre IN ('Cliente E', 'Cliente F'));

UPDATE logistica.rutas r
SET id_zona = (SELECT id_zona FROM operaciones.zonas WHERE codigo = 'ZONA-QUITUMBE')
WHERE r.id_zona IS NULL
  AND r.id_nodo_destino IN (SELECT id_nodo FROM logistica.nodos WHERE nombre IN ('Cliente G', 'Cliente H'));

UPDATE logistica.rutas r
SET id_zona = (SELECT id_zona FROM operaciones.zonas WHERE codigo = 'ZONA-TUMBACO')
WHERE r.id_zona IS NULL;

-- Una guia por pedido existente (1 a 1). El estado deriva del pedido.
INSERT INTO operaciones.guias (
    numero_guia, id_pedido, id_ruta, id_zona,
    destinatario_nombre, direccion_texto, telefono_autorizado,
    estado, fecha_entrega
)
SELECT
    'GUI-' || p.codigo,
    p.id_pedido,
    rp.id_ruta,
    r.id_zona,
    COALESCE(NULLIF(c.razon_social, ''), TRIM(COALESCE(c.nombres, '') || ' ' || COALESCE(c.apellidos, ''))),
    d.direccion_texto,
    NULLIF(c.telefono, ''),
    CASE p.estado
        WHEN 'ENTREGADO' THEN 'ENTREGADA'
        WHEN 'EN_RUTA' THEN 'EN_RUTA'
        WHEN 'CANCELADO' THEN 'CANCELADA'
        ELSE 'PENDIENTE'
    END,
    CASE WHEN p.estado = 'ENTREGADO' THEN CURRENT_TIMESTAMP ELSE NULL END
FROM operaciones.pedidos p
JOIN operaciones.clientes c ON c.id_cliente = p.id_cliente
JOIN operaciones.direcciones d ON d.id_direccion = p.id_direccion_entrega
LEFT JOIN (
    SELECT DISTINCT ON (rp.id_pedido) rp.id_pedido, rp.id_ruta
    FROM logistica.ruta_pedidos rp
    ORDER BY rp.id_pedido, rp.id_ruta_pedido DESC
) rp ON rp.id_pedido = p.id_pedido
LEFT JOIN logistica.rutas r ON r.id_ruta = rp.id_ruta
WHERE NOT EXISTS (SELECT 1 FROM operaciones.guias g WHERE g.id_pedido = p.id_pedido);

-- Historial inicial para las guias ya entregadas (actor NULL = seed).
INSERT INTO operaciones.guia_eventos (
    id_guia, tipo, receptor_nombre, relacion_destinatario, gps_origen, observaciones
)
SELECT g.id_guia, 'ENTREGADA', 'Receptor demo', 'DESTINATARIO', 'DESCONOCIDO', 'Seed demo 005'
FROM operaciones.guias g
WHERE g.estado = 'ENTREGADA'
  AND NOT EXISTS (SELECT 1 FROM operaciones.guia_eventos e WHERE e.id_guia = g.id_guia);
