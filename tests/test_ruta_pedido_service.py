from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from backend.app.services import ruta_pedido_service
from backend.app.services.excepciones import ReglaNegocioError
from tests.conftest import ConexionSimulada


AHORA = datetime(2026, 8, 16, tzinfo=timezone.utc)


def test_agregar_pedido_a_ruta(monkeypatch):
    conexion = ConexionSimulada(
        [
            (1,),
            (8, "PED-000008", "PENDIENTE"),
            None,
            None,
            (4, AHORA),
        ]
    )
    monkeypatch.setattr(
        ruta_pedido_service,
        "obtener_conexion",
        lambda: conexion,
    )

    resultado = ruta_pedido_service.agregar_pedido_ruta(1, 8, 1)

    assert resultado["id_ruta_pedido"] == 4
    assert resultado["id_pedido"] == 8
    assert resultado["orden_entrega"] == 1
    assert conexion.commits == 1


def test_rechazar_pedido_duplicado(monkeypatch):
    conexion = ConexionSimulada(
        [
            (1,),
            (8, "PED-000008", "PENDIENTE"),
            (4,),
        ]
    )
    monkeypatch.setattr(
        ruta_pedido_service,
        "obtener_conexion",
        lambda: conexion,
    )

    with pytest.raises(ReglaNegocioError, match="ya esta asociado"):
        ruta_pedido_service.agregar_pedido_ruta(1, 8, 1)

    assert conexion.commits == 0
    assert conexion.rollbacks == 1


def test_consultar_pedidos_de_ruta(monkeypatch):
    pedidos = [
        (
            4,
            1,
            8,
            "PED-000008",
            2,
            3,
            "Paquete",
            Decimal("4.50"),
            Decimal("0.125"),
            "ALTA",
            "PENDIENTE",
            date(2026, 8, 17),
            AHORA,
        )
    ]
    conexion = ConexionSimulada([(1,), pedidos])
    monkeypatch.setattr(
        ruta_pedido_service,
        "obtener_conexion",
        lambda: conexion,
    )

    resultado = ruta_pedido_service.listar_pedidos_ruta(1)

    assert resultado[0]["codigo"] == "PED-000008"
    assert resultado[0]["peso_kg"] == 4.5
    assert resultado[0]["orden_entrega"] == 1
    consulta = conexion.cursor_simulado.consultas[1][0]
    assert "ORDER BY rp.orden_entrega" in consulta
