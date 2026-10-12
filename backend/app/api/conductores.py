from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from backend.app.core.deps import Principal, requiere_permiso
from backend.app.core.permisos import Permiso
from backend.app.schemas.catalogos import ConductorCatalogo
from backend.app.services.conductores_service import (
    listar_conductores,
    obtener_conductor,
)


router = APIRouter(prefix="/api/conductores", tags=["Conductores"])
IdConductor = Annotated[int, Path(gt=0)]


@router.get("", response_model=list[ConductorCatalogo])
def consultar_conductores(
    principal: Principal = Depends(requiere_permiso(Permiso.RECURSOS_VER)),
):
    return listar_conductores()


@router.get("/{id_conductor}", response_model=ConductorCatalogo)
def consultar_conductor(
    id_conductor: IdConductor,
    principal: Principal = Depends(requiere_permiso(Permiso.RECURSOS_VER)),
):
    conductor = obtener_conductor(id_conductor)
    if conductor is None:
        raise HTTPException(status_code=404, detail="El conductor no existe.")
    return conductor
