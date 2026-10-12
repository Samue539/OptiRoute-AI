"""Errores especificos de la capa de repositorios de acceso.

Permiten distinguir, sin acoplar el servicio a un backend concreto, entre
una cuenta duplicada (correo o identificador ya usado), un registro
inexistente y una tabla que todavia no fue creada por las migraciones.
"""

from __future__ import annotations


class ErrorRepositorio(Exception):
    """Error base de la capa de persistencia de acceso."""


class ErrorCuentaDuplicada(ErrorRepositorio):
    """Ya existe una cuenta con ese correo o identificador."""


class ErrorNoEncontrado(ErrorRepositorio):
    """El registro que se intenta modificar ya no existe."""


class ErrorTablaInexistente(ErrorRepositorio):
    """Las tablas de acceso no fueron creadas (falta la migracion 006)."""


__all__ = [
    "ErrorCuentaDuplicada",
    "ErrorNoEncontrado",
    "ErrorRepositorio",
    "ErrorTablaInexistente",
]
