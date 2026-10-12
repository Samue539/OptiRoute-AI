"""Contratos (interfaces) de los repositorios de acceso.

Al programar contra estas interfaces es posible sustituir el almacenamiento
local persistente por Supabase (o cualquier otro backend) sin tocar los
servicios de autenticacion. La integracion con Supabase queda como trabajo
posterior: no se simula que ya esta conectado.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.repositories.modelos import Cuenta, Sesion


class RepositorioCuentas(ABC):
    """Persistencia de cuentas de acceso."""

    @abstractmethod
    def crear(self, cuenta: Cuenta) -> Cuenta:
        ...

    @abstractmethod
    def obtener(self, id_usuario: int) -> Cuenta | None:
        ...

    @abstractmethod
    def obtener_por_correo(self, correo: str) -> Cuenta | None:
        ...

    @abstractmethod
    def listar(self) -> list[Cuenta]:
        ...

    @abstractmethod
    def actualizar(self, cuenta: Cuenta) -> Cuenta:
        ...

    @abstractmethod
    def existe_rol(self, rol: str) -> bool:
        ...


class RepositorioSesiones(ABC):
    """Persistencia de sesiones emitidas."""

    @abstractmethod
    def crear(self, sesion: Sesion) -> Sesion:
        ...

    @abstractmethod
    def obtener(self, token_hash: str) -> Sesion | None:
        ...

    @abstractmethod
    def actualizar(self, sesion: Sesion) -> Sesion:
        ...

    @abstractmethod
    def revocar(self, token_hash: str) -> bool:
        ...

    @abstractmethod
    def revocar_por_usuario(self, id_usuario: int) -> int:
        ...

    @abstractmethod
    def limpiar_expiradas(self) -> int:
        ...

    @abstractmethod
    def contar_activas(self) -> int:
        ...


class RepositorioAuditoria(ABC):
    """Bitacora de eventos de seguridad (append-only)."""

    @abstractmethod
    def registrar(self, evento: dict) -> dict:
        ...

    @abstractmethod
    def listar(self, limite: int = 100) -> list[dict]:
        ...
