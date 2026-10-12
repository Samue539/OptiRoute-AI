"""Modelos de dominio usados por la capa de repositorios de acceso."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def ahora_utc() -> datetime:
    """Fecha-hora actual con zona UTC."""

    return datetime.now(timezone.utc)


def a_iso(valor: datetime | None) -> str | None:
    return valor.isoformat() if valor else None


def desde_iso(valor: str | None) -> datetime | None:
    if not valor:
        return None
    return datetime.fromisoformat(valor)


@dataclass
class Cuenta:
    """Cuenta de acceso a OperiRoute (no es el usuario logistico de PostgreSQL)."""

    id_usuario: int
    nombres: str
    apellidos: str
    correo: str
    password_hash: str
    rol: str
    activo: bool = True
    id_conductor: int | None = None
    es_propietario: bool = False
    creado_en: datetime = field(default_factory=ahora_utc)
    actualizado_en: datetime = field(default_factory=ahora_utc)
    ultimo_acceso: datetime | None = None

    def to_dict(self) -> dict:
        datos = asdict(self)
        datos["creado_en"] = a_iso(self.creado_en)
        datos["actualizado_en"] = a_iso(self.actualizado_en)
        datos["ultimo_acceso"] = a_iso(self.ultimo_acceso)
        return datos

    @classmethod
    def from_dict(cls, datos: dict) -> "Cuenta":
        return cls(
            id_usuario=int(datos["id_usuario"]),
            nombres=datos["nombres"],
            apellidos=datos["apellidos"],
            correo=datos["correo"],
            password_hash=datos["password_hash"],
            rol=datos["rol"],
            activo=bool(datos.get("activo", True)),
            id_conductor=datos.get("id_conductor"),
            es_propietario=bool(datos.get("es_propietario", False)),
            creado_en=desde_iso(datos.get("creado_en")) or ahora_utc(),
            actualizado_en=desde_iso(datos.get("actualizado_en")) or ahora_utc(),
            ultimo_acceso=desde_iso(datos.get("ultimo_acceso")),
        )

    def info_publica(self) -> dict:
        """Version sin hash de contrasena para exponer a la API."""

        return {
            "id_usuario": self.id_usuario,
            "nombres": self.nombres,
            "apellidos": self.apellidos,
            "correo": self.correo,
            "rol": self.rol,
            "activo": self.activo,
            "id_conductor": self.id_conductor,
            "es_propietario": self.es_propietario,
            "creado_en": a_iso(self.creado_en),
            "ultimo_acceso": a_iso(self.ultimo_acceso),
        }


@dataclass
class Sesion:
    """Sesion emitida tras un login valido.

    ``agente_hash`` e ``ip_prefijo`` son metadatos opcionales de la sesion:
    permiten (con ``AUTH_SESION_ESTRICTA=1``) invalidar el token si cambia el
    navegador o la red desde la que se inicio sesion. Son opcionales para
    conservar compatibilidad con sesiones ya emitidas.
    """

    token_hash: str
    id_usuario: int
    creado_en: datetime = field(default_factory=ahora_utc)
    expira_en: datetime = field(default_factory=ahora_utc)
    revocado: bool = False
    revocado_en: datetime | None = None
    agente_hash: str | None = None
    ip_prefijo: str | None = None

    def to_dict(self) -> dict:
        return {
            "token_hash": self.token_hash,
            "id_usuario": self.id_usuario,
            "creado_en": a_iso(self.creado_en),
            "expira_en": a_iso(self.expira_en),
            "revocado": self.revocado,
            "revocado_en": a_iso(self.revocado_en),
            "agente_hash": self.agente_hash,
            "ip_prefijo": self.ip_prefijo,
        }

    @classmethod
    def from_dict(cls, datos: dict) -> "Sesion":
        return cls(
            token_hash=datos["token_hash"],
            id_usuario=int(datos["id_usuario"]),
            creado_en=desde_iso(datos.get("creado_en")) or ahora_utc(),
            expira_en=desde_iso(datos.get("expira_en")) or ahora_utc(),
            revocado=bool(datos.get("revocado", False)),
            revocado_en=desde_iso(datos.get("revocado_en")),
            agente_hash=datos.get("agente_hash"),
            ip_prefijo=datos.get("ip_prefijo"),
        )

    def esta_vigente(self, momento: datetime | None = None) -> bool:
        referencia = momento or ahora_utc()
        return (not self.revocado) and self.expira_en > referencia
