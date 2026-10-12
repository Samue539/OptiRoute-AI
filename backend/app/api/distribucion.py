"""Centro de Distribucion y Entregas: Mis rutas, Mis guias y entregas.

Seguridad:
* Cada endpoint exige sesion y un permiso de distribucion.
* El servicio re-verifica empresa, membresia y asignacion: un OPERADOR o
  CONDUCTOR solo opera sobre guias asignadas (o visibles por regla legada
  en modo bootstrap). Consultar una guia ajena responde 403.
* Las fotos se validan por firma magica y tamano en el servidor; la
  fecha/hora la pone PostgreSQL (CURRENT_TIMESTAMP), nunca el dispositivo.
* Sin 008 aplicada, los endpoints responden 503 en vez de inventar datos.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from backend.app.core.deps import Principal, requiere_permiso
from backend.app.core.permisos import Permiso
from backend.app.schemas.distribucion import (
    AsignacionDistribucionCrear,
    GuiaEventoInfo,
    GuiaInfo,
    ResumenGuias,
    RutaAsignadaInfo,
    ZonaInfo,
)
from backend.app.services import auth_service
from backend.app.services.evidencias_storage import (
    ErrorEvidencia,
    RepositorioEvidencias,
    repositorio_evidencias,
)
from backend.app.services.guias_service import (
    ErrorDistribucion,
    asignar_distribucion,
    historial_guia,
    listar_guias_de_ruta,
    listar_mis_rutas,
    listar_zonas,
    obtener_guia_por_numero,
    registrar_entrega,
    registrar_novedad,
    resumen_mis_guias,
)


router = APIRouter(prefix="/api/distribucion", tags=["Distribución"])

VerDistribucion = requiere_permiso(
    Permiso.GUIAS_VER_ASIGNADAS, Permiso.RUTAS_VER_ASIGNADAS
)
EntregarGuias = requiere_permiso(Permiso.GUIAS_ENTREGAR)
NovedadGuias = requiere_permiso(Permiso.GUIAS_NOVEDAD)
VerEvidencias = requiere_permiso(Permiso.EVIDENCIAS_VER)


def _error(error: Exception) -> HTTPException:
    if isinstance(error, (ErrorDistribucion, ErrorEvidencia)):
        return HTTPException(status_code=error.codigo, detail=error.mensaje)
    return HTTPException(status_code=500, detail="Error interno de distribucion.")


def _contexto(principal: Principal) -> dict:
    return {
        "id_cuenta": principal.cuenta.id_usuario,
        "id_conductor": principal.id_conductor,
        "ver_todas": principal.tiene(Permiso.RUTAS_VER_TODAS),
    }


def _auditar(principal: Principal, accion: str, **detalle) -> None:
    auth_service.auditar_evento_seguro(
        accion, principal.cuenta.correo, principal.cuenta.id_usuario, **detalle
    )


async def _leer_foto(archivo: UploadFile | None) -> tuple[bytes, str | None, str | None]:
    if archivo is None:
        return b"", None, None
    contenido = await archivo.read()
    return contenido, archivo.filename, archivo.content_type


@router.get("/zonas", response_model=list[ZonaInfo])
def consultar_zonas(principal: Principal = Depends(VerDistribucion)):
    try:
        return listar_zonas()
    except Exception as error:
        raise _error(error) from error


@router.get("/mis-rutas", response_model=list[RutaAsignadaInfo])
def consultar_mis_rutas(principal: Principal = Depends(VerDistribucion)):
    try:
        return listar_mis_rutas(**_contexto(principal))
    except Exception as error:
        raise _error(error) from error


@router.get("/mis-rutas/{id_ruta}/guias", response_model=list[GuiaInfo])
def consultar_guias_de_ruta(
    id_ruta: int,
    search: str | None = None,
    estado: str | None = None,
    principal: Principal = Depends(VerDistribucion),
):
    if id_ruta <= 0:
        raise HTTPException(status_code=400, detail="El ID de la ruta debe ser mayor que cero.")
    try:
        return listar_guias_de_ruta(
            **_contexto(principal), id_ruta=id_ruta, search=search, estado=estado
        )
    except Exception as error:
        raise _error(error) from error


@router.get("/guias/{numero_guia}", response_model=GuiaInfo)
def consultar_guia(
    numero_guia: str, principal: Principal = Depends(VerDistribucion)
):
    try:
        return obtener_guia_por_numero(
            **_contexto(principal), numero=numero_guia.strip()
        )
    except Exception as error:
        raise _error(error) from error


@router.get("/guias/{id_guia}/eventos")
def consultar_historial_guia(
    id_guia: int, principal: Principal = Depends(VerDistribucion)
):
    if id_guia <= 0:
        raise HTTPException(status_code=400, detail="El ID de la guia debe ser mayor que cero.")
    try:
        datos = historial_guia(**_contexto(principal), id_guia=id_guia)
        return {
            "guia": GuiaInfo(**datos["guia"]).model_dump(),
            "eventos": [GuiaEventoInfo(**e).model_dump() for e in datos["eventos"]],
        }
    except Exception as error:
        raise _error(error) from error


@router.get("/resumen", response_model=ResumenGuias)
def consultar_resumen(principal: Principal = Depends(VerDistribucion)):
    try:
        return resumen_mis_guias(**_contexto(principal))
    except Exception as error:
        raise _error(error) from error


@router.post("/guias/{id_guia}/entrega")
async def registrar_entrega_guia(
    id_guia: int,
    receptor_nombre: str = Form(...),
    relacion_destinatario: str = Form(...),
    gps_latitud: float | None = Form(None),
    gps_longitud: float | None = Form(None),
    gps_precision_m: float | None = Form(None),
    gps_origen: str | None = Form(None),
    observaciones: str | None = Form(None),
    clave_idempotencia: str | None = Form(None),
    foto_guia: UploadFile | None = File(None),
    foto_paquete: UploadFile | None = File(None),
    principal: Principal = Depends(EntregarGuias),
):
    if id_guia <= 0:
        raise HTTPException(status_code=400, detail="El ID de la guia debe ser mayor que cero.")
    try:
        bin_guia = await _leer_foto(foto_guia)
        bin_paquete = await _leer_foto(foto_paquete)
        fotos = [
            ("FOTO_GUIA", *bin_guia),
            ("FOTO_PAQUETE", *bin_paquete),
        ]
        resultado = registrar_entrega(
            **_contexto(principal),
            id_guia=id_guia,
            receptor_nombre=receptor_nombre,
            relacion_destinatario=(relacion_destinatario or "").upper(),
            gps_latitud=gps_latitud,
            gps_longitud=gps_longitud,
            gps_precision_m=gps_precision_m,
            gps_origen=(gps_origen or "").upper() or None,
            observaciones=observaciones,
            clave_idempotencia=(clave_idempotencia or "").strip() or str(uuid.uuid4().hex),
            fotos=fotos,
        )
        if not resultado.get("duplicada"):
            _auditar(
                principal, "guia_entregada",
                id_guia=id_guia, numero_guia=resultado.get("numero_guia"),
                id_evento=resultado.get("id_evento"),
            )
        return resultado
    except Exception as error:
        raise _error(error) from error


@router.post("/guias/{id_guia}/novedad")
async def registrar_novedad_guia(
    id_guia: int,
    tipo: str = Form("FALLIDA"),
    motivo_falla: str | None = Form(None),
    gps_latitud: float | None = Form(None),
    gps_longitud: float | None = Form(None),
    gps_precision_m: float | None = Form(None),
    gps_origen: str | None = Form(None),
    observaciones: str | None = Form(None),
    clave_idempotencia: str | None = Form(None),
    foto_1: UploadFile | None = File(None),
    foto_2: UploadFile | None = File(None),
    principal: Principal = Depends(NovedadGuias),
):
    if id_guia <= 0:
        raise HTTPException(status_code=400, detail="El ID de la guia debe ser mayor que cero.")
    try:
        fotos = []
        for contenido, nombre, ctype in (await _leer_foto(foto_1), await _leer_foto(foto_2)):
            if contenido:
                fotos.append(("OTRO", contenido, nombre, ctype))
        resultado = registrar_novedad(
            **_contexto(principal),
            id_guia=id_guia,
            tipo=(tipo or "FALLIDA").upper(),
            motivo_falla=motivo_falla,
            gps_latitud=gps_latitud,
            gps_longitud=gps_longitud,
            gps_precision_m=gps_precision_m,
            gps_origen=(gps_origen or "").upper() or None,
            observaciones=observaciones,
            clave_idempotencia=(clave_idempotencia or "").strip() or str(uuid.uuid4().hex),
            fotos=fotos,
        )
        if not resultado.get("duplicada"):
            _auditar(
                principal, "guia_novedad",
                id_guia=id_guia, tipo=tipo, id_evento=resultado.get("id_evento"),
            )
        return resultado
    except Exception as error:
        raise _error(error) from error


@router.get("/evidencias/{id_evidencia}/url")
def url_temporal_evidencia(
    id_evidencia: int,
    segundos: int = 300,
    principal: Principal = Depends(VerEvidencias),
):
    from backend.app.core.database import obtener_conexion

    if id_evidencia <= 0:
        raise HTTPException(status_code=400, detail="El ID de la evidencia debe ser mayor que cero.")
    try:
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT e.storage_key, e.mime, e.id_guia, g.id_ruta
                    FROM operaciones.guia_evidencias e
                    JOIN operaciones.guias g ON g.id_guia = e.id_guia
                    WHERE e.id_evidencia = %s;
                    """,
                    (id_evidencia,),
                )
                fila = cursor.fetchone()
        finally:
            conexion.close()
        if fila is None:
            raise HTTPException(status_code=404, detail="La evidencia no existe.")
        storage_key, _, id_guia, id_ruta = fila
        ctx = _contexto(principal)
        if id_ruta is not None:
            from backend.app.services.guias_service import exigir_008, _verificar_acceso_ruta

            conexion = obtener_conexion()
            try:
                with conexion.cursor() as cursor:
                    exigir_008(cursor)
                    _verificar_acceso_ruta(cursor, id_ruta, ctx["id_cuenta"], ctx["id_conductor"], ctx["ver_todas"])
            except ErrorDistribucion as error:
                raise HTTPException(status_code=error.codigo, detail=error.mensaje) from error
            finally:
                conexion.close()
        elif not ctx["ver_todas"]:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta evidencia.")
        firmado = repositorio_evidencias().firmar_acceso(storage_key, segundos)
        _auditar(principal, "evidencia_url_temporal", id_evidencia=id_evidencia)
        if "signed_url" in firmado:
            return {"url": firmado["signed_url"], "expira_en_segundos": segundos}
        return {
            "url": (
                f"/api/distribucion/evidencias/{id_evidencia}/archivo"
                f"?expira={firmado['expira']}&firma={firmado['firma']}"
            ),
            "expira": firmado["expira"],
        }
    except HTTPException:
        raise
    except Exception as error:
        raise _error(error) from error


@router.get("/evidencias/{id_evidencia}/archivo")
def descargar_evidencia(
    id_evidencia: int,
    expira: int,
    firma: str,
    principal: Principal = Depends(VerEvidencias),
):
    from backend.app.core.database import obtener_conexion

    if id_evidencia <= 0:
        raise HTTPException(status_code=400, detail="El ID de la evidencia debe ser mayor que cero.")
    try:
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT e.storage_key, e.mime, g.id_ruta
                    FROM operaciones.guia_evidencias e
                    JOIN operaciones.guias g ON g.id_guia = e.id_guia
                    WHERE e.id_evidencia = %s;
                    """,
                    (id_evidencia,),
                )
                fila = cursor.fetchone()
        finally:
            conexion.close()
        if fila is None:
            raise HTTPException(status_code=404, detail="La evidencia no existe.")
        storage_key, mime, id_ruta = fila
        if storage_key.startswith("supabase:"):
            raise HTTPException(
                status_code=409,
                detail="Esta evidencia vive en Supabase: usa /url para obtener el acceso firmado.",
            )
        if not RepositorioEvidencias.verificar_token(storage_key, expira, firma):
            raise HTTPException(status_code=403, detail="El acceso temporal expiro o es invalido.")
        contenido = repositorio_evidencias().abrir(storage_key)
        return Response(content=contenido, media_type=mime)
    except HTTPException:
        raise
    except Exception as error:
        raise _error(error) from error


@router.post("/asignaciones", status_code=201)
def asignar_ruta_o_zona(
    datos: AsignacionDistribucionCrear,
    principal: Principal = Depends(requiere_permiso(Permiso.RUTAS_ASIGNAR)),
):
    """El ADMINISTRADOR vincula y asigna una RUTA, ZONA o GUIA a una cuenta."""

    try:
        resultado = asignar_distribucion(
            principal.cuenta,
            datos.id_empresa,
            datos.id_cuenta,
            datos.tipo_recurso,
            datos.id_recurso,
        )
        _auditar(
            principal, "distribucion_asignada",
            id_empresa=str(datos.id_empresa), id_cuenta=datos.id_cuenta,
            tipo_recurso=datos.tipo_recurso, id_recurso=datos.id_recurso,
        )
        return resultado
    except Exception as error:
        raise _error(error) from error
