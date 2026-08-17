from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.algorithms.grafo import Grafo
from backend.app.main import app
from backend.app.services import (
    optimizacion_service,
    planificacion_service,
)
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
)


client = TestClient(app)


def _nodo(id_nodo):
    return {
        "id_nodo": id_nodo,
        "nombre": f"Nodo {id_nodo}",
        "tipo_nodo": "PUNTO_ENTREGA",
        "latitud": -0.2,
        "longitud": -78.5,
    }


def _restricciones(
    factible=True,
    peso_total=65,
    capacidad_peso=100,
    volumen_total=0.65,
    capacidad_volumen=1.5,
    destinos=(2, 3),
):
    pedidos = [
        {
            "id_pedido": indice,
            "codigo": f"PED-{indice:06d}",
            "id_cliente": 10,
            "id_direccion_entrega": 20 + indice,
            "descripcion": "Paquete",
            "peso_kg": peso_total / len(destinos),
            "volumen_m3": volumen_total / len(destinos),
            "prioridad": "NORMAL" if indice > 1 else "URGENTE",
            "estado": "PENDIENTE",
            "destino": _nodo(id_nodo),
        }
        for indice, id_nodo in enumerate(destinos, start=1)
    ]
    return {
        "factible": factible,
        "peso_total": peso_total,
        "capacidad_peso": capacidad_peso,
        "volumen_total": volumen_total,
        "capacidad_volumen": capacidad_volumen,
        "excede_peso": peso_total > capacidad_peso,
        "excede_volumen": volumen_total > capacidad_volumen,
        "exceso_peso_kg": max(peso_total - capacidad_peso, 0),
        "exceso_volumen_m3": max(volumen_total - capacidad_volumen, 0),
        "pedidos": pedidos,
        "vehiculo": {
            "id_vehiculo": 1,
            "placa": "ABC-123",
            "marca": "Marca",
            "modelo": "Modelo",
            "tipo_vehiculo": "CAMIONETA",
            "capacidad_kg": capacidad_peso,
            "capacidad_volumen_m3": capacidad_volumen,
            "estado": "DISPONIBLE",
        },
    }


def _respuesta_planificacion():
    restricciones = _restricciones()
    return {
        "factible": True,
        "vehiculo": restricciones["vehiculo"],
        "pedidos": restricciones["pedidos"],
        "peso_total": 65,
        "capacidad_peso": 100,
        "volumen_total": 0.65,
        "capacidad_volumen": 1.5,
        "origen": _nodo(1),
        "destinos": [2, 3],
        "orden_optimo": [2, 3],
        "recorrido": [1, 2, 3],
        "distancia_total_km": 7,
        "regresar_origen": False,
        "algoritmo": "TSP_EXACTO_DIJKSTRA",
        "permutaciones_evaluadas": 2,
    }


def test_planificacion_valida_invoca_optimizador(monkeypatch):
    monkeypatch.setattr(
        planificacion_service,
        "evaluar_restricciones_logisticas",
        lambda **kwargs: _restricciones(),
    )
    argumentos = {}

    def optimizar(**kwargs):
        argumentos.update(kwargs)
        return {
            "origen": _nodo(1),
            "orden_optimo": [2, 3],
            "recorrido": [1, 2, 3],
            "distancia_total_km": 7,
            "permutaciones_evaluadas": 2,
        }

    monkeypatch.setattr(
        planificacion_service,
        "optimizar_multi_entrega",
        optimizar,
    )

    resultado = planificacion_service.planificar_entregas(1, [1, 2], 1)

    assert resultado["factible"] is True
    assert resultado["algoritmo"] == "TSP_EXACTO_DIJKSTRA"
    assert argumentos["destinos"] == [2, 3]


@pytest.mark.parametrize(
    ("restricciones", "mensaje"),
    [
        (_restricciones(False, 110, 80, 1, 2), "peso total"),
        (_restricciones(False, 60, 80, 2.5, 2), "volumen total"),
    ],
)
def test_planificacion_rechaza_capacidad(
    monkeypatch,
    restricciones,
    mensaje,
):
    monkeypatch.setattr(
        planificacion_service,
        "evaluar_restricciones_logisticas",
        lambda **kwargs: restricciones,
    )

    with pytest.raises(ReglaNegocioError, match=mensaje):
        planificacion_service.planificar_entregas(1, [1, 2], 1)


