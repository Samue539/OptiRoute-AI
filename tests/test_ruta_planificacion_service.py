from backend.app.algorithms.grafo import Grafo
from backend.app.services import ruta_planificacion_service as servicio
from backend.app.services.ruta_recursos import RecursoOcupadoError
from tests.conftest import ConexionSimulada

import pytest


def _plan(regresar=True):
    return {
        "orden_optimo": [2, 3],
        "recorrido": [1, 2, 3, 1] if regresar else [1, 2, 3],
        "distancia_total_km": 9,
        "destinos": [2, 3],
    }


def _grafo():
    grafo = Grafo()
    grafo.agregar_arista(1, 2, 2, bidireccional=False)
    grafo.agregar_arista(2, 3, 3, bidireccional=False)
    grafo.agregar_arista(3, 1, 4, bidireccional=False)
    return grafo


def _respuestas_guardado():
    respuestas = [
        None, None,
        (7, "LIC-7", "C", "099", True, True), None,
        (5, "ABC-123", "Marca", "Modelo", "CAMION", "DISPONIBLE", True, 100, 2), None,
        [(10, "PENDIENTE", 20, 0.2, 2), (11, "PENDIENTE", 30, 0.3, 3)],
        None,
        (42,), None,
    ]
    respuestas.extend([None] * 4)  # todos los puntos, incluido retorno
    respuestas.extend([None] * 2)  # ambos pedidos
    respuestas.extend([None, None, None])
    return respuestas


def _guardar(monkeypatch, conexion):
    monkeypatch.setattr(servicio, "planificar_entregas", lambda *args: _plan())
    monkeypatch.setattr(servicio, "cargar_grafo_desde_bd", _grafo)
    monkeypatch.setattr(servicio, "obtener_conexion", lambda: conexion)
    return servicio.guardar_ruta_planificada(
        origen=1, ids_pedidos=[10, 11], id_conductor=7, id_vehiculo=5,
        regresar_origen=True, clave_idempotencia="plan-prueba-001",
    )


def test_guarda_recorrido_completo_con_retorno(monkeypatch):
    conexion = ConexionSimulada(_respuestas_guardado())
    resultado = _guardar(monkeypatch, conexion)

    assert resultado["recorrido"] == [1, 2, 3, 1]
    assert resultado["pedidos"] == [
        {"id_pedido": 10, "orden_entrega": 1},
        {"id_pedido": 11, "orden_entrega": 2},
    ]
    puntos = [q for q, _ in conexion.cursor_simulado.consultas if "INSERT INTO logistica.ruta_puntos" in q]
    assert len(puntos) == 4
    assert conexion.commits == 1


def test_varios_pedidos_en_mismo_destino_no_se_pierden():
    pedidos = [
        {"id_pedido": 10, "id_nodo": 2},
        {"id_pedido": 11, "id_nodo": 2},
        {"id_pedido": 12, "id_nodo": 3},
    ]
    resultado = servicio._ordenar_pedidos(pedidos, [2, 3])

    assert [p["id_pedido"] for p in resultado] == [10, 11, 12]
    assert [p["orden_entrega"] for p in resultado] == [1, 2, 3]


def test_fallo_intermedio_hace_rollback(monkeypatch):
    respuestas = _respuestas_guardado()[:11]
    conexion = ConexionSimulada(respuestas)

    with pytest.raises(AssertionError, match="No se preparo"):
        _guardar(monkeypatch, conexion)

    assert conexion.commits == 0
    assert conexion.rollbacks == 1


def test_reintento_idempotente_devuelve_ruta_existente(monkeypatch):
    conexion = ConexionSimulada([None, (42, "RUT-000042", "ASIGNADA", 9)])
    monkeypatch.setattr(
        servicio,
        "planificar_entregas",
        lambda *args: (_ for _ in ()).throw(AssertionError("no debe recalcular")),
    )
    monkeypatch.setattr(servicio, "obtener_conexion", lambda: conexion)

    resultado = servicio.guardar_ruta_planificada(
        origen=1, ids_pedidos=[10, 11], id_conductor=7, id_vehiculo=5,
        regresar_origen=True, clave_idempotencia="plan-repetido-001",
    )

    assert resultado["id_ruta"] == 42
    assert resultado["duplicada"] is True
    assert conexion.commits == 1


def test_recurso_ocupado_impide_guardar(monkeypatch):
    conexion = ConexionSimulada([
        None, None,
        (7, "LIC-7", "C", "099", True, True),
        (1,),
    ])
    monkeypatch.setattr(servicio, "planificar_entregas", lambda *args: _plan())
    monkeypatch.setattr(servicio, "cargar_grafo_desde_bd", _grafo)
    monkeypatch.setattr(servicio, "obtener_conexion", lambda: conexion)

    with pytest.raises(RecursoOcupadoError, match="conductor"):
        servicio.guardar_ruta_planificada(
            origen=1, ids_pedidos=[10, 11], id_conductor=7, id_vehiculo=5,
            regresar_origen=True, clave_idempotencia="plan-ocupado-001",
        )
    assert conexion.rollbacks == 1


def test_vehiculo_ocupado_impide_guardar(monkeypatch):
    conexion = ConexionSimulada([
        None, None,
        (7, "LIC-7", "C", "099", True, True), None,
        (5, "ABC-123", "Marca", "Modelo", "CAMION", "DISPONIBLE", True, 100, 2),
        (1,),
    ])
    monkeypatch.setattr(servicio, "planificar_entregas", lambda *args: _plan())
    monkeypatch.setattr(servicio, "cargar_grafo_desde_bd", _grafo)
    monkeypatch.setattr(servicio, "obtener_conexion", lambda: conexion)

    with pytest.raises(RecursoOcupadoError, match="vehiculo"):
        servicio.guardar_ruta_planificada(
            origen=1, ids_pedidos=[10, 11], id_conductor=7, id_vehiculo=5,
            regresar_origen=True, clave_idempotencia="plan-vehiculo-ocupado",
        )
    assert conexion.rollbacks == 1
