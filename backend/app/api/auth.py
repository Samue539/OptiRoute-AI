"""API de autenticacion y administracion de cuentas."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request

from backend.app.core.deps import (
    Principal,
    extraer_token,
    requiere_permiso,
    sesion_actual,
)
from backend.app.core.permisos import Permiso, catalogo_permisos
from backend.app.schemas.auth import (
    BootstrapRequest,
    CambiarPasswordRequest,
    CatalogoPermisosRespuesta,
    EstadoBootstrapRespuesta,
    LoginRequest,
    RestablecerPasswordRequest,
    SesionRespuesta,
    UsuarioCrearRequest,
    UsuarioEstadoRequest,
    UsuarioInfo,
    UsuarioRolRequest,
)
from backend.app.services import auth_service


router = APIRouter(prefix="/api/auth", tags=["Autenticacion"])
IdUsuario = Annotated[int, Path(gt=0)]


def _convertir(error: auth_service.ErrorAutenticacion) -> HTTPException:
    return HTTPException(status_code=error.codigo, detail=error.mensaje)


@router.get("/estado", response_model=EstadoBootstrapRespuesta)
def consultar_estado():
    """Estado publico: indica si ya existe la cuenta propietaria."""

    return auth_service.estado_bootstrap()


@router.post("/bootstrap", response_model=SesionRespuesta, status_code=201)
def crear_propietario(datos: BootstrapRequest, solicitud: Request = None):
    """Crea la cuenta propietaria de desarrollador (solo la primera vez)."""

    try:
        return auth_service.crear_propietario(
            nombres=datos.nombres,
            apellidos=datos.apellidos,
            correo=datos.correo,
            password=datos.password,
            metadatos=auth_service.metadatos_peticion(solicitud),
        )
    except auth_service.ErrorAutenticacion as error:
        raise _convertir(error) from error


@router.post("/login", response_model=SesionRespuesta)
def iniciar_sesion(datos: LoginRequest, solicitud: Request = None):
    try:
        return auth_service.login(
            datos.correo,
            datos.password,
            metadatos=auth_service.metadatos_peticion(solicitud),
        )
    except auth_service.ErrorAutenticacion as error:
        raise _convertir(error) from error


@router.get("/session", response_model=SesionRespuesta)
def consultar_sesion(principal: Principal = Depends(sesion_actual)):
    return {
        "token": None,
        "expira_en": principal.sesion.expira_en.isoformat(),
        "usuario": principal.cuenta.info_publica(),
        "permisos": sorted(p.value for p in principal.permisos),
    }


@router.post("/logout")
def cerrar_sesion(
    principal: Principal = Depends(sesion_actual),
    authorization: str | None = Header(default=None),
):
    token = extraer_token(authorization)
    auth_service.cerrar_sesion(token or "")
    return {"cerrado": True}


@router.post("/logout-todo")
def cerrar_sesiones_todos_los_equipos(
    principal: Principal = Depends(sesion_actual),
    authorization: str | None = Header(default=None),
):
    """Cierra las sesiones abiertas en otros equipos o navegadores.

    La sesion actual se renueva: la respuesta incluye el token nuevo que el
    cliente debe usar a partir de ese momento (igual vencimiento).
    """

    token = extraer_token(authorization)
    resultado = auth_service.cerrar_sesiones_usuario(
        principal.cuenta,
        conservar_token=token or None,
    )
    return {
        "cerrado": True,
        "sesiones_revocadas": resultado["sesiones_revocadas"],
        "token": resultado["token"],
        "expira_en": resultado["expira_en"],
        "mensaje": "Sesiones cerradas. Se emitio un token nuevo.",
    }


@router.post("/cambiar-password")
def cambiar_password(
    datos: CambiarPasswordRequest,
    principal: Principal = Depends(sesion_actual),
):
    try:
        revocadas = auth_service.cambiar_password(
            principal.cuenta, datos.password_actual, datos.password_nueva
        )
    except auth_service.ErrorAutenticacion as error:
        raise _convertir(error) from error
    return {
        "actualizado": True,
        "sesiones_revocadas": revocadas,
        "mensaje": "Contrasena actualizada. Vuelve a iniciar sesion.",
    }


@router.get("/usuarios", response_model=list[UsuarioInfo])
def listar_usuarios(
    principal: Principal = Depends(
        requiere_permiso(
            Permiso.CUENTAS_OPERATIVAS,
            Permiso.PERFILES_ADMINISTRAR,
            Permiso.AUDITORIA_VER,
        )
    ),
):
    return auth_service.listar_usuarios()


@router.post("/usuarios", response_model=UsuarioInfo, status_code=201)
def crear_usuario(
    datos: UsuarioCrearRequest,
    principal: Principal = Depends(
        requiere_permiso(Permiso.CUENTAS_OPERATIVAS, Permiso.PERFILES_ADMINISTRAR)
    ),
):
    try:
        return auth_service.crear_usuario(principal.cuenta, datos.model_dump())
    except auth_service.ErrorAutenticacion as error:
        raise _convertir(error) from error


@router.patch("/usuarios/{id_usuario}/estado", response_model=UsuarioInfo)
def cambiar_estado(
    id_usuario: IdUsuario,
    datos: UsuarioEstadoRequest,
    principal: Principal = Depends(
        requiere_permiso(Permiso.CUENTAS_OPERATIVAS, Permiso.PERFILES_ADMINISTRAR)
    ),
):
    try:
        return auth_service.cambiar_estado(principal.cuenta, id_usuario, datos.activo)
    except auth_service.ErrorAutenticacion as error:
        raise _convertir(error) from error


@router.patch("/usuarios/{id_usuario}/rol", response_model=UsuarioInfo)
def cambiar_rol(
    id_usuario: IdUsuario,
    datos: UsuarioRolRequest,
    principal: Principal = Depends(requiere_permiso(Permiso.PERFILES_ADMINISTRAR)),
):
    try:
        return auth_service.cambiar_rol(principal.cuenta, id_usuario, datos.rol)
    except auth_service.ErrorAutenticacion as error:
        raise _convertir(error) from error


@router.post("/usuarios/{id_usuario}/password")
def restablecer_password(
    id_usuario: IdUsuario,
    datos: RestablecerPasswordRequest,
    principal: Principal = Depends(
        requiere_permiso(Permiso.CUENTAS_OPERATIVAS, Permiso.PERFILES_ADMINISTRAR)
    ),
):
    """Restablece la contrasena de otra cuenta y cierra sus sesiones."""

    try:
        revocadas = auth_service.restablecer_password(
            principal.cuenta, id_usuario, datos.password_nueva
        )
    except auth_service.ErrorAutenticacion as error:
        raise _convertir(error) from error
    return {
        "actualizado": True,
        "sesiones_revocadas": revocadas,
        "mensaje": "Contrasena restablecida. Las sesiones de la cuenta se cerraron.",
    }


@router.get("/auditoria")
def consultar_auditoria(
    limite: int = 100,
    principal: Principal = Depends(requiere_permiso(Permiso.AUDITORIA_VER)),
):
    return auth_service.listar_auditoria(limite)


@router.get("/permisos", response_model=CatalogoPermisosRespuesta)
def consultar_permisos(principal: Principal = Depends(sesion_actual)):
    """Catalogo de permisos por perfil (matriz efectiva, solo lectura).

    Es la misma informacion que usa el backend para autorizar: el frontend la
    consume para mostrar la matriz sin duplicar reglas.
    """

    catalogo = catalogo_permisos()
    catalogo["efectivos"] = sorted(permiso.value for permiso in principal.permisos)
    catalogo["rol_actual"] = principal.rol
    return catalogo


@router.get("/diagnostico")
def consultar_diagnostico(
    principal: Principal = Depends(requiere_permiso(Permiso.DIAGNOSTICO_VER)),
):
    return auth_service.diagnostico()
