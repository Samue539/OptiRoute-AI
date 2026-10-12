"""Esquemas del Centro de Distribucion y Entregas (Fase 1).

Solo validan forma y rangos. La pertenencia (empresa, membresia y
asignacion) y la unicidad real se verifican en el servicio contra la
base de datos: nunca se confia en lo que envia el frontend.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


RELACIONES_RECEPTOR = (
    "DESTINATARIO",
    "FAMILIAR",
    "VECINO",
    "PORTERIA",
    "EMPLEADO",
    "OTRO",
)

MOTIVOS_FALLA = (
    "AUSENTE",
    "DIRECCION_INCOMPLETA",
    "RECHAZADO",
    "ZONA_INSEGURA",
    "REPROGRAMADO",
    "OTRO",
)

ORIGENES_GPS = ("GPS", "RED", "MANUAL", "DESCONOCIDO")


class ZonaInfo(BaseModel):
    id_zona: int
    codigo: str
    nombre: str
    ciudad: str
    activa: bool


class ProgresoRuta(BaseModel):
    total: int = 0
    pendientes: int = 0
    en_ruta: int = 0
    entregadas: int = 0
    fallidas: int = 0


class RutaAsignadaInfo(BaseModel):
    id_ruta: int
    codigo: str
    nombre_ruta: str | None = None
    estado: str
    zona: ZonaInfo | None = None
    conductor: dict | None = None
    vehiculo: dict | None = None
    distancia_total_km: float | None = None
    progreso: ProgresoRuta = Field(default_factory=ProgresoRuta)


class GuiaInfo(BaseModel):
    id_guia: int
    numero_guia: str
    estado: str
    destinatario_nombre: str
    direccion_texto: str
    telefono_autorizado: str | None = None
    id_ruta: int | None = None
    ruta_codigo: str | None = None
    zona: ZonaInfo | None = None
    intentos_entrega: int = 0
    fecha_entrega: str | None = None


class GuiaEventoInfo(BaseModel):
    id_evento: int
    tipo: str
    actor_cuenta: int | None = None
    receptor_nombre: str | None = None
    relacion_destinatario: str | None = None
    motivo_falla: str | None = None
    gps_latitud: float | None = None
    gps_longitud: float | None = None
    gps_precision_m: float | None = None
    gps_origen: str | None = None
    observaciones: str | None = None
    evidencias: list[dict] = Field(default_factory=list)
    creado_en: str | None = None


class ResumenGuias(BaseModel):
    total: int = 0
    pendientes: int = 0
    en_ruta: int = 0
    entregadas: int = 0
    fallidas: int = 0


class EntregaRegistrar(BaseModel):
    receptor_nombre: str = Field(min_length=2, max_length=150)
    relacion_destinatario: Literal[
        "DESTINATARIO", "FAMILIAR", "VECINO", "PORTERIA", "EMPLEADO", "OTRO"
    ]
    gps_latitud: float | None = Field(default=None, ge=-90, le=90)
    gps_longitud: float | None = Field(default=None, ge=-180, le=180)
    gps_precision_m: float | None = Field(default=None, gt=0, le=100000)
    gps_origen: Literal["GPS", "RED", "MANUAL", "DESCONOCIDO"] | None = None
    observaciones: str | None = Field(default=None, max_length=500)
    clave_idempotencia: str | None = Field(
        default=None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    )


class NovedadRegistrar(BaseModel):
    tipo: Literal["FALLIDA", "NOVEDAD"] = "FALLIDA"
    motivo_falla: str | None = Field(default=None, min_length=5, max_length=300)
    gps_latitud: float | None = Field(default=None, ge=-90, le=90)
    gps_longitud: float | None = Field(default=None, ge=-180, le=180)
    gps_precision_m: float | None = Field(default=None, gt=0, le=100000)
    gps_origen: Literal["GPS", "RED", "MANUAL", "DESCONOCIDO"] | None = None
    observaciones: str | None = Field(default=None, max_length=500)
    clave_idempotencia: str | None = Field(
        default=None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    )


class AsignacionDistribucionCrear(BaseModel):
    id_empresa: UUID
    id_cuenta: int = Field(gt=0)
    tipo_recurso: Literal["RUTA", "ZONA", "GUIA"] = "RUTA"
    id_recurso: int = Field(gt=0)
