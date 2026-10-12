-- ============================================================
-- OptiRoute AI - FASE 1 (Centro de Distribucion y Entregas)
-- Script: 008_guias_evidencias_zonas.sql
-- Alcance: entidades nuevas para OPERADOR/CONDUCTOR (zonas, guias,
--          eventos de guia y evidencias). Estructura aditiva.
--
-- PRECONDICION: haber aplicado 003, 006 y 007. No se ejecuta en la
-- base real sin autorizacion explicita.
--
-- SEGURIDAD / REGLAS DE ESTA MIGRACION:
--   * NO modifica ni elimina tablas, columnas ni datos existentes.
--   * Solo ADD COLUMN IF NOT EXISTS en tablas existentes
--     (logistica.rutas, operaciones.pedidos) y CREATE TABLE IF NOT EXISTS
--     para las 4 tablas nuevas.
--   * Es idempotente: puede ejecutarse varias veces sin error
--     (IF NOT EXISTS, ON CONFLICT DO NOTHING, indices IF NOT EXISTS).
--   * La fecha/hora de entrega la fija el servidor (DEFAULT
--     CURRENT_TIMESTAMP); nunca se acepta la del dispositivo.
--   * Las fotos son privadas: se guarda solo storage_key + hash;
--     jamas una URL publica. El acceso temporal se concede por codigo
--     (endpoint de URL firmada, fuera de esta migracion).
--   * Unicidad parcial para idempotencia: una guia se entrega una sola
--     vez aunque el dispositivo reintente (UNIQUE numero_guia y UNIQUE
--     parcial por clave_idempotencia en eventos).
--   * ZONA y GUIA ya estaban reservados en plataforma.recursos_empresa
--     (007); esta migracion crea sus tablas hijas para que el repositorio
--     pueda aceptarlos en una fase posterior autorizada.
--   * Este archivo se entrega SIN ejecutarse en PostgreSQL real.
-- ============================================================

-- ------------------------------------------------------------
-- TABLA: operaciones.zonas
-- Catalogo de zonas de reparto (La Carolina, La Pradera,
-- Calderon, etc.). Sin geometria en Fase 1: el poligono vendra
-- en una migracion posterior si se requiere.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operaciones.zonas (
    id_zona BIGSERIAL PRIMARY KEY,

    -- Empresa propietaria (NULL = zona global/legada sin asignar).
    -- No se asigna automaticamente ninguna zona a una empresa.
    id_empresa UUID,

    codigo VARCHAR(40) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,

    ciudad VARCHAR(100) NOT NULL DEFAULT 'Quito',
    provincia VARCHAR(100) NOT NULL DEFAULT 'Pichincha',
    pais VARCHAR(100) NOT NULL DEFAULT 'Ecuador',

    activa BOOLEAN NOT NULL DEFAULT TRUE,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_zonas_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES plataforma.empresas (id_empresa)
        ON DELETE RESTRICT,

    CONSTRAINT chk_zonas_codigo_no_vacio
        CHECK (length(trim(codigo)) >= 2),

    CONSTRAINT chk_zonas_nombre_no_vacio
        CHECK (length(trim(nombre)) >= 2)
);

CREATE INDEX IF NOT EXISTS ix_zonas_empresa_activa
    ON operaciones.zonas (id_empresa, nombre)
    WHERE activa = TRUE;

-- ------------------------------------------------------------
-- TABLA: operaciones.guias
-- Guia de transporte/asignacion. Nace de un pedido (1 a 1) o de
-- forma independiente (id_pedido NULL, p. ej. guia externa).
-- El numero_guia es el identificador operativo que buscan
-- OPERADOR y CONDUCTOR (no el id interno).
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operaciones.guias (
    id_guia BIGSERIAL PRIMARY KEY,

    numero_guia VARCHAR(40) NOT NULL UNIQUE,

    -- Empresa propietaria (NULL = guia legada sin asignar).
    id_empresa UUID,

    -- Pedido origen (NULL = guia sin pedido asociado).
    id_pedido BIGINT,

    -- Ruta y zona asignadas (NULL = sin asignar todavia).
    id_ruta BIGINT,
    id_zona BIGINT,

    destinatario_nombre VARCHAR(200) NOT NULL,
    direccion_texto VARCHAR(300) NOT NULL,
    telefono_autorizado VARCHAR(30),

    estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',

    intentos_entrega SMALLINT NOT NULL DEFAULT 0,

    -- Clave de idempotencia del ultimo intento (la genera el
    -- servidor o el cliente y se valida en guia_eventos).
    clave_idempotencia VARCHAR(64),

    fecha_entrega TIMESTAMPTZ,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_guias_empresa
        FOREIGN KEY (id_empresa)
        REFERENCES plataforma.empresas (id_empresa)
        ON DELETE RESTRICT,

    CONSTRAINT fk_guias_pedido
        FOREIGN KEY (id_pedido)
        REFERENCES operaciones.pedidos (id_pedido)
        ON DELETE RESTRICT,

    CONSTRAINT fk_guias_ruta
        FOREIGN KEY (id_ruta)
        REFERENCES logistica.rutas (id_ruta)
        ON DELETE RESTRICT,

    CONSTRAINT fk_guias_zona
        FOREIGN KEY (id_zona)
        REFERENCES operaciones.zonas (id_zona)
        ON DELETE RESTRICT,

    CONSTRAINT chk_guias_numero_no_vacio
        CHECK (length(trim(numero_guia)) >= 3),

    CONSTRAINT chk_guias_estado
        CHECK (
            estado IN (
                'PENDIENTE',
                'EN_RUTA',
                'ENTREGADA',
                'FALLIDA',
                'CANCELADA',
                'DEVUELTA'
            )
        ),

    CONSTRAINT chk_guias_intentos
        CHECK (intentos_entrega >= 0),

    CONSTRAINT chk_guias_telefono
        CHECK (
            telefono_autorizado IS NULL
            OR length(trim(telefono_autorizado)) BETWEEN 7 AND 30
        ),

    CONSTRAINT chk_guias_fecha_entrega
        CHECK (
            estado NOT IN ('ENTREGADA', 'FALLIDA')
            OR fecha_entrega IS NOT NULL
        )
);

