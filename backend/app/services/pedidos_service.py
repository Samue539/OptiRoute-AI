"""Consultas de catalogo para pedidos y sus destinos logisticos."""

from backend.app.core.database import obtener_conexion


_COLUMNAS_PEDIDO = """
    p.id_pedido,
    p.codigo,
    p.id_cliente,
    p.id_direccion_entrega,
    p.descripcion,
    p.peso_kg,
    p.volumen_m3,
    p.prioridad,
    p.estado,
    p.fecha_solicitada,
    n.id_nodo,
    n.nombre,
    n.tipo_nodo,
    n.latitud,
    n.longitud,
    n.activo,
    e.estado,
    p.creado_en
"""


def _numero(valor):
    return float(valor) if valor is not None else None


def _pedido_desde_fila(fila):
    destino = None
    if fila[10] is not None:
        destino = {
            "id_nodo": fila[10],
            "nombre": fila[11],
            "tipo_nodo": fila[12],
            "latitud": float(fila[13]),
            "longitud": float(fila[14]),
            "activo": fila[15],
        }

    return {
        "id_pedido": fila[0],
        "codigo": fila[1],
        "id_cliente": fila[2],
        "id_direccion_entrega": fila[3],
        "descripcion": fila[4],
        "peso_kg": _numero(fila[5]),
        "volumen_m3": _numero(fila[6]),
        "prioridad": fila[7],
        "estado": fila[8],
        "fecha_solicitada": fila[9],
        "destino": destino,
        "estado_entrega": fila[16],
        "creado_en": fila[17],
    }


def _consultar_pedidos(consulta, parametros=None):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(consulta, parametros)
            return cursor.fetchall()
    finally:
        conexion.close()


def listar_pedidos():
    filas = _consultar_pedidos(
        f"""
        SELECT {_COLUMNAS_PEDIDO}
        FROM operaciones.pedidos p
        JOIN operaciones.direcciones d
            ON d.id_direccion = p.id_direccion_entrega
        LEFT JOIN logistica.nodos n
            ON n.id_nodo = d.id_nodo
        LEFT JOIN operaciones.entregas e
            ON e.id_pedido = p.id_pedido
        ORDER BY p.creado_en DESC, p.id_pedido DESC;
        """
    )
    return [_pedido_desde_fila(fila) for fila in filas]


def obtener_pedido(id_pedido: int):
    filas = _consultar_pedidos(
        f"""
        SELECT {_COLUMNAS_PEDIDO}
        FROM operaciones.pedidos p
        JOIN operaciones.direcciones d
            ON d.id_direccion = p.id_direccion_entrega
        LEFT JOIN logistica.nodos n
            ON n.id_nodo = d.id_nodo
        LEFT JOIN operaciones.entregas e
            ON e.id_pedido = p.id_pedido
        WHERE p.id_pedido = %s;
        """,
        (id_pedido,),
    )
    return _pedido_desde_fila(filas[0]) if filas else None


