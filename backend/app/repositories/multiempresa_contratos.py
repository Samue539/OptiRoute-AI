"""Contratos de persistencia para empresas, membresias y asignaciones."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from backend.app.repositories.multiempresa_modelos import (
    AsignacionEmpresa,
    Empresa,
    MembresiaEmpresa,
    VinculoRecursoEmpresa,
)


class RepositorioMultiempresa(ABC):
    @abstractmethod
    def crear_empresa(self, empresa: Empresa) -> Empresa: ...

    @abstractmethod
    def obtener_empresa(self, id_empresa: UUID) -> Empresa | None: ...

    @abstractmethod
    def listar_empresas(self) -> list[Empresa]: ...

    @abstractmethod
    def crear_membresia(self, membresia: MembresiaEmpresa) -> MembresiaEmpresa: ...

    @abstractmethod
    def obtener_membresia(self, id_membresia: UUID) -> MembresiaEmpresa | None: ...

    @abstractmethod
    def membresia_de_cuenta(
        self, id_empresa: UUID, id_cuenta: int
    ) -> MembresiaEmpresa | None: ...

    @abstractmethod
    def listar_membresias(self, id_empresa: UUID) -> list[MembresiaEmpresa]: ...

    @abstractmethod
    def listar_membresias_cuenta(self, id_cuenta: int) -> list[MembresiaEmpresa]: ...

    @abstractmethod
    def actualizar_membresia(self, membresia: MembresiaEmpresa) -> MembresiaEmpresa: ...

    @abstractmethod
    def contar_propietarios_activos(self, id_empresa: UUID) -> int: ...

    @abstractmethod
    def vincular_recurso(
        self, vinculo: VinculoRecursoEmpresa
    ) -> VinculoRecursoEmpresa: ...

    @abstractmethod
    def obtener_vinculo(
        self, tipo_recurso: str, id_recurso: int
    ) -> VinculoRecursoEmpresa | None: ...

    @abstractmethod
    def recurso_operativo_existe(self, tipo_recurso: str, id_recurso: int) -> bool: ...

    @abstractmethod
    def crear_asignacion(self, asignacion: AsignacionEmpresa) -> AsignacionEmpresa: ...

    @abstractmethod
    def existe_asignacion_activa(
        self,
        id_empresa: UUID,
        id_membresia: UUID,
        tipo_recurso: str,
        id_recurso: int,
    ) -> bool: ...
