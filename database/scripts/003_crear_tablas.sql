-- ============================================================
-- OptiRoute AI
-- Script: 003_crear_tablas.sql
-- Descripción: Creación de las tablas principales
-- ============================================================


-- ============================================================
-- ESQUEMA: SEGURIDAD
-- ============================================================

CREATE TABLE IF NOT EXISTS seguridad.usuarios (
    id_usuario BIGSERIAL PRIMARY KEY,

    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,

    correo VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,

    tipo_usuario VARCHAR(20) NOT NULL DEFAULT 'OPERADOR',

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_usuarios_tipo
        CHECK (
            tipo_usuario IN (
                'ADMINISTRADOR',
                'OPERADOR',
                'CONDUCTOR'
            )
        )
);


-- ============================================================
-- ESQUEMA: OPERACIONES
-- TABLA: CLIENTES
-- ============================================================

CREATE TABLE IF NOT EXISTS operaciones.clientes (
    id_cliente BIGSERIAL PRIMARY KEY,

    tipo_cliente VARCHAR(20) NOT NULL DEFAULT 'PERSONA',

    nombres VARCHAR(100),
    apellidos VARCHAR(100),
    razon_social VARCHAR(200),

    identificacion VARCHAR(20),

    correo VARCHAR(255),
    telefono VARCHAR(30),

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_clientes_tipo
        CHECK (tipo_cliente IN ('PERSONA', 'EMPRESA')),

    CONSTRAINT chk_clientes_nombre
        CHECK (
            (
                tipo_cliente = 'PERSONA'
                AND nombres IS NOT NULL
                AND apellidos IS NOT NULL
            )
            OR
            (
                tipo_cliente = 'EMPRESA'
                AND razon_social IS NOT NULL
            )
        )
);


-- ============================================================
-- ESQUEMA: OPERACIONES
-- TABLA: DIRECCIONES
-- ============================================================

CREATE TABLE IF NOT EXISTS operaciones.direcciones (
    id_direccion BIGSERIAL PRIMARY KEY,

    id_cliente BIGINT NOT NULL,

    etiqueta VARCHAR(50) NOT NULL DEFAULT 'PRINCIPAL',

    direccion_texto VARCHAR(300) NOT NULL,

    ciudad VARCHAR(100) NOT NULL,
    provincia VARCHAR(100),
    pais VARCHAR(100) NOT NULL DEFAULT 'Ecuador',

    latitud NUMERIC(9,6) NOT NULL,
    longitud NUMERIC(9,6) NOT NULL,

    referencia VARCHAR(300),

    es_principal BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_direcciones_cliente
        FOREIGN KEY (id_cliente)
        REFERENCES operaciones.clientes(id_cliente),

    CONSTRAINT chk_direcciones_latitud
        CHECK (latitud BETWEEN -90 AND 90),

    CONSTRAINT chk_direcciones_longitud
        CHECK (longitud BETWEEN -180 AND 180)
);

-- ============================================================
-- ESQUEMA: LOGISTICA
-- TABLA: CONDUCTORES
-- ============================================================

CREATE TABLE IF NOT EXISTS logistica.conductores (
    id_conductor BIGSERIAL PRIMARY KEY,

    id_usuario BIGINT NOT NULL UNIQUE,

    numero_licencia VARCHAR(50) NOT NULL UNIQUE,
    tipo_licencia VARCHAR(20),

    telefono VARCHAR(30),

    disponible BOOLEAN NOT NULL DEFAULT TRUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_conductores_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES seguridad.usuarios(id_usuario)
);

-- ============================================================
-- ESQUEMA: LOGISTICA
-- TABLA: VEHICULOS
-- ============================================================

CREATE TABLE IF NOT EXISTS logistica.vehiculos (
    id_vehiculo BIGSERIAL PRIMARY KEY,

    placa VARCHAR(15) NOT NULL UNIQUE,

    marca VARCHAR(80),
    modelo VARCHAR(80),
    anio SMALLINT,

    tipo_vehiculo VARCHAR(30) NOT NULL,

    capacidad_kg NUMERIC(10,2),

    estado VARCHAR(20) NOT NULL DEFAULT 'DISPONIBLE',

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_vehiculos_tipo
        CHECK (
            tipo_vehiculo IN (
                'MOTO',
                'AUTO',
                'CAMIONETA',
                'CAMION'
            )
        ),

    CONSTRAINT chk_vehiculos_estado
        CHECK (
            estado IN (
                'DISPONIBLE',
                'EN_RUTA',
                'MANTENIMIENTO',
                'INACTIVO'
            )
        ),

    CONSTRAINT chk_vehiculos_capacidad
        CHECK (
            capacidad_kg IS NULL
            OR capacidad_kg > 0
        ),

    CONSTRAINT chk_vehiculos_anio
        CHECK (
            anio IS NULL
            OR anio BETWEEN 1980 AND 2100
        )
);
-- ============================================================
-- ESQUEMA: OPERACIONES
-- TABLA: PEDIDOS
-- ============================================================

