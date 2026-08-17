from datetime import datetime, timezone
from decimal import Decimal

import pytest

from backend.app.services import ruta_service
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
)
from tests.conftest import ConexionSimulada


AHORA = datetime(2026, 8, 16, tzinfo=timezone.utc)


def test_consultar_ruta_existente(monkeypatch):
    fila_ruta = (
        1,
        "RUT-000001",
        1,
        "Bodega Principal",
        5,
        "Cliente D",
        "PLANIFICADA",
        Decimal("12.000"),
        Decimal("23.00"),
        Decimal("5.00"),
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        AHORA,
        None,
        None,
        AHORA,
        AHORA,
    )
    puntos = [
        (1, 1, "Bodega Principal", "BODEGA", -0.2, -78.5, 0),
        (2, 2, "Cliente A", "CLIENTE", -0.205, -78.495, 4),
    ]
    conexion = ConexionSimulada([fila_ruta, puntos])
    monkeypatch.setattr(ruta_service, "obtener_conexion", lambda: conexion)

    resultado = ruta_service.obtener_ruta(1)

    assert resultado["codigo"] == "RUT-000001"
    assert resultado["conductor"] is None
    assert resultado["vehiculo"] is None
    assert resultado["puntos"][1]["distancia_acumulada_km"] == 4.0
    assert conexion.cerrada is True


def test_consultar_ruta_inexistente(monkeypatch):
    conexion = ConexionSimulada([None])
    monkeypatch.setattr(ruta_service, "obtener_conexion", lambda: conexion)

    assert ruta_service.obtener_ruta(9999) is None


def test_listar_rutas_mas_recientes(monkeypatch):
    filas = [
        (
            2,
            "RUT-000002",
            1,
            "Bodega",
            5,
            "Cliente",
            "ASIGNADA",
            Decimal("12"),
            3,
            "Ana",
            "Perez",
            "LIC-3",
            4,
            "ABC-123",
            "Marca",
            "Modelo",
            AHORA,
            AHORA,
        )
    ]
    conexion = ConexionSimulada([filas])
    monkeypatch.setattr(ruta_service, "obtener_conexion", lambda: conexion)

    resultado = ruta_service.listar_rutas()

    assert resultado[0]["id_ruta"] == 2
    assert resultado[0]["conductor"]["nombres"] == "Ana"
    assert resultado[0]["vehiculo"]["placa"] == "ABC-123"
    consulta = conexion.cursor_simulado.consultas[0][0]
    assert "ORDER BY r.creado_en DESC, r.id_ruta DESC" in consulta


def test_asignar_conductor_y_vehiculo_validos(monkeypatch):
    conexion = ConexionSimulada(
        [
            ("PLANIFICADA",),
            (1, "LIC-1", "B", "099", True, True),
            (1, "ABC-123", "Marca", "Modelo", "CAMIONETA", "DISPONIBLE", True),
            (1, "RUT-000001", "ASIGNADA", AHORA),
        ]
    )
    monkeypatch.setattr(ruta_service, "obtener_conexion", lambda: conexion)

    resultado = ruta_service.asignar_conductor_vehiculo(1, 1, 1)

    assert resultado["estado"] == "ASIGNADA"
    assert resultado["conductor"]["id_conductor"] == 1
    assert resultado["vehiculo"]["id_vehiculo"] == 1
    assert conexion.commits == 1
    assert conexion.rollbacks == 0


def test_asignar_conductor_inexistente(monkeypatch):
    conexion = ConexionSimulada([("PLANIFICADA",), None])
    monkeypatch.setattr(ruta_service, "obtener_conexion", lambda: conexion)

    with pytest.raises(RecursoNoEncontradoError, match="conductor"):
        ruta_service.asignar_conductor_vehiculo(1, 999, 1)

    assert conexion.commits == 0
    assert conexion.rollbacks == 1


@pytest.mark.parametrize(
    ("estado_actual", "estado_nuevo", "fecha_inicio", "fecha_fin"),
    [
        ("ASIGNADA", "EN_RUTA", AHORA, None),
        ("EN_RUTA", "COMPLETADA", AHORA, AHORA),
    ],
)
def test_cambiar_estado_valido(
    monkeypatch,
    estado_actual,
    estado_nuevo,
    fecha_inicio,
    fecha_fin,
):
    conexion = ConexionSimulada(
        [
            (estado_actual, 1, 1),
            (1, "RUT-000001", estado_nuevo, fecha_inicio, fecha_fin, AHORA),
        ]
    )
    monkeypatch.setattr(ruta_service, "obtener_conexion", lambda: conexion)

    resultado = ruta_service.actualizar_estado_ruta(1, estado_nuevo)

    assert resultado["estado"] == estado_nuevo
    assert resultado["fecha_inicio"] == fecha_inicio
    assert resultado["fecha_fin"] == fecha_fin
    assert conexion.commits == 1


def test_rechazar_transicion_completada_a_en_ruta(monkeypatch):
    conexion = ConexionSimulada([("COMPLETADA", 1, 1)])
    monkeypatch.setattr(ruta_service, "obtener_conexion", lambda: conexion)

    with pytest.raises(ReglaNegocioError, match="No se permite"):
        ruta_service.actualizar_estado_ruta(1, "EN_RUTA")

    assert conexion.commits == 0
    assert conexion.rollbacks == 1
