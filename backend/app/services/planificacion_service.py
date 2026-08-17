"""Orquestacion de restricciones logisticas y optimizacion multi-entrega."""

from backend.app.services.excepciones import ReglaNegocioError
from backend.app.services.optimizacion_service import optimizar_multi_entrega
from backend.app.services.restricciones_service import (
    evaluar_restricciones_logisticas,
)


LIMITE_DESTINOS_TSP = 8


def planificar_entregas(
    origen: int,
    ids_pedidos: list[int],
    id_vehiculo: int,
    regresar_origen: bool = False,
):
    restricciones = evaluar_restricciones_logisticas(
        ids_pedidos=ids_pedidos,
        id_vehiculo=id_vehiculo,
    )

    if not restricciones["factible"]:
        motivos = []
        if restricciones["excede_peso"]:
            motivos.append(
                "el peso total "
                f"({restricciones['peso_total']} kg) supera la capacidad "
                f"({restricciones['capacidad_peso']} kg)"
            )
        if restricciones["excede_volumen"]:
            motivos.append(
                "el volumen total "
                f"({restricciones['volumen_total']} m3) supera la capacidad "
                f"({restricciones['capacidad_volumen']} m3)"
            )
        raise ReglaNegocioError(
            "La planificacion no es factible: " + "; ".join(motivos) + "."
        )

    destinos = list(
        dict.fromkeys(
            pedido["destino"]["id_nodo"]
            for pedido in restricciones["pedidos"]
        )
    )

    if len(destinos) > LIMITE_DESTINOS_TSP:
        raise ReglaNegocioError(
            f"La planificacion contiene {len(destinos)} destinos distintos; "
            f"el TSP exacto permite maximo {LIMITE_DESTINOS_TSP}."
        )

    optimizacion = optimizar_multi_entrega(
        origen=origen,
        destinos=destinos,
        regresar_origen=regresar_origen,
    )

    return {
        "factible": True,
        "vehiculo": restricciones["vehiculo"],
        "pedidos": restricciones["pedidos"],
        "peso_total": restricciones["peso_total"],
        "capacidad_peso": restricciones["capacidad_peso"],
        "volumen_total": restricciones["volumen_total"],
        "capacidad_volumen": restricciones["capacidad_volumen"],
        "origen": optimizacion["origen"],
        "destinos": destinos,
        "orden_optimo": optimizacion["orden_optimo"],
        "recorrido": optimizacion["recorrido"],
        "distancia_total_km": optimizacion["distancia_total_km"],
        "regresar_origen": regresar_origen,
        "algoritmo": "TSP_EXACTO_DIJKSTRA",
        "permutaciones_evaluadas": optimizacion["permutaciones_evaluadas"],
    }
