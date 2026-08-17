"""
Módulo TSP (Traveling Salesman Problem)

Implementa el Problema del Vendedor Viajero mediante búsqueda exhaustiva.
Determina el orden óptimo de visita de múltiples destinos minimizando la
distancia total del recorrido.

Complejidad: O(n!) donde n es el número de destinos.
Por esta razón, está limitado a conjuntos pequeños (máximo 8 destinos).

Diferencia conceptual:
- Orden de visita: [2, 4, 3, 5] (qué nodos visitar y en qué orden)
- Recorrido físico: [1, 2, 3, 4, 3, 5] (nodos intermedios incluidos)
"""

from itertools import permutations
from typing import Optional


def calcular_distancia_recorrido(
    grafo,
    funcion_dijkstra,
    camino: list[int]
) -> Optional[tuple[float, list[int]]]:
    """
    Calcula la distancia total de un recorrido y el camino físico completo.

    Utiliza Dijkstra entre cada par de nodos consecutivos para obtener
    la distancia mínima y el camino exacto que debe recorrer el vehículo.

    Args:
        grafo: Instancia del grafo con la estructura de red
        funcion_dijkstra: Función Dijkstra que retorna {"camino": [...], "distancia": ...}
        camino: Lista de IDs de nodos a visitar en orden

    Returns:
        (distancia_total, camino_fisico_completo) si es posible, None si hay nodo inaccesible
    """
    if not camino:
        return (0, [])

    if len(camino) == 1:
        return (0, camino)

    distancia_total = 0
    recorrido_completo = []
    inicio = camino[0]

    for i in range(len(camino) - 1):
        origen = camino[i]
        destino = camino[i + 1]

        resultado = funcion_dijkstra(grafo, origen, destino)

        if resultado is None:
            return None

        distancia = resultado["distancia"]
        path = resultado["camino"]

        distancia_total += distancia

        if i == 0:
            recorrido_completo.extend(path)
        else:
            recorrido_completo.extend(path[1:])

    return (distancia_total, recorrido_completo)


def resolver_tsp_exacto(
    grafo,
    funcion_dijkstra,
    origen: int,
    destinos: list[int],
    regresar_origen: bool = False,
    limite_destinos: int = 8
) -> Optional[dict]:
    """
    Resuelve el TSP mediante búsqueda exhaustiva de permutaciones.

    Evalúa todas las posibles órdenes de visita de los destinos y retorna
    la que minimiza la distancia total.

    Args:
        grafo: Instancia del grafo
        funcion_dijkstra: Función Dijkstra para calcular distancias
        origen: ID del nodo de origen (bodega)
        destinos: Lista de IDs de nodos a visitar
        regresar_origen: Si True, incluye retorno a bodega en el cálculo
        limite_destinos: Número máximo permitido de destinos

    Returns:
        Diccionario con:
        - orden_optimo: Lista de IDs de destinos en orden óptimo
        - recorrido: Camino físico completo (incluyendo nodos intermedios)
        - distancia_total_km: Distancia mínima calculada
        - permutaciones_evaluadas: Cantidad de permutaciones probadas
        O None si no existe solución válida
    """
    if len(destinos) > limite_destinos:
        raise ValueError(
            f"Número de destinos ({len(destinos)}) excede el límite permitido ({limite_destinos}). "
            f"TSP exacto tiene complejidad factorial O(n!) y no es escalable para grandes conjuntos."
        )

    if not destinos:
        return None

    if len(destinos) == 1:
        resultado = calcular_distancia_recorrido(
            grafo,
            funcion_dijkstra,
            [origen, destinos[0]]
        )

        if resultado is None:
            return None

        distancia, recorrido = resultado

        if regresar_origen:
            resultado_regreso = calcular_distancia_recorrido(
                grafo,
                funcion_dijkstra,
                [destinos[0], origen]
            )

            if resultado_regreso is None:
                return None

            distancia_regreso, recorrido_regreso = resultado_regreso
            distancia += distancia_regreso
            recorrido.extend(recorrido_regreso[1:])

        return {
            "orden_optimo": destinos,
            "recorrido": recorrido,
            "distancia_total_km": distancia,
            "regresar_origen": regresar_origen,
            "permutaciones_evaluadas": 1,
        }

    mejor_distancia = float("inf")
    mejor_orden = None
    mejor_recorrido = None
    permutaciones_evaluadas = 0

    for permutacion in permutations(destinos):
        permutaciones_evaluadas += 1

        camino = [origen] + list(permutacion)

        if regresar_origen:
            camino.append(origen)

        resultado = calcular_distancia_recorrido(
            grafo,
            funcion_dijkstra,
            camino
        )

        if resultado is None:
            continue

        distancia, recorrido = resultado

        if distancia < mejor_distancia:
            mejor_distancia = distancia
            mejor_orden = list(permutacion)
            mejor_recorrido = recorrido

    if mejor_orden is None:
        return None

    return {
        "orden_optimo": mejor_orden,
        "recorrido": mejor_recorrido,
        "distancia_total_km": mejor_distancia,
        "regresar_origen": regresar_origen,
        "permutaciones_evaluadas": permutaciones_evaluadas,
    }
