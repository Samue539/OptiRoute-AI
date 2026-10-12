"""Consultas de catalogo para clientes y sus direcciones."""

from backend.app.core.database import obtener_conexion


def _cliente_desde_fila(fila):
    return {
        "id_cliente": fila[0],
        "tipo_cliente": fila[1],
        "nombres": fila[2],
        "apellidos": fila[3],
        "razon_social": fila[4],
        "identificacion": fila[5],
        "correo": fila[6],
        "telefono": fila[7],
        "activo": fila[8],
        "creado_en": fila[9],
    }


def _consultar_clientes(consulta, parametros=None):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(consulta, parametros)
            return cursor.fetchall()
    finally:
        conexion.close()


def listar_clientes():
    filas = _consultar_clientes(
        """
        SELECT
            id_cliente, tipo_cliente, nombres, apellidos, razon_social,
            identificacion, correo, telefono, activo, creado_en
        FROM operaciones.clientes
        ORDER BY creado_en DESC, id_cliente DESC;
        """
    )
    return [_cliente_desde_fila(fila) for fila in filas]


def obtener_cliente(id_cliente: int):
    filas = _consultar_clientes(
        """
        SELECT
            id_cliente, tipo_cliente, nombres, apellidos, razon_social,
            identificacion, correo, telefono, activo, creado_en
        FROM operaciones.clientes
        WHERE id_cliente = %s;
        """,
        (id_cliente,),
    )
    return _cliente_desde_fila(filas[0]) if filas else None


def listar_direcciones_cliente(id_cliente: int):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    d.id_direccion, d.id_cliente, d.id_nodo, d.etiqueta,
                    d.direccion_texto, d.ciudad, d.provincia, d.pais,
                    d.latitud, d.longitud, d.referencia, d.es_principal, d.activo,
                    n.id_nodo, n.nombre, n.tipo_nodo, n.latitud, n.longitud, n.activo
                FROM operaciones.direcciones d
                LEFT JOIN logistica.nodos n ON n.id_nodo = d.id_nodo
                WHERE d.id_cliente = %s
                ORDER BY d.es_principal DESC, d.id_direccion;
                """,
                (id_cliente,),
            )
            filas = cursor.fetchall()
            direcciones = []
            for fila in filas:
                nodo = None
                if fila[13] is not None:
                    nodo = {
                        "id_nodo": fila[13],
                        "nombre": fila[14],
                        "tipo_nodo": fila[15],
                        "latitud": float(fila[16]),
                        "longitud": float(fila[17]),
                        "activo": fila[18],
                    }
                direcciones.append({
                    "id_direccion": fila[0],
                    "id_cliente": fila[1],
                    "id_nodo": fila[2],
                    "etiqueta": fila[3],
                    "direccion_texto": fila[4],
                    "ciudad": fila[5],
                    "provincia": fila[6],
                    "pais": fila[7],
                    "latitud": float(fila[8]),
                    "longitud": float(fila[9]),
                    "referencia": fila[10],
                    "es_principal": fila[11],
                    "activo": fila[12],
                    "nodo": nodo,
                })
            return direcciones
    finally:
        conexion.close()


def listar_pedidos_cliente(id_cliente: int):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id_pedido, p.codigo, p.id_cliente, p.id_direccion_entrega,
                    p.descripcion, p.peso_kg, p.volumen_m3, p.prioridad, p.estado,
                    p.fecha_solicitada, p.creado_en
                FROM operaciones.pedidos p
                WHERE p.id_cliente = %s
                ORDER BY p.creado_en DESC;
                """,
                (id_cliente,),
            )
            return [
                {
                    "id_pedido": f[0],
                    "codigo": f[1],
                    "id_cliente": f[2],
                    "id_direccion_entrega": f[3],
                    "descripcion": f[4],
                    "peso_kg": float(f[5]) if f[5] is not None else None,
                    "volumen_m3": float(f[6]) if f[6] is not None else None,
                    "prioridad": f[7],
                    "estado": f[8],
                    "fecha_solicitada": f[9],
                    "creado_en": f[10],
                }
                for f in cursor.fetchall()
            ]
    finally:
        conexion.close()
