import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.api import rutas as rutas_api
from backend.app.schemas.ruta import RutaEstadoActualizar


def test_endpoint_consultar_ruta_existente(monkeypatch):
    monkeypatch.setattr(
        rutas_api,
        "obtener_ruta",
        lambda id_ruta: {
            "id_ruta": id_ruta,
            "codigo": "RUT-000001",
            "puntos": [],
        },
    )

    respuesta = rutas_api.consultar_ruta(1)

    assert respuesta["id_ruta"] == 1


def test_endpoint_consultar_ruta_inexistente_devuelve_404(monkeypatch):
    monkeypatch.setattr(rutas_api, "obtener_ruta", lambda id_ruta: None)

    with pytest.raises(HTTPException) as error:
        rutas_api.consultar_ruta(9999)

    assert error.value.status_code == 404
    assert error.value.detail == "La ruta no existe."


def test_schema_rechaza_estado_fuera_del_catalogo():
    with pytest.raises(ValidationError):
        RutaEstadoActualizar(estado="REABIERTA")
