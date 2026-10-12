from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from backend.app.core.deps import Principal, requiere_permiso
from backend.app.core.permisos import Permiso
from backend.app.schemas.catalogos import VehiculoCatalogo
from backend.app.services.vehiculos_service import (
    listar_vehiculos,
    obtener_vehiculo,
)


router = APIRouter(prefix="/api/vehiculos", tags=["Vehiculos"])
IdVehiculo = Annotated[int, Path(gt=0)]


@router.get("", response_model=list[VehiculoCatalogo])
def consultar_vehiculos(
    principal: Principal = Depends(requiere_permiso(Permiso.RECURSOS_VER)),
):
    return listar_vehiculos()


@router.get("/{id_vehiculo}", response_model=VehiculoCatalogo)
def consultar_vehiculo(
    id_vehiculo: IdVehiculo,
    principal: Principal = Depends(requiere_permiso(Permiso.RECURSOS_VER)),
):
    vehiculo = obtener_vehiculo(id_vehiculo)
    if vehiculo is None:
        raise HTTPException(status_code=404, detail="El vehiculo no existe.")
    return vehiculo
