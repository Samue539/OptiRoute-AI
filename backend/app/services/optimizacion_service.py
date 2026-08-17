"""
Servicio de optimización multi-entrega.

Orquesta la validación de datos, carga del grafo desde PostgreSQL,
invocación del algoritmo TSP y construcción de la respuesta.
"""

from backend.app.algorithms.dijkstra import dijkstra
from backend.app.algorithms.tsp import resolver_tsp_exacto
from backend.app.services.excepciones import ReglaNegocioError
from backend.app.services.grafo_service import (
    cargar_grafo_desde_bd,
    obtener_nodo,
)


def optimizar_multi_entrega(
    origen: int,
    destinos: list[int],
    regresar_origen: bool = False
) -> dict:
    """
    Resuelve el problema de optimización multi-entrega.

    Validaciones:
    - Origen existe y está activo
    - Todos los destinos existen y están activos
    - Origen no está dentro de destinos
    - No hay destinos duplicados
    - Número de destinos <= 8

    Retorna:
        Diccionario con información completa de la optimización.

    Raises:
        ReglaNegocioError: Si no se cumplen validaciones o no hay solución.
    """

    # 1. Validación: origen existe
    nodo_origen = obtener_nodo(origen)
    if nodo_origen is None:
        raise ReglaNegocioError(f"El nodo origen {origen} no existe o está inactivo.")

    # 2. Validación: destinos no vacío
    if not destinos:
        raise ReglaNegocioError("La lista de destinos no puede estar vacía.")

    # 3. Validación: sin duplicados en destinos
    if len(destinos) != len(set(destinos)):
        raise ReglaNegocioError("La lista de destinos contiene IDs duplicados.")

    # 4. Validación: origen no dentro de destinos
    if origen in destinos:
        raise ReglaNegocioError(
            "El nodo de origen no puede estar incluido en la lista de destinos."
        )

    # 5. Validación: máximo 8 destinos
    if len(destinos) > 8:
        raise ReglaNegocioError(
            f"Número de destinos ({len(destinos)}) excede el máximo permitido (8). "
            f"El TSP exacto tiene complejidad factorial y está limitado a conjuntos pequeños."
        )

    # 6. Validación: todos los destinos existen
    nodos_destino = []
    for destino in destinos:
        nodo = obtener_nodo(destino)
        if nodo is None:
            raise ReglaNegocioError(
                f"El nodo destino {destino} no existe o está inactivo."
            )
        nodos_destino.append(nodo)

    # 7. Cargar grafo desde PostgreSQL
    try:
        grafo = cargar_grafo_desde_bd()
    except Exception as error:
        raise ReglaNegocioError(
            f"Error al cargar el grafo desde la base de datos: {error}"
        ) from error

    # 8. Resolver TSP
    try:
        resultado_tsp = resolver_tsp_exacto(
            grafo=grafo,
            funcion_dijkstra=dijkstra,
            origen=origen,
            destinos=destinos,
            regresar_origen=regresar_origen,
            limite_destinos=8
        )
    except ValueError as error:
        raise ReglaNegocioError(f"Error en el algoritmo TSP: {error}") from error

    if resultado_tsp is None:
        raise ReglaNegocioError(
            "No existe una ruta posible que conecte todos los destinos. "
            "Verifique que el grafo sea conexo."
        )

    # 9. Construir respuesta detallada
    orden_optimo = resultado_tsp["orden_optimo"]
    recorrido = resultado_tsp["recorrido"]
    distancia_total = resultado_tsp["distancia_total_km"]
    permutaciones = resultado_tsp["permutaciones_evaluadas"]

    orden_optimo_info = [obtener_nodo(nodo_id) for nodo_id in orden_optimo]
    recorrido_info = [obtener_nodo(nodo_id) for nodo_id in recorrido]

    return {
        "origen": nodo_origen,
        "destinos_solicitados": nodos_destino,
        "orden_optimo": orden_optimo,
        "orden_optimo_info": orden_optimo_info,
        "recorrido": recorrido,
        "recorrido_info": recorrido_info,
        "distancia_total_km": distancia_total,
        "regresar_origen": regresar_origen,
        "algoritmo": "TSP_EXACTO",
        "permutaciones_evaluadas": permutaciones,
    }
