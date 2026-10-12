"""Contratos HTTP de la capa multiempresa."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EmpresaCrear(BaseModel):
    codigo: str = Field(min_length=2, max_length=40)
    nombre: str = Field(min_length=2, max_length=160)
    identificacion_fiscal: str | None = Field(default=None, max_length=40)


class EmpresaInfo(BaseModel):
    id_empresa: UUID
    codigo: str
    nombre: str
    identificacion_fiscal: str | None
    activa: bool
    creado_en: str
    actualizado_en: str


class MembresiaCrear(BaseModel):
    id_cuenta: int = Field(gt=0)
    rol: str
    es_propietario_empresa: bool = False

    @field_validator("rol")
    @classmethod
    def normalizar_rol(cls, valor: str) -> str:
        return valor.strip().upper()


class MembresiaEstado(BaseModel):
    activa: bool


class MembresiaInfo(BaseModel):
    id_membresia: UUID
    id_empresa: UUID
    id_cuenta: int
    rol: str
    activa: bool
    es_propietario_empresa: bool
    creado_en: str
    actualizado_en: str


class VinculoRecursoCrear(BaseModel):
    tipo_recurso: str
    id_recurso: int = Field(gt=0)

    @field_validator("tipo_recurso")
    @classmethod
    def normalizar_tipo(cls, valor: str) -> str:
        return valor.strip().upper()


class VinculoRecursoInfo(BaseModel):
    id_vinculo: UUID
    id_empresa: UUID
    tipo_recurso: str
    id_recurso: int
    creado_en: str


class AsignacionCrear(BaseModel):
    id_membresia: UUID
    tipo_recurso: str
    id_recurso: int = Field(gt=0)

    @field_validator("tipo_recurso")
    @classmethod
    def normalizar_tipo(cls, valor: str) -> str:
        return valor.strip().upper()


class AsignacionInfo(BaseModel):
    id_asignacion: UUID
    id_empresa: UUID
    id_membresia: UUID
    tipo_recurso: str
    id_recurso: int
    asignado_por: int
    activa: bool
    creado_en: str
    finalizado_en: str | None
