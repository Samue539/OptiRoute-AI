"""
Router de API para optimización multi-entrega.

Endpoint: POST /api/optimizacion/multi-entrega
"""

from fastapi import APIRouter, HTTPException

from backend.app.schemas.optimizacion import (
    OptimizacionRequest,
    OptimizacionResponse,
    PlanificacionRequest,
    PlanificacionResponse,
)
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
)
from backend.app.services.optimizacion_service import optimizar_multi_entrega
from backend.app.services.planificacion_service import planificar_entregas


router = APIRouter(
    prefix="/api/optimizacion",
    tags=["Optimización"],
)


@router.post("/multi-entrega", response_model=OptimizacionResponse)
def calcular_multi_entrega(solicitud: OptimizacionRequest):
    """
    Calcula la orden óptima de visita para múltiples destinos.

    Entrada:
        - origen: ID del nodo de origen (bodega)
        - destinos: Lista de IDs de destinos (1-8 nodos)
        - regresar_origen: Si incluir regreso a la bodega

    Salida:
        - Orden óptimo de visita (minimiza distancia)
        - Recorrido físico completo (incluyendo nodos intermedios)
        - Distancia total en km
        - Información del algoritmo utilizado

    Excepciones:
        400: Validación fallida
        404: Nodo no encontrado
        409: Validación de regla de negocio fallida
    """
    try:
        resultado = optimizar_multi_entrega(
            origen=solicitud.origen,
            destinos=solicitud.destinos,
            regresar_origen=solicitud.regresar_origen,
        )

        return OptimizacionResponse(**resultado)

    except ReglaNegocioError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(error)}",
        ) from error


@router.post("/planificar", response_model=PlanificacionResponse)
def planificar_multi_entrega(solicitud: PlanificacionRequest):
    """Valida pedidos y capacidad antes de ejecutar TSP con Dijkstra."""
    try:
        resultado = planificar_entregas(
            origen=solicitud.origen,
            ids_pedidos=solicitud.pedidos,
            id_vehiculo=solicitud.id_vehiculo,
            regresar_origen=solicitud.regresar_origen,
        )
        return PlanificacionResponse(**resultado)

    except RecursoNoEncontradoError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    except ReglaNegocioError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(error)}",
        ) from error
