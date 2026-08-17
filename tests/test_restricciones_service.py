from decimal import Decimal

import pytest

from backend.app.services import restricciones_service
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
)
from tests.conftest import ConexionSimulada


def _pedidos_carga():
    return [
        {"peso_kg": 25, "volumen_m3": 0.25},
        {"peso_kg": 40, "volumen_m3": 0.40},
        {"peso_kg": 15, "volumen_m3": 0.15},
        {"peso_kg": 30, "volumen_m3": 0.30},
    ]


def _vehiculo(capacidad_kg=120, capacidad_volumen_m3=2):
    return {
        "capacidad_kg": capacidad_kg,
        "capacidad_volumen_m3": capacidad_volumen_m3,
    }


def _fila_pedido(
    id_pedido=1,
    peso=Decimal("25.00"),
    volumen=Decimal("0.250"),
    id_nodo=2,
    direccion_activa=True,
    nodo_existe=True,
    nodo_activo=True,
):
    nodo_bd = id_nodo if nodo_existe and id_nodo is not None else None
    return (
        id_pedido,
        f"PED-{id_pedido:06d}",
        10,
        20,
        "Paquete",
        peso,
        volumen,
        "ALTA",
        "PENDIENTE",
        id_nodo,
        direccion_activa,
        nodo_bd,
        "Cliente A" if nodo_bd is not None else None,
        "PUNTO_ENTREGA" if nodo_bd is not None else None,
        Decimal("-0.205000") if nodo_bd is not None else None,
        Decimal("-78.495000") if nodo_bd is not None else None,
        nodo_activo if nodo_bd is not None else None,
    )


def test_capacidad_suficiente_y_totales_correctos():
    resultado = restricciones_service.calcular_capacidad(
        _pedidos_carga(),
        _vehiculo(),
    )

    assert resultado["factible"] is True
    assert resultado["peso_total"] == 110.0
    assert resultado["volumen_total"] == 1.10
    assert resultado["excede_peso"] is False
    assert resultado["excede_volumen"] is False


def test_exceso_de_peso_no_es_factible():
    resultado = restricciones_service.calcular_capacidad(
        _pedidos_carga(),
        _vehiculo(capacidad_kg=80),
    )

    assert resultado["factible"] is False
    assert resultado["excede_peso"] is True
    assert resultado["exceso_peso_kg"] == 30.0


def test_exceso_de_volumen_no_es_factible():
    resultado = restricciones_service.calcular_capacidad(
        _pedidos_carga(),
        _vehiculo(capacidad_volumen_m3=0.8),
    )

    assert resultado["factible"] is False
    assert resultado["excede_volumen"] is True
    assert resultado["exceso_volumen_m3"] == 0.3


def test_pedido_inexistente(monkeypatch):
    conexion = ConexionSimulada([[]])
    monkeypatch.setattr(
        restricciones_service,
        "obtener_conexion",
        lambda: conexion,
    )

    with pytest.raises(RecursoNoEncontradoError, match="pedido 99"):
        restricciones_service.obtener_pedidos_para_planificacion([99])


def test_vehiculo_inexistente(monkeypatch):
    conexion = ConexionSimulada([None])
    monkeypatch.setattr(
        restricciones_service,
        "obtener_conexion",
        lambda: conexion,
    )

    with pytest.raises(RecursoNoEncontradoError, match="vehiculo"):
        restricciones_service.obtener_vehiculo_para_planificacion(99)


def test_vehiculo_no_disponible(monkeypatch):
    fila = (
        1,
        "ABC-123",
        "Marca",
        "Modelo",
        "CAMIONETA",
        Decimal("120"),
        Decimal("2"),
        "MANTENIMIENTO",
        True,
    )
    conexion = ConexionSimulada([fila])
    monkeypatch.setattr(
        restricciones_service,
        "obtener_conexion",
        lambda: conexion,
    )

    with pytest.raises(ReglaNegocioError, match="no esta disponible"):
        restricciones_service.obtener_vehiculo_para_planificacion(1)


def test_vehiculo_inactivo(monkeypatch):
    fila = (
        1,
        "ABC-123",
        "Marca",
        "Modelo",
        "CAMIONETA",
        Decimal("120"),
        Decimal("2"),
        "DISPONIBLE",
        False,
    )
    conexion = ConexionSimulada([fila])
    monkeypatch.setattr(
        restricciones_service,
        "obtener_conexion",
        lambda: conexion,
    )

    with pytest.raises(ReglaNegocioError, match="no esta activo"):
        restricciones_service.obtener_vehiculo_para_planificacion(1)


def test_obtener_vehiculo_reutiliza_ambas_capacidades(monkeypatch):
    fila = (
        1,
        "ABC-123",
        "Marca",
        "Modelo",
        "CAMIONETA",
        Decimal("120.00"),
        Decimal("2.500"),
        "DISPONIBLE",
        True,
    )
    conexion = ConexionSimulada([fila])
    monkeypatch.setattr(
        restricciones_service,
        "obtener_conexion",
        lambda: conexion,
    )

    vehiculo = restricciones_service.obtener_vehiculo_para_planificacion(1)

    assert vehiculo["capacidad_kg"] == 120.0
    assert vehiculo["capacidad_volumen_m3"] == 2.5


def test_pedidos_duplicados_se_rechazan_sin_consultar_bd(monkeypatch):
    def no_debe_consultar(*args, **kwargs):
        raise AssertionError("No debe consultar la base con IDs duplicados")

    monkeypatch.setattr(
        restricciones_service,
        "obtener_pedidos_para_planificacion",
        no_debe_consultar,
    )

    with pytest.raises(ReglaNegocioError, match="duplicados"):
        restricciones_service.evaluar_restricciones_logisticas([1, 1], 1)


def test_pedido_sin_nodo_destino(monkeypatch):
    conexion = ConexionSimulada([[ _fila_pedido(id_nodo=None) ]])
    monkeypatch.setattr(
        restricciones_service,
        "obtener_conexion",
        lambda: conexion,
    )

    with pytest.raises(ReglaNegocioError, match="no tiene un nodo"):
        restricciones_service.obtener_pedidos_para_planificacion([1])


def test_pedido_con_nodo_inexistente(monkeypatch):
    conexion = ConexionSimulada(
        [[_fila_pedido(id_nodo=999, nodo_existe=False)]]
    )
    monkeypatch.setattr(
        restricciones_service,
        "obtener_conexion",
        lambda: conexion,
    )

    with pytest.raises(ReglaNegocioError, match="no existe o esta inactivo"):
        restricciones_service.obtener_pedidos_para_planificacion([1])


def test_obtener_pedido_conserva_prioridad_y_destino(monkeypatch):
    conexion = ConexionSimulada([[_fila_pedido()]])
    monkeypatch.setattr(
        restricciones_service,
        "obtener_conexion",
        lambda: conexion,
    )

    pedidos = restricciones_service.obtener_pedidos_para_planificacion([1])

    assert pedidos[0]["prioridad"] == "ALTA"
    assert pedidos[0]["destino"]["id_nodo"] == 2
    assert pedidos[0]["peso_kg"] == 25.0
    assert pedidos[0]["volumen_m3"] == 0.25
