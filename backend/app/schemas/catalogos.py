"""Schemas de respuesta para los catalogos operativos."""

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class NodoCatalogo(BaseModel):
    id_nodo: int
    nombre: str
    tipo_nodo: str
    latitud: float
    longitud: float
    activo: bool


class PedidoCatalogo(BaseModel):
    id_pedido: int
    codigo: str
    id_cliente: int
    id_direccion_entrega: int
    descripcion: str | None
    peso_kg: float | None
    volumen_m3: float | None
    prioridad: str
    estado: str
    fecha_solicitada: date | None
    destino: NodoCatalogo | None
    estado_entrega: str | None
    creado_en: datetime


class VehiculoCatalogo(BaseModel):
    id_vehiculo: int
    placa: str
    marca: str | None
    modelo: str | None
    anio: int | None
    tipo_vehiculo: str
    capacidad_kg: float | None
    capacidad_volumen_m3: float | None
    estado: str
    activo: bool
    disponible: bool


class ConductorCatalogo(BaseModel):
    id_conductor: int
    nombres: str
    apellidos: str
    numero_licencia: str
    tipo_licencia: str | None
    telefono: str | None
    activo: bool
    disponible: bool


class ClienteCatalogo(BaseModel):
    id_cliente: int
    tipo_cliente: str
    nombres: str | None
    apellidos: str | None
    razon_social: str | None
    identificacion: str | None
    correo: str | None
    telefono: str | None
    activo: bool
    creado_en: datetime


class DireccionCliente(BaseModel):
    id_direccion: int
    id_cliente: int
    id_nodo: int | None
    etiqueta: str
    direccion_texto: str
    ciudad: str
    provincia: str | None
    pais: str
    latitud: float
    longitud: float
    referencia: str | None
    es_principal: bool
    activo: bool
    nodo: NodoCatalogo | None


class PedidoCrear(BaseModel):
    id_cliente: int
    id_direccion_entrega: int
    descripcion: str | None = None
    peso_kg: float
    volumen_m3: float
    prioridad: str = "NORMAL"
    fecha_solicitada: date | None = None


class PedidoActualizar(BaseModel):
    descripcion: str | None = None
    peso_kg: float | None = None
    volumen_m3: float | None = None
    prioridad: str | None = None


class PedidoEstadoActualizar(BaseModel):
    estado: str
    motivo: str | None = Field(default=None, min_length=5, max_length=300)

    @model_validator(mode="after")
    def validar_motivo_de_cancelacion(self) -> "PedidoEstadoActualizar":
        """Cancelar un pedido exige un motivo que queda en auditoria."""

        if self.estado == "CANCELADO" and not (self.motivo or "").strip():
            raise ValueError(
                "Debes indicar un motivo (entre 5 y 300 caracteres) para cancelar el pedido."
            )
        return self
