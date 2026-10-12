"""Fabrica de repositorios de acceso.

El backend de almacenamiento se selecciona con la variable de entorno
``OPTIROUTE_AUTH_STORAGE``:

* ``local`` (por defecto): archivos JSON en el directorio de datos
  provisional. Pensado para desarrollo y pruebas.
* ``postgres``: persistencia segura en PostgreSQL mediante
  ``database/scripts/006_seguridad_acceso.sql``. Opcion recomendada para
  produccion. Si las tablas no existen se lanza
  :class:`ErrorTablaInexistente` con instrucciones claras.
* ``supabase``: reservado. Todavia no hay conector implementado; se lanza un
  error explicito para no simular que Supabase esta conectado.

El paso de ``local`` a ``postgres`` es progresivo y reversible: con
``OPTIROUTE_AUTH_STORAGE=local`` se vuelve al almacenamiento anterior sin
perder datos (la migracion no borra los archivos JSON).
"""

from __future__ import annotations

import os

from backend.app.repositories.contratos import (
    RepositorioAuditoria,
    RepositorioCuentas,
    RepositorioSesiones,
)
from backend.app.repositories.errores import ErrorTablaInexistente
from backend.app.repositories.local import (
    RepositorioAuditoriaLocal,
    RepositorioCuentasLocal,
    RepositorioSesionesLocal,
)
from backend.app.repositories.postgres import (
    RepositorioAuditoriaPostgres,
    RepositorioCuentasPostgres,
    RepositorioSesionesPostgres,
    verificar_esquema,
)

ALMACENAMIENTO_LOCAL = "local"
ALMACENAMIENTO_POSTGRES = "postgres"
ALMACENAMIENTO_SUPABASE = "supabase"

_ALIAS_POSTGRES = {"postgres", "postgresql", "bd", "base_datos"}
_ALIAS_LOCAL = {"local", "json", "archivos", "ficheros"}


def backend_almacenamiento() -> str:
    valor = os.getenv(
        "OPTIROUTE_AUTH_STORAGE", ALMACENAMIENTO_LOCAL
    ).strip().lower()
    if valor in _ALIAS_POSTGRES:
        return ALMACENAMIENTO_POSTGRES
    if valor in _ALIAS_LOCAL:
        return ALMACENAMIENTO_LOCAL
    return valor


def _validar_backend() -> str:
    backend = backend_almacenamiento()
    if backend == ALMACENAMIENTO_SUPABASE:
        raise NotImplementedError(
            "El conector de Supabase para autenticacion todavia no esta "
            "implementado. Use OPTIROUTE_AUTH_STORAGE=local o "
            "OPTIROUTE_AUTH_STORAGE=postgres."
        )
    if backend not in (ALMACENAMIENTO_LOCAL, ALMACENAMIENTO_POSTGRES):
        raise ValueError(
            f"Backend de autenticacion no soportado: {backend!r}. "
            "Use 'local' o 'postgres'."
        )
    return backend


def _usar_postgres() -> bool:
    """Indica si el backend activo es PostgreSQL (con fallback opcional)."""

    if _validar_backend() != ALMACENAMIENTO_POSTGRES:
        return False
    if os.getenv("OPTIROUTE_AUTH_FALLBACK_LOCAL", "").strip().lower() in {
        "1",
        "true",
        "si",
        "yes",
    }:
        # Sin base de datos disponible se degrada al almacenamiento local para
        # no impedir el arranque en desarrollo. Debe activarse de forma
        # explicita: en silencio podria divergir los datos.
        esquema = verificar_esquema()
        if not (esquema.get("conectado") and esquema["tablas"].get(
            "seguridad.cuentas_acceso"
        )):
            return False
    return True


def repositorio_cuentas() -> RepositorioCuentas:
    if _usar_postgres():
        return RepositorioCuentasPostgres()
    return RepositorioCuentasLocal()


def repositorio_sesiones() -> RepositorioSesiones:
    if _usar_postgres():
        return RepositorioSesionesPostgres()
    return RepositorioSesionesLocal()


def repositorio_auditoria() -> RepositorioAuditoria:
    if _usar_postgres():
        return RepositorioAuditoriaPostgres()
    return RepositorioAuditoriaLocal()


def tablas_acceso_listas() -> bool:
    """True si las tablas de acceso existen y PostgreSQL responde."""

    esquema = verificar_esquema()
    return bool(
        esquema.get("conectado")
        and all(esquema.get("tablas", {}).values())
    )


def estado_almacenamiento() -> dict:
    """Descripcion honesta del almacenamiento usado (para diagnostico)."""

    backend = backend_almacenamiento()
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    provisional = backend == ALMACENAMIENTO_LOCAL
    esquema: dict = {}
    if backend == ALMACENAMIENTO_POSTGRES:
        esquema = verificar_esquema()
        if not esquema.get("conectado"):
            provisional = True
    return {
        "backend": backend,
        "provisional": provisional,
        # No exponer rutas absolutas del equipo en el diagnostico HTTP.
        "directorio_datos": "local_provisional" if provisional else "postgresql",
        "supabase_configurado": bool(supabase_url),
        "supabase_conectado": False,
        "tablas_acceso": esquema.get("tablas"),
        "migracion_requerida": bool(
            backend == ALMACENAMIENTO_POSTGRES and esquema.get("conectado")
            and not all(esquema.get("tablas", {}).values())
        ),
        "nota": (
            "El almacenamiento de cuentas es local y persistente, provisional "
            "para desarrollo y pruebas. Supabase se integrara en una etapa "
            "posterior; no esta conectado."
            if provisional
            else "Cuentas, sesiones y auditoria persistidas en PostgreSQL "
            "(seguridad.cuentas_acceso)."
        ),
    }


__all__ = [
    "ALMACENAMIENTO_LOCAL",
    "ALMACENAMIENTO_POSTGRES",
    "ALMACENAMIENTO_SUPABASE",
    "ErrorTablaInexistente",
    "backend_almacenamiento",
    "estado_almacenamiento",
    "repositorio_auditoria",
    "repositorio_cuentas",
    "repositorio_sesiones",
    "tablas_acceso_listas",
]
