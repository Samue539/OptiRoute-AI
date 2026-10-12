"""Paridad entre el catalogo de permisos del backend y el espejo del frontend.

``frontend/src/auth/permissions.ts`` es solo un espejo para decidir que
muestra la interfaz (la validacion real ocurre en el backend), pero si diverge
puede ocultar opciones validas o mostrar acciones que terminarian en 403.
Estas pruebas comparan ambos catalogos para detectar cualquier divergencia.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.app.core.permisos import MATRIZ_PERMISOS, Permiso, Rol

RAIZ = Path(__file__).resolve().parents[1]
RUTA_TS = RAIZ / "frontend" / "src" / "auth" / "permissions.ts"


def _leer_ts() -> str:
    assert RUTA_TS.exists(), f"No se encontro el espejo frontend: {RUTA_TS}"
    return RUTA_TS.read_text(encoding="utf-8")


def _permisos_de_tipo(texto: str) -> set[str]:
    bloque = re.search(r"export type Permission =(.*?);", texto, re.S)
    assert bloque, "No se encontro el tipo Permission en permissions.ts"
    return set(re.findall(r'"([a-z:_]+)"', bloque.group(1)))


def _lista_del_ts(texto: str, nombre: str) -> list[str]:
    coincidencia = re.search(rf"const {nombre}: Permission\[\] = \[(.*?)\]", texto, re.S)
    assert coincidencia, f"No se encontro la lista {nombre} en permissions.ts"
    return re.findall(r'"([a-z:_]+)"', coincidencia.group(1))


class TestParidadDeCatalogos:
    def test_mismos_perfiles(self):
        texto = _leer_ts()
        roles_ts = set(
            re.findall(r'\| "([A-Z]+)"', re.search(r"export type Role =(.*?);", texto, re.S).group(1))
        )
        roles_backend = {rol.value for rol in Rol}
        assert roles_ts == roles_backend

    def test_mismo_catalogo_de_permisos(self):
        texto = _leer_ts()
        permisos_ts = _permisos_de_tipo(texto)
        permisos_backend = {permiso.value for permiso in Permiso}
        faltan_en_ts = permisos_backend - permisos_ts
        sobran_en_ts = permisos_ts - permisos_backend
        assert not faltan_en_ts, f"Permisos del backend ausentes en el frontend: {sorted(faltan_en_ts)}"
        assert not sobran_en_ts, f"Permisos del frontend que no existen en el backend: {sorted(sobran_en_ts)}"

    @pytest.mark.parametrize("rol", ["OPERADOR", "ADMINISTRADOR", "DESARROLLADOR", "CONDUCTOR"])
    def test_matriz_por_perfil_identica(self, rol):
        texto = _leer_ts()
        # Nombre de la lista frontend por perfil (OPERADOR usa "OPERACION").
        nombres = {
            "OPERADOR": "OPERACION",
            "ADMINISTRADOR": "ADMINISTRADOR",
            "DESARROLLADOR": "DESARROLLADOR",
            "CONDUCTOR": "CONDUCTOR",
        }
        # Las listas se componen con spreads en orden: se resuelven acumulando.
        acumulado: dict[str, list[str]] = {}
        for nombre in ("OPERACION", "ADMINISTRADOR", "DESARROLLADOR", "CONDUCTOR"):
            clave = f"PERMISOS_{nombre}"
            bloque = re.search(rf"const {clave}: Permission\[\] = \[(.*?)\]", texto, re.S)
            assert bloque, f"Falta {clave} en el frontend"
            items: list[str] = []
            for linea in bloque.group(1).splitlines():
                linea = linea.strip().rstrip(",")
                if linea.startswith("..."):
                    items.extend(acumulado[linea[3:]])
                else:
                    items.extend(re.findall(r'"([a-z:_]+)"', linea))
            acumulado[clave] = items

        permisos_ts = set(acumulado[f"PERMISOS_{nombres[rol]}"])
        permisos_backend = {p.value for p in MATRIZ_PERMISOS[Rol(rol)]}
        assert permisos_ts == permisos_backend, (
            f"Divergencia en {rol}: solo frontend={sorted(permisos_ts - permisos_backend)}, "
            f"solo backend={sorted(permisos_backend - permisos_ts)}"
        )
