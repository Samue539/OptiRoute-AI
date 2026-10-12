"""Consultas de catalogo para vehiculos."""

from backend.app.core.database import obtener_conexion


def _numero(valor):
    return float(valor) if valor is not None else None


def _vehiculo_desde_fila(fila):
    return {
        "id_vehiculo": fila[0],
        "placa": fila[1],
        "marca": fila[2],
        "modelo": fila[3],
        "anio": fila[4],
        "tipo_vehiculo": fila[5],
        "capacidad_kg": _numero(fila[6]),
        "capacidad_volumen_m3": _numero(fila[7]),
        "estado": fila[8],
        "activo": fila[9],
        "disponible": fila[9] and fila[8] == "DISPONIBLE",
    }


def _consultar_vehiculos(consulta, parametros=None):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(consulta, parametros)
            return cursor.fetchall()
    finally:
        conexion.close()


def listar_vehiculos():
    filas = _consultar_vehiculos(
        """
        SELECT
            id_vehiculo, placa, marca, modelo, anio, tipo_vehiculo,
            capacidad_kg, capacidad_volumen_m3, estado, activo
        FROM logistica.vehiculos
        ORDER BY placa, id_vehiculo;
        """
    )
    return [_vehiculo_desde_fila(fila) for fila in filas]


def obtener_vehiculo(id_vehiculo: int):
    filas = _consultar_vehiculos(
        """
        SELECT
            id_vehiculo, placa, marca, modelo, anio, tipo_vehiculo,
            capacidad_kg, capacidad_volumen_m3, estado, activo
        FROM logistica.vehiculos
        WHERE id_vehiculo = %s;
        """,
        (id_vehiculo,),
    )
    return _vehiculo_desde_fila(filas[0]) if filas else None
