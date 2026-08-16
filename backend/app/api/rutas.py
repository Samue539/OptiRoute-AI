from fastapi import APIRouter, HTTPException

from backend.app.algorithms.dijkstra import dijkstra
from backend.app.services.grafo_service import (
    cargar_grafo_desde_bd,
    obtener_nodo,
)


router = APIRouter(
    prefix="/api/rutas",
    tags=["Rutas"],
)


@router.get("/calcular")
def calcular_ruta(origen: int, destino: int):

    # 1. Comprobar que existen los nodos
    nodo_origen = obtener_nodo(origen)
    nodo_destino = obtener_nodo(destino)

    if nodo_origen is None:
        raise HTTPException(
            status_code=404,
            detail="El nodo de origen no existe.",
        )

    if nodo_destino is None:
        raise HTTPException(
            status_code=404,
            detail="El nodo de destino no existe.",
        )

    # 2. Construir el grafo desde PostgreSQL
    grafo = cargar_grafo_desde_bd()

    # 3. Calcular el camino mínimo
    resultado = dijkstra(
        grafo,
        origen,
        destino,
    )

    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail="No existe una ruta entre los nodos indicados.",
        )

    # 4. Obtener información de cada nodo de la ruta
    ruta_detallada = []

    for id_nodo in resultado["camino"]:
        nodo = obtener_nodo(id_nodo)

        if nodo is not None:
            ruta_detallada.append(nodo)

    # 5. Respuesta de la API
    return {
        "origen": nodo_origen,
        "destino": nodo_destino,
        "ruta": ruta_detallada,
        "distancia_total_km": resultado["distancia"],
    }