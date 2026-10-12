"""Schemas de la API de autenticacion y administracion de cuentas."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLES_VALIDOS = ("OPERADOR", "ADMINISTRADOR", "DESARROLLADOR", "CONDUCTOR")


def _normalizar_correo(valor: str) -> str:
    valor = (valor or "").strip().lower()
    if not PATRON_CORREO.match(valor):
        raise ValueError("Correo electronico invalido.")
    return valor


class BootstrapRequest(BaseModel):
    nombres: str = Field(min_length=2, max_length=100)
    apellidos: str = Field(min_length=2, max_length=100)
    correo: str
    password: str

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        return _normalizar_correo(valor)


class LoginRequest(BaseModel):
    correo: str
    password: str

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        return _normalizar_correo(valor)


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


class UsuarioCrearRequest(BaseModel):
    nombres: str = Field(min_length=2, max_length=100)
    apellidos: str = Field(min_length=2, max_length=100)
    correo: str
    password: str
    rol: str
    id_conductor: int | None = None

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, valor: str) -> str:
        return _normalizar_correo(valor)

    @field_validator("rol")
    @classmethod
    def validar_rol(cls, valor: str) -> str:
        valor = (valor or "").upper()
        if valor not in ROLES_VALIDOS:
            raise ValueError(f"Perfil invalido. Permitidos: {', '.join(ROLES_VALIDOS)}")
        return valor


class UsuarioEstadoRequest(BaseModel):
    activo: bool


class UsuarioRolRequest(BaseModel):
    rol: str

    @field_validator("rol")
    @classmethod
    def validar_rol(cls, valor: str) -> str:
        valor = (valor or "").upper()
        if valor not in ROLES_VALIDOS:
            raise ValueError(f"Perfil invalido. Permitidos: {', '.join(ROLES_VALIDOS)}")
        return valor


class RestablecerPasswordRequest(BaseModel):
    password_nueva: str


class UsuarioInfo(BaseModel):
    id_usuario: int
    nombres: str
    apellidos: str
    correo: str
    rol: str
    activo: bool
    id_conductor: int | None = None
    es_propietario: bool
    creado_en: str | None = None
    ultimo_acceso: str | None = None


class SesionRespuesta(BaseModel):
    token: str | None = None
    expira_en: str
    usuario: UsuarioInfo
    permisos: list[str]


class EstadoBootstrapRespuesta(BaseModel):
    propietario_creado: bool
    almacenamiento: str


class PermisoCatalogo(BaseModel):
    codigo: str
    nombre: str
    descripcion: str
    modulo: str
    ambito: str = "general"
    limite: str | None = None


class RolCatalogo(BaseModel):
    rol: str
    descripcion: str
    total_permisos: int
    permisos: list[str]
    estados_pedido: str = ""
    estados_ruta: str = ""


class ModuloCatalogo(BaseModel):
    id: str
    nombre: str


class ReglaCatalogo(BaseModel):
    titulo: str
    detalle: str


class CatalogoPermisosRespuesta(BaseModel):
    """Matriz de permisos efectiva (solo lectura)."""

    roles: list[RolCatalogo]
    modulos: list[ModuloCatalogo]
    permisos: list[PermisoCatalogo]
    reglas: list[ReglaCatalogo] = []
    rol_actual: str
    efectivos: list[str]
