-- ============================================================
-- OptiRoute AI - Script 005: Restricciones adicionales
-- Reservado para CHECKs, FKs o triggers evolutivos.
-- Actualmente 003_crear_tablas.sql ya contiene las restricciones
-- base (UNIQUE, FOREIGN KEY, CHECK). Este archivo permanece
-- idempotente y listo para ampliaciones futuras.
-- ============================================================

ALTER TABLE logistica.rutas
    ADD COLUMN IF NOT EXISTS clave_idempotencia VARCHAR(64);

CREATE TABLE IF NOT EXISTS logistica.ruta_novedades (
    id_novedad BIGSERIAL PRIMARY KEY,
    id_ruta BIGINT NOT NULL REFERENCES logistica.rutas(id_ruta),
    id_pedido BIGINT REFERENCES operaciones.pedidos(id_pedido),
    tipo VARCHAR(40) NOT NULL,
    descripcion VARCHAR(500) NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_rutas_clave_idempotencia
    ON logistica.rutas (clave_idempotencia)
    WHERE clave_idempotencia IS NOT NULL;

-- La exclusividad de recursos se implementa en el servicio mediante
-- SELECT ... FOR UPDATE y una consulta de rutas activas. No se crea un
-- indice unico parcial para conservar historiales preexistentes intactos.
