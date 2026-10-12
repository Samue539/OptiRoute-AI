"""Capa de repositorios de acceso (interfaces + implementaciones)."""

from backend.app.repositories.contratos import (
    RepositorioAuditoria,
    RepositorioCuentas,
    RepositorioSesiones,
)
from backend.app.repositories.errores import (
    ErrorCuentaDuplicada,
    ErrorNoEncontrado,
    ErrorRepositorio,
    ErrorTablaInexistente,
)
from backend.app.repositories.fabrica import (
    backend_almacenamiento,
    estado_almacenamiento,
    repositorio_auditoria,
    repositorio_cuentas,
    repositorio_sesiones,
    tablas_acceso_listas,
)
from backend.app.repositories.modelos import Cuenta, Sesion, ahora_utc

__all__ = [
    "Cuenta",
    "Sesion",
    "RepositorioAuditoria",
    "RepositorioCuentas",
    "RepositorioSesiones",
    "ErrorCuentaDuplicada",
    "ErrorNoEncontrado",
    "ErrorRepositorio",
    "ErrorTablaInexistente",
    "ahora_utc",
    "backend_almacenamiento",
    "estado_almacenamiento",
    "repositorio_auditoria",
    "repositorio_cuentas",
    "repositorio_sesiones",
    "tablas_acceso_listas",
]