def crear_pedido(datos: dict):
    import uuid

    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # validar cliente existe
            cursor.execute("SELECT 1 FROM operaciones.clientes WHERE id_cliente=%s", (datos["id_cliente"],))
            if cursor.fetchone() is None:
                raise ValueError("El cliente no existe.")
            cursor.execute("SELECT 1 FROM operaciones.direcciones WHERE id_direccion=%s AND id_cliente=%s", (datos["id_direccion_entrega"], datos["id_cliente"]))
            if cursor.fetchone() is None:
                raise ValueError("La dirección no pertenece al cliente.")
            # validar prioridad
            if datos.get("prioridad") not in ("BAJA", "NORMAL", "ALTA", "URGENTE"):
                raise ValueError("Prioridad inválida.")
            if datos["peso_kg"] <= 0 or datos["volumen_m3"] <= 0:
                raise ValueError("Peso y volumen deben ser mayores a 0.")
            codigo = f"PED-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute(
                """
                INSERT INTO operaciones.pedidos
                    (codigo, id_cliente, id_direccion_entrega, descripcion, peso_kg, volumen_m3, prioridad, estado, fecha_solicitada)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'PENDIENTE', COALESCE(%s, CURRENT_DATE))
                RETURNING id_pedido;
                """,
                (codigo, datos["id_cliente"], datos["id_direccion_entrega"], datos.get("descripcion"), datos["peso_kg"], datos["volumen_m3"], datos.get("prioridad","NORMAL"), datos.get("fecha_solicitada")),
            )
            id_pedido = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO operaciones.entregas (id_pedido, estado) VALUES (%s,'PENDIENTE') ON CONFLICT DO NOTHING",
                (id_pedido,),
            )
        conexion.commit()
        return obtener_pedido(id_pedido)
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def actualizar_pedido(id_pedido: int, datos: dict):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_pedido FROM operaciones.pedidos WHERE id_pedido=%s", (id_pedido,))
            if cursor.fetchone() is None:
                return None
            campos = []
            valores = []
            if datos.get("descripcion") is not None:
                campos.append("descripcion=%s")
                valores.append(datos["descripcion"])
            if datos.get("peso_kg") is not None:
                if datos["peso_kg"] <= 0:
                    raise ValueError("Peso debe ser >0")
                campos.append("peso_kg=%s")
                valores.append(datos["peso_kg"])
            if datos.get("volumen_m3") is not None:
                if datos["volumen_m3"] <= 0:
                    raise ValueError("Volumen debe ser >0")
                campos.append("volumen_m3=%s")
                valores.append(datos["volumen_m3"])
            if datos.get("prioridad") is not None:
                if datos["prioridad"] not in ("BAJA", "NORMAL", "ALTA", "URGENTE"):
                    raise ValueError("Prioridad inválida")
                campos.append("prioridad=%s")
                valores.append(datos["prioridad"])
            if not campos:
                raise ValueError("Nada para actualizar")
            campos.append("actualizado_en=CURRENT_TIMESTAMP")
            valores.append(id_pedido)
            cursor.execute(f"UPDATE operaciones.pedidos SET {', '.join(campos)} WHERE id_pedido=%s", tuple(valores))
        conexion.commit()
        return obtener_pedido(id_pedido)
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def actualizar_estado_pedido(id_pedido: int, nuevo_estado: str):
    ESTADOS = {"PENDIENTE", "PLANIFICADO", "EN_RUTA", "ENTREGADO", "CANCELADO"}
    TRANSICIONES = {
        "PENDIENTE": {"PLANIFICADO", "CANCELADO"},
        "PLANIFICADO": {"EN_RUTA", "PENDIENTE", "CANCELADO"},
        "EN_RUTA": {"ENTREGADO", "CANCELADO"},
        "ENTREGADO": set(),
        "CANCELADO": set(),
    }
    if nuevo_estado not in ESTADOS:
        raise ValueError(f"Estado no válido. Permitidos: {', '.join(ESTADOS)}")
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT estado FROM operaciones.pedidos WHERE id_pedido=%s FOR UPDATE", (id_pedido,))
            fila = cursor.fetchone()
            if fila is None:
                return None
            if nuevo_estado not in TRANSICIONES[fila[0]]:
                raise ValueError(f"No se permite cambiar de {fila[0]} a {nuevo_estado}.")
            cursor.execute("UPDATE operaciones.pedidos SET estado=%s, actualizado_en=CURRENT_TIMESTAMP WHERE id_pedido=%s", (nuevo_estado, id_pedido))
            # sincronizar entrega si corresponde
            if nuevo_estado in ("EN_RUTA", "ENTREGADO", "CANCELADO"):
                estado_entrega = "EN_RUTA" if nuevo_estado=="EN_RUTA" else "ENTREGADO" if nuevo_estado=="ENTREGADO" else "CANCELADO"
                cursor.execute("UPDATE operaciones.entregas SET estado=%s, actualizado_en=CURRENT_TIMESTAMP WHERE id_pedido=%s", (estado_entrega, id_pedido))
        conexion.commit()
        return obtener_pedido(id_pedido)
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def listar_pedidos_por_conductor(id_conductor: int):
    """Pedidos asignados a rutas cuyo conductor es ``id_conductor``.

    Se usa para que una cuenta de conductor solo vea sus propios pedidos,
    incluso si manipula parametros de la peticion.
    """

    filas = _consultar_pedidos(
        f"""
        SELECT DISTINCT {_COLUMNAS_PEDIDO}
        FROM operaciones.pedidos p
        JOIN operaciones.direcciones d
            ON d.id_direccion = p.id_direccion_entrega
        LEFT JOIN logistica.nodos n
            ON n.id_nodo = d.id_nodo
        LEFT JOIN operaciones.entregas e
            ON e.id_pedido = p.id_pedido
        JOIN logistica.ruta_pedidos rp
            ON rp.id_pedido = p.id_pedido
        JOIN logistica.rutas r
            ON r.id_ruta = rp.id_ruta
        WHERE r.id_conductor = %s
        ORDER BY p.creado_en DESC, p.id_pedido DESC;
        """,
        (id_conductor,),
    )
    return [_pedido_desde_fila(fila) for fila in filas]


def conductor_de_pedido(id_pedido: int):
    """Devuelve el id del conductor asignado al pedido, o ``None``."""

    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.id_conductor
                FROM logistica.ruta_pedidos rp
                JOIN logistica.rutas r ON r.id_ruta = rp.id_ruta
                WHERE rp.id_pedido = %s
                ORDER BY rp.creado_en DESC
                LIMIT 1;
                """,
                (id_pedido,),
            )
            fila = cursor.fetchone()
            return fila[0] if fila else None
    finally:
        conexion.close()


def obtener_ruta_de_pedido(id_pedido: int):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cur:
            cur.execute("""
                SELECT r.id_ruta, r.codigo, r.estado, r.distancia_total_km,
                       c.id_conductor, u.nombres, u.apellidos,
                       v.id_vehiculo, v.placa
                FROM logistica.ruta_pedidos rp
                JOIN logistica.rutas r ON r.id_ruta=rp.id_ruta
                LEFT JOIN logistica.conductores c ON c.id_conductor=r.id_conductor
                LEFT JOIN seguridad.usuarios u ON u.id_usuario=c.id_usuario
                LEFT JOIN logistica.vehiculos v ON v.id_vehiculo=r.id_vehiculo
                WHERE rp.id_pedido=%s
                ORDER BY rp.creado_en DESC LIMIT 1;
            """, (id_pedido,))
            fila = cur.fetchone()
            if fila is None:
                return None
            return {"id_ruta": fila[0], "codigo": fila[1], "estado": fila[2], "distancia_km": float(fila[3]) if fila[3] else None,
                    "conductor": {"id_conductor": fila[4], "nombres": fila[5], "apellidos": fila[6]} if fila[4] else None,
                    "vehiculo": {"id_vehiculo": fila[7], "placa": fila[8]} if fila[7] else None}
    finally:
        conexion.close()
