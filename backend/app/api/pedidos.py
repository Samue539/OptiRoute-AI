from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from backend.app.core.deps import Principal, requiere_permiso
from backend.app.core.permisos import (
    Permiso,
    alcance_estado_pedido,
    estado_pedido_autorizado,
    texto_estados_permitidos,
)
from backend.app.schemas.catalogos import PedidoActualizar, PedidoCatalogo, PedidoCrear, PedidoEstadoActualizar
from backend.app.services.pedidos_service import (
    actualizar_estado_pedido,
    actualizar_pedido,
    conductor_de_pedido,
    crear_pedido,
    listar_pedidos,
    listar_pedidos_por_conductor,
    obtener_pedido,
    obtener_ruta_de_pedido,
)
from backend.app.services.ruta_service import confirmar_entrega_ruta
from backend.app.services import auth_service


router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])
IdPedido = Annotated[int, Path(gt=0)]


@router.get("", response_model=list[PedidoCatalogo])
def consultar_pedidos(
    principal: Principal = Depends(
        requiere_permiso(Permiso.PEDIDOS_VER, Permiso.PEDIDOS_VER_PROPIOS)
    ),
):
    if principal.tiene(Permiso.PEDIDOS_VER):
        return listar_pedidos()
    if principal.id_conductor is None:
        return []
    return listar_pedidos_por_conductor(principal.id_conductor)


@router.post("", response_model=PedidoCatalogo, status_code=201)
def crear_nuevo_pedido(
    datos: PedidoCrear,
    principal: Principal = Depends(requiere_permiso(Permiso.PEDIDOS_CREAR)),
):
    try:
        return crear_pedido(datos.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{id_pedido}", response_model=PedidoCatalogo)
def consultar_pedido(
    id_pedido: IdPedido,
    principal: Principal = Depends(
        requiere_permiso(Permiso.PEDIDOS_VER, Permiso.PEDIDOS_VER_PROPIOS)
    ),
):
    pedido = obtener_pedido(id_pedido)
    if pedido is None:
        raise HTTPException(status_code=404, detail="El pedido no existe.")
    if not principal.tiene(Permiso.PEDIDOS_VER):
        if conductor_de_pedido(id_pedido) != principal.id_conductor:
            raise HTTPException(status_code=403, detail="No tienes acceso a este pedido.")
    return pedido


@router.patch("/{id_pedido}", response_model=PedidoCatalogo)
def editar_pedido(
    id_pedido: IdPedido,
    datos: PedidoActualizar,
    principal: Principal = Depends(requiere_permiso(Permiso.PEDIDOS_EDITAR)),
):
    try:
        pedido = actualizar_pedido(id_pedido, datos.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if pedido is None:
        raise HTTPException(status_code=404, detail="El pedido no existe.")
    return pedido


@router.patch("/{id_pedido}/estado", response_model=PedidoCatalogo)
def cambiar_estado_pedido(
    id_pedido: IdPedido,
    datos: PedidoEstadoActualizar,
    principal: Principal = Depends(
        requiere_permiso(Permiso.PEDIDOS_ESTADO, Permiso.PEDIDOS_ESTADO_PROPIO, Permiso.PEDIDOS_ESTADO_LIMITADO)
    ),
):
    alcance = alcance_estado_pedido(principal.rol)
    if alcance == "ninguno":
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para cambiar el estado de un pedido.",
        )

    # El CONDUCTOR conserva su flujo especifico: solo entrega de pedidos de
    # rutas propias ya iniciadas. Un permiso limitado no implica ser dueno.
    if principal.es_conductor:
        if conductor_de_pedido(id_pedido) != principal.id_conductor:
            raise HTTPException(status_code=403, detail="No tienes acceso a este pedido.")
        if datos.estado != "ENTREGADO":
            raise HTTPException(
                status_code=403,
                detail="El conductor solo puede confirmar la entrega de sus pedidos.",
            )
        ruta = obtener_ruta_de_pedido(id_pedido)
        if ruta is None:
            raise HTTPException(status_code=409, detail="El pedido no tiene ruta asignada.")
        try:
            confirmar_entrega_ruta(ruta["id_ruta"], id_pedido)
        except Exception as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return obtener_pedido(id_pedido)

    # Perfiles de alcance propio (sin permiso pleno) solo actuan sobre sus
    # recursos; los administrativos sobre cualquiera.
    if alcance == "propio" and conductor_de_pedido(id_pedido) != principal.id_conductor:
        raise HTTPException(status_code=403, detail="No tienes acceso a este pedido.")
    if not estado_pedido_autorizado(principal.rol, datos.estado):
        raise HTTPException(
            status_code=403,
            detail=(
                "Tu perfil no permite fijar este estado. "
                + texto_estados_permitidos(principal.rol, "pedido")
            ),
        )
    try:
        pedido = actualizar_estado_pedido(id_pedido, datos.estado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if pedido is None:
        raise HTTPException(status_code=404, detail="El pedido no existe.")
    if datos.estado == "CANCELADO":
        auth_service.auditar_evento_seguro(
            "cancelacion_pedido",
            principal.cuenta.correo,
            principal.cuenta.id_usuario,
            objetivo=id_pedido,
            estado="CANCELADO",
            motivo=datos.motivo,
        )
    return pedido


@router.get("/{id_pedido}/ruta")
def consultar_ruta_pedido(
    id_pedido: IdPedido,
    principal: Principal = Depends(
        requiere_permiso(Permiso.PEDIDOS_VER, Permiso.PEDIDOS_VER_PROPIOS)
    ),
):
    pedido = obtener_pedido(id_pedido)
    if pedido is None:
        raise HTTPException(status_code=404, detail="El pedido no existe.")
    ruta = obtener_ruta_de_pedido(id_pedido)
    if ruta is None:
        raise HTTPException(status_code=404, detail="El pedido no tiene ruta asignada.")
    if not principal.tiene(Permiso.PEDIDOS_VER):
        conductor = ruta.get("conductor") if ruta else None
        if not conductor or conductor.get("id_conductor") != principal.id_conductor:
            raise HTTPException(status_code=403, detail="No tienes acceso a este pedido.")
    return ruta
