"""Consultas de catalogo para conductores."""

from backend.app.core.database import obtener_conexion


def _conductor_desde_fila(fila):
    return {
        "id_conductor": fila[0],
        "nombres": fila[1],
        "apellidos": fila[2],
        "numero_licencia": fila[3],
        "tipo_licencia": fila[4],
        "telefono": fila[5],
        "disponible": fila[6],
        "activo": fila[7],
    }


def _consultar_conductores(consulta, parametros=None):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(consulta, parametros)
            return cursor.fetchall()
    finally:
        conexion.close()


def listar_conductores():
    filas = _consultar_conductores(
        """
        SELECT
            c.id_conductor, u.nombres, u.apellidos, c.numero_licencia,
            c.tipo_licencia, c.telefono, c.disponible, c.activo
        FROM logistica.conductores c
        JOIN seguridad.usuarios u
            ON u.id_usuario = c.id_usuario
        ORDER BY u.apellidos, u.nombres, c.id_conductor;
        """
    )
    return [_conductor_desde_fila(fila) for fila in filas]


def obtener_conductor(id_conductor: int):
    filas = _consultar_conductores(
        """
        SELECT
            c.id_conductor, u.nombres, u.apellidos, c.numero_licencia,
            c.tipo_licencia, c.telefono, c.disponible, c.activo
        FROM logistica.conductores c
        JOIN seguridad.usuarios u
            ON u.id_usuario = c.id_usuario
        WHERE c.id_conductor = %s;
        """,
        (id_conductor,),
    )
    return _conductor_desde_fila(filas[0]) if filas else None
