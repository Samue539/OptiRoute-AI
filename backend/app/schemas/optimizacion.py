"""
Schemas Pydantic para el módulo de optimización multi-entrega.
"""

from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class OptimizacionRequest(BaseModel):
    """
    Solicitud de optimización multi-entrega.

    Valida:
    - origen > 0
    - destinos no vacío y cada ID > 0
    - máximo 8 destinos
    - sin duplicados
    """
    origen: int = Field(
        gt=0,
        description="ID del nodo de origen (bodega)"
    )

    destinos: list[int] = Field(
        min_length=1,
        max_length=8,
        description="Lista de IDs de nodos a visitar (máximo 8)"
    )

    regresar_origen: bool = Field(
        default=False,
        description="Si True, incluye regreso a la bodega en el cálculo"
    )

    def validate_destinos(self):
        """Valida que todos los destinos sean mayores que cero."""
        for destino in self.destinos:
            if destino <= 0:
                raise ValueError("Todos los IDs de destinos deben ser mayores que cero.")

    def model_post_init(self, __context):
        """Hook ejecutado después de la inicialización del modelo."""
        self.validate_destinos()


class NodoInfo(BaseModel):
    """Información de un nodo en la respuesta."""
    id_nodo: int
    nombre: str
    tipo_nodo: str
    latitud: float
    longitud: float


class OptimizacionResponse(BaseModel):
    """
    Respuesta de la optimización multi-entrega.

    Incluye:
    - Información de origen y destinos
    - Orden óptimo de visita
    - Recorrido físico completo
    - Distancia total
    - Metadata del algoritmo
    """
    origen: NodoInfo
    destinos_solicitados: list[NodoInfo]
    orden_optimo: list[int]
    orden_optimo_info: list[NodoInfo] = Field(
        description="Información detallada de nodos en orden óptimo"
    )
    recorrido: list[int]
    recorrido_info: list[NodoInfo] = Field(
        description="Información detallada de todos los nodos en el recorrido"
    )
    distancia_total_km: float
    regresar_origen: bool
    algoritmo: str = "TSP_EXACTO"
    permutaciones_evaluadas: int


IdPositivo = Annotated[int, Field(gt=0)]


class PlanificacionRequest(BaseModel):
    """Solicitud de planificacion basada en pedidos y capacidad vehicular."""

    origen: int = Field(gt=0, description="ID del nodo de origen")
    pedidos: list[IdPositivo] = Field(
        min_length=1,
        description="IDs de pedidos que se deben entregar",
    )
    id_vehiculo: int = Field(
        gt=0,
        description="ID del vehiculo asignado a la planificacion",
    )
    regresar_origen: bool = False

    @field_validator("pedidos")
    @classmethod
    def validar_pedidos_unicos(cls, pedidos):
        if len(pedidos) != len(set(pedidos)):
            raise ValueError("La lista de pedidos contiene IDs duplicados.")
        return pedidos


class VehiculoPlanificacionInfo(BaseModel):
    id_vehiculo: int
    placa: str
    marca: str | None
    modelo: str | None
    tipo_vehiculo: str
    estado: str
    capacidad_kg: float
    capacidad_volumen_m3: float


class PedidoPlanificacionInfo(BaseModel):
    id_pedido: int
    codigo: str
    id_cliente: int
    id_direccion_entrega: int
    descripcion: str | None
    peso_kg: float
    volumen_m3: float
    prioridad: str
    estado: str
    destino: NodoInfo


class PlanificacionResponse(BaseModel):
    factible: bool
    vehiculo: VehiculoPlanificacionInfo
    pedidos: list[PedidoPlanificacionInfo]
    peso_total: float
    capacidad_peso: float
    volumen_total: float
    capacidad_volumen: float
    origen: NodoInfo
    destinos: list[int]
    orden_optimo: list[int]
    recorrido: list[int]
    distancia_total_km: float
    regresar_origen: bool
    algoritmo: str = "TSP_EXACTO_DIJKSTRA"
    permutaciones_evaluadas: int
