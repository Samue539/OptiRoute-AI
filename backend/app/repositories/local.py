"""Implementacion local persistente de los repositorios de acceso.

ADVERTENCIA (provisional): este backend guarda cuentas, sesiones y auditoria
en archivos JSON dentro de ``backend/data/seguridad`` (configurable con la
variable ``OPTIROUTE_AUTH_DATA_DIR``). Se usa unicamente para desarrollo y
pruebas y NO debe considerarse el almacenamiento definitivo. La etapa
siguiente reemplazara esta implementacion por Supabase detras de las mismas
interfaces de ``contratos.py``.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from backend.app.repositories.contratos import (
    RepositorioAuditoria,
    RepositorioCuentas,
    RepositorioSesiones,
)
from backend.app.repositories.errores import ErrorCuentaDuplicada
from backend.app.repositories.modelos import Cuenta, Sesion, ahora_utc

# Candados por archivo para evitar escrituras concurrentes corruptas cuando
# uvicorn ejecuta varios hilos en el mismo proceso.
_CANDADOS: dict[str, threading.Lock] = {}
_CANDADOS_GLOBAL = threading.Lock()


def directorio_datos() -> Path:
    """Directorio raiz del almacenamiento provisional."""

    predeterminado = Path(__file__).resolve().parents[2] / "data" / "seguridad"
    return Path(os.getenv("OPTIROUTE_AUTH_DATA_DIR", str(predeterminado)))


def _candado(ruta: Path) -> threading.Lock:
    clave = str(ruta)
    with _CANDADOS_GLOBAL:
        if clave not in _CANDADOS:
            _CANDADOS[clave] = threading.Lock()
        return _CANDADOS[clave]


class _RepositorioJson:
    """Base comun para leer y escribir archivos JSON de forma atomica."""

    nombre_archivo = "datos.json"

    def __init__(self, directorio: str | Path | None = None) -> None:
        self.directorio = Path(directorio) if directorio else directorio_datos()
        self.ruta = self.directorio / self.nombre_archivo

    def _leer(self) -> dict:
        if not self.ruta.exists():
            return {}
        with self.ruta.open("r", encoding="utf-8") as archivo:
            contenido = archivo.read().strip()
        if not contenido:
            return {}
        return json.loads(contenido)

    def _escribir(self, datos: dict) -> None:
        self.directorio.mkdir(parents=True, exist_ok=True)
        temporal = self.ruta.with_suffix(self.ruta.suffix + ".tmp")
        with temporal.open("w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, self.ruta)


class RepositorioCuentasLocal(_RepositorioJson, RepositorioCuentas):
    nombre_archivo = "cuentas.json"

    def _leer_cuentas(self, datos: dict) -> list[Cuenta]:
        return [Cuenta.from_dict(item) for item in datos.get("cuentas", [])]

    def crear(self, cuenta: Cuenta) -> Cuenta:
        with _candado(self.ruta):
            datos = self._leer()
            cuentas = self._leer_cuentas(datos)
            objetivo = (cuenta.correo or "").strip().lower()
            for existente in cuentas:
                # Unicidad garantizada dentro del candado: sin esta revision
                # dos altas simultaneas con el mismo correo se duplicarian.
                if existente.correo.strip().lower() == objetivo:
                    raise ErrorCuentaDuplicada(
                        "Ya existe una cuenta con ese correo."
                    )
                if existente.id_usuario == cuenta.id_usuario:
                    raise ErrorCuentaDuplicada(
                        "Ya existe una cuenta con ese identificador."
                    )
            siguiente = int(datos.get("siguiente_id", 1))
            cuenta.id_usuario = siguiente
            cuentas.append(cuenta)
            datos["cuentas"] = [item.to_dict() for item in cuentas]
            datos["siguiente_id"] = siguiente + 1
            self._escribir(datos)
            return cuenta

    def obtener(self, id_usuario: int) -> Cuenta | None:
        for cuenta in self._leer_cuentas(self._leer()):
            if cuenta.id_usuario == id_usuario:
                return cuenta
        return None

    def obtener_por_correo(self, correo: str) -> Cuenta | None:
        objetivo = (correo or "").strip().lower()
        for cuenta in self._leer_cuentas(self._leer()):
            if cuenta.correo.lower() == objetivo:
                return cuenta
        return None

    def listar(self) -> list[Cuenta]:
        return sorted(
            self._leer_cuentas(self._leer()),
            key=lambda cuenta: cuenta.id_usuario,
        )

    def actualizar(self, cuenta: Cuenta) -> Cuenta:
        with _candado(self.ruta):
            datos = self._leer()
            cuentas = self._leer_cuentas(datos)
            cuenta.actualizado_en = ahora_utc()
            for indice, existente in enumerate(cuentas):
                if existente.id_usuario == cuenta.id_usuario:
                    cuentas[indice] = cuenta
                    break
            datos["cuentas"] = [item.to_dict() for item in cuentas]
            self._escribir(datos)
            return cuenta

    def existe_rol(self, rol: str) -> bool:
        objetivo = (rol or "").upper()
        return any(cuenta.rol == objetivo for cuenta in self.listar())


class RepositorioSesionesLocal(_RepositorioJson, RepositorioSesiones):
    nombre_archivo = "sesiones.json"

    def _leer_sesiones(self, datos: dict) -> list[Sesion]:
        return [Sesion.from_dict(item) for item in datos.get("sesiones", [])]

    def _guardar(self, sesiones: list[Sesion]) -> None:
        self._escribir({"sesiones": [item.to_dict() for item in sesiones]})

    def crear(self, sesion: Sesion) -> Sesion:
        with _candado(self.ruta):
            datos = self._leer()
            sesiones = self._leer_sesiones(datos)
            sesiones.append(sesion)
            self._guardar(sesiones)
            return sesion

    def obtener(self, token_hash: str) -> Sesion | None:
        for sesion in self._leer_sesiones(self._leer()):
            if sesion.token_hash == token_hash:
                return sesion
        return None

    def actualizar(self, sesion: Sesion) -> Sesion:
        with _candado(self.ruta):
            sesiones = self._leer_sesiones(self._leer())
            for indice, existente in enumerate(sesiones):
                if existente.token_hash == sesion.token_hash:
                    sesiones[indice] = sesion
                    break
            self._guardar(sesiones)
            return sesion

    def revocar(self, token_hash: str) -> bool:
        with _candado(self.ruta):
            sesiones = self._leer_sesiones(self._leer())
            encontrada = False
            for sesion in sesiones:
                if sesion.token_hash == token_hash and not sesion.revocado:
                    sesion.revocado = True
                    sesion.revocado_en = ahora_utc()
                    encontrada = True
            if encontrada:
                self._guardar(sesiones)
            return encontrada

    def revocar_por_usuario(self, id_usuario: int) -> int:
        with _candado(self.ruta):
            sesiones = self._leer_sesiones(self._leer())
            revocadas = 0
            for sesion in sesiones:
                if sesion.id_usuario == id_usuario and not sesion.revocado:
                    sesion.revocado = True
                    sesion.revocado_en = ahora_utc()
                    revocadas += 1
            if revocadas:
                self._guardar(sesiones)
            return revocadas

    def limpiar_expiradas(self) -> int:
        with _candado(self.ruta):
            sesiones = self._leer_sesiones(self._leer())
            prescindibles = [
                sesion
                for sesion in sesiones
                if sesion.revocado or sesion.expira_en <= ahora_utc()
            ]
            if prescindibles:
                conservadas = [
                    sesion for sesion in sesiones if sesion not in prescindibles
                ]
                self._guardar(conservadas)
            return len(prescindibles)

    def contar_activas(self) -> int:
        momento = ahora_utc()
        return sum(
            1 for sesion in self._leer_sesiones(self._leer()) if sesion.esta_vigente(momento)
        )


class RepositorioAuditoriaLocal(RepositorioAuditoria):
    """Bitacora append-only en formato JSON Lines."""

    nombre_archivo = "auditoria.jsonl"

    def __init__(self, directorio: str | Path | None = None) -> None:
        self.directorio = Path(directorio) if directorio else directorio_datos()
        self.ruta = self.directorio / self.nombre_archivo

    def registrar(self, evento: dict) -> dict:
        registro = dict(evento)
        registro.setdefault("creado_en", ahora_utc().isoformat())
        with _candado(self.ruta):
            self.directorio.mkdir(parents=True, exist_ok=True)
            with self.ruta.open("a", encoding="utf-8") as archivo:
                archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
        return registro

    def listar(self, limite: int = 100) -> list[dict]:
        if not self.ruta.exists():
            return []
        with self.ruta.open("r", encoding="utf-8") as archivo:
            lineas = [linea.strip() for linea in archivo if linea.strip()]
        eventos: list[dict] = []
        for linea in lineas[-max(limite, 1):]:
            try:
                eventos.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
        eventos.reverse()
        return eventos
