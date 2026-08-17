"""Validaciones de pedidos y capacidad para la planificacion logistica."""

from decimal import Decimal

from backend.app.core.database import obtener_conexion
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
)


def _decimal(valor):
    return Decimal(str(valor))


def obtener_pedidos_para_planificacion(ids_pedidos: list[int]):
    if len(ids_pedidos) != len(set(ids_pedidos)):
        raise ReglaNegocioError("La lista de pedidos contiene IDs duplicados.")

    conexion = obtener_conexion()

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id_pedido,
                    p.codigo,
                    p.id_cliente,
                    p.id_direccion_entrega,
                    p.descripcion,
                    p.peso_kg,
                    p.volumen_m3,
                    p.prioridad,
                    p.estado,
                    d.id_nodo,
                    d.activo,
                    n.id_nodo,
                    n.nombre,
                    n.tipo_nodo,
                    n.latitud,
                    n.longitud,
                    n.activo
                FROM operaciones.pedidos p
                JOIN operaciones.direcciones d
                    ON d.id_direccion = p.id_direccion_entrega
                LEFT JOIN logistica.nodos n
                    ON n.id_nodo = d.id_nodo
                WHERE p.id_pedido = ANY(%s);
                """,
                (ids_pedidos,),
            )
            filas = cursor.fetchall()

        filas_por_id = {fila[0]: fila for fila in filas}
        faltantes = [
            id_pedido
            for id_pedido in ids_pedidos
            if id_pedido not in filas_por_id
        ]
        if faltantes:
            raise RecursoNoEncontradoError(
                f"El pedido {faltantes[0]} no existe."
            )

        pedidos = []
        for id_pedido in ids_pedidos:
            fila = filas_por_id[id_pedido]

            if not fila[10]:
                raise ReglaNegocioError(
                    f"La direccion del pedido {id_pedido} no esta activa."
                )
            if fila[9] is None:
                raise ReglaNegocioError(
                    f"El pedido {id_pedido} no tiene un nodo de destino asignado."
                )
            if fila[11] is None or not fila[16]:
                raise ReglaNegocioError(
                    f"El nodo destino del pedido {id_pedido} no existe o esta inactivo."
                )
            if fila[5] is None:
                raise ReglaNegocioError(
                    f"El pedido {id_pedido} no tiene peso registrado."
                )
            if fila[6] is None:
                raise ReglaNegocioError(
                    f"El pedido {id_pedido} no tiene volumen registrado."
                )

            pedidos.append(
                {
                    "id_pedido": fila[0],
                    "codigo": fila[1],
                    "id_cliente": fila[2],
                    "id_direccion_entrega": fila[3],
                    "descripcion": fila[4],
                    "peso_kg": float(fila[5]),
                    "volumen_m3": float(fila[6]),
                    "prioridad": fila[7],
                    "estado": fila[8],
                    "destino": {
                        "id_nodo": fila[11],
                        "nombre": fila[12],
                        "tipo_nodo": fila[13],
                        "latitud": float(fila[14]),
                        "longitud": float(fila[15]),
                    },
                }
            )

        return pedidos

    finally:
        conexion.close()


def obtener_vehiculo_para_planificacion(id_vehiculo: int):
    conexion = obtener_conexion()

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id_vehiculo,
                    placa,
                    marca,
                    modelo,
                    tipo_vehiculo,
                    capacidad_kg,
                    capacidad_volumen_m3,
                    estado,
                    activo
                FROM logistica.vehiculos
                WHERE id_vehiculo = %s;
                """,
                (id_vehiculo,),
            )
            fila = cursor.fetchone()

        if fila is None:
            raise RecursoNoEncontradoError("El vehiculo no existe.")
        if not fila[8]:
            raise ReglaNegocioError("El vehiculo no esta activo.")
        if fila[7] != "DISPONIBLE":
            raise ReglaNegocioError("El vehiculo no esta disponible.")
        if fila[5] is None:
            raise ReglaNegocioError(
                "El vehiculo no tiene capacidad de peso registrada."
            )
        if fila[6] is None:
            raise ReglaNegocioError(
                "El vehiculo no tiene capacidad de volumen registrada."
            )

        return {
            "id_vehiculo": fila[0],
            "placa": fila[1],
            "marca": fila[2],
            "modelo": fila[3],
            "tipo_vehiculo": fila[4],
            "capacidad_kg": float(fila[5]),
            "capacidad_volumen_m3": float(fila[6]),
            "estado": fila[7],
        }

    finally:
        conexion.close()


def calcular_capacidad(pedidos: list[dict], vehiculo: dict):
    peso_total = sum(
        (_decimal(pedido["peso_kg"]) for pedido in pedidos),
        Decimal("0"),
    )
    volumen_total = sum(
        (_decimal(pedido["volumen_m3"]) for pedido in pedidos),
        Decimal("0"),
    )
    capacidad_peso = _decimal(vehiculo["capacidad_kg"])
    capacidad_volumen = _decimal(vehiculo["capacidad_volumen_m3"])
    excede_peso = peso_total > capacidad_peso
    excede_volumen = volumen_total > capacidad_volumen

    return {
        "factible": not excede_peso and not excede_volumen,
        "peso_total": float(peso_total),
        "capacidad_peso": float(capacidad_peso),
        "volumen_total": float(volumen_total),
        "capacidad_volumen": float(capacidad_volumen),
        "excede_peso": excede_peso,
        "excede_volumen": excede_volumen,
        "exceso_peso_kg": float(max(peso_total - capacidad_peso, 0)),
        "exceso_volumen_m3": float(
            max(volumen_total - capacidad_volumen, 0)
        ),
    }


def evaluar_restricciones_logisticas(
    ids_pedidos: list[int],
    id_vehiculo: int,
):
    if len(ids_pedidos) != len(set(ids_pedidos)):
        raise ReglaNegocioError("La lista de pedidos contiene IDs duplicados.")

    pedidos = obtener_pedidos_para_planificacion(ids_pedidos)
    vehiculo = obtener_vehiculo_para_planificacion(id_vehiculo)
    capacidad = calcular_capacidad(pedidos, vehiculo)

    return {
        **capacidad,
        "pedidos": pedidos,
        "vehiculo": vehiculo,
    }
