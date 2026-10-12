from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.app.api import conductores as conductores_api
from backend.app.api import pedidos as pedidos_api
from backend.app.api import vehiculos as vehiculos_api
from backend.app.main import app
from backend.app.services import (
    conductores_service,
    pedidos_service,
    vehiculos_service,
)
from tests.conftest import ConexionSimulada, crear_principal


AHORA = datetime(2026, 8, 22, tzinfo=timezone.utc)
client = TestClient(app)


@pytest.fixture(autouse=True)
def _auth_operador_api():
    from backend.app.core.deps import sesion_actual

    app.dependency_overrides[sesion_actual] = lambda: crear_principal("OPERADOR")
    yield
    app.dependency_overrides.pop(sesion_actual, None)


def _fila_pedido():
    return (
        1, "PED-DEMO-001", 10, 20, "Carga demo", Decimal("20.00"),
        Decimal("0.250"), "URGENTE", "PENDIENTE", date(2026, 8, 22),
        2, "Cliente A", "CLIENTE", Decimal("-0.205"),
        Decimal("-78.495"), True, "PENDIENTE", AHORA,
    )


def _fila_vehiculo():
    return (
        1, "DEM-001", "OptiRoute", "Demo", 2024, "CAMIONETA",
        Decimal("500.00"), Decimal("5.000"), "DISPONIBLE", True,
    )


def _fila_conductor():
    return (1, "Ana", "Demo", "LIC-DEMO-001", "B", "0990000000", True, True)


def test_listado_pedidos_vacio(monkeypatch):
    conexion = ConexionSimulada([[]])
    monkeypatch.setattr(pedidos_service, "obtener_conexion", lambda: conexion)

    assert pedidos_service.listar_pedidos() == []
    assert conexion.cerrada is True


def test_listado_pedidos_incluye_destino(monkeypatch):
    conexion = ConexionSimulada([[_fila_pedido()]])
    monkeypatch.setattr(pedidos_service, "obtener_conexion", lambda: conexion)

    pedido = pedidos_service.listar_pedidos()[0]

    assert pedido["codigo"] == "PED-DEMO-001"
    assert pedido["destino"]["id_nodo"] == 2
    assert pedido["peso_kg"] == 20.0


def test_pedido_inexistente(monkeypatch):
    conexion = ConexionSimulada([[]])
    monkeypatch.setattr(pedidos_service, "obtener_conexion", lambda: conexion)

    assert pedidos_service.obtener_pedido(999) is None


def test_listado_vehiculos_vacio(monkeypatch):
    conexion = ConexionSimulada([[]])
    monkeypatch.setattr(vehiculos_service, "obtener_conexion", lambda: conexion)

    assert vehiculos_service.listar_vehiculos() == []


def test_listado_vehiculos_expone_capacidad_y_disponibilidad(monkeypatch):
    conexion = ConexionSimulada([[_fila_vehiculo()]])
    monkeypatch.setattr(vehiculos_service, "obtener_conexion", lambda: conexion)

    vehiculo = vehiculos_service.listar_vehiculos()[0]

    assert vehiculo["capacidad_kg"] == 500.0
    assert vehiculo["capacidad_volumen_m3"] == 5.0
    assert vehiculo["disponible"] is True


def test_vehiculo_inexistente(monkeypatch):
    conexion = ConexionSimulada([[]])
    monkeypatch.setattr(vehiculos_service, "obtener_conexion", lambda: conexion)

    assert vehiculos_service.obtener_vehiculo(999) is None


def test_listado_conductores_vacio(monkeypatch):
    conexion = ConexionSimulada([[]])
    monkeypatch.setattr(conductores_service, "obtener_conexion", lambda: conexion)

    assert conductores_service.listar_conductores() == []


def test_listado_conductores_expone_estado(monkeypatch):
    conexion = ConexionSimulada([[_fila_conductor()]])
    monkeypatch.setattr(conductores_service, "obtener_conexion", lambda: conexion)

    conductor = conductores_service.listar_conductores()[0]

    assert conductor["activo"] is True
    assert conductor["disponible"] is True


def test_conductor_inexistente(monkeypatch):
    conexion = ConexionSimulada([[]])
    monkeypatch.setattr(conductores_service, "obtener_conexion", lambda: conexion)

    assert conductores_service.obtener_conductor(999) is None


def test_endpoint_catalogos_devuelven_listas_vacias(monkeypatch):
    monkeypatch.setattr(pedidos_api, "listar_pedidos", lambda: [])
    monkeypatch.setattr(vehiculos_api, "listar_vehiculos", lambda: [])
    monkeypatch.setattr(conductores_api, "listar_conductores", lambda: [])

    assert client.get("/api/pedidos").json() == []
    assert client.get("/api/vehiculos").json() == []
    assert client.get("/api/conductores").json() == []


def test_endpoint_catalogos_inexistentes_devuelven_404(monkeypatch):
    monkeypatch.setattr(pedidos_api, "obtener_pedido", lambda _: None)
    monkeypatch.setattr(vehiculos_api, "obtener_vehiculo", lambda _: None)
    monkeypatch.setattr(conductores_api, "obtener_conductor", lambda _: None)

    assert client.get("/api/pedidos/999").status_code == 404
    assert client.get("/api/vehiculos/999").status_code == 404
    assert client.get("/api/conductores/999").status_code == 404


def test_integracion_catalogos_consulta_postgresql_real():
    """Los servicios usan la conexion real y aceptan catalogos vacios o poblados."""
    import pytest

    try:
        assert isinstance(pedidos_service.listar_pedidos(), list)
        assert isinstance(vehiculos_service.listar_vehiculos(), list)
        assert isinstance(conductores_service.listar_conductores(), list)
    except RuntimeError as exc:
        if "psycopg no disponible" in str(exc):
            pytest.skip(f"PostgreSQL driver bloqueado en este entorno (WDAC/SAC): {exc}")
        raise
    except Exception as exc:
        # Si PostgreSQL no esta disponible, marcar como skip en lugar de fallar.
        if "no pq wrapper" in str(exc).lower() or "could not" in str(exc).lower():
            pytest.skip(f"PostgreSQL no disponible: {exc}")
        raise
