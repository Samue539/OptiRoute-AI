"""Almacenamiento privado de evidencias fotograficas (Fase 1).

Reglas:
* Las fotos nunca son publicas: se guarda el binario fuera del arbol
  servido por el frontend y solo se expone mediante un endpoint que exige
  sesion, permiso ``evidencias:ver`` y un token temporal firmado (HMAC).
* La validacion (tipo real por firma magica, tamano y hash) ocurre aqui y
  se re-valida en el servicio: el frontend solo pre-filtra por comodidad.
* Interfaz preparada para Supabase Storage: ``repositorio_evidencias()``
  devuelve el backend local salvo que ``EVIDENCIAS_BACKEND=supabase`` con
  ``SUPABASE_URL``, ``SUPABASE_SERVICE_KEY`` y ``SUPABASE_BUCKET``.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


TAMANO_MAXIMO_BYTES = 15 * 1024 * 1024  # 15 MB (igual que el CHECK de la 008)

_MIMES_PERMITIDOS = ("image/jpeg", "image/png", "image/webp")
_EXTENSION_POR_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

# Solo para desarrollo cuando EVIDENCIAS_SECRET no esta configurado. Se crea
# una vez por proceso y nunca se persiste ni se publica; por eso los enlaces
# firmados dejan de ser validos al reiniciar el backend.
_SECRETO_EFIMERO = secrets.token_bytes(32)


class ErrorEvidencia(Exception):
    def __init__(self, mensaje: str, codigo: int = 400) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


@dataclass
class EvidenciaValidada:
    mime: str
    extension: str
    sha256: str
    tamano_bytes: int


def _mime_por_firma(contenido: bytes) -> str | None:
    if contenido[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if contenido[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if (
        len(contenido) >= 12
        and contenido[:4] == b"RIFF"
        and contenido[8:12] == b"WEBP"
    ):
        return "image/webp"
    return None


def validar_imagen(
    contenido: bytes,
    nombre_archivo: str | None = None,
    content_type: str | None = None,
) -> EvidenciaValidada:
    """Valida el binario real (no el Content-Type declarado)."""

    if not contenido:
        raise ErrorEvidencia("La fotografia esta vacia.")
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise ErrorEvidencia(
            f"La fotografia supera el maximo de {TAMANO_MAXIMO_BYTES} bytes."
        )
    mime = _mime_por_firma(contenido)
    if mime is None:
        raise ErrorEvidencia(
            "Formato no permitido: solo JPEG, PNG o WebP."
        )
    if content_type and content_type.split(";")[0].strip().lower() not in (
        mime,
        "application/octet-stream",
    ):
        raise ErrorEvidencia(
            "El tipo declarado no coincide con el contenido de la imagen."
        )
    if nombre_archivo:
        sufijo = Path(nombre_archivo).suffix.lower()
        permitidos = {".jpg", ".jpeg", ".png", ".webp"}
        if sufijo and sufijo not in permitidos:
            raise ErrorEvidencia("Extension de archivo no permitida.")
    return EvidenciaValidada(
        mime=mime,
        extension=_EXTENSION_POR_MIME[mime],
        sha256=hashlib.sha256(contenido).hexdigest(),
        tamano_bytes=len(contenido),
    )


def _directorio_base() -> Path:
    raiz = Path(__file__).resolve().parents[3]
    ruta = Path(os.getenv("EVIDENCIAS_DIR", str(raiz / "backend" / "data" / "evidencias")))
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def _secreto_firmas() -> bytes:
    secreto = os.getenv("EVIDENCIAS_SECRET", "")
    if not secreto:
        # Secreto efimero: los enlaces temporales mueren al reiniciar.
        return _SECRETO_EFIMERO
    return secreto.encode("utf-8")


class RepositorioEvidencias:
    """Interfaz comun local / Supabase."""

    def guardar(self, sha256: str, extension: str, contenido: bytes) -> str:
        raise NotImplementedError

    def abrir(self, storage_key: str) -> bytes:
        raise NotImplementedError

    def firmar_acceso(self, storage_key: str, segundos: int = 300) -> dict:
        raise NotImplementedError

    @staticmethod
    def verificar_token(storage_key: str, expira: int, firma: str) -> bool:
        mensaje = f"{storage_key}.{expira}".encode("utf-8")
        esperada = hmac.new(_secreto_firmas(), mensaje, hashlib.sha256).hexdigest()
        vigente = int(time.time()) <= int(expira)
        return vigente and hmac.compare_digest(esperada, firma)


class AlmacenamientoLocalPrivado(RepositorioEvidencias):
    """Bucket privado en disco (gitignored). Nada se sirve como estatico."""

    def guardar(self, sha256: str, extension: str, contenido: bytes) -> str:
        clave = f"{sha256}{extension}"
        destino = _directorio_base() / clave
        if not destino.exists():
            destino.write_bytes(contenido)
        return clave

    def abrir(self, storage_key: str) -> bytes:
        if "/" in storage_key or "\\" in storage_key or ".." in storage_key:
            raise ErrorEvidencia("Clave de evidencia invalida.", 400)
        ruta = _directorio_base() / storage_key
        if not ruta.exists():
            raise ErrorEvidencia("La evidencia no existe.", 404)
        return ruta.read_bytes()

    def firmar_acceso(self, storage_key: str, segundos: int = 300) -> dict:
        expira = int(time.time()) + max(60, min(segundos, 3600))
        mensaje = f"{storage_key}.{expira}".encode("utf-8")
        firma = hmac.new(_secreto_firmas(), mensaje, hashlib.sha256).hexdigest()
        return {"storage_key": storage_key, "expira": expira, "firma": firma}


class AlmacenamientoSupabase(RepositorioEvidencias):
    """Adaptador Supabase Storage (misma interfaz, bucket privado).

    Requiere EVIDENCIAS_BACKEND=supabase, SUPABASE_URL,
    SUPABASE_SERVICE_KEY y SUPABASE_BUCKET. Sin esas variables responde
    501 en vez de degradar a un almacenamiento inseguro.
    """

    def __init__(self) -> None:
        self.url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_KEY") or ""
        self.bucket = os.getenv("SUPABASE_BUCKET") or "evidencias"
        if not (self.url and self.key):
            raise ErrorEvidencia(
                "Supabase Storage no configurado (SUPABASE_URL / SUPABASE_SERVICE_KEY).",
                501,
            )

    def _cabeceras(self, content_type: str = "application/json") -> dict:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": content_type,
        }

    def guardar(self, sha256: str, extension: str, contenido: bytes) -> str:
        clave = f"{sha256}{extension}"
        destino = f"{self.url}/storage/v1/object/{self.bucket}/{clave}"
        peticion = urllib.request.Request(
            destino, data=contenido, headers=self._cabeceras("application/octet-stream"),
            method="POST",
        )
        try:
            with urllib.request.urlopen(peticion, timeout=30):
                pass
        except Exception as error:
            raise ErrorEvidencia(f"No se pudo guardar en Supabase: {error}", 502) from error
        return f"supabase:{self.bucket}/{clave}"

    def abrir(self, storage_key: str) -> bytes:
        ruta = storage_key.split(f"{self.bucket}/", 1)[-1]
        destino = f"{self.url}/storage/v1/object/{self.bucket}/{ruta}"
        peticion = urllib.request.Request(destino, headers=self._cabeceras())
        try:
            with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                return respuesta.read()
        except Exception as error:
            raise ErrorEvidencia(f"No se pudo leer de Supabase: {error}", 502) from error

    def firmar_acceso(self, storage_key: str, segundos: int = 300) -> dict:
        ruta = storage_key.split(f"{self.bucket}/", 1)[-1]
        destino = f"{self.url}/storage/v1/object/sign/{self.bucket}/{ruta}"
        cuerpo = f'{{"expiresIn": {max(60, min(segundos, 3600))}}}'.encode("utf-8")
        peticion = urllib.request.Request(
            destino, data=cuerpo, headers=self._cabeceras(), method="POST"
        )
        try:
            with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                import json

                datos = json.loads(respuesta.read().decode("utf-8"))
                return {"signed_url": urllib.parse.urljoin(self.url + "/", datos["signedURL"])}
        except Exception as error:
            raise ErrorEvidencia(f"No se pudo firmar en Supabase: {error}", 502) from error


def repositorio_evidencias() -> RepositorioEvidencias:
    if (os.getenv("EVIDENCIAS_BACKEND") or "local").lower() == "supabase":
        return AlmacenamientoSupabase()
    return AlmacenamientoLocalPrivado()
