"""Endpoints aditivos de empresas, membresias y asignaciones.

Las tablas no se crean al arrancar. Antes de aplicar la migracion 007 en un
entorno autorizado, estos endpoints responden 503 en vez de tocar el modelo
actual o degradar el aislamiento.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.deps import Principal, sesion_actual
from backend.app.repositories.fabrica import repositorio_cuentas
from backend.app.repositories.multiempresa_modelos import (
    ArquitecturaMultiempresaNoInstalada,
)
from backend.app.repositories.multiempresa_postgres import (
    RepositorioMultiempresaPostgres,
)
from backend.app.schemas.multiempresa import (
    AsignacionCrear,
    AsignacionInfo,
    EmpresaCrear,
    EmpresaInfo,
    MembresiaCrear,
    MembresiaEstado,
    MembresiaInfo,
    VinculoRecursoCrear,
    VinculoRecursoInfo,
)
from backend.app.services.multiempresa_service import (
    ErrorMultiempresa,
    ServicioMultiempresa,
    catalogo_acciones_empresa,
)
from backend.app.services import auth_service


router = APIRouter(prefix="/api/empresas", tags=["Multiempresa"])


def obtener_servicio_multiempresa() -> ServicioMultiempresa:
    cuentas = repositorio_cuentas()

    def rol_cuenta(id_cuenta: int) -> str | None:
        cuenta = cuentas.obtener(id_cuenta)
        return cuenta.rol if cuenta and cuenta.activo else None

    def es_propietaria(id_cuenta: int) -> bool:
        cuenta = cuentas.obtener(id_cuenta)
        return bool(cuenta and cuenta.es_propietario)

    return ServicioMultiempresa(
        RepositorioMultiempresaPostgres(),
        obtener_rol_cuenta=rol_cuenta,
        es_cuenta_propietaria=es_propietaria,
    )


def _error(error: Exception) -> HTTPException:
    if isinstance(error, ArquitecturaMultiempresaNoInstalada):
        return HTTPException(
            status_code=503,
            detail=(
                "La arquitectura multiempresa esta preparada pero la migracion "
                "007 no ha sido aplicada en este entorno."
            ),
        )
    if isinstance(error, ErrorMultiempresa):
        return HTTPException(status_code=error.codigo, detail=error.mensaje)
    return HTTPException(status_code=500, detail="Error interno multiempresa.")


def _auditar(principal: Principal, accion: str, **detalle) -> None:
    auth_service.auditar_evento_seguro(
        accion,
        principal.cuenta.correo,
        principal.cuenta.id_usuario,
        **detalle,
    )


@router.get("/permisos")
def permisos_empresariales(principal: Principal = Depends(sesion_actual)):
    """Catalogo separado del RBAC historico; no expone datos empresariales."""

    catalogo = catalogo_acciones_empresa()
    catalogo["rol_actual"] = principal.rol
    return catalogo


@router.get("", response_model=list[EmpresaInfo])
def listar_empresas(
    principal: Principal = Depends(sesion_actual),
    servicio: ServicioMultiempresa = Depends(obtener_servicio_multiempresa),
):
    try:
        return [item.to_dict() for item in servicio.listar_empresas(principal.cuenta)]
    except Exception as error:
        raise _error(error) from error


@router.post("", response_model=EmpresaInfo, status_code=201)
def crear_empresa(
    datos: EmpresaCrear,
    principal: Principal = Depends(sesion_actual),
    servicio: ServicioMultiempresa = Depends(obtener_servicio_multiempresa),
):
    try:
        empresa = servicio.crear_empresa(
            principal.cuenta,
            datos.codigo,
            datos.nombre,
            datos.identificacion_fiscal,
        )
        _auditar(
            principal,
            "empresa_creada",
            id_empresa=str(empresa.id_empresa),
            codigo=empresa.codigo,
        )
        return empresa.to_dict()
    except Exception as error:
        raise _error(error) from error


@router.get("/{id_empresa}", response_model=EmpresaInfo)
def consultar_empresa(
    id_empresa: UUID,
    principal: Principal = Depends(sesion_actual),
    servicio: ServicioMultiempresa = Depends(obtener_servicio_multiempresa),
):
    try:
        return servicio.obtener_empresa(principal.cuenta, id_empresa).to_dict()
    except Exception as error:
        raise _error(error) from error


@router.get("/{id_empresa}/membresias", response_model=list[MembresiaInfo])
def listar_membresias(
    id_empresa: UUID,
    principal: Principal = Depends(sesion_actual),
    servicio: ServicioMultiempresa = Depends(obtener_servicio_multiempresa),
):
    try:
        return [
            item.to_dict()
            for item in servicio.listar_membresias(principal.cuenta, id_empresa)
        ]
    except Exception as error:
        raise _error(error) from error


@router.post("/{id_empresa}/membresias", response_model=MembresiaInfo, status_code=201)
def crear_membresia(
    id_empresa: UUID,
    datos: MembresiaCrear,
    principal: Principal = Depends(sesion_actual),
    servicio: ServicioMultiempresa = Depends(obtener_servicio_multiempresa),
):
    try:
        membresia = servicio.crear_membresia(
            principal.cuenta,
            id_empresa,
            datos.id_cuenta,
            datos.rol,
            datos.es_propietario_empresa,
        )
        _auditar(
            principal,
            "membresia_empresa_creada",
            id_empresa=str(id_empresa),
            id_membresia=str(membresia.id_membresia),
            id_cuenta=membresia.id_cuenta,
            rol=membresia.rol,
        )
        return membresia.to_dict()
    except Exception as error:
        raise _error(error) from error


@router.patch(
    "/{id_empresa}/membresias/{id_membresia}", response_model=MembresiaInfo
)
def cambiar_estado_membresia(
    id_empresa: UUID,
    id_membresia: UUID,
    datos: MembresiaEstado,
    principal: Principal = Depends(sesion_actual),
    servicio: ServicioMultiempresa = Depends(obtener_servicio_multiempresa),
):
    try:
        membresia = servicio.cambiar_estado_membresia(
            principal.cuenta, id_empresa, id_membresia, datos.activa
        )
        _auditar(
            principal,
            "membresia_empresa_estado",
            id_empresa=str(id_empresa),
            id_membresia=str(id_membresia),
            activa=membresia.activa,
        )
        return membresia.to_dict()
    except Exception as error:
        raise _error(error) from error


@router.post("/{id_empresa}/recursos", response_model=VinculoRecursoInfo, status_code=201)
def vincular_recurso(
    id_empresa: UUID,
    datos: VinculoRecursoCrear,
    principal: Principal = Depends(sesion_actual),
    servicio: ServicioMultiempresa = Depends(obtener_servicio_multiempresa),
):
    try:
        vinculo = servicio.vincular_recurso(
            principal.cuenta, id_empresa, datos.tipo_recurso, datos.id_recurso
        )
        _auditar(
            principal,
            "recurso_vinculado_empresa",
            id_empresa=str(id_empresa),
            tipo_recurso=vinculo.tipo_recurso,
            id_recurso=vinculo.id_recurso,
        )
        return vinculo.to_dict()
    except Exception as error:
        raise _error(error) from error


@router.post(
    "/{id_empresa}/asignaciones", response_model=AsignacionInfo, status_code=201
)
def asignar_recurso(
    id_empresa: UUID,
    datos: AsignacionCrear,
    principal: Principal = Depends(sesion_actual),
    servicio: ServicioMultiempresa = Depends(obtener_servicio_multiempresa),
):
    try:
        asignacion = servicio.asignar_recurso(
            principal.cuenta,
            id_empresa,
            datos.id_membresia,
            datos.tipo_recurso,
            datos.id_recurso,
        )
        _auditar(
            principal,
            "recurso_empresa_asignado",
            id_empresa=str(id_empresa),
            id_membresia=str(asignacion.id_membresia),
            tipo_recurso=asignacion.tipo_recurso,
            id_recurso=asignacion.id_recurso,
        )
        return asignacion.to_dict()
    except Exception as error:
        raise _error(error) from error


@router.get("/{id_empresa}/recursos/{tipo_recurso}/{id_recurso}/acceso")
def validar_acceso_recurso(
    id_empresa: UUID,
    tipo_recurso: str,
    id_recurso: int,
    principal: Principal = Depends(sesion_actual),
    servicio: ServicioMultiempresa = Depends(obtener_servicio_multiempresa),
):
    try:
        servicio.autorizar_recurso_asignado(
            principal.cuenta, id_empresa, tipo_recurso, id_recurso
        )
        return {"autorizado": True}
    except Exception as error:
        raise _error(error) from error
