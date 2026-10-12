"""Script manual para inspeccionar el grafo cargado desde PostgreSQL.

No es una prueba de pytest: no contiene funciones test_*. Se protege con
`if __name__ == "__main__":` para que pytest pueda recolectar este archivo
sin abrir una conexion real a la base de datos durante el import.

Ejecucion manual:
    python -m tests.test_grafo_database
"""

from backend.app.algorithms.dijkstra import dijkstra
from backend.app.services.grafo_service import (
    cargar_grafo_desde_bd,
    obtener_nodo,
)


def main():
    grafo = cargar_grafo_desde_bd()

    print("GRAFO CARGADO DESDE POSTGRESQL")
    print("------------------------------")
    grafo.mostrar_lista_adyacencia()

    print()
    print("DATOS DEL NODO 1")
    print("----------------")
    nodo = obtener_nodo(1)
    print(nodo)

    print()
    print("DIJKSTRA CON IDs")
    print("----------------")
    resultado = dijkstra(grafo, 1, 5)

    if resultado:
        print("IDs de la ruta:", resultado["camino"])

        nombres = []
        for id_nodo in resultado["camino"]:
            datos_nodo = obtener_nodo(id_nodo)
            nombres.append(datos_nodo["nombre"])

        print("Ruta:", " -> ".join(nombres))
        print("Distancia total:", resultado["distancia"], "km")
    else:
        print("No existe una ruta.")


if __name__ == "__main__":
    main()
