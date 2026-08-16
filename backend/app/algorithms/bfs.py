from collections import deque


def bfs(grafo, inicio):
    if inicio not in grafo.adyacencia:
        return []

    visitados = set()
    cola = deque([inicio])
    recorrido = []

    while cola:
        vertice = cola.popleft()

        if vertice not in visitados:
            visitados.add(vertice)
            recorrido.append(vertice)

            for vecino, peso in grafo.obtener_vecinos(vertice):
                if vecino not in visitados:
                    cola.append(vecino)

    return recorrido