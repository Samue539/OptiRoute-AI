from backend.app.algorithms.grafo import Grafo
from backend.app.core.database import obtener_conexion


def cargar_grafo_desde_bd():
    grafo = Grafo()

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        # Cargar los vértices del grafo
        cursor.execute("""
            SELECT id_nodo
            FROM logistica.nodos
            WHERE activo = TRUE
            ORDER BY id_nodo;
        """)

        nodos = cursor.fetchall()

        for (id_nodo,) in nodos:
            grafo.agregar_vertice(id_nodo)

        # Cargar las aristas del grafo
        cursor.execute("""
            SELECT
                id_nodo_origen,
                id_nodo_destino,
                distancia_km,
                bidireccional
            FROM logistica.conexiones
            WHERE activo = TRUE
            ORDER BY id_conexion;
        """)

        conexiones = cursor.fetchall()

        for origen, destino, distancia, bidireccional in conexiones:
            grafo.agregar_arista(
                origen,
                destino,
                float(distancia),
                bidireccional
            )

        return grafo

    finally:
        cursor.close()
        conexion.close()


def obtener_nodo(id_nodo):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            SELECT
                id_nodo,
                nombre,
                tipo_nodo,
                latitud,
                longitud
            FROM logistica.nodos
            WHERE id_nodo = %s
              AND activo = TRUE;
        """, (id_nodo,))

        nodo = cursor.fetchone()

        if nodo is None:
            return None

        return {
            "id_nodo": nodo[0],
            "nombre": nodo[1],
            "tipo_nodo": nodo[2],
            "latitud": float(nodo[3]),
            "longitud": float(nodo[4])
        }

    finally:
        cursor.close()
        conexion.close()