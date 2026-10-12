-- ============================================================
-- OptiRoute AI - Script 004: Indices para optimizacion
-- Reservado para indices adicionales (ej. busquedas por estado,
-- codigo, fechas). Actualmente las tablas base ya incluyen
-- PRIMARY KEY y UNIQUE necesarios; este script queda preparado
-- para futuras optimizaciones sin modificar 003_crear_tablas.sql.
-- Es seguro ejecutar varias veces (CREATE INDEX IF NOT EXISTS).
-- ============================================================

-- Ejemplo (comentado hasta definir carga real):
-- CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON operaciones.pedidos(estado);
-- CREATE INDEX IF NOT EXISTS idx_rutas_estado ON logistica.rutas(estado);
-- CREATE INDEX IF NOT EXISTS idx_ruta_puntos_ruta_orden ON logistica.ruta_puntos(id_ruta, orden);
CREATE UNIQUE INDEX IF NOT EXISTS uq_rutas_clave_idempotencia
    ON logistica.rutas (clave_idempotencia)
    WHERE clave_idempotencia IS NOT NULL;

-- La exclusividad de recursos se valida bajo bloqueo FOR UPDATE sobre las
-- filas de conductor y vehiculo. Asi la migracion no destruye ni invalida
-- historiales anteriores que ya pudieran contener conflictos.
