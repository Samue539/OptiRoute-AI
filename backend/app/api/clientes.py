from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from backend.app.core.deps import Principal, requiere_permiso
from backend.app.core.permisos import Permiso
from backend.app.schemas.catalogos import ClienteCatalogo, DireccionCliente
from backend.app.services.clientes_service import (
    listar_clientes,
    listar_direcciones_cliente,
    listar_pedidos_cliente,
    obtener_cliente,
)

router = APIRouter(prefix="/api/clientes", tags=["Clientes"])
IdCliente = Annotated[int, Path(gt=0)]


@router.get("", response_model=list[ClienteCatalogo])
def consultar_clientes(
    principal: Principal = Depends(requiere_permiso(Permiso.CLIENTES_VER)),
):
    return listar_clientes()


@router.get("/{id_cliente}", response_model=ClienteCatalogo)
def consultar_cliente(
    id_cliente: IdCliente,
    principal: Principal = Depends(requiere_permiso(Permiso.CLIENTES_VER)),
):
    cliente = obtener_cliente(id_cliente)
    if cliente is None:
        raise HTTPException(status_code=404, detail="El cliente no existe.")
    return cliente


@router.get("/{id_cliente}/direcciones", response_model=list[DireccionCliente])
def consultar_direcciones_cliente(
    id_cliente: IdCliente,
    principal: Principal = Depends(requiere_permiso(Permiso.CLIENTES_VER)),
):
    cliente = obtener_cliente(id_cliente)
    if cliente is None:
        raise HTTPException(status_code=404, detail="El cliente no existe.")
    return listar_direcciones_cliente(id_cliente)


@router.get("/{id_cliente}/pedidos")
def consultar_pedidos_cliente(
    id_cliente: IdCliente,
    principal: Principal = Depends(requiere_permiso(Permiso.CLIENTES_VER)),
):
    cliente = obtener_cliente(id_cliente)
    if cliente is None:
        raise HTTPException(status_code=404, detail="El cliente no existe.")
    return listar_pedidos_cliente(id_cliente)
