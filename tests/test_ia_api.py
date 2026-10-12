from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
)
from tests.conftest import crear_principal


client = TestClient(app)


@pytest.fixture(autouse=True)
def _auth_operador_api():
    from backend.app.core.deps import sesion_actual

    app.dependency_overrides[sesion_actual] = lambda: crear_principal("OPERADOR")
    yield
    app.dependency_overrides.pop(sesion_actual, None)


def _planificacion():
    return {
        "factible": True,
        "peso_total": 75,
        "capacidad_peso": 100,
        "volumen_total": 0.6,
        "capacidad_volumen": 1,
        "pedidos": [
            {"id_pedido": 1, "prioridad": "NORMAL"},
            {"id_pedido": 2, "prioridad": "URGENTE"},
        ],
        "destinos": [2, 3],
        "recorrido": [1, 2, 3],
        "distancia_total_km": 7,
        "regresar_origen": False,
    }


def test_endpoint_ia_responde_analisis():
    with patch(
        "backend.app.api.ia.planificar_entregas",
        return_value=_planificacion(),
    ):
        respuesta = client.post(
            "/api/ia/analizar-planificacion",
            json={
                "origen": 1,
                "pedidos": [1, 2],
                "id_vehiculo": 1,
                "regresar_origen": False,
            },
        )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["nivel_riesgo"] == "MEDIO"
    assert datos["indicadores"]["cantidad_pedidos"] == 2
    assert datos["motor"] == "REGLAS_LOGISTICAS_V1"


def test_endpoint_ia_rechaza_datos_invalidos():
    respuesta = client.post(
        "/api/ia/analizar-planificacion",
        json={"origen": 0, "pedidos": [], "id_vehiculo": 0},
    )

    assert respuesta.status_code == 422


def test_endpoint_ia_pedido_inexistente_retorna_404():
    with patch(
        "backend.app.api.ia.planificar_entregas",
        side_effect=RecursoNoEncontradoError("El pedido 99 no existe."),
    ):
        respuesta = client.post(
            "/api/ia/analizar-planificacion",
            json={"origen": 1, "pedidos": [99], "id_vehiculo": 1},
        )

    assert respuesta.status_code == 404


def test_endpoint_ia_error_negocio_retorna_409():
    with patch(
        "backend.app.api.ia.planificar_entregas",
        side_effect=ReglaNegocioError("La planificacion no es factible."),
    ):
        respuesta = client.post(
            "/api/ia/analizar-planificacion",
            json={"origen": 1, "pedidos": [1], "id_vehiculo": 1},
        )

    assert respuesta.status_code == 409
