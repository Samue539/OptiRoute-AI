"""Validaciones compartidas para reservar recursos logisticos."""

from __future__ import annotations

from backend.app.services.excepciones import RecursoNoEncontradoError, ReglaNegocioError


class RecursoOcupadoError(ReglaNegocioError):
    """Un conductor o vehiculo ya participa en otra ruta activa."""


def obtener_conductor(cursor, id_conductor: int) -> dict:
    cursor.execute(
        """
        SELECT id_conductor, numero_licencia, tipo_licencia, telefono,
               disponible, activo
        FROM logistica.conductores
        WHERE id_conductor = %s
        FOR UPDATE;
        """,
        (id_conductor,),
    )
    fila = cursor.fetchone()
    if fila is None:
        raise RecursoNoEncontradoError("El conductor no existe.")
    return {
        "id_conductor": fila[0], "numero_licencia": fila[1],
        "tipo_licencia": fila[2], "telefono": fila[3],
        "disponible": bool(fila[4]), "activo": bool(fila[5]),
    }


def obtener_vehiculo(cursor, id_vehiculo: int) -> dict:
    cursor.execute(
        """
        SELECT id_vehiculo, placa, marca, modelo, tipo_vehiculo, estado,
               activo, capacidad_kg, capacidad_volumen_m3
        FROM logistica.vehiculos
        WHERE id_vehiculo = %s
        FOR UPDATE;
        """,
        (id_vehiculo,),
    )
    fila = cursor.fetchone()
    if fila is None:
        raise RecursoNoEncontradoError("El vehiculo no existe.")
    return {
        "id_vehiculo": fila[0], "placa": fila[1], "marca": fila[2],
        "modelo": fila[3], "tipo_vehiculo": fila[4], "estado": fila[5],
        "activo": bool(fila[6]),
        "capacidad_kg": float(fila[7]) if len(fila) > 7 and fila[7] is not None else None,
        "capacidad_volumen_m3": float(fila[8]) if len(fila) > 8 and fila[8] is not None else None,
        "disponible": fila[5] == "DISPONIBLE",
    }


def conductor_en_ruta_activa(cursor, id_conductor: int, excluir_ruta: int | None = None) -> bool:
    consulta = """SELECT 1 FROM logistica.rutas WHERE id_conductor = %s
        AND estado IN ('PLANIFICADA', 'ASIGNADA', 'EN_RUTA')"""
    parametros: list[int] = [id_conductor]
    if excluir_ruta is not None:
        consulta += " AND id_ruta <> %s"
        parametros.append(excluir_ruta)
    cursor.execute(consulta + " LIMIT 1;", tuple(parametros))
    return cursor.fetchone() is not None


def vehiculo_en_ruta_activa(cursor, id_vehiculo: int, excluir_ruta: int | None = None) -> bool:
    consulta = """SELECT 1 FROM logistica.rutas WHERE id_vehiculo = %s
        AND estado IN ('PLANIFICADA', 'ASIGNADA', 'EN_RUTA')"""
    parametros: list[int] = [id_vehiculo]
    if excluir_ruta is not None:
        consulta += " AND id_ruta <> %s"
        parametros.append(excluir_ruta)
    cursor.execute(consulta + " LIMIT 1;", tuple(parametros))
    return cursor.fetchone() is not None


def validar_recursos(cursor, id_conductor: int, id_vehiculo: int, excluir_ruta: int | None = None) -> tuple[dict, dict]:
    conductor = obtener_conductor(cursor, id_conductor)
    if not conductor["activo"]:
        raise ReglaNegocioError("El conductor no esta activo.")
    if not conductor["disponible"]:
        raise ReglaNegocioError("El conductor no esta disponible.")
    if conductor_en_ruta_activa(cursor, id_conductor, excluir_ruta):
        raise RecursoOcupadoError("El conductor ya tiene una ruta activa.")
    vehiculo = obtener_vehiculo(cursor, id_vehiculo)
    if not vehiculo["activo"]:
        raise ReglaNegocioError("El vehiculo no esta activo.")
    if vehiculo["estado"] != "DISPONIBLE" or not vehiculo["disponible"]:
        raise ReglaNegocioError("El vehiculo no esta disponible.")
    if vehiculo_en_ruta_activa(cursor, id_vehiculo, excluir_ruta):
        raise RecursoOcupadoError("El vehiculo ya esta asignado a una ruta activa.")
    return conductor, vehiculo