-- Un pedido genera como maximo una guia (relacion 1 a 1);
-- las guias sin pedido (externas) no se restringen.
CREATE UNIQUE INDEX IF NOT EXISTS uq_guias_pedido_unico
    ON operaciones.guias (id_pedido)
    WHERE id_pedido IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_guias_numero
    ON operaciones.guias (numero_guia);

CREATE INDEX IF NOT EXISTS ix_guias_zona_estado
    ON operaciones.guias (id_zona, estado);

CREATE INDEX IF NOT EXISTS ix_guias_ruta_estado
    ON operaciones.guias (id_ruta, estado);

CREATE INDEX IF NOT EXISTS ix_guias_empresa_estado
    ON operaciones.guias (id_empresa, estado);

-- ------------------------------------------------------------
-- TABLA: operaciones.guia_eventos
-- Historial append-only de cada guia (asignacion, salida,
-- entrega exitosa, entrega fallida, novedad, cancelacion).
-- Solo INSERT: ningun UPDATE/DELETE desde la aplicacion.
-- La marca temporal la pone el servidor (creado_en).
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operaciones.guia_eventos (
    id_evento BIGSERIAL PRIMARY KEY,

    id_guia BIGINT NOT NULL,

    tipo VARCHAR(30) NOT NULL,

    -- Cuenta que registra el evento (actor auditado).
    actor_cuenta BIGINT,

    -- Datos de la entrega exitosa (NULL en otros tipos).
    receptor_nombre VARCHAR(150),
    relacion_destinatario VARCHAR(60),

    motivo_falla VARCHAR(300),

    -- GPS del dispositivo en el momento del registro.
    -- Se valida rango en CHECK; la precision/origen se auditan
    -- pero la decision operativa usa la marca del servidor.
    gps_latitud NUMERIC(9, 6),
    gps_longitud NUMERIC(9, 6),
    gps_precision_m NUMERIC(8, 2),
    gps_origen VARCHAR(20),

    -- Idempotencia: reintentos del mismo intento comparten clave.
    clave_idempotencia VARCHAR(64),

    observaciones VARCHAR(500),

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_guia_eventos_guia
        FOREIGN KEY (id_guia)
        REFERENCES operaciones.guias (id_guia)
        ON DELETE CASCADE,

    CONSTRAINT fk_guia_eventos_actor
        FOREIGN KEY (actor_cuenta)
        REFERENCES seguridad.cuentas_acceso (id_usuario)
        ON DELETE RESTRICT,

    CONSTRAINT chk_guia_eventos_tipo
        CHECK (
            tipo IN (
                'ASIGNADA',
                'EN_RUTA',
                'ENTREGADA',
                'FALLIDA',
                'NOVEDAD',
                'CANCELADA',
                'DEVUELTA'
            )
        ),

    CONSTRAINT chk_guia_eventos_gps_lat
        CHECK (gps_latitud IS NULL OR (gps_latitud BETWEEN -90 AND 90)),

    CONSTRAINT chk_guia_eventos_gps_lng
        CHECK (gps_longitud IS NULL OR (gps_longitud BETWEEN -180 AND 180)),

    CONSTRAINT chk_guia_eventos_gps_precision
        CHECK (gps_precision_m IS NULL OR gps_precision_m > 0),

    CONSTRAINT chk_guia_eventos_gps_origen
        CHECK (
            gps_origen IS NULL
            OR gps_origen IN ('GPS', 'RED', 'MANUAL', 'DESCONOCIDO')
        ),

    CONSTRAINT chk_guia_eventos_entrega_completa
        CHECK (
            tipo <> 'ENTREGADA'
            OR (
                receptor_nombre IS NOT NULL
                AND length(trim(receptor_nombre)) >= 2
                AND relacion_destinatario IS NOT NULL
            )
        ),

    CONSTRAINT chk_guia_eventos_falla_motivada
        CHECK (
            tipo <> 'FALLIDA'
            OR (
                motivo_falla IS NOT NULL
                AND length(trim(motivo_falla)) >= 5
            )
        )
);

