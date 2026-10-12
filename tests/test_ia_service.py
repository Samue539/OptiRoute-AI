import pytest

from backend.app.services.excepciones import ReglaNegocioError
from backend.app.services.ia_service import analizar_planificacion


def _planificacion(
    peso_total=50,
    capacidad_peso=100,
    volumen_total=0.6,
    capacidad_volumen=1,
    prioridades=("NORMAL", "ALTA"),
    destinos=(2, 3),
    factible=True,
    regresar_origen=False,
):
    pedidos = [
        {
            "id_pedido": indice,
            "prioridad": prioridad,
        }
        for indice, prioridad in enumerate(prioridades, start=1)
    ]
    return {
        "factible": factible,
        "peso_total": peso_total,
        "capacidad_peso": capacidad_peso,
        "volumen_total": volumen_total,
        "capacidad_volumen": capacidad_volumen,
        "pedidos": pedidos,
        "destinos": list(destinos),
        "recorrido": [1, *destinos],
        "distancia_total_km": 12,
        "regresar_origen": regresar_origen,
    }


def _codigos(resultado):
    return {alerta["codigo"] for alerta in resultado["alertas"]}


def test_riesgo_bajo():
    resultado = analizar_planificacion(_planificacion())

    assert resultado["nivel_riesgo"] == "BAJO"
    assert resultado["alertas"] == []
    assert resultado["indicadores"]["utilizacion_peso_pct"] == 50.0
    assert resultado["indicadores"]["utilizacion_volumen_pct"] == 60.0


def test_capacidad_alta_genera_riesgo_alto():
    resultado = analizar_planificacion(_planificacion(peso_total=94))

    assert resultado["nivel_riesgo"] == "ALTO"
    assert "CAPACIDAD_PESO_ALTA" in _codigos(resultado)


def test_capacidad_critica():
    resultado = analizar_planificacion(_planificacion(peso_total=100))

    assert resultado["nivel_riesgo"] == "CRITICO"
    assert "CAPACIDAD_PESO_CRITICA" in _codigos(resultado)


def test_pedido_urgente_genera_alerta():
    resultado = analizar_planificacion(
        _planificacion(prioridades=("URGENTE", "NORMAL"))
    )

    assert resultado["nivel_riesgo"] == "MEDIO"
    assert "PEDIDOS_URGENTES" in _codigos(resultado)
    assert resultado["indicadores"]["pedidos_urgentes"] == 1


def test_multiples_alertas_y_limite_tsp():
    resultado = analizar_planificacion(
        _planificacion(
            peso_total=95,
            volumen_total=0.92,
            prioridades=("URGENTE", "ALTA", "NORMAL"),
            destinos=tuple(range(2, 9)),
        )
    )

    assert resultado["nivel_riesgo"] == "ALTO"
    assert _codigos(resultado) == {
        "CAPACIDAD_PESO_ALTA",
        "CAPACIDAD_VOLUMEN_ALTA",
        "PEDIDOS_URGENTES",
        "TSP_CERCA_LIMITE",
    }


def test_planificacion_no_factible_es_critica():
    resultado = analizar_planificacion(
        _planificacion(peso_total=110, factible=False)
    )

    assert resultado["nivel_riesgo"] == "CRITICO"
    assert "PLAN_NO_FACTIBLE" in _codigos(resultado)
    assert "CAPACIDAD_PESO_CRITICA" in _codigos(resultado)


def test_regreso_origen_se_explica_sin_inventar_distancia():
    resultado = analizar_planificacion(
        _planificacion(regresar_origen=True)
    )

    assert resultado["indicadores"]["regresar_origen"] is True
    assert any(
        "regreso al origen" in recomendacion
        for recomendacion in resultado["recomendaciones"]
    )


def test_capacidad_invalida_se_rechaza():
    with pytest.raises(ReglaNegocioError, match="capacidad"):
        analizar_planificacion(_planificacion(capacidad_peso=0))
