"""Primitivas de seguridad: hashing de contrasenas y tokens de sesion.

Las contrasenas se almacenan con PBKDF2-HMAC-SHA256 (implementacion de la
biblioteca estandar de Python) con salt aleatorio por cuenta y un numero de
iteraciones configurable. Nunca se guarda la contrasena en texto plano.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets


ALGORITMO = "pbkdf2_sha256"
ITERACIONES_POR_DEFECTO = int(os.getenv("AUTH_PBKDF2_ITERACIONES", "210000"))
LONGITUD_SALT = 16
LONGITUD_CLAVE = 32


class ErrorPasswordDebil(ValueError):
    """La contrasena no cumple la politica minima de seguridad."""


def validar_password(password: str) -> None:
    """Valida la politica minima de contrasenas (no almacena nada)."""

    if not isinstance(password, str) or len(password) < 10:
        raise ErrorPasswordDebil(
            "La contrasena debe tener al menos 10 caracteres."
        )
    if password.strip() == "":
        raise ErrorPasswordDebil("La contrasena no puede estar vacia.")
    tiene_letra = any(caracter.isalpha() for caracter in password)
    tiene_digito = any(caracter.isdigit() for caracter in password)
    if not (tiene_letra and tiene_digito):
        raise ErrorPasswordDebil(
            "La contrasena debe combinar letras y numeros."
        )


def hashear_password(password: str) -> str:
    """Genera un hash PBKDF2 con formato autodescriptivo."""

    validar_password(password)
    salt = secrets.token_bytes(LONGITUD_SALT)
    derivada = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERACIONES_POR_DEFECTO,
        dklen=LONGITUD_CLAVE,
    )
    return (
        f"{ALGORITMO}${ITERACIONES_POR_DEFECTO}$"
        f"{salt.hex()}${derivada.hex()}"
    )


def verificar_password(password: str, hash_almacenado: str) -> bool:
    """Compara una contrasena con su hash en tiempo constante."""

    if not password or not hash_almacenado:
        return False
    try:
        algoritmo, iteraciones, salt_hex, hash_hex = hash_almacenado.split("$")
        if algoritmo != ALGORITMO:
            return False
        salt = bytes.fromhex(salt_hex)
        esperado = bytes.fromhex(hash_hex)
        derivada = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iteraciones),
            dklen=len(esperado),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derivada, esperado)


def generar_token() -> str:
    """Crea un token de sesion opaco y de alta entropia."""

    return secrets.token_urlsafe(48)


def hashear_token(token: str) -> str:
    """Devuelve el hash SHA-256 del token para almacenarlo sin exponerlo."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hashear_metadato(valor: str) -> str:
    """Hash SHA-256 de metadatos de sesion (User-Agent, similares).

    Nunca se guarda el valor original: Solo su hash, para poder detectar
    que una sesion se reutiliza desde otro navegador o cliente.
    """

    return hashlib.sha256((valor or "").strip().encode("utf-8")).hexdigest()
