"""Repositorio aislado para pruebas de la arquitectura multiempresa.

No se usa como almacenamiento de produccion ni reemplaza los JSON actuales.
"""

from __future__ import annotations

from threading import RLock
from uuid import UUID

from backend.app.repositories.multiempresa_contratos import RepositorioMultiempresa
from backend.app.repositories.multiempresa_modelos import (
    AsignacionEmpresa,
    Empresa,
    MembresiaEmpresa,
    RegistroMultiempresaDuplicado,
    VinculoRecursoEmpresa,
)


class RepositorioMultiempresaMemoria(RepositorioMultiempresa):
    def __init__(self) -> None:
        self.empresas: dict[UUID, Empresa] = {}
        self.membresias: dict[UUID, MembresiaEmpresa] = {}
        self.vinculos: dict[tuple[str, int], VinculoRecursoEmpresa] = {}
        self.asignaciones: dict[UUID, AsignacionEmpresa] = {}
        self._candado = RLock()

    def crear_empresa(self, empresa: Empresa) -> Empresa:
        with self._candado:
            if any(e.codigo == empresa.codigo for e in self.empresas.values()):
                raise RegistroMultiempresaDuplicado("El codigo de empresa ya existe.")
            self.empresas[empresa.id_empresa] = empresa
        return empresa

    def obtener_empresa(self, id_empresa: UUID) -> Empresa | None:
        return self.empresas.get(id_empresa)

    def listar_empresas(self) -> list[Empresa]:
        return sorted(self.empresas.values(), key=lambda item: item.nombre)

    def crear_membresia(self, membresia: MembresiaEmpresa) -> MembresiaEmpresa:
        with self._candado:
            if self.membresia_de_cuenta(membresia.id_empresa, membresia.id_cuenta):
                raise RegistroMultiempresaDuplicado(
                    "La cuenta ya tiene una membresia en esta empresa."
                )
            self.membresias[membresia.id_membresia] = membresia
        return membresia

    def obtener_membresia(self, id_membresia: UUID) -> MembresiaEmpresa | None:
        return self.membresias.get(id_membresia)

    def membresia_de_cuenta(
        self, id_empresa: UUID, id_cuenta: int
    ) -> MembresiaEmpresa | None:
        return next(
            (
                item
                for item in self.membresias.values()
                if item.id_empresa == id_empresa and item.id_cuenta == id_cuenta
            ),
            None,
        )

    def listar_membresias(self, id_empresa: UUID) -> list[MembresiaEmpresa]:
        return [m for m in self.membresias.values() if m.id_empresa == id_empresa]

    def listar_membresias_cuenta(self, id_cuenta: int) -> list[MembresiaEmpresa]:
        return [m for m in self.membresias.values() if m.id_cuenta == id_cuenta]

    def actualizar_membresia(self, membresia: MembresiaEmpresa) -> MembresiaEmpresa:
        self.membresias[membresia.id_membresia] = membresia
        return membresia

    def contar_propietarios_activos(self, id_empresa: UUID) -> int:
        return sum(
            1
            for item in self.membresias.values()
            if item.id_empresa == id_empresa
            and item.activa
            and item.es_propietario_empresa
        )

    def vincular_recurso(
        self, vinculo: VinculoRecursoEmpresa
    ) -> VinculoRecursoEmpresa:
        clave = (vinculo.tipo_recurso, vinculo.id_recurso)
        with self._candado:
            existente = self.vinculos.get(clave)
            if existente:
                raise RegistroMultiempresaDuplicado(
                    "El recurso ya pertenece a una empresa."
                )
            self.vinculos[clave] = vinculo
        return vinculo

    def obtener_vinculo(
        self, tipo_recurso: str, id_recurso: int
    ) -> VinculoRecursoEmpresa | None:
        return self.vinculos.get((tipo_recurso, id_recurso))

    def recurso_operativo_existe(self, tipo_recurso: str, id_recurso: int) -> bool:
        # El repositorio aislado no contiene los catalogos legados; los tests
        # registran IDs positivos ficticios de manera deliberada.
        return id_recurso > 0

    def crear_asignacion(self, asignacion: AsignacionEmpresa) -> AsignacionEmpresa:
        with self._candado:
            if self.existe_asignacion_activa(
                asignacion.id_empresa,
                asignacion.id_membresia,
                asignacion.tipo_recurso,
                asignacion.id_recurso,
            ):
                raise RegistroMultiempresaDuplicado("La asignacion activa ya existe.")
            self.asignaciones[asignacion.id_asignacion] = asignacion
        return asignacion

    def existe_asignacion_activa(
        self,
        id_empresa: UUID,
        id_membresia: UUID,
        tipo_recurso: str,
        id_recurso: int,
    ) -> bool:
        return any(
            item.activa
            and item.id_empresa == id_empresa
            and item.id_membresia == id_membresia
            and item.tipo_recurso == tipo_recurso
            and item.id_recurso == id_recurso
            for item in self.asignaciones.values()
        )
