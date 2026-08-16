def dfs(grafo, inicio):
    if inicio not in grafo.adyacencia:
        return []

    visitados = set()
    recorrido = []

    def recorrer(vertice):
        visitados.add(vertice)
        recorrido.append(vertice)

        for vecino, peso in grafo.obtener_vecinos(vertice):
            if vecino not in visitados:
                recorrer(vecino)

    recorrer(inicio)

    return recorrido