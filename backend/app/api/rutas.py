from fastapi import APIRouter, Depends, HTTPException

from backend.app.algorithms.dijkstra import dijkstra
from backend.app.core.deps import (
    Principal,
    autorizar_estado_ruta,
    autorizar_ver_ruta,
    filtrar_rutas_visibles,
    requiere_permiso,
)
from backend.app.core.permisos import Permiso
from backend.app.schemas.ruta import (
    EntregaConfirmar,
    EstadoRuta,
    NovedadCrear,
    RutaAsignacion,
    RutaCrear,
    RutaEstadoActualizar,
    RutaPedidoCrear,
    RutaPlanificadaGuardar,
)
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
    RutaNoEncontradaError,
)
from backend.app.services import auth_service
from backend.app.services.grafo_service import (
    cargar_grafo_desde_bd,
    obtener_nodo,
)
from backend.app.services.ruta_pedido_service import (
    agregar_pedido_ruta,
    listar_pedidos_ruta,
)
from backend.app.services.ruta_service import (
    actualizar_estado_ruta,
    asignar_conductor_vehiculo,
    confirmar_entrega_ruta,
    crear_ruta,
    listar_rutas,
    obtener_ruta,
    registrar_novedad_ruta,
)
from backend.app.services.ruta_planificacion_service import guardar_ruta_planificada


router = APIRouter(
    prefix="/api/rutas",
    tags=["Rutas"],
)

# Consultar rutas (todas o propias) y gestionarlas son permisos distintos.
VerRutas = requiere_permiso(Permiso.RUTAS_VER_TODAS, Permiso.RUTAS_VER_PROPIAS)


def _validar_id_ruta(id_ruta: int):
    if id_ruta <= 0:
        raise HTTPException(
            status_code=400,
            detail="El ID de la ruta debe ser mayor que cero.",
        )


def _convertir_error(error):
    if isinstance(error, (RutaNoEncontradaError, RecursoNoEncontradoError)):
        return HTTPException(status_code=404, detail=str(error))
    return HTTPException(status_code=409, detail=str(error))


@router.get("/calcular")
def calcular_ruta(
    origen: int,
    destino: int,
    principal: Principal = Depends(VerRutas),
):
    nodo_origen = obtener_nodo(origen)
    nodo_destino = obtener_nodo(destino)

    if nodo_origen is None:
        raise HTTPException(
            status_code=404,
            detail="El nodo de origen no existe.",
        )

    if nodo_destino is None:
        raise HTTPException(
            status_code=404,
            detail="El nodo de destino no existe.",
        )

    grafo = cargar_grafo_desde_bd()
    resultado = dijkstra(grafo, origen, destino)

    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail="No existe una ruta entre los nodos indicados.",
        )

    ruta_detallada = []

    for id_nodo in resultado["camino"]:
        nodo = obtener_nodo(id_nodo)
        if nodo is not None:
            ruta_detallada.append(nodo)

    return {
        "origen": nodo_origen,
        "destino": nodo_destino,
        "ruta": ruta_detallada,
        "distancia_total_km": resultado["distancia"],
    }


@router.post("", status_code=201)
def guardar_ruta(
    datos: RutaCrear,
    principal: Principal = Depends(requiere_permiso(Permiso.RUTAS_CREAR)),
):
    try:
        return crear_ruta(origen=datos.origen, destino=datos.destino)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("")
def consultar_rutas(principal: Principal = Depends(VerRutas)):
    return filtrar_rutas_visibles(principal, listar_rutas())


@router.post("/planificada", status_code=201)
def guardar_planificacion(
    datos: RutaPlanificadaGuardar,
    principal: Principal = Depends(requiere_permiso(Permiso.RUTAS_CREAR)),
):
    """Recalcula y persiste el plan completo en una sola transaccion."""

    try:
        return guardar_ruta_planificada(
            origen=datos.origen,
            ids_pedidos=datos.pedidos,
            id_conductor=datos.id_conductor,
            id_vehiculo=datos.id_vehiculo,
            regresar_origen=datos.regresar_origen,
            clave_idempotencia=datos.clave_idempotencia,
        )
    except (RecursoNoEncontradoError, ReglaNegocioError) as error:
        raise _convertir_error(error) from error


@router.patch("/{id_ruta}/asignacion")
def asignar_ruta(
    id_ruta: int,
    datos: RutaAsignacion,
    principal: Principal = Depends(requiere_permiso(Permiso.RUTAS_ASIGNAR)),
):
    _validar_id_ruta(id_ruta)

    try:
        return asignar_conductor_vehiculo(
            id_ruta=id_ruta,
            id_conductor=datos.id_conductor,
            id_vehiculo=datos.id_vehiculo,
        )
    except (
        RutaNoEncontradaError,
        RecursoNoEncontradoError,
        ReglaNegocioError,
    ) as error:
        raise _convertir_error(error) from error


@router.patch("/{id_ruta}/estado")
def cambiar_estado_ruta(
    id_ruta: int,
    datos: RutaEstadoActualizar,
    principal: Principal = Depends(
        requiere_permiso(Permiso.RUTAS_ESTADO, Permiso.RUTAS_ESTADO_LIMITADO)
    ),
):
    _validar_id_ruta(id_ruta)

    ruta = obtener_ruta(id_ruta)
    if ruta is None:
        raise HTTPException(status_code=404, detail="La ruta no existe.")
    autorizar_estado_ruta(principal, ruta, datos.estado.value)

    try:
        ruta_actualizada = actualizar_estado_ruta(
            id_ruta=id_ruta,
            estado_nuevo=datos.estado.value,
        )
    except (RutaNoEncontradaError, ReglaNegocioError) as error:
        raise _convertir_error(error) from error

    if datos.estado is EstadoRuta.CANCELADA:
        auth_service.auditar_evento_seguro(
            "cancelacion_ruta",
            principal.cuenta.correo,
            principal.cuenta.id_usuario,
            objetivo=id_ruta,
            estado="CANCELADA",
            motivo=datos.motivo,
        )
    return ruta_actualizada


@router.post("/{id_ruta}/pedidos", status_code=201)
def agregar_pedido(
    id_ruta: int,
    datos: RutaPedidoCrear,
    principal: Principal = Depends(requiere_permiso(Permiso.RUTAS_CREAR)),
):
    _validar_id_ruta(id_ruta)

    try:
        return agregar_pedido_ruta(
            id_ruta=id_ruta,
            id_pedido=datos.id_pedido,
            orden_entrega=datos.orden_entrega,
        )
    except (
        RutaNoEncontradaError,
        RecursoNoEncontradoError,
        ReglaNegocioError,
    ) as error:
        raise _convertir_error(error) from error


@router.get("/{id_ruta}/pedidos")
def consultar_pedidos_ruta(
    id_ruta: int,
    principal: Principal = Depends(VerRutas),
):
    _validar_id_ruta(id_ruta)

    ruta = obtener_ruta(id_ruta)
    if ruta is None:
        raise HTTPException(status_code=404, detail="La ruta no existe.")
    autorizar_ver_ruta(principal, ruta)

    try:
        return listar_pedidos_ruta(id_ruta)
    except RutaNoEncontradaError as error:
        raise _convertir_error(error) from error


@router.post("/{id_ruta}/pedidos/{id_pedido}/entrega")
def confirmar_entrega(
    id_ruta: int,
    id_pedido: int,
    datos: EntregaConfirmar,
    principal: Principal = Depends(
        requiere_permiso(Permiso.PEDIDOS_ESTADO, Permiso.PEDIDOS_ESTADO_PROPIO)
    ),
):
    _validar_id_ruta(id_ruta)
    ruta = obtener_ruta(id_ruta)
    if ruta is None:
        raise HTTPException(status_code=404, detail="La ruta no existe.")
    autorizar_estado_ruta(principal, ruta)
    try:
        return confirmar_entrega_ruta(
            id_ruta, id_pedido, datos.nombre_receptor, datos.observaciones
        )
    except (RutaNoEncontradaError, RecursoNoEncontradoError, ReglaNegocioError) as error:
        raise _convertir_error(error) from error


@router.post("/{id_ruta}/novedades", status_code=201)
def registrar_novedad(
    id_ruta: int,
    datos: NovedadCrear,
    principal: Principal = Depends(requiere_permiso(Permiso.RUTAS_ESTADO)),
):
    _validar_id_ruta(id_ruta)
    ruta = obtener_ruta(id_ruta)
    if ruta is None:
        raise HTTPException(status_code=404, detail="La ruta no existe.")
    autorizar_estado_ruta(principal, ruta)
    try:
        return registrar_novedad_ruta(
            id_ruta, datos.tipo.upper().replace(" ", "_"), datos.descripcion, datos.id_pedido
        )
    except (RutaNoEncontradaError, RecursoNoEncontradoError, ReglaNegocioError) as error:
        raise _convertir_error(error) from error


@router.get("/{id_ruta}")
def consultar_ruta(
    id_ruta: int,
    principal: Principal = Depends(VerRutas),
):
    _validar_id_ruta(id_ruta)
    ruta = obtener_ruta(id_ruta)

    if ruta is None:
        raise HTTPException(status_code=404, detail="La ruta no existe.")

    autorizar_ver_ruta(principal, ruta)
    return ruta
