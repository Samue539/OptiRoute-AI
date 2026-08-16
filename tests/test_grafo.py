from backend.app.algorithms.grafo import Grafo
from backend.app.algorithms.bfs import bfs
from backend.app.algorithms.dfs import dfs
from backend.app.algorithms.dijkstra import dijkstra

grafo = Grafo()

grafo.agregar_arista("Bodega", "Cliente A", 4)
grafo.agregar_arista("Bodega", "Cliente B", 10)
grafo.agregar_arista("Cliente A", "Cliente B", 3)
grafo.agregar_arista("Cliente A", "Cliente C", 7)
grafo.agregar_arista("Cliente B", "Cliente C", 2)
grafo.agregar_arista("Cliente B", "Cliente D", 6)
grafo.agregar_arista("Cliente C", "Cliente D", 3)


print("LISTA DE ADYACENCIA")
print("-------------------")

grafo.mostrar_lista_adyacencia()

print()
print("Grado de Cliente B:", grafo.grado("Cliente B"))

print()
print("MATRIZ DE ADYACENCIA")
print("--------------------")

vertices, matriz = grafo.matriz_adyacencia()

print(f"{'':20}", end="")

for vertice in vertices:
    print(f"{vertice:20}", end="")

print()

for i in range(len(vertices)):
    print(f"{vertices[i]:20}", end="")

    for valor in matriz[i]:
        print(f"{valor:<20}", end="")

    print()

    print()
print("RECORRIDO BFS")
print("-------------")

recorrido_bfs = bfs(grafo, "Bodega")

print(" -> ".join(recorrido_bfs))

print()
print("RECORRIDO DFS")
print("-------------")

recorrido_dfs = dfs(grafo, "Bodega")

print(" -> ".join(recorrido_dfs))

print()
print("DIJKSTRA")
print("--------")

resultado = dijkstra(
    grafo,
    "Bodega",
    "Cliente D"
)

if resultado:

    print(
        "Ruta:",
        " -> ".join(resultado["camino"])
    )

    print(
        "Distancia total:",
        resultado["distancia"],
        "km"
    )

else:
    print("No existe una ruta.")