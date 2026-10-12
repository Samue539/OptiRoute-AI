"""Motor local y determinista de analisis para planes logisticos."""

from collections import Counter

from backend.app.services.excepciones import ReglaNegocioError


UMBRAL_CAPACIDAD_ALTA_PCT = 90.0
UMBRAL_CAPACIDAD_CRITICA_PCT = 100.0
UMBRAL_DESTINOS_TSP_CERCANO = 7
LIMITE_DESTINOS_TSP = 8

_ORDEN_RIESGO = {
    "BAJO": 0,
    "MEDIO": 1,
    "ALTO": 2,
    "CRITICO": 3,
}


def _porcentaje(utilizado, capacidad):
    if capacidad is None or capacidad <= 0:
        raise ReglaNegocioError(
            "La capacidad debe ser mayor que cero para analizar la planificacion."
        )
    if utilizado is None or utilizado < 0:
        raise ReglaNegocioError(
            "La carga utilizada no puede ser negativa ni estar ausente."
        )
    return round((utilizado / capacidad) * 100, 2)


def _elevar_riesgo(nivel_actual, nivel_nuevo):
    if _ORDEN_RIESGO[nivel_nuevo] > _ORDEN_RIESGO[nivel_actual]:
        return nivel_nuevo
    return nivel_actual


def analizar_planificacion(planificacion: dict):
    peso_pct = _porcentaje(
        planificacion.get("peso_total"),
        planificacion.get("capacidad_peso"),
    )
    volumen_pct = _porcentaje(
        planificacion.get("volumen_total"),
        planificacion.get("capacidad_volumen"),
    )
    pedidos = planificacion.get("pedidos") or []
    destinos = planificacion.get("destinos") or []
    recorrido = planificacion.get("recorrido") or []
    distancia = planificacion.get("distancia_total_km")

    if distancia is None or distancia < 0:
        raise ReglaNegocioError(
            "La distancia total no puede ser negativa ni estar ausente."
        )

    prioridades = Counter(
        str(pedido.get("prioridad", "NORMAL")).upper()
        for pedido in pedidos
    )
    urgentes = prioridades.get("URGENTE", 0)
    factible = bool(planificacion.get("factible"))
    regresar_origen = bool(planificacion.get("regresar_origen"))
    nivel_riesgo = "BAJO"
    alertas = []
    recomendaciones = []

    if not factible:
        nivel_riesgo = "CRITICO"
        alertas.append(
            {
                "codigo": "PLAN_NO_FACTIBLE",
                "severidad": "CRITICA",
                "mensaje": "La planificacion no cumple las restricciones logisticas.",
            }
        )
        recomendaciones.append(
            "Redistribuya la carga o seleccione un vehiculo con mayor capacidad."
        )

    for dimension, porcentaje in (
        ("PESO", peso_pct),
        ("VOLUMEN", volumen_pct),
    ):
        nombre = dimension.lower()
        if porcentaje >= UMBRAL_CAPACIDAD_CRITICA_PCT:
            nivel_riesgo = _elevar_riesgo(nivel_riesgo, "CRITICO")
            alertas.append(
                {
                    "codigo": f"CAPACIDAD_{dimension}_CRITICA",
                    "severidad": "CRITICA",
                    "mensaje": (
                        f"La utilizacion de {nombre} alcanza el {porcentaje:.2f}%."
                    ),
                }
            )
            recomendaciones.append(
                f"Reduzca la carga de {nombre} o use un vehiculo con mayor capacidad."
            )
        elif porcentaje >= UMBRAL_CAPACIDAD_ALTA_PCT:
            nivel_riesgo = _elevar_riesgo(nivel_riesgo, "ALTO")
            alertas.append(
                {
                    "codigo": f"CAPACIDAD_{dimension}_ALTA",
                    "severidad": "ADVERTENCIA",
                    "mensaje": (
                        f"La utilizacion de {nombre} es alta: {porcentaje:.2f}%."
                    ),
                }
            )
            recomendaciones.append(
                f"Verifique el margen operativo de {nombre} antes de despachar."
            )

    if urgentes:
        nivel_riesgo = _elevar_riesgo(nivel_riesgo, "MEDIO")
        sustantivo = "pedido" if urgentes == 1 else "pedidos"
        alertas.append(
            {
                "codigo": "PEDIDOS_URGENTES",
                "severidad": "ADVERTENCIA",
                "mensaje": f"La planificacion contiene {urgentes} {sustantivo} URGENTE.",
            }
        )
        recomendaciones.append(
            "Revise la posicion de los pedidos urgentes sin alterar la factibilidad del plan."
        )

    if len(destinos) >= UMBRAL_DESTINOS_TSP_CERCANO:
        nivel_riesgo = _elevar_riesgo(nivel_riesgo, "MEDIO")
        alertas.append(
            {
                "codigo": "TSP_CERCA_LIMITE",
                "severidad": "ADVERTENCIA",
                "mensaje": (
                    f"La ruta contiene {len(destinos)} destinos y el limite del "
                    f"TSP exacto es {LIMITE_DESTINOS_TSP}."
                ),
            }
        )
        recomendaciones.append(
            "Evite agregar mas destinos a esta ejecucion del TSP exacto."
        )

    if regresar_origen:
        recomendaciones.append(
            "El plan incluye regreso al origen; considere esa distancia al estimar tiempo y costo."
        )

    if not recomendaciones:
        recomendaciones.append(
            "Mantenga las capacidades y prioridades actuales durante la ejecucion."
        )

    indicadores = {
        "utilizacion_peso_pct": peso_pct,
        "utilizacion_volumen_pct": volumen_pct,
        "cantidad_pedidos": len(pedidos),
        "cantidad_destinos": len(destinos),
        "cantidad_nodos_recorrido": len(recorrido),
        "pedidos_urgentes": urgentes,
        "distancia_total_km": float(distancia),
        "regresar_origen": regresar_origen,
        "factible": factible,
        "distribucion_prioridades": dict(sorted(prioridades.items())),
    }
    resumen = (
        f"Plan {nivel_riesgo.lower()} con {len(pedidos)} pedidos, "
        f"{len(destinos)} destinos y {float(distancia):.2f} km. "
        f"Utiliza {peso_pct:.2f}% del peso y {volumen_pct:.2f}% del volumen disponible."
    )

    return {
        "nivel_riesgo": nivel_riesgo,
        "alertas": alertas,
        "recomendaciones": recomendaciones,
        "indicadores": indicadores,
        "resumen": resumen,
        "motor": "REGLAS_LOGISTICAS_V1",
    }
