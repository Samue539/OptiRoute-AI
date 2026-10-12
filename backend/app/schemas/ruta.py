from enum import Enum

from pydantic import BaseModel, Field, model_validator


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
    motivo: str | None = Field(default=None, min_length=5, max_length=300)

    @model_validator(mode="after")
    def validar_motivo_de_cancelacion(self) -> "RutaEstadoActualizar":
        """Cancelar una ruta exige un motivo que queda en auditoria."""

        if self.estado is EstadoRuta.CANCELADA and not (self.motivo or "").strip():
            raise ValueError(
                "Debes indicar un motivo (entre 5 y 300 caracteres) para cancelar la ruta."
            )
        return self


class RutaPedidoCrear(BaseModel):
    id_pedido: int = Field(
        gt=0,
        description="ID del pedido que se agregara a la ruta",
    )
    orden_entrega: int = Field(
        gt=0,
        description="Posicion del pedido dentro de la secuencia de entrega",
    )


class RutaPlanificadaGuardar(BaseModel):
    origen: int = Field(gt=0)
    pedidos: list[int] = Field(min_length=1)
    id_conductor: int = Field(gt=0)
    id_vehiculo: int = Field(gt=0)
    regresar_origen: bool = False
    clave_idempotencia: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class EntregaConfirmar(BaseModel):
    nombre_receptor: str | None = Field(default=None, max_length=150)
    observaciones: str | None = Field(default=None, max_length=500)


class NovedadCrear(BaseModel):
    tipo: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_ -]+$")
    descripcion: str = Field(min_length=3, max_length=500)
    id_pedido: int | None = Field(default=None, gt=0)
