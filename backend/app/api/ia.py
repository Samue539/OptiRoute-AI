from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.deps import Principal, requiere_permiso
from backend.app.core.permisos import Permiso
from backend.app.schemas.ia import AnalisisPlanificacionResponse
from backend.app.schemas.optimizacion import PlanificacionRequest
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
)
from backend.app.services.ia_service import analizar_planificacion
from backend.app.services.planificacion_service import planificar_entregas


router = APIRouter(prefix="/api/ia", tags=["IA"])


@router.post(
    "/analizar-planificacion",
    response_model=AnalisisPlanificacionResponse,
)
def analizar_plan(
    solicitud: PlanificacionRequest,
    principal: Principal = Depends(requiere_permiso(Permiso.IA_USAR)),
):
    """Planifica con las reglas existentes y analiza el resultado localmente."""
    try:
        planificacion = planificar_entregas(
            origen=solicitud.origen,
            ids_pedidos=solicitud.pedidos,
            id_vehiculo=solicitud.id_vehiculo,
            regresar_origen=solicitud.regresar_origen,
        )
        return AnalisisPlanificacionResponse(
            **analizar_planificacion(planificacion)
        )
    except RecursoNoEncontradoError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ReglaNegocioError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
