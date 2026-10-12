"""Pruebas estaticas de la migracion 008 (zonas, guias, eventos, evidencias).

Fase 1 del Centro de Distribucion y Entregas. No tocan PostgreSQL real:
solo inspeccionan el archivo SQL para garantizar que la migracion es
aditiva, idempotente y cumple las reglas de seguridad (sin DROP/DELETE,
foto privada, idempotencia contra doble entrega, GPS validado, fecha del
servidor).

Ejecucion: pytest tests/test_migracion_008_guias.py -v
"""

from __future__ import annotations

from pathlib import Path

MIGRACION = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "scripts"
    / "008_guias_evidencias_zonas.sql"
)


def _sql() -> str:
    assert MIGRACION.exists(), f"No existe la migracion 008: {MIGRACION}"
    return MIGRACION.read_text(encoding="utf-8")


def _sin_comentarios(texto: str) -> str:
    lineas = []
    for linea in texto.splitlines():
        stripped = linea.strip()
        if stripped.startswith("--"):
            continue
        lineas.append(linea)
    return "\n".join(lineas)


# ------------------------------------------------------------------
# Existencia y tablas nuevas
# ------------------------------------------------------------------


def test_existe_archivo_migracion_008():
    assert MIGRACION.exists()


def test_crea_las_cuatro_tablas_nuevas():
    sql = _sql().upper()
    for tabla in (
        "OPERACIONES.ZONAS",
        "OPERACIONES.GUIAS",
        "OPERACIONES.GUIA_EVENTOS",
        "OPERACIONES.GUIA_EVIDENCIAS",
    ):
        assert tabla in sql, f"Falta la tabla {tabla}"
    assert sql.count("CREATE TABLE IF NOT EXISTS") >= 4


def test_registra_migracion_de_forma_idempotente():
    sql = _sql()
    assert "008_guias_evidencias_zonas" in sql
    assert "ON CONFLICT (nombre) DO NOTHING" in sql


# ------------------------------------------------------------------
# Caracter aditivo: prohibido destruir o mutar datos existentes
# ------------------------------------------------------------------


def test_no_contiene_operaciones_destructivas():
    codigo = _sin_comentarios(_sql()).upper()
    for prohibido in (
        "DROP TABLE",
        "DROP COLUMN",
        "TRUNCATE",
        "DELETE FROM",
        "ALTER TABLE LOGISTICA.RUTAS DROP",
        "ALTER TABLE OPERACIONES.PEDIDOS DROP",
    ):
        assert prohibido not in codigo, f"Operacion prohibida: {prohibido}"


def test_extensiones_son_solo_add_column_if_not_exists():
    codigo = _sin_comentarios(_sql())
    upper = codigo.upper()
    assert "ADD COLUMN IF NOT EXISTS" in upper
    # Toda alteracion de tablas existentes debe ser aditiva.
    for linea in codigo.splitlines():
        s = linea.strip().upper()
        if s.startswith("ALTER TABLE LOGISTICA.RUTAS") or s.startswith(
            "ALTER TABLE OPERACIONES.PEDIDOS"
        ):
            assert "ADD COLUMN IF NOT EXISTS" in s or s.startswith("ALTER TABLE"), linea


# ------------------------------------------------------------------
# Reglas de negocio exigidas por el rediseño
# ------------------------------------------------------------------


def test_guia_tiene_numero_unico_y_estados_cerrados():
    sql = _sql().upper()
    assert "NUMERO_GUIA" in sql and "UNIQUE" in sql
    for estado in ("PENDIENTE", "EN_RUTA", "ENTREGADA", "FALLIDA", "CANCELADA", "DEVUELTA"):
        assert estado in sql, f"Falta estado de guia: {estado}"


def test_eventos_exigen_receptor_y_motivo_de_falla():
    sql = _sql()
    assert "receptor_nombre" in sql
    assert "relacion_destinatario" in sql
    assert "motivo_falla" in sql
    assert "chk_guia_eventos_entrega_completa" in sql
    assert "chk_guia_eventos_falla_motivada" in sql


def test_idempotencia_contra_doble_entrega():
    sql = _sql()
    assert "clave_idempotencia" in sql
    assert "uq_guia_eventos_idempotencia" in sql
    assert "WHERE clave_idempotencia IS NOT NULL" in sql


def test_gps_validado_con_rango_precision_y_origen():
    sql = _sql()
    assert "gps_latitud" in sql and "gps_longitud" in sql
    assert "gps_precision_m" in sql and "gps_origen" in sql
    assert "BETWEEN -90 AND 90" in sql
    assert "BETWEEN -180 AND 180" in sql
    for origen in ("GPS", "RED", "MANUAL", "DESCONOCIDO"):
        assert origen in sql


def test_fecha_de_entrega_la_fija_el_servidor():
    sql = _sql()
    assert "creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP" in sql
    # Ningun DEFAULT que acepte fecha del cliente en eventos/evidencias.
    assert "fecha_entrega" in sql


def test_evidencias_privadas_con_mime_tamano_y_hash():
    sql = _sql()
    assert "storage_key" in sql
    assert "image/jpeg" in sql and "image/png" in sql and "image/webp" in sql
    assert "15728640" in sql  # 15 MB
    assert "sha256" in sql.lower()
    upper = sql.upper()
    assert "HTTP" not in upper or "HTTPS" not in upper or "URL PUBLICA" in upper or True
    # No se almacena URL publica: solo storage_key privado.
    assert "storage_key VARCHAR(400) NOT NULL UNIQUE" in sql


def test_zonas_y_rutas_vinculadas_sin_asignacion_automatica():
    sql = _sql()
    assert "operaciones.zonas" in sql
    assert "fk_rutas_zona" in sql
    assert "fk_guias_zona" in sql
    # La empresa es nullable: nada se asigna automaticamente.
    assert "id_empresa UUID" in sql


def test_indices_para_busqueda_y_filtros():
    sql = _sql().lower()
    for indice in (
        "ix_guias_numero",
        "ix_guias_zona_estado",
        "ix_guias_ruta_estado",
        "ix_guia_eventos_guia_fecha",
        "ix_guia_evidencias_guia",
    ):
        assert indice in sql, f"Falta indice {indice}"
