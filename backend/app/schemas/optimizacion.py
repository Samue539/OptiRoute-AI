"""
Schemas Pydantic para el módulo de optimización multi-entrega.
"""

from pydantic import BaseModel, Field


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