def test_planificacion_rechaza_mas_de_ocho_destinos(monkeypatch):
    monkeypatch.setattr(
        planificacion_service,
        "evaluar_restricciones_logisticas",
        lambda **kwargs: _restricciones(destinos=tuple(range(2, 11))),
    )

    with pytest.raises(ReglaNegocioError, match="9 destinos"):
        planificacion_service.planificar_entregas(
            1,
            list(range(1, 10)),
            1,
        )


def test_integracion_real_tsp_y_dijkstra(monkeypatch):
    grafo = Grafo()
    grafo.agregar_arista(1, 2, 4)
    grafo.agregar_arista(2, 3, 3)
    grafo.agregar_arista(1, 3, 10)

    monkeypatch.setattr(
        planificacion_service,
        "evaluar_restricciones_logisticas",
        lambda **kwargs: _restricciones(),
    )
    monkeypatch.setattr(
        optimizacion_service,
        "obtener_nodo",
        lambda id_nodo: _nodo(id_nodo),
    )
    monkeypatch.setattr(
        optimizacion_service,
        "cargar_grafo_desde_bd",
        lambda: grafo,
    )

    resultado = planificacion_service.planificar_entregas(1, [1, 2], 1)

    assert resultado["orden_optimo"] == [2, 3]
    assert resultado["recorrido"] == [1, 2, 3]
    assert resultado["distancia_total_km"] == 7
    assert resultado["permutaciones_evaluadas"] == 2


def test_destino_inaccesible_se_propaga_como_error_de_negocio(monkeypatch):
    monkeypatch.setattr(
        planificacion_service,
        "evaluar_restricciones_logisticas",
        lambda **kwargs: _restricciones(),
    )

    def sin_solucion(**kwargs):
        raise ReglaNegocioError("No existe una ruta posible.")

    monkeypatch.setattr(
        planificacion_service,
        "optimizar_multi_entrega",
        sin_solucion,
    )

    with pytest.raises(ReglaNegocioError, match="No existe una ruta"):
        planificacion_service.planificar_entregas(1, [1, 2], 1)


def test_endpoint_planificar_responde_plan_factible():
    with patch(
        "backend.app.api.optimizacion.planificar_entregas",
        return_value=_respuesta_planificacion(),
    ):
        respuesta = client.post(
            "/api/optimizacion/planificar",
            json={
                "origen": 1,
                "pedidos": [1, 2],
                "id_vehiculo": 1,
                "regresar_origen": False,
            },
        )

    assert respuesta.status_code == 200
    assert respuesta.json()["factible"] is True
    assert respuesta.json()["algoritmo"] == "TSP_EXACTO_DIJKSTRA"


def test_endpoint_pedido_inexistente_retorna_404():
    with patch(
        "backend.app.api.optimizacion.planificar_entregas",
        side_effect=RecursoNoEncontradoError("El pedido 99 no existe."),
    ):
        respuesta = client.post(
            "/api/optimizacion/planificar",
            json={"origen": 1, "pedidos": [99], "id_vehiculo": 1},
        )

    assert respuesta.status_code == 404


def test_endpoint_exceso_capacidad_retorna_409():
    with patch(
        "backend.app.api.optimizacion.planificar_entregas",
        side_effect=ReglaNegocioError("La planificacion no es factible."),
    ):
        respuesta = client.post(
            "/api/optimizacion/planificar",
            json={"origen": 1, "pedidos": [1], "id_vehiculo": 1},
        )

    assert respuesta.status_code == 409


def test_endpoint_rechaza_pedidos_duplicados():
    respuesta = client.post(
        "/api/optimizacion/planificar",
        json={"origen": 1, "pedidos": [1, 1], "id_vehiculo": 1},
    )

    assert respuesta.status_code == 422
