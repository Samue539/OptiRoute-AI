-- ============================================================
-- OptiRoute AI
-- Script: 006_seguridad_acceso.sql
-- Descripción: Persistencia segura en PostgreSQL de las cuentas de
--              acceso, sesiones y auditoría (Fase 3).
--
-- REGLAS DE ESTA MIGRACIÓN (aditiva y reversible):
--   * NO modifica ni elimina tablas, columnas ni datos existentes.
--   * NO toca seguridad.usuarios (usuarios logísticos) ni logistica.conductores.
--   * Es idempotente: puede ejecutarse varias veces sin error.
--   * Crea las tablas que reemplazan al almacenamiento JSON provisional
--     (backend/data/seguridad/cuentas.json, sesiones.json, auditoria.jsonl).
--   * Reversión: ver docs/FASE3_SEGURIDAD_POSTGRES.md (solo se eliminan las
--     tablas creadas aquí; ninguna tabla previa se ve afectada).
-- ============================================================


-- ============================================================
-- ESQUEMA: SEGURIDAD
-- TABLA: CUENTAS_ACCESO
-- Cuentas de inicio de sesión (perfiles del sistema).
-- Reemplaza cuentas.json conservando identificadores, hashes de
-- contraseña compatibles (pbkdf2_sha256$...), roles, estados y permisos.
-- ============================================================

CREATE TABLE IF NOT EXISTS seguridad.cuentas_acceso (
    id_usuario BIGSERIAL PRIMARY KEY,

    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,

    correo VARCHAR(255) NOT NULL UNIQUE,

    -- Hash autodescriptivo pbkdf2_sha256$iteraciones$salt$hash.
    -- Se migra tal cual desde el almacenamiento JSON: sigue siendo
    -- verificable por backend.app.core.seguridad.verificar_password.
    password_hash VARCHAR(255) NOT NULL,

    rol VARCHAR(20) NOT NULL DEFAULT 'OPERADOR',

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    es_propietario BOOLEAN NOT NULL DEFAULT FALSE,

    id_conductor BIGINT,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMPTZ,

    origen VARCHAR(30) NOT NULL DEFAULT 'API',
    migrado_en TIMESTAMPTZ,

    CONSTRAINT chk_cuentas_acceso_rol
        CHECK (
            rol IN (
                'DESARROLLADOR',
                'ADMINISTRADOR',
                'OPERADOR',
                'CONDUCTOR'
            )
        ),

    CONSTRAINT chk_cuentas_acceso_conductor
        CHECK (id_conductor IS NULL OR id_conductor > 0)
);

CREATE INDEX IF NOT EXISTS ix_cuentas_acceso_rol
    ON seguridad.cuentas_acceso (rol);

CREATE INDEX IF NOT EXISTS ix_cuentas_acceso_activo
    ON seguridad.cuentas_acceso (activo);


-- ============================================================
-- ESQUEMA: SEGURIDAD
-- TABLA: SESIONES_ACCESO
-- Sesiones emitidas (tokens opacos). Solo se guarda el hash SHA-256
-- del token, nunca el token en texto plano.
-- ============================================================

CREATE TABLE IF NOT EXISTS seguridad.sesiones_acceso (
    token_hash CHAR(64) PRIMARY KEY,

    id_usuario BIGINT NOT NULL,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_en TIMESTAMPTZ NOT NULL,

    revocado BOOLEAN NOT NULL DEFAULT FALSE,
    revocado_en TIMESTAMPTZ,

    agente_hash CHAR(64),
    ip_prefijo VARCHAR(64),

    CONSTRAINT fk_sesiones_acceso_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES seguridad.cuentas_acceso (id_usuario)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_sesiones_acceso_usuario
    ON seguridad.sesiones_acceso (id_usuario);

CREATE INDEX IF NOT EXISTS ix_sesiones_acceso_vigentes
    ON seguridad.sesiones_acceso (id_usuario)
    WHERE revocado = FALSE;

CREATE INDEX IF NOT EXISTS ix_sesiones_acceso_expiracion
    ON seguridad.sesiones_acceso (expira_en);


-- ============================================================
-- ESQUEMA: SEGURIDAD
-- TABLA: AUDITORIA_ACCESO
-- Bitácora append-only de eventos de seguridad.
-- ============================================================

CREATE TABLE IF NOT EXISTS seguridad.auditoria_acceso (
    id_auditoria BIGSERIAL PRIMARY KEY,

    accion VARCHAR(80) NOT NULL,
    actor VARCHAR(255),
    actor_id BIGINT,

    detalle JSONB NOT NULL DEFAULT '{}'::jsonb,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_auditoria_acceso_creado
    ON seguridad.auditoria_acceso (creado_en DESC);

CREATE INDEX IF NOT EXISTS ix_auditoria_acceso_accion
    ON seguridad.auditoria_acceso (accion);


-- ============================================================
-- ESQUEMA: SEGURIDAD
-- TABLA: MIGRACIONES_ACCESO
-- Registro de scripts de acceso aplicados (trazabilidad y
-- verificación de requisitos previos antes de migrar datos).
-- ============================================================

CREATE TABLE IF NOT EXISTS seguridad.migraciones_acceso (
    nombre VARCHAR(100) PRIMARY KEY,
    aplicado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- Nota: esta migración evita bloques DO $$ ... $$ a propósito. En equipos con
-- políticas de control de aplicaciones (WDAC/SAC) la biblioteca plpgsql puede
-- estar bloqueada; con SQL plano el script funciona en cualquier entorno.
INSERT INTO seguridad.migraciones_acceso (nombre)
VALUES ('006_seguridad_acceso')
ON CONFLICT (nombre) DO NOTHING;


-- ============================================================
-- NOTA DE COMPATIBILIDAD
-- seguridad.usuarios (usuarios logísticos) se mantiene intacta.
-- logistica.conductores.id_usuario sigue apuntando a ella.
-- cuentas_acceso.id_conductor referencia al conductor logístico por
-- identificador; se deja sin FOREIGN KEY para no bloquear la migración
-- de cuentas con vínculos pendientes. La validación la hace el servicio
-- de autenticación (una cuenta CONDUCTOR debe tener id_conductor).
-- ============================================================
