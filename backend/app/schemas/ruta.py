from enum import Enum

from pydantic import BaseModel, Field


class EstadoRuta(str, Enum):
    PLANIFICADA = "PLANIFICADA"
    ASIGNADA = "ASIGNADA"
    EN_RUTA = "EN_RUTA"
    COMPLETADA = "COMPLETADA"
    CANCELADA = "CANCELADA"


class RutaCrear(BaseModel):
    origen: int = Field(
        gt=0,
        description="ID del nodo de origen"
    )

    destino: int = Field(
        gt=0,
        description="ID del nodo de destino"
    )


class RutaAsignacion(BaseModel):
    id_conductor: int = Field(
        gt=0,
        description="ID del conductor que se asignara a la ruta",
    )
    id_vehiculo: int = Field(
        gt=0,
        description="ID del vehiculo que se asignara a la ruta",
    )


class RutaEstadoActualizar(BaseModel):
    estado: EstadoRuta


class RutaPedidoCrear(BaseModel):
    id_pedido: int = Field(
        gt=0,
        description="ID del pedido que se agregara a la ruta",
    )
    orden_entrega: int = Field(
        gt=0,
        description="Posicion del pedido dentro de la secuencia de entrega",
    )
