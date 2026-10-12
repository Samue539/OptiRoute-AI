"""Persistencia atomica de planes TSP/Dijkstra."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from backend.app.core.database import obtener_conexion
from backend.app.services.excepciones import RecursoNoEncontradoError, ReglaNegocioError
from backend.app.services.grafo_service import cargar_grafo_desde_bd
from backend.app.services.planificacion_service import planificar_entregas
from backend.app.services.ruta_recursos import validar_recursos


def _ordenar_pedidos(pedidos: list[dict], orden_optimo: list[int]) -> list[dict]:
    """Da orden individual a cada pedido, incluso si comparten destino."""

    posicion = {id_nodo: indice for indice, id_nodo in enumerate(orden_optimo)}
    ordenados = sorted(
        enumerate(pedidos),
        key=lambda par: (posicion[par[1]["id_nodo"]], par[0]),
    )
    return [
        {**pedido, "orden_entrega": orden}
        for orden, (_, pedido) in enumerate(ordenados, start=1)
    ]


def _distancias_acumuladas(grafo, recorrido: Iterable[int]) -> list[tuple[int, float]]:
    acumulada = Decimal("0")
    anterior = None
    resultado: list[tuple[int, float]] = []
    for id_nodo in recorrido:
        if anterior is not None:
            pesos = [
                Decimal(str(peso))
                for vecino, peso in grafo.obtener_vecinos(anterior)
                if vecino == id_nodo
            ]
            if not pesos:
                raise ReglaNegocioError(
                    f"El recorrido calculado contiene el tramo inexistente {anterior}->{id_nodo}."
                )
            acumulada += min(pesos)
        resultado.append((id_nodo, float(acumulada)))
        anterior = id_nodo
    return resultado


def _validar_pedidos_bloqueados(cursor, ids_pedidos: list[int]) -> list[dict]:
    cursor.execute(
        """
        SELECT p.id_pedido, p.estado, p.peso_kg, p.volumen_m3, d.id_nodo
        FROM operaciones.pedidos p
        JOIN operaciones.direcciones d ON d.id_direccion = p.id_direccion_entrega
        WHERE p.id_pedido = ANY(%s)
        ORDER BY array_position(%s::bigint[], p.id_pedido)
        FOR UPDATE OF p;
        """,
        (ids_pedidos, ids_pedidos),
    )
    filas = cursor.fetchall()
    por_id = {fila[0]: fila for fila in filas}
    if len(por_id) != len(ids_pedidos):
        faltante = next(id_pedido for id_pedido in ids_pedidos if id_pedido not in por_id)
        raise RecursoNoEncontradoError(f"El pedido {faltante} no existe.")

    pedidos = []
    for id_pedido in ids_pedidos:
        fila = por_id[id_pedido]
        if fila[1] != "PENDIENTE":
            raise ReglaNegocioError(
                f"El pedido {id_pedido} ya no esta pendiente y no puede planificarse."
            )
        if fila[2] is None or fila[3] is None or fila[4] is None:
            raise ReglaNegocioError(f"El pedido {id_pedido} tiene datos logisticos incompletos.")
        pedidos.append(
            {
                "id_pedido": fila[0], "estado": fila[1],
                "peso_kg": float(fila[2]), "volumen_m3": float(fila[3]),
                "id_nodo": fila[4],
            }
        )

    cursor.execute(
        """
        SELECT rp.id_pedido
        FROM logistica.ruta_pedidos rp
        JOIN logistica.rutas r ON r.id_ruta = rp.id_ruta
        WHERE rp.id_pedido = ANY(%s)
          AND r.estado IN ('PLANIFICADA', 'ASIGNADA', 'EN_RUTA')
        LIMIT 1;
        """,
        (ids_pedidos,),
    )
    ocupada = cursor.fetchone()
    if ocupada:
        raise ReglaNegocioError(f"El pedido {ocupada[0]} ya pertenece a una ruta activa.")
    return pedidos


def guardar_ruta_planificada(
    *,
    origen: int,
    ids_pedidos: list[int],
    id_conductor: int,
    id_vehiculo: int,
    regresar_origen: bool,
    clave_idempotencia: str,
) -> dict:
    """Recalcula y guarda ruta, puntos, pedidos y asignacion en un commit."""

    if len(ids_pedidos) != len(set(ids_pedidos)):
        raise ReglaNegocioError("La lista de pedidos contiene IDs duplicados.")
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Serializa dos reintentos con la misma clave antes de comprobarla.
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s));", (clave_idempotencia,))
            cursor.execute(
                """SELECT id_ruta, codigo, estado, distancia_total_km
                   FROM logistica.rutas WHERE clave_idempotencia = %s;""",
                (clave_idempotencia,),
            )
            existente = cursor.fetchone()
            if existente:
                conexion.commit()
                return {
                    "id_ruta": existente[0], "codigo": existente[1],
                    "estado": existente[2], "distancia_total_km": float(existente[3]),
                    "recorrido": [], "pedidos": ids_pedidos,
                    "duplicada": True,
                }

            # Solo se recalcula tras descartar un reintento. La clave queda
            # bloqueada durante todo el calculo y la persistencia.
            plan = planificar_entregas(origen, ids_pedidos, id_vehiculo, regresar_origen)
            recorrido = list(plan["recorrido"])
            if not recorrido or recorrido[0] != origen:
                raise ReglaNegocioError("El recorrido calculado no inicia en el origen.")
            if regresar_origen and recorrido[-1] != origen:
                raise ReglaNegocioError("El recorrido calculado no incluye el retorno al origen.")
            destino_final = plan["orden_optimo"][-1]
            grafo = cargar_grafo_desde_bd()
            puntos = _distancias_acumuladas(grafo, recorrido)

            conductor, vehiculo = validar_recursos(cursor, id_conductor, id_vehiculo)
            pedidos = _validar_pedidos_bloqueados(cursor, ids_pedidos)
            peso_total = sum(Decimal(str(p["peso_kg"])) for p in pedidos)
            volumen_total = sum(Decimal(str(p["volumen_m3"])) for p in pedidos)
            if vehiculo["capacidad_kg"] is None or peso_total > Decimal(str(vehiculo["capacidad_kg"])):
                raise ReglaNegocioError("La carga excede la capacidad de peso del vehiculo.")
            if vehiculo["capacidad_volumen_m3"] is None or volumen_total > Decimal(str(vehiculo["capacidad_volumen_m3"])):
                raise ReglaNegocioError("La carga excede la capacidad de volumen del vehiculo.")
            if {p["id_nodo"] for p in pedidos} != set(plan["destinos"]):
                raise ReglaNegocioError("Los destinos cambiaron desde la planificacion; vuelve a calcular.")

            pedidos_ordenados = _ordenar_pedidos(pedidos, plan["orden_optimo"])
            cursor.execute(
                """
                INSERT INTO logistica.rutas (
                    codigo, id_conductor, id_vehiculo, id_nodo_origen,
                    id_nodo_destino, estado, distancia_total_km,
                    fecha_planificada, clave_idempotencia
                ) VALUES (%s, %s, %s, %s, %s, 'ASIGNADA', %s, CURRENT_TIMESTAMP, %s)
                RETURNING id_ruta;
                """,
                (
                    f"TEMP-{clave_idempotencia[:20]}", id_conductor, id_vehiculo,
                    origen, destino_final, plan["distancia_total_km"], clave_idempotencia,
                ),
            )
            id_ruta = cursor.fetchone()[0]
            codigo = f"RUT-{id_ruta:06d}"
            cursor.execute("UPDATE logistica.rutas SET codigo=%s WHERE id_ruta=%s;", (codigo, id_ruta))
            for orden, (id_nodo, distancia) in enumerate(puntos, start=1):
                cursor.execute(
                    """INSERT INTO logistica.ruta_puntos
                       (id_ruta, id_nodo, orden, distancia_acumulada_km)
                       VALUES (%s, %s, %s, %s);""",
                    (id_ruta, id_nodo, orden, distancia),
                )
            for pedido in pedidos_ordenados:
                cursor.execute(
                    """INSERT INTO logistica.ruta_pedidos
                       (id_ruta, id_pedido, orden_entrega) VALUES (%s, %s, %s);""",
                    (id_ruta, pedido["id_pedido"], pedido["orden_entrega"]),
                )
            cursor.execute(
                "UPDATE operaciones.pedidos SET estado='PLANIFICADO', actualizado_en=CURRENT_TIMESTAMP WHERE id_pedido=ANY(%s);",
                (ids_pedidos,),
            )
            cursor.execute(
                "UPDATE logistica.conductores SET disponible=FALSE, actualizado_en=CURRENT_TIMESTAMP WHERE id_conductor=%s;",
                (id_conductor,),
            )
            cursor.execute(
                "UPDATE logistica.vehiculos SET estado='EN_RUTA', actualizado_en=CURRENT_TIMESTAMP WHERE id_vehiculo=%s;",
                (id_vehiculo,),
            )
        conexion.commit()
        return {
            "id_ruta": id_ruta, "codigo": codigo, "estado": "ASIGNADA",
            "distancia_total_km": float(plan["distancia_total_km"]),
            "recorrido": recorrido,
            "pedidos": [
                {"id_pedido": p["id_pedido"], "orden_entrega": p["orden_entrega"]}
                for p in pedidos_ordenados
            ],
            "conductor": conductor, "vehiculo": vehiculo, "duplicada": False,
        }
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()
