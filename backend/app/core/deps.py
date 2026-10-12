"""Dependencias de FastAPI para autenticacion, permisos y scoping de conductor.

El objeto :class:`Principal` representa la sesion validada en cada peticion.
Las dependencias leen la cabecera ``Authorization: Bearer <token>`` y vuelven a
cargar la cuenta desde el repositorio, de modo que desactivar una cuenta o
cambiar su perfil invalida el acceso aunque el token siga vigente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Header, HTTPException, Request, status

from backend.app.core.permisos import (
    Permiso,
    Rol,
    alcance_estado_pedido,
    alcance_estado_ruta,
    estado_pedido_autorizado,
    estado_ruta_autorizado,
    permisos_de,
    texto_estados_permitidos,
)
from backend.app.repositories import Cuenta, Sesion
from backend.app.services import auth_service


@dataclass
class Principal:
    """Sesion validada: cuenta, sesion y permisos efectivos."""

    cuenta: Cuenta
    sesion: Sesion
    permisos: frozenset[Permiso]

    @property
    def rol(self) -> str:
        return self.cuenta.rol

    @property
    def id_conductor(self) -> int | None:
        return self.cuenta.id_conductor

    @property
    def es_conductor(self) -> bool:
        return self.cuenta.rol == Rol.CONDUCTOR.value

    def tiene(self, permiso: Permiso) -> bool:
        return permiso in self.permisos


def extraer_token(authorization: str | None) -> str | None:
    """Extrae el token de una cabecera ``Bearer``."""

    if not authorization:
        return None
    partes = authorization.split()
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1]
    return None


def sesion_actual(
    authorization: str | None = Header(default=None),
    solicitud: Request = None,  # inyectado por FastAPI
) -> Principal:
    """Devuelve el :class:`Principal` o lanza 401 si no hay sesion valida."""

    token = extraer_token(authorization)
    metadatos = auth_service.metadatos_peticion(solicitud)
    resuelto = (
        auth_service.resolver_sesion(token, metadatos=metadatos)
        if token
        else None
    )
    if resuelto is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesion no valida o expirada. Inicia sesion nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sesion, cuenta = resuelto
    return Principal(
        cuenta=cuenta,
        sesion=sesion,
        permisos=permisos_de(cuenta.rol),
    )


def requiere_permiso(*permisos: Permiso) -> Callable[..., Principal]:
    """Crea una dependencia que exige al menos uno de los permisos."""

    def dependencia(principal: Principal = Depends(sesion_actual)) -> Principal:
        if not any(principal.tiene(permiso) for permiso in permisos):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta accion.",
            )
        return principal

    return dependencia


def ruta_es_propia(principal: Principal, ruta: dict | None) -> bool:
    """Indica si la ruta pertenece al conductor autenticado."""

    if principal.id_conductor is None or not ruta:
        return False
    conductor = ruta.get("conductor") if isinstance(ruta, dict) else None
    return bool(conductor) and conductor.get("id_conductor") == principal.id_conductor


def autorizar_ver_ruta(principal: Principal, ruta: dict | None) -> None:
    """Permite ver una ruta a quien ve todas o al conductor asignado."""

    if principal.tiene(Permiso.RUTAS_VER_TODAS):
        return
    if ruta_es_propia(principal, ruta):
        return
    raise HTTPException(
        status_code=403,
        detail="No tienes acceso a esta ruta.",
    )


def _permitir_estado(principal: Principal, estado: str | None, tipo: str) -> None:
    """Comprueba que el perfil puede fijar ese estado concreto.

    Tener ``rutas:estado`` no autoriza cualquier cambio: un perfil con permiso
    limitado solo puede fijar los estados declarados en el catalogo.
    """

    if not estado:
        return
    if tipo == "ruta":
        autorizado = estado_ruta_autorizado(principal.rol, estado)
    else:
        autorizado = estado_pedido_autorizado(principal.rol, estado)
    if autorizado:
        return
    raise HTTPException(
        status_code=403,
        detail=(
            "Tu perfil no permite fijar este estado. "
            + texto_estados_permitidos(principal.rol, tipo)
        ),
    )


def autorizar_estado_ruta(
    principal: Principal, ruta: dict | None, estado: str | None = None
) -> None:
    """Autoriza cambiar el estado de una ruta.

    Denega por defecto. Exige un permiso de estado y, ademas, comprobar la
    propiedad de la ruta cuando el perfil es de alcance propio.
    """

    if alcance_estado_ruta(principal.rol) == "ninguno":
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para cambiar el estado de una ruta.",
        )
    if principal.tiene(Permiso.RUTAS_VER_TODAS):
        _permitir_estado(principal, estado, "ruta")
        return
    if ruta_es_propia(principal, ruta):
        _permitir_estado(principal, estado, "ruta")
        return
    raise HTTPException(
        status_code=403,
        detail="No tienes acceso a esta ruta.",
    )


def filtrar_rutas_visibles(principal: Principal, rutas: list[dict]) -> list[dict]:
    """Recorta el listado de rutas segun el perfil autenticado."""

    if principal.tiene(Permiso.RUTAS_VER_TODAS):
        return rutas
    return [ruta for ruta in rutas if ruta_es_propia(principal, ruta)]