CREATE TABLE IF NOT EXISTS operaciones.pedidos (
    id_pedido BIGSERIAL PRIMARY KEY,

    codigo VARCHAR(30) NOT NULL UNIQUE,

    id_cliente BIGINT NOT NULL,
    id_direccion_entrega BIGINT NOT NULL,

    descripcion VARCHAR(300),

    peso_kg NUMERIC(10,2),
    volumen_m3 NUMERIC(10,3),

    prioridad VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
    estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',

    fecha_solicitada DATE,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_pedidos_cliente
        FOREIGN KEY (id_cliente)
        REFERENCES operaciones.clientes(id_cliente),

    CONSTRAINT fk_pedidos_direccion
        FOREIGN KEY (id_direccion_entrega)
        REFERENCES operaciones.direcciones(id_direccion),

    CONSTRAINT chk_pedidos_peso
        CHECK (peso_kg IS NULL OR peso_kg > 0),

    CONSTRAINT chk_pedidos_volumen
        CHECK (volumen_m3 IS NULL OR volumen_m3 > 0),

    CONSTRAINT chk_pedidos_prioridad
        CHECK (
            prioridad IN ('BAJA', 'NORMAL', 'ALTA', 'URGENTE')
        ),

    CONSTRAINT chk_pedidos_estado
        CHECK (
            estado IN (
                'PENDIENTE',
                'PLANIFICADO',
                'EN_RUTA',
                'ENTREGADO',
                'CANCELADO'
            )
        )
);

-- ============================================================
-- ESQUEMA: OPERACIONES
-- TABLA: ENTREGAS
-- ============================================================

CREATE TABLE IF NOT EXISTS operaciones.entregas (
    id_entrega BIGSERIAL PRIMARY KEY,

    id_pedido BIGINT NOT NULL UNIQUE,

    estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',

    fecha_salida TIMESTAMPTZ,
    fecha_entrega TIMESTAMPTZ,

    nombre_receptor VARCHAR(150),
    observaciones VARCHAR(500),

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_entregas_pedido
        FOREIGN KEY (id_pedido)
        REFERENCES operaciones.pedidos(id_pedido),

    CONSTRAINT chk_entregas_estado
        CHECK (
            estado IN (
                'PENDIENTE',
                'EN_RUTA',
                'ENTREGADO',
                'FALLIDO',
                'CANCELADO'
            )
        ),

    CONSTRAINT chk_entregas_fechas
        CHECK (
            fecha_entrega IS NULL
            OR fecha_salida IS NULL
            OR fecha_entrega >= fecha_salida
        )
);

-- ============================================================
-- ESQUEMA: LOGISTICA
-- TABLA: NODOS
-- Representa los vertices del grafo
-- ============================================================

CREATE TABLE IF NOT EXISTS logistica.nodos (
    id_nodo BIGSERIAL PRIMARY KEY,

    nombre VARCHAR(150) NOT NULL,

    tipo_nodo VARCHAR(30) NOT NULL,

    latitud NUMERIC(9,6) NOT NULL,
    longitud NUMERIC(9,6) NOT NULL,

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_nodos_tipo
        CHECK (
            tipo_nodo IN (
                'BODEGA',
                'CLIENTE',
                'INTERSECCION',
                'PUNTO_ENTREGA',
                'OTRO'
            )
        ),

    CONSTRAINT chk_nodos_latitud
        CHECK (latitud BETWEEN -90 AND 90),

    CONSTRAINT chk_nodos_longitud
        CHECK (longitud BETWEEN -180 AND 180)
);


-- ============================================================
-- ESQUEMA: LOGISTICA
-- TABLA: CONEXIONES
-- Representa las aristas del grafo
-- ============================================================

CREATE TABLE IF NOT EXISTS logistica.conexiones (
    id_conexion BIGSERIAL PRIMARY KEY,

    id_nodo_origen BIGINT NOT NULL,
    id_nodo_destino BIGINT NOT NULL,

    distancia_km NUMERIC(10,3) NOT NULL,
    tiempo_minutos NUMERIC(10,2),

    costo NUMERIC(10,2) NOT NULL DEFAULT 0,

    bidireccional BOOLEAN NOT NULL DEFAULT TRUE,

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_conexiones_origen
        FOREIGN KEY (id_nodo_origen)
        REFERENCES logistica.nodos(id_nodo),

    CONSTRAINT fk_conexiones_destino
        FOREIGN KEY (id_nodo_destino)
        REFERENCES logistica.nodos(id_nodo),

    CONSTRAINT chk_conexiones_nodos
        CHECK (id_nodo_origen <> id_nodo_destino),

    CONSTRAINT chk_conexiones_distancia
        CHECK (distancia_km > 0),

    CONSTRAINT chk_conexiones_tiempo
        CHECK (
            tiempo_minutos IS NULL
            OR tiempo_minutos > 0
        ),

    CONSTRAINT chk_conexiones_costo
        CHECK (costo >= 0),

    CONSTRAINT uq_conexiones_origen_destino
        UNIQUE (id_nodo_origen, id_nodo_destino)
);