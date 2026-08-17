from fastapi import APIRouter, HTTPException

from backend.app.algorithms.dijkstra import dijkstra
from backend.app.schemas.ruta import (
    RutaAsignacion,
    RutaCrear,
    RutaEstadoActualizar,
    RutaPedidoCrear,
)
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
    RutaNoEncontradaError,
)
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
    crear_ruta,
    listar_rutas,
    obtener_ruta,
)


router = APIRouter(
    prefix="/api/rutas",
    tags=["Rutas"],
)


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
def calcular_ruta(origen: int, destino: int):
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
def guardar_ruta(datos: RutaCrear):
    try:
        return crear_ruta(origen=datos.origen, destino=datos.destino)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("")
def consultar_rutas():
    return listar_rutas()


@router.patch("/{id_ruta}/asignacion")
def asignar_ruta(id_ruta: int, datos: RutaAsignacion):
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
def cambiar_estado_ruta(id_ruta: int, datos: RutaEstadoActualizar):
    _validar_id_ruta(id_ruta)

    try:
        return actualizar_estado_ruta(
            id_ruta=id_ruta,
            estado_nuevo=datos.estado.value,
        )
    except (RutaNoEncontradaError, ReglaNegocioError) as error:
        raise _convertir_error(error) from error


@router.post("/{id_ruta}/pedidos", status_code=201)
def agregar_pedido(id_ruta: int, datos: RutaPedidoCrear):
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
def consultar_pedidos_ruta(id_ruta: int):
    _validar_id_ruta(id_ruta)

    try:
        return listar_pedidos_ruta(id_ruta)
    except RutaNoEncontradaError as error:
        raise _convertir_error(error) from error


@router.get("/{id_ruta}")
def consultar_ruta(id_ruta: int):
    _validar_id_ruta(id_ruta)
    ruta = obtener_ruta(id_ruta)

    if ruta is None:
        raise HTTPException(status_code=404, detail="La ruta no existe.")

    return ruta
