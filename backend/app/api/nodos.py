from fastapi import APIRouter, Depends

from backend.app.core.deps import Principal, requiere_permiso
from backend.app.core.permisos import Permiso
from backend.app.schemas.catalogos import NodoCatalogo
from backend.app.services.grafo_service import listar_nodos_activos


router = APIRouter(prefix="/api/nodos", tags=["Nodos"])


@router.get("", response_model=list[NodoCatalogo])
def consultar_nodos(
    principal: Principal = Depends(requiere_permiso(Permiso.RECURSOS_VER)),
):
    """Nodos activos disponibles como origen o destino de una planificacion."""

    return listar_nodos_activos()
