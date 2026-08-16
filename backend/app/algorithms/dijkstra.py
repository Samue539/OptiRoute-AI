import heapq


def dijkstra(grafo, origen, destino):

    if origen not in grafo.adyacencia:
        return None

    if destino not in grafo.adyacencia:
        return None

    distancias = {}

    anteriores = {}

    for vertice in grafo.obtener_vertices():
        distancias[vertice] = float("inf")
        anteriores[vertice] = None

    distancias[origen] = 0

    cola = [(0, origen)]

    while cola:

        distancia_actual, vertice_actual = heapq.heappop(cola)

        if distancia_actual > distancias[vertice_actual]:
            continue

        if vertice_actual == destino:
            break

        for vecino, peso in grafo.obtener_vecinos(vertice_actual):

            nueva_distancia = distancia_actual + peso

            if nueva_distancia < distancias[vecino]:

                distancias[vecino] = nueva_distancia

                anteriores[vecino] = vertice_actual

                heapq.heappush(
                    cola,
                    (nueva_distancia, vecino)
                )

    if distancias[destino] == float("inf"):
        return None

    camino = []

    actual = destino

    while actual is not None:

        camino.append(actual)

        actual = anteriores[actual]

    camino.reverse()

    return {
        "camino": camino,
        "distancia": distancias[destino]
    }