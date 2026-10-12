"""Modelos de dominio para la capa multiempresa aditiva.

Estos modelos no sustituyen ``Cuenta`` ni modifican el almacenamiento de
autenticacion actual. Una membresia enlaza la identidad canonica de
``seguridad.cuentas_acceso`` con una empresa y define su alcance empresarial.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from backend.app.repositories.modelos import ahora_utc


class RolEmpresa(str, Enum):
    """Roles validos dentro de una empresa.

    DESARROLLADOR se mantiene deliberadamente fuera: es un rol de plataforma.
    """

    ADMINISTRADOR = "ADMINISTRADOR"
    OPERADOR = "OPERADOR"
    CONDUCTOR = "CONDUCTOR"


class TipoRecursoEmpresa(str, Enum):
    CLIENTE = "CLIENTE"
    CONDUCTOR = "CONDUCTOR"
    VEHICULO = "VEHICULO"
    PEDIDO = "PEDIDO"
    RUTA = "RUTA"
    ZONA = "ZONA"
    GUIA = "GUIA"


@dataclass
class Empresa:
    codigo: str
    nombre: str
    id_empresa: UUID = field(default_factory=uuid4)
    identificacion_fiscal: str | None = None
    activa: bool = True
    creado_en: datetime = field(default_factory=ahora_utc)
    actualizado_en: datetime = field(default_factory=ahora_utc)

    def to_dict(self) -> dict:
        datos = asdict(self)
        datos["id_empresa"] = str(self.id_empresa)
        datos["creado_en"] = self.creado_en.isoformat()
        datos["actualizado_en"] = self.actualizado_en.isoformat()
        return datos


@dataclass
class MembresiaEmpresa:
    id_empresa: UUID
    id_cuenta: int
    rol: str
    id_membresia: UUID = field(default_factory=uuid4)
    activa: bool = True
    es_propietario_empresa: bool = False
    creado_en: datetime = field(default_factory=ahora_utc)
    actualizado_en: datetime = field(default_factory=ahora_utc)

    def to_dict(self) -> dict:
        datos = asdict(self)
        datos["id_empresa"] = str(self.id_empresa)
        datos["id_membresia"] = str(self.id_membresia)
        datos["creado_en"] = self.creado_en.isoformat()
        datos["actualizado_en"] = self.actualizado_en.isoformat()
        return datos


@dataclass
class VinculoRecursoEmpresa:
    id_empresa: UUID
    tipo_recurso: str
    id_recurso: int
    id_vinculo: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=ahora_utc)

    def to_dict(self) -> dict:
        datos = asdict(self)
        datos["id_empresa"] = str(self.id_empresa)
        datos["id_vinculo"] = str(self.id_vinculo)
        datos["creado_en"] = self.creado_en.isoformat()
        return datos


@dataclass
class AsignacionEmpresa:
    id_empresa: UUID
    id_membresia: UUID
    tipo_recurso: str
    id_recurso: int
    asignado_por: int
    id_asignacion: UUID = field(default_factory=uuid4)
    activa: bool = True
    creado_en: datetime = field(default_factory=ahora_utc)
    finalizado_en: datetime | None = None

    def to_dict(self) -> dict:
        datos = asdict(self)
        for clave in ("id_empresa", "id_membresia", "id_asignacion"):
            datos[clave] = str(datos[clave])
        datos["creado_en"] = self.creado_en.isoformat()
        datos["finalizado_en"] = (
            self.finalizado_en.isoformat() if self.finalizado_en else None
        )
        return datos


class ErrorRepositorioMultiempresa(Exception):
    """Error base de persistencia multiempresa."""


class ArquitecturaMultiempresaNoInstalada(ErrorRepositorioMultiempresa):
    """La migracion 007 aun no fue aplicada en el entorno consultado."""


class RegistroMultiempresaDuplicado(ErrorRepositorioMultiempresa):
    """Una restriccion unica impide duplicar el registro."""


__all__ = [
    "ArquitecturaMultiempresaNoInstalada",
    "AsignacionEmpresa",
    "Empresa",
    "ErrorRepositorioMultiempresa",
    "MembresiaEmpresa",
    "RegistroMultiempresaDuplicado",
    "RolEmpresa",
    "TipoRecursoEmpresa",
    "VinculoRecursoEmpresa",
]
