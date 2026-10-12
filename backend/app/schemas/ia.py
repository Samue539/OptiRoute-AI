from enum import Enum

from pydantic import BaseModel


class NivelRiesgo(str, Enum):
    BAJO = "BAJO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"
    CRITICO = "CRITICO"


class SeveridadAlerta(str, Enum):
    INFORMATIVA = "INFORMATIVA"
    ADVERTENCIA = "ADVERTENCIA"
    CRITICA = "CRITICA"


class AlertaIA(BaseModel):
    codigo: str
    severidad: SeveridadAlerta
    mensaje: str


class IndicadoresIA(BaseModel):
    utilizacion_peso_pct: float
    utilizacion_volumen_pct: float
    cantidad_pedidos: int
    cantidad_destinos: int
    cantidad_nodos_recorrido: int
    pedidos_urgentes: int
    distancia_total_km: float
    regresar_origen: bool
    factible: bool
    distribucion_prioridades: dict[str, int]


class AnalisisPlanificacionResponse(BaseModel):
    nivel_riesgo: NivelRiesgo
    alertas: list[AlertaIA]
    recomendaciones: list[str]
    indicadores: IndicadoresIA
    resumen: str
    motor: str = "REGLAS_LOGISTICAS_V1"
