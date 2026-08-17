from backend.app.algorithms.grafo import Grafo
from backend.app.services import ruta_service
from tests.conftest import ConexionSimulada


def test_crear_ruta_guarda_recorrido_y_confirma_transaccion(monkeypatch):
    grafo = Grafo()
    grafo.agregar_arista(1, 2, 4)
    grafo.agregar_arista(2, 3, 3)

    conexion = ConexionSimulada(
        [
            (7,),
            None,
            None,
            None,
            None,
        ]
    )

    monkeypatch.setattr(
        ruta_service,
        "obtener_nodo",
        lambda id_nodo: {
            "id_nodo": id_nodo,
            "nombre": f"Nodo {id_nodo}",
        },
    )
    monkeypatch.setattr(
        ruta_service,
        "cargar_grafo_desde_bd",
        lambda: grafo,
    )
    monkeypatch.setattr(
        ruta_service,
        "obtener_conexion",
        lambda: conexion,
    )

    resultado = ruta_service.crear_ruta(origen=1, destino=3)

    assert resultado["id_ruta"] == 7
    assert resultado["codigo"] == "RUT-000007"
    assert resultado["camino"] == [1, 2, 3]
    assert resultado["distancia_total_km"] == 7
    assert conexion.commits == 1
    assert conexion.rollbacks == 0
    assert conexion.cerrada is True

    inserts_puntos = [
        parametros
        for consulta, parametros in conexion.cursor_simulado.consultas
        if "INSERT INTO logistica.ruta_puntos" in consulta
    ]
    assert [fila[3] for fila in inserts_puntos] == [0.0, 4.0, 7.0]
