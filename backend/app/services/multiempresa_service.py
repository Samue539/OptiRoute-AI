"""Reglas de negocio y aislamiento para la arquitectura multiempresa.

La autorizacion ocurre en dos capas: el RBAC global existente determina la
capacidad general y esta capa exige una membresia empresarial activa. Ningun
identificador recibido del cliente se considera prueba de pertenencia.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Callable
from uuid import UUID

from backend.app.core.permisos import Rol
from backend.app.repositories.modelos import Cuenta, ahora_utc
from backend.app.repositories.multiempresa_contratos import RepositorioMultiempresa
from backend.app.repositories.multiempresa_modelos import (
    AsignacionEmpresa,
    Empresa,
    MembresiaEmpresa,
    RegistroMultiempresaDuplicado,
    RolEmpresa,
    TipoRecursoEmpresa,
    VinculoRecursoEmpresa,
)


class AccionEmpresa(str, Enum):
    VER = "empresa:ver"
    VER_MEMBRESIAS = "empresa:membresias_ver"
    ADMINISTRAR_MEMBRESIAS = "empresa:membresias_administrar"
    VINCULAR_RECURSOS = "empresa:recursos_vincular"
    ASIGNAR_RECURSOS = "empresa:recursos_asignar"
    ACCEDER_RECURSO = "empresa:recurso_acceder"
    VER_ENTREGAS_ASIGNADAS = "empresa:entregas_ver_asignadas"
    REGISTRAR_ENTREGA_ASIGNADA = "empresa:entregas_registrar_asignada"


ACCIONES_POR_ROL_EMPRESA: dict[RolEmpresa, frozenset[AccionEmpresa]] = {
    RolEmpresa.ADMINISTRADOR: frozenset(AccionEmpresa),
    RolEmpresa.OPERADOR: frozenset(
        {
            AccionEmpresa.VER,
            AccionEmpresa.ACCEDER_RECURSO,
            AccionEmpresa.VER_ENTREGAS_ASIGNADAS,
            AccionEmpresa.REGISTRAR_ENTREGA_ASIGNADA,
        }
    ),
    RolEmpresa.CONDUCTOR: frozenset(
        {
            AccionEmpresa.VER,
            AccionEmpresa.ACCEDER_RECURSO,
            AccionEmpresa.VER_ENTREGAS_ASIGNADAS,
            AccionEmpresa.REGISTRAR_ENTREGA_ASIGNADA,
        }
    ),
}


class ErrorMultiempresa(Exception):
    def __init__(self, mensaje: str, codigo: int = 400) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


class AccesoEmpresaDenegado(ErrorMultiempresa):
    def __init__(self, mensaje: str = "No tienes acceso a esta empresa.") -> None:
        super().__init__(mensaje, 403)


class RecursoEmpresaNoEncontrado(ErrorMultiempresa):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje, 404)


class ConflictoMultiempresa(ErrorMultiempresa):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje, 409)


class ServicioMultiempresa:
    def __init__(
        self,
        repositorio: RepositorioMultiempresa,
        obtener_rol_cuenta: Callable[[int], str | None] | None = None,
        es_cuenta_propietaria: Callable[[int], bool] | None = None,
    ) -> None:
        self.repositorio = repositorio
        self._obtener_rol_cuenta = obtener_rol_cuenta or (lambda _id: None)
        self._es_cuenta_propietaria = es_cuenta_propietaria or (lambda _id: False)

    @staticmethod
    def _es_desarrollador(actor: Cuenta) -> bool:
        return actor.activo and actor.rol == Rol.DESARROLLADOR.value

    def _empresa(self, id_empresa: UUID) -> Empresa:
        empresa = self.repositorio.obtener_empresa(id_empresa)
        if not empresa:
            raise RecursoEmpresaNoEncontrado("La empresa no existe.")
        return empresa

    def membresia_activa(self, actor: Cuenta, id_empresa: UUID) -> MembresiaEmpresa:
        membresia = self.repositorio.membresia_de_cuenta(
            id_empresa, actor.id_usuario
        )
        if not membresia or not membresia.activa:
            raise AccesoEmpresaDenegado()
        # Durante la transicion el rol global sigue siendo la autoridad de
        # autenticacion. Un desacuerdo nunca aumenta privilegios.
        if membresia.rol != actor.rol:
            raise AccesoEmpresaDenegado(
                "La membresia no coincide con el perfil autenticado."
            )
        return membresia

    def autorizar(
        self, actor: Cuenta, id_empresa: UUID, accion: AccionEmpresa
    ) -> MembresiaEmpresa | None:
        self._empresa(id_empresa)
        if self._es_desarrollador(actor):
            return None
        membresia = self.membresia_activa(actor, id_empresa)
        try:
            rol = RolEmpresa(membresia.rol)
        except ValueError as error:
            raise AccesoEmpresaDenegado("La membresia tiene un perfil invalido.") from error
        if accion not in ACCIONES_POR_ROL_EMPRESA[rol]:
            raise AccesoEmpresaDenegado(
                "Tu perfil no permite esta accion dentro de la empresa."
            )
        return membresia

    def listar_empresas(self, actor: Cuenta) -> list[Empresa]:
        if self._es_desarrollador(actor):
            return self.repositorio.listar_empresas()
        ids = {
            item.id_empresa
            for item in self.repositorio.listar_membresias_cuenta(actor.id_usuario)
            if item.activa and item.rol == actor.rol
        }
        return [
            empresa
            for empresa in self.repositorio.listar_empresas()
            if empresa.id_empresa in ids and empresa.activa
        ]

    def crear_empresa(
        self,
        actor: Cuenta,
        codigo: str,
        nombre: str,
        identificacion_fiscal: str | None = None,
    ) -> Empresa:
        if not self._es_desarrollador(actor):
            raise AccesoEmpresaDenegado(
                "Solo el DESARROLLADOR de plataforma puede crear empresas."
            )
        codigo = re.sub(r"[^A-Z0-9_-]", "-", codigo.strip().upper())
        if not 2 <= len(codigo) <= 40:
            raise ErrorMultiempresa("El codigo de empresa debe tener entre 2 y 40 caracteres.")
        nombre = nombre.strip()
        if not 2 <= len(nombre) <= 160:
            raise ErrorMultiempresa("El nombre de empresa debe tener entre 2 y 160 caracteres.")
        empresa = Empresa(
            codigo=codigo,
            nombre=nombre,
            identificacion_fiscal=(identificacion_fiscal or "").strip() or None,
        )
        try:
            return self.repositorio.crear_empresa(empresa)
        except RegistroMultiempresaDuplicado as error:
            raise ConflictoMultiempresa(str(error)) from error

    def obtener_empresa(self, actor: Cuenta, id_empresa: UUID) -> Empresa:
        self.autorizar(actor, id_empresa, AccionEmpresa.VER)
        return self._empresa(id_empresa)

    def listar_membresias(
        self, actor: Cuenta, id_empresa: UUID
    ) -> list[MembresiaEmpresa]:
        self.autorizar(actor, id_empresa, AccionEmpresa.VER_MEMBRESIAS)
        return self.repositorio.listar_membresias(id_empresa)

    def crear_membresia(
        self,
        actor: Cuenta,
        id_empresa: UUID,
        id_cuenta: int,
        rol: str,
        es_propietario_empresa: bool = False,
    ) -> MembresiaEmpresa:
        self.autorizar(actor, id_empresa, AccionEmpresa.ADMINISTRAR_MEMBRESIAS)
        try:
            rol_empresa = RolEmpresa(rol.upper())
        except ValueError as error:
            raise ErrorMultiempresa(
                "La membresia admite ADMINISTRADOR, OPERADOR o CONDUCTOR."
            ) from error
        if not self._es_desarrollador(actor) and rol_empresa == RolEmpresa.ADMINISTRADOR:
            raise AccesoEmpresaDenegado(
                "Solo el DESARROLLADOR puede otorgar ADMINISTRADOR."
            )
        if es_propietario_empresa and not self._es_desarrollador(actor):
            raise AccesoEmpresaDenegado(
                "Solo el DESARROLLADOR puede designar al propietario empresarial."
            )
        if es_propietario_empresa and rol_empresa != RolEmpresa.ADMINISTRADOR:
            raise ErrorMultiempresa(
                "El propietario empresarial debe ser ADMINISTRADOR."
            )
        rol_cuenta = self._obtener_rol_cuenta(id_cuenta)
        if rol_cuenta is None:
            raise RecursoEmpresaNoEncontrado("La cuenta canonica no existe.")
        if rol_cuenta != rol_empresa.value:
            raise ConflictoMultiempresa(
                "El rol empresarial debe coincidir con el perfil actual de la cuenta."
            )
        membresia = MembresiaEmpresa(
            id_empresa=id_empresa,
            id_cuenta=id_cuenta,
            rol=rol_empresa.value,
            es_propietario_empresa=es_propietario_empresa,
        )
        try:
            return self.repositorio.crear_membresia(membresia)
        except RegistroMultiempresaDuplicado as error:
            raise ConflictoMultiempresa(str(error)) from error

    def cambiar_estado_membresia(
        self,
        actor: Cuenta,
        id_empresa: UUID,
        id_membresia: UUID,
        activa: bool,
    ) -> MembresiaEmpresa:
        self.autorizar(actor, id_empresa, AccionEmpresa.ADMINISTRAR_MEMBRESIAS)
        membresia = self.repositorio.obtener_membresia(id_membresia)
        if not membresia or membresia.id_empresa != id_empresa:
            raise RecursoEmpresaNoEncontrado("La membresia no existe en esta empresa.")
        if not activa:
            if self._es_cuenta_propietaria(membresia.id_cuenta):
                raise AccesoEmpresaDenegado(
                    "La cuenta propietaria de plataforma no puede desactivarse."
                )
            if membresia.id_cuenta == actor.id_usuario:
                raise ConflictoMultiempresa("No puedes desactivar tu propia membresia.")
            if (
                membresia.es_propietario_empresa
                and membresia.activa
                and self.repositorio.contar_propietarios_activos(id_empresa) <= 1
            ):
                raise ConflictoMultiempresa(
                    "La empresa debe conservar un propietario activo."
                )
        membresia.activa = activa
        membresia.actualizado_en = ahora_utc()
        return self.repositorio.actualizar_membresia(membresia)

    def vincular_recurso(
        self,
        actor: Cuenta,
        id_empresa: UUID,
        tipo_recurso: str,
        id_recurso: int,
    ) -> VinculoRecursoEmpresa:
        self.autorizar(actor, id_empresa, AccionEmpresa.VINCULAR_RECURSOS)
        try:
            tipo = TipoRecursoEmpresa(tipo_recurso.upper()).value
        except ValueError as error:
            raise ErrorMultiempresa("Tipo de recurso empresarial invalido.") from error
        if not self.repositorio.recurso_operativo_existe(tipo, id_recurso):
            raise RecursoEmpresaNoEncontrado(
                "El recurso operativo no existe o su modulo aun no esta habilitado."
            )
        vinculo = VinculoRecursoEmpresa(
            id_empresa=id_empresa, tipo_recurso=tipo, id_recurso=id_recurso
        )
        try:
            return self.repositorio.vincular_recurso(vinculo)
        except RegistroMultiempresaDuplicado as error:
            raise ConflictoMultiempresa(str(error)) from error

    def asignar_recurso(
        self,
        actor: Cuenta,
        id_empresa: UUID,
        id_membresia: UUID,
        tipo_recurso: str,
        id_recurso: int,
    ) -> AsignacionEmpresa:
        self.autorizar(actor, id_empresa, AccionEmpresa.ASIGNAR_RECURSOS)
        tipo_recurso = tipo_recurso.upper()
        if tipo_recurso not in {"PEDIDO", "RUTA", "ZONA", "GUIA"}:
            raise ErrorMultiempresa(
                "Solo se asignan PEDIDO, RUTA, ZONA o GUIA."
            )
        membresia = self.repositorio.obtener_membresia(id_membresia)
        if not membresia or membresia.id_empresa != id_empresa or not membresia.activa:
            raise RecursoEmpresaNoEncontrado(
                "La membresia activa no pertenece a esta empresa."
            )
        vinculo = self.repositorio.obtener_vinculo(tipo_recurso, id_recurso)
        if not vinculo or vinculo.id_empresa != id_empresa:
            raise AccesoEmpresaDenegado(
                "El recurso no esta vinculado a esta empresa."
            )
        asignacion = AsignacionEmpresa(
            id_empresa=id_empresa,
            id_membresia=id_membresia,
            tipo_recurso=tipo_recurso,
            id_recurso=id_recurso,
            asignado_por=actor.id_usuario,
        )
        try:
            return self.repositorio.crear_asignacion(asignacion)
        except RegistroMultiempresaDuplicado as error:
            raise ConflictoMultiempresa(str(error)) from error

    def autorizar_recurso_asignado(
        self,
        actor: Cuenta,
        id_empresa: UUID,
        tipo_recurso: str,
        id_recurso: int,
    ) -> None:
        membresia = self.autorizar(
            actor, id_empresa, AccionEmpresa.ACCEDER_RECURSO
        )
        vinculo = self.repositorio.obtener_vinculo(tipo_recurso.upper(), id_recurso)
        if not vinculo or vinculo.id_empresa != id_empresa:
            raise AccesoEmpresaDenegado(
                "El recurso no pertenece a la empresa solicitada."
            )
        if self._es_desarrollador(actor):
            return
        assert membresia is not None
        if membresia.rol == RolEmpresa.ADMINISTRADOR.value:
            return
        if not self.repositorio.existe_asignacion_activa(
            id_empresa,
            membresia.id_membresia,
            tipo_recurso.upper(),
            id_recurso,
        ):
            raise AccesoEmpresaDenegado(
                "El recurso no esta asignado a la cuenta autenticada."
            )


def catalogo_acciones_empresa() -> dict:
    return {
        "alcance_plataforma": {
            "rol": Rol.DESARROLLADOR.value,
            "acciones": [accion.value for accion in AccionEmpresa],
        },
        "roles_empresa": [
            {
                "rol": rol.value,
                "acciones": sorted(accion.value for accion in acciones),
            }
            for rol, acciones in ACCIONES_POR_ROL_EMPRESA.items()
        ],
        "regla": (
            "Denegacion por defecto: rol global compatible, membresia activa, "
            "empresa correcta y asignacion explicita para recursos operativos."
        ),
    }
