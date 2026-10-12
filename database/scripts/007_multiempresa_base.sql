-- ============================================================
-- OptiRoute AI - FASE 1A
-- Script: 007_multiempresa_base.sql
-- Alcance: estructura multiempresa aditiva (NO migra datos).
--
-- PRECONDICION FUTURA: ejecutar 006_seguridad_acceso.sql y migrar/verificar
-- las cuentas canonicas antes de crear membresias.
--
-- SEGURIDAD:
--   * No modifica ni elimina tablas o datos existentes.
--   * No asigna automaticamente rutas, pedidos ni usuarios a una empresa.
--   * Es idempotente: CREATE IF NOT EXISTS e INSERT ON CONFLICT.
--   * Los UUID son generados por la aplicacion; no requiere extensiones.
--   * Este archivo se entrega sin ejecutarse en la base real.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS plataforma;

CREATE TABLE IF NOT EXISTS plataforma.empresas (
    id_empresa UUID PRIMARY KEY,
    codigo VARCHAR(40) NOT NULL UNIQUE,
    nombre VARCHAR(160) NOT NULL,
    identificacion_fiscal VARCHAR(40) UNIQUE,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_empresas_codigo_no_vacio CHECK (length(trim(codigo)) >= 2),
    CONSTRAINT chk_empresas_nombre_no_vacio CHECK (length(trim(nombre)) >= 2)
);

CREATE INDEX IF NOT EXISTS ix_empresas_activas
    ON plataforma.empresas (nombre)
    WHERE activa = TRUE;


-- La identidad canonica sigue siendo seguridad.cuentas_acceso.
-- DESARROLLADOR es un perfil de plataforma y deliberadamente no es un rol
-- empresarial. Los otros tres perfiles se acotan mediante esta membresia.
CREATE TABLE IF NOT EXISTS plataforma.empresa_usuarios (
    id_membresia UUID PRIMARY KEY,
    id_empresa UUID NOT NULL,
    id_cuenta BIGINT NOT NULL,
    rol VARCHAR(20) NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    es_propietario_empresa BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_empresa_usuarios_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES plataforma.empresas (id_empresa)
        ON DELETE RESTRICT,
    CONSTRAINT fk_empresa_usuarios_cuenta
        FOREIGN KEY (id_cuenta)
        REFERENCES seguridad.cuentas_acceso (id_usuario)
        ON DELETE RESTRICT,
    CONSTRAINT uq_empresa_usuarios_cuenta UNIQUE (id_empresa, id_cuenta),
    CONSTRAINT uq_empresa_usuarios_membresia_empresa
        UNIQUE (id_empresa, id_membresia),
    CONSTRAINT chk_empresa_usuarios_rol
        CHECK (rol IN ('ADMINISTRADOR', 'OPERADOR', 'CONDUCTOR')),
    CONSTRAINT chk_propietario_empresa_admin
        CHECK (NOT es_propietario_empresa OR rol = 'ADMINISTRADOR')
);

CREATE INDEX IF NOT EXISTS ix_empresa_usuarios_cuenta_activa
    ON plataforma.empresa_usuarios (id_cuenta, id_empresa)
    WHERE activa = TRUE;

CREATE INDEX IF NOT EXISTS ix_empresa_usuarios_empresa_rol
    ON plataforma.empresa_usuarios (id_empresa, rol)
    WHERE activa = TRUE;


-- Capa de transicion: vincula recursos legados sin añadir columnas ni
-- actualizar las tablas actuales. La unicidad global impide que el mismo
-- recurso quede asociado simultaneamente con dos empresas.
CREATE TABLE IF NOT EXISTS plataforma.recursos_empresa (
    id_vinculo UUID PRIMARY KEY,
    id_empresa UUID NOT NULL,
    tipo_recurso VARCHAR(20) NOT NULL,
    id_recurso BIGINT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_recursos_empresa_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES plataforma.empresas (id_empresa)
        ON DELETE RESTRICT,
    CONSTRAINT uq_recurso_empresa_global UNIQUE (tipo_recurso, id_recurso),
    CONSTRAINT uq_recurso_empresa_compuesto
        UNIQUE (id_empresa, tipo_recurso, id_recurso),
    CONSTRAINT chk_recurso_empresa_tipo
        CHECK (tipo_recurso IN (
            'CLIENTE', 'CONDUCTOR', 'VEHICULO', 'PEDIDO', 'RUTA', 'ZONA', 'GUIA'
        )),
    CONSTRAINT chk_recurso_empresa_id CHECK (id_recurso > 0)
);

CREATE INDEX IF NOT EXISTS ix_recursos_empresa_busqueda
    ON plataforma.recursos_empresa (id_empresa, tipo_recurso, id_recurso);


-- Asignacion explicita a una membresia. Es la base para que OPERADOR y
-- CONDUCTOR trabajen solo sobre rutas, pedidos o futuras guias asignadas.
CREATE TABLE IF NOT EXISTS plataforma.asignaciones_operativas (
    id_asignacion UUID PRIMARY KEY,
    id_empresa UUID NOT NULL,
    id_membresia UUID NOT NULL,
    tipo_recurso VARCHAR(20) NOT NULL,
    id_recurso BIGINT NOT NULL,
    asignado_por BIGINT NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finalizado_en TIMESTAMPTZ,

    CONSTRAINT fk_asignaciones_membresia_empresa
        FOREIGN KEY (id_empresa, id_membresia)
        REFERENCES plataforma.empresa_usuarios (id_empresa, id_membresia)
        ON DELETE RESTRICT,
    CONSTRAINT fk_asignaciones_recurso_empresa
        FOREIGN KEY (id_empresa, tipo_recurso, id_recurso)
        REFERENCES plataforma.recursos_empresa
            (id_empresa, tipo_recurso, id_recurso)
        ON DELETE RESTRICT,
    CONSTRAINT fk_asignaciones_actor
        FOREIGN KEY (asignado_por)
        REFERENCES seguridad.cuentas_acceso (id_usuario)
        ON DELETE RESTRICT,
    CONSTRAINT chk_asignaciones_tipo
        CHECK (tipo_recurso IN ('PEDIDO', 'RUTA', 'ZONA', 'GUIA')),
    CONSTRAINT chk_asignacion_fechas
        CHECK (finalizado_en IS NULL OR finalizado_en >= creado_en)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_asignacion_operativa_activa
    ON plataforma.asignaciones_operativas
        (id_empresa, id_membresia, tipo_recurso, id_recurso)
    WHERE activa = TRUE;

CREATE INDEX IF NOT EXISTS ix_asignaciones_recurso_activas
    ON plataforma.asignaciones_operativas
        (id_empresa, tipo_recurso, id_recurso)
    WHERE activa = TRUE;


CREATE TABLE IF NOT EXISTS plataforma.migraciones (
    nombre VARCHAR(120) PRIMARY KEY,
    aplicado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO plataforma.migraciones (nombre)
VALUES ('007_multiempresa_base')
ON CONFLICT (nombre) DO NOTHING;