-- Reintentos del mismo intento: una sola fila efectiva por clave.
CREATE UNIQUE INDEX IF NOT EXISTS uq_guia_eventos_idempotencia
    ON operaciones.guia_eventos (id_guia, clave_idempotencia)
    WHERE clave_idempotencia IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_guia_eventos_guia_fecha
    ON operaciones.guia_eventos (id_guia, creado_en DESC);

CREATE INDEX IF NOT EXISTS ix_guia_eventos_tipo_fecha
    ON operaciones.guia_eventos (tipo, creado_en DESC);

-- ------------------------------------------------------------
-- TABLA: operaciones.guia_evidencias
-- Fotos privadas de cada entrega (foto de la guia firmada y
-- foto del paquete). Solo metadatos + storage_key privado;
-- el binario vive en almacenamiento privado fuera de la BD.
-- Limites validados en BD y re-validados en el backend:
-- JPEG/PNG/WebP, 1 byte a 15 MB, sha256 obligatorio.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operaciones.guia_evidencias (
    id_evidencia BIGSERIAL PRIMARY KEY,

    id_guia BIGINT NOT NULL,
    id_evento BIGINT,

    tipo VARCHAR(30) NOT NULL,

    -- Clave privada en el almacenamiento (bucket privado).
    -- Nunca una URL publica.
    storage_key VARCHAR(400) NOT NULL UNIQUE,

    mime VARCHAR(80) NOT NULL,
    tamano_bytes BIGINT NOT NULL,
    sha256 CHAR(64) NOT NULL,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_guia_evidencias_guia
        FOREIGN KEY (id_guia)
        REFERENCES operaciones.guias (id_guia)
        ON DELETE CASCADE,

    CONSTRAINT fk_guia_evidencias_evento
        FOREIGN KEY (id_evento)
        REFERENCES operaciones.guia_eventos (id_evento)
        ON DELETE SET NULL,

    CONSTRAINT chk_guia_evidencias_tipo
        CHECK (
            tipo IN ('FOTO_GUIA', 'FOTO_PAQUETE', 'OTRO')
        ),

    CONSTRAINT chk_guia_evidencias_mime
        CHECK (
            mime IN ('image/jpeg', 'image/png', 'image/webp')
        ),

    CONSTRAINT chk_guia_evidencias_tamano
        CHECK (tamano_bytes > 0 AND tamano_bytes <= 15728640),

    CONSTRAINT chk_guia_evidencias_sha
        CHECK (sha256 ~ '^[0-9a-fA-F]{64}$')
);

CREATE INDEX IF NOT EXISTS ix_guia_evidencias_guia
    ON operaciones.guia_evidencias (id_guia);

CREATE INDEX IF NOT EXISTS ix_guia_evidencias_evento
    ON operaciones.guia_evidencias (id_evento);

-- ------------------------------------------------------------
-- EXTENSIONES ADITIVAS EN TABLAS EXISTENTES
-- (solo ADD COLUMN IF NOT EXISTS; jamas DROP/ALTER TYPE)
-- ------------------------------------------------------------

ALTER TABLE logistica.rutas
    ADD COLUMN IF NOT EXISTS id_zona BIGINT;

ALTER TABLE logistica.rutas
    ADD COLUMN IF NOT EXISTS nombre_ruta VARCHAR(120);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_rutas_zona'
          AND conrelid = 'logistica.rutas'::regclass
    ) THEN
        ALTER TABLE logistica.rutas
            ADD CONSTRAINT fk_rutas_zona
            FOREIGN KEY (id_zona)
            REFERENCES operaciones.zonas (id_zona)
            ON DELETE RESTRICT;
    END IF;
END
$$;

-- Telefono autorizado a nivel pedido para backfill de guias
-- (la fuente operativa sera operaciones.guias.telefono_autorizado).
ALTER TABLE operaciones.pedidos
    ADD COLUMN IF NOT EXISTS telefono_autorizado VARCHAR(30);

-- ------------------------------------------------------------
-- REGISTRO DE MIGRACION (idempotente)
-- ------------------------------------------------------------

INSERT INTO plataforma.migraciones (nombre)
VALUES ('008_guias_evidencias_zonas')
ON CONFLICT (nombre) DO NOTHING;
