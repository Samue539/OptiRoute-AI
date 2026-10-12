"""Implementacion PostgreSQL de los repositorios de acceso (Fase 3).

Reemplaza el almacenamiento provisional en archivos JSON conservando
exactamente los mismos contratos (``contratos.py``): cuentas, sesiones y
auditoria. Las tablas las crea ``database/scripts/006_seguridad_acceso.sql``.

Decisiones de seguridad:

* Todo el SQL usa consultas parametrizadas (``%s``): nunca se interpolan
  valores del usuario en la cadena SQL.
* Los hashes de contrasena se copian y se leen tal cual; el repositorio
  nunca los reinterpreta. El formato ``pbkdf2_sha256$...`` sigue siendo
  verificable por :mod:`backend.app.core.seguridad`.
* Los tokens se guardan unicamente como SHA-256 (``token_hash``).
* Cada operacion abre su propia conexion (mismo criterio que el resto de
  servicios del proyecto) y cierra siempre; los errores hacen rollback.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Callable

from backend.app.core.database import obtener_conexion
from backend.app.repositories.contratos import (
    RepositorioAuditoria,
    RepositorioCuentas,
    RepositorioSesiones,
)
from backend.app.repositories.errores import (
    ErrorCuentaDuplicada,
    ErrorNoEncontrado,
    ErrorTablaInexistente,
)
from backend.app.repositories.modelos import Cuenta, Sesion, ahora_utc

TABLA_CUENTAS = "seguridad.cuentas_acceso"
TABLA_SESIONES = "seguridad.sesiones_acceso"
TABLA_AUDITORIA = "seguridad.auditoria_acceso"
TABLA_MIGRACIONES = "seguridad.migraciones_acceso"

COLUMNAS_CUENTA = (
    "id_usuario",
    "nombres",
    "apellidos",
    "correo",
    "password_hash",
    "rol",
    "activo",
    "es_propietario",
    "id_conductor",
    "creado_en",
    "actualizado_en",
    "ultimo_acceso",
)

COLUMNAS_SESION = (
    "token_hash",
    "id_usuario",
    "creado_en",
    "expira_en",
    "revocado",
    "revocado_en",
    "agente_hash",
    "ip_prefijo",
)

_MARCAS_DUPLICADO = (
    "duplicate key value violates unique constraint",
    "unique constraint failed",
    "llave duplicada",
)


def _a_utc(valor: datetime | None) -> datetime | None:
    """Normaliza valores TIMESTAMPTZ a datetimes conscientes en UTC.

    psycopg devuelve datetimes con zona horaria; pg8000 los devuelve
    ingenuos. Sin esta normalizacion las sesiones caducarian de forma
    distinta segun el driver utilizado.
    """

    if valor is None:
        return None
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            return valor.replace(tzinfo=timezone.utc)
        return valor.astimezone(timezone.utc)
    return valor


def _como_dict(valor) -> dict:
    """Convierte una columna JSONB en diccionario (dict o texto)."""

    if valor is None:
        return {}
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, (bytes, bytearray)):
        valor = valor.decode("utf-8")
    if isinstance(valor, str):
        if not valor.strip():
            return {}
        try:
            cargado = json.loads(valor)
        except json.JSONDecodeError:
            return {}
        return cargado if isinstance(cargado, dict) else {}
    return {}


def _fila_cuenta(fila) -> Cuenta:
    valores = dict(zip(COLUMNAS_CUENTA, fila))
    return Cuenta(
        id_usuario=int(valores["id_usuario"]),
        nombres=valores["nombres"],
        apellidos=valores["apellidos"],
        correo=valores["correo"],
        password_hash=valores["password_hash"],
        rol=valores["rol"],
        activo=bool(valores["activo"]),
        id_conductor=valores["id_conductor"],
        es_propietario=bool(valores["es_propietario"]),
        creado_en=_a_utc(valores["creado_en"]) or ahora_utc(),
        actualizado_en=_a_utc(valores["actualizado_en"]) or ahora_utc(),
        ultimo_acceso=_a_utc(valores["ultimo_acceso"]),
    )


def _fila_sesion(fila) -> Sesion:
    valores = dict(zip(COLUMNAS_SESION, fila))
    return Sesion(
        token_hash=valores["token_hash"],
        id_usuario=int(valores["id_usuario"]),
        creado_en=_a_utc(valores["creado_en"]) or ahora_utc(),
        expira_en=_a_utc(valores["expira_en"]) or ahora_utc(),
        revocado=bool(valores["revocado"]),
        revocado_en=_a_utc(valores["revocado_en"]),
        agente_hash=valores["agente_hash"],
        ip_prefijo=valores["ip_prefijo"],
    )


def _es_duplicado(error: Exception) -> bool:
    mensaje = str(error).lower()
    return any(marca in mensaje for marca in _MARCAS_DUPLICADO)


def _es_tabla_inexistente(error: Exception) -> bool:
    mensaje = str(error).lower()
    return "does not exist" in mensaje or "no existe la relación" in mensaje


class _RepositorioPostgres:
    """Base comun: conexion por operacion y manejo uniforme de errores."""

    def __init__(self, conector: Callable[[], object] | None = None) -> None:
        self._conector = conector or obtener_conexion

    def _consultar(self, funcion):
        """Ejecuta ``funcion(cursor)`` y devuelve sus filas.

        Abre la conexion, hace commit si hubo escritura, rollback ante
        cualquier error y cierra siempre.
        """

        conexion = self._conector()
        try:
            with conexion.cursor() as cursor:
                filas = funcion(cursor)
            conexion.commit()
            return filas
        except Exception:
            try:
                conexion.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conexion.close()
            except Exception:
                pass


class RepositorioCuentasPostgres(_RepositorioPostgres, RepositorioCuentas):
    """Cuentas de acceso persistidas en ``seguridad.cuentas_acceso``."""

    _INSERTAR = f"""
        INSERT INTO {TABLA_CUENTAS} (
            id_usuario,
            nombres,
            apellidos,
            correo,
            password_hash,
            rol,
            activo,
            es_propietario,
            id_conductor,
            creado_en,
            actualizado_en,
            ultimo_acceso,
            origen
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_usuario) DO NOTHING
        RETURNING {', '.join(COLUMNAS_CUENTA)}
    """

    _INSERTAR_SIN_ID = f"""
        INSERT INTO {TABLA_CUENTAS} (
            nombres,
            apellidos,
            correo,
            password_hash,
            rol,
            activo,
            es_propietario,
            id_conductor,
            creado_en,
            actualizado_en,
            ultimo_acceso,
            origen
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING {', '.join(COLUMNAS_CUENTA)}
    """

    _ACTUALIZAR = f"""
        UPDATE {TABLA_CUENTAS}
        SET nombres = %s,
            apellidos = %s,
            correo = %s,
            password_hash = %s,
            rol = %s,
            activo = %s,
            es_propietario = %s,
            id_conductor = %s,
            actualizado_en = %s,
            ultimo_acceso = %s
        WHERE id_usuario = %s
        RETURNING {', '.join(COLUMNAS_CUENTA)}
    """

    @staticmethod
    def _parametros(cuenta: Cuenta) -> tuple:
        return (
            cuenta.id_usuario,
            cuenta.nombres,
            cuenta.apellidos,
            cuenta.correo,
            cuenta.password_hash,
            cuenta.rol,
            cuenta.activo,
            cuenta.es_propietario,
            cuenta.id_conductor,
            cuenta.creado_en,
            cuenta.actualizado_en,
            cuenta.ultimo_acceso,
            "JSON" if cuenta.id_usuario else "API",
        )

    def _insertar(self, cuenta: Cuenta):
        def ejecutar(cursor):
            if cuenta.id_usuario:
                cursor.execute(self._INSERTAR, self._parametros(cuenta))
            else:
                cursor.execute(
                    self._INSERTAR_SIN_ID,
                    self._parametros(cuenta)[1:],
                )
            return cursor.fetchone()

        try:
            return self._consultar(ejecutar)
        except Exception as error:
            if _es_tabla_inexistente(error):
                raise ErrorTablaInexistente(
                    "La tabla seguridad.cuentas_acceso no existe. Aplique "
                    "database/scripts/006_seguridad_acceso.sql."
                ) from error
            if _es_duplicado(error):
                raise ErrorCuentaDuplicada(
                    "Ya existe una cuenta con ese correo."
                ) from error
            raise

    def crear(self, cuenta: Cuenta) -> Cuenta:
        if self.obtener_por_correo(cuenta.correo) is not None:
            raise ErrorCuentaDuplicada("Ya existe una cuenta con ese correo.")
        fila = self._insertar(cuenta)
        if fila is None:
            # Identificador ya ocupado (por ejemplo, tras una migracion):
            # no se sobreescribe la cuenta existente.
            raise ErrorCuentaDuplicada(
                "Ya existe una cuenta con ese identificador."
            )
        return _fila_cuenta(fila)

    def obtener(self, id_usuario: int) -> Cuenta | None:
        def ejecutar(cursor):
            cursor.execute(
                f"SELECT {', '.join(COLUMNAS_CUENTA)} FROM {TABLA_CUENTAS} "
                "WHERE id_usuario = %s",
                (id_usuario,),
            )
            return cursor.fetchone()

        return self._envolver(self._consultar(ejecutar), _fila_cuenta)

    def obtener_por_correo(self, correo: str) -> Cuenta | None:
        objetivo = (correo or "").strip().lower()

        def ejecutar(cursor):
            cursor.execute(
                f"SELECT {', '.join(COLUMNAS_CUENTA)} FROM {TABLA_CUENTAS} "
                "WHERE LOWER(correo) = %s",
                (objetivo,),
            )
            return cursor.fetchone()

        return self._envolver(self._consultar(ejecutar), _fila_cuenta)

    def listar(self) -> list[Cuenta]:
        def ejecutar(cursor):
            cursor.execute(
                f"SELECT {', '.join(COLUMNAS_CUENTA)} FROM {TABLA_CUENTAS} "
                "ORDER BY id_usuario"
            )
            return cursor.fetchall()

        filas = self._consultar(ejecutar) or []
        return [_fila_cuenta(fila) for fila in filas]

    def actualizar(self, cuenta: Cuenta) -> Cuenta:
        parametros = (
            cuenta.nombres,
            cuenta.apellidos,
            cuenta.correo,
            cuenta.password_hash,
            cuenta.rol,
            cuenta.activo,
            cuenta.es_propietario,
            cuenta.id_conductor,
            cuenta.actualizado_en,
            cuenta.ultimo_acceso,
            cuenta.id_usuario,
        )

        def ejecutar(cursor):
            cursor.execute(self._ACTUALIZAR, parametros)
            return cursor.fetchone()

        fila = self._consultar(ejecutar)
        if fila is None:
            raise ErrorNoEncontrado(
                f"La cuenta {cuenta.id_usuario} ya no existe."
            )
        return _fila_cuenta(fila)

    def existe_rol(self, rol: str) -> bool:
        objetivo = (rol or "").upper()

        def ejecutar(cursor):
            cursor.execute(
                f"SELECT 1 FROM {TABLA_CUENTAS} WHERE UPPER(rol) = %s LIMIT 1",
                (objetivo,),
            )
            return cursor.fetchone()

        return self._consultar(ejecutar) is not None

    @staticmethod
    def _envolver(fila, convertir):
        return convertir(fila) if fila else None


class RepositorioSesionesPostgres(_RepositorioPostgres, RepositorioSesiones):
    """Sesiones persistidas en ``seguridad.sesiones_acceso``."""

    _CREAR = f"""
        INSERT INTO {TABLA_SESIONES} (
            token_hash,
            id_usuario,
            creado_en,
            expira_en,
            revocado,
            revocado_en,
            agente_hash,
            ip_prefijo
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (token_hash) DO UPDATE
        SET expira_en = EXCLUDED.expira_en,
            revocado = FALSE,
            revocado_en = NULL
        RETURNING {', '.join(COLUMNAS_SESION)}
    """

    _ACTUALIZAR = f"""
        UPDATE {TABLA_SESIONES}
        SET expira_en = %s,
            revocado = %s,
            revocado_en = %s
        WHERE token_hash = %s
        RETURNING {', '.join(COLUMNAS_SESION)}
    """

    @staticmethod
    def _parametros(sesion: Sesion) -> tuple:
        return (
            sesion.token_hash,
            sesion.id_usuario,
            sesion.creado_en,
            sesion.expira_en,
            sesion.revocado,
            sesion.revocado_en,
            sesion.agente_hash,
            sesion.ip_prefijo,
        )

    def crear(self, sesion: Sesion) -> Sesion:
        def ejecutar(cursor):
            cursor.execute(self._CREAR, self._parametros(sesion))
            return cursor.fetchone()

        fila = self._consultar(ejecutar)
        if fila is None:  # pragma: no cover - el RETURNING siempre devuelve fila
            return sesion
        return _fila_sesion(fila)

    def obtener(self, token_hash: str) -> Sesion | None:
        def ejecutar(cursor):
            cursor.execute(
                f"SELECT {', '.join(COLUMNAS_SESION)} FROM {TABLA_SESIONES} "
                "WHERE token_hash = %s",
                (token_hash,),
            )
            return cursor.fetchone()

        fila = self._consultar(ejecutar)
        return _fila_sesion(fila) if fila else None

    def actualizar(self, sesion: Sesion) -> Sesion:
        parametros = (
            sesion.expira_en,
            sesion.revocado,
            sesion.revocado_en,
            sesion.token_hash,
        )

        def ejecutar(cursor):
            cursor.execute(self._ACTUALIZAR, parametros)
            return cursor.fetchone()

        fila = self._consultar(ejecutar)
        if fila is None:
            raise ErrorNoEncontrado("La sesion ya no existe.")
        return _fila_sesion(fila)

    def revocar(self, token_hash: str) -> bool:
        def ejecutar(cursor):
            cursor.execute(
                f"UPDATE {TABLA_SESIONES} SET revocado = TRUE, revocado_en = %s "
                "WHERE token_hash = %s AND revocado = FALSE "
                f"RETURNING {', '.join(COLUMNAS_SESION)}",
                (ahora_utc(), token_hash),
            )
            return cursor.fetchone()

        return self._consultar(ejecutar) is not None

    def revocar_por_usuario(self, id_usuario: int) -> int:
        def ejecutar(cursor):
            cursor.execute(
                f"UPDATE {TABLA_SESIONES} SET revocado = TRUE, revocado_en = %s "
                "WHERE id_usuario = %s AND revocado = FALSE RETURNING token_hash",
                (ahora_utc(), id_usuario),
            )
            return cursor.fetchall()

        return len(self._consultar(ejecutar) or [])

    def limpiar_expiradas(self) -> int:
        def ejecutar(cursor):
            cursor.execute(
                f"DELETE FROM {TABLA_SESIONES} "
                "WHERE revocado = TRUE OR expira_en <= %s RETURNING token_hash",
                (ahora_utc(),),
            )
            return cursor.fetchall()

        return len(self._consultar(ejecutar) or [])

    def contar_activas(self) -> int:
        def ejecutar(cursor):
            cursor.execute(
                f"SELECT COUNT(*) FROM {TABLA_SESIONES} "
                "WHERE revocado = FALSE AND expira_en > %s",
                (ahora_utc(),),
            )
            return cursor.fetchone()

        fila = self._consultar(ejecutar)
        return int(fila[0]) if fila else 0


class RepositorioAuditoriaPostgres(_RepositorioPostgres, RepositorioAuditoria):
    """Bitacora de eventos de seguridad en ``seguridad.auditoria_acceso``."""

    _REGISTRAR = f"""
        INSERT INTO {TABLA_AUDITORIA} (accion, actor, actor_id, detalle)
        VALUES (%s, %s, %s, %s::jsonb)
        RETURNING accion, actor, actor_id, detalle
    """

    _LISTAR = f"""
        SELECT accion, actor, actor_id, detalle
        FROM {TABLA_AUDITORIA}
        ORDER BY id_auditoria DESC
        LIMIT %s
    """

    def registrar(self, evento: dict) -> dict:
        registro = dict(evento)
        registro.setdefault("creado_en", ahora_utc().isoformat())
        accion = str(registro.pop("accion", "evento"))
        actor = registro.pop("actor", None)
        actor_id = registro.pop("actor_id", None)
        if actor_id is not None:
            try:
                actor_id = int(actor_id)
            except (TypeError, ValueError):
                actor_id = None
        detalle = json.dumps(registro, ensure_ascii=False, default=str)

        def ejecutar(cursor):
            cursor.execute(self._REGISTRAR, (accion, actor, actor_id, detalle))
            return cursor.fetchone()

        fila = self._consultar(ejecutar)
        if fila is None:  # pragma: no cover - el RETURNING siempre devuelve fila
            return {"accion": accion, **registro}
        accion_guardada, actor_guardado, actor_id_guardado, detalle_guardado = fila
        return {
            "accion": accion_guardada,
            "actor": actor_guardado,
            "actor_id": actor_id_guardado,
            **_como_dict(detalle_guardado),
        }

    def listar(self, limite: int = 100) -> list[dict]:
        def ejecutar(cursor):
            cursor.execute(self._LISTAR, (max(int(limite), 1),))
            return cursor.fetchall()

        eventos: list[dict] = []
        for accion, actor, actor_id, detalle in self._consultar(ejecutar) or []:
            eventos.append(
                {
                    "accion": accion,
                    "actor": actor,
                    "actor_id": actor_id,
                    **_como_dict(detalle),
                }
            )
        return eventos


def verificar_esquema(conector: Callable[[], object] | None = None) -> dict:
    """Comprueba la existencia de las tablas de acceso en PostgreSQL.

    No lanza excepciones: devuelve un dict utilizable por el diagnostico.
    """

    tablas = (TABLA_CUENTAS, TABLA_SESIONES, TABLA_AUDITORIA, TABLA_MIGRACIONES)
    try:
        conexion = (conector or obtener_conexion)()
    except Exception as error:  # base de datos inaccesible
        return {
            "conectado": False,
            "tablas": {tabla: False for tabla in tablas},
            "detalle": f"{type(error).__name__}",
        }
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT to_regclass(%s) IS NOT NULL",
                (TABLA_CUENTAS,),
            )
            fila = cursor.fetchone()
        conexion.commit()
        presentes = {TABLA_CUENTAS: bool(fila and fila[0])}
        with conexion.cursor() as cursor:
            for tabla in tablas[1:]:
                cursor.execute("SELECT to_regclass(%s) IS NOT NULL", (tabla,))
                resultado = cursor.fetchone()
                presentes[tabla] = bool(resultado and resultado[0])
        conexion.commit()
        return {"conectado": True, "tablas": presentes}
    except Exception as error:
        return {
            "conectado": False,
            "tablas": {tabla: False for tabla in tablas},
            "detalle": f"{type(error).__name__}",
        }
    finally:
        try:
            conexion.close()
        except Exception:
            pass


def alinear_secuencias(conector: Callable[[], object] | None = None) -> None:
    """Ajusta las secuencias tras migrar identificadores explicitos.

    Sin este ajuste, la insercion de cuentas nuevas chocaria con los
    identificadores migrados desde el almacenamiento JSON.
    """

    consulta = """
        SELECT setval(
            pg_get_serial_sequence(%s, 'id_usuario'),
            GREATEST(
                (SELECT COALESCE(MAX(id_usuario), 0) FROM seguridad.cuentas_acceso),
                1
            ),
            (
                SELECT COALESCE(MAX(id_usuario), 0) > 0
                FROM seguridad.cuentas_acceso
            )
        )
    """

    def ejecutar(cursor):
        cursor.execute(consulta, (TABLA_CUENTAS,))
        return cursor.fetchone()

    RepositorioCuentasPostgres(conector=conector)._consultar(ejecutar)


__all__ = [
    "RepositorioAuditoriaPostgres",
    "RepositorioCuentasPostgres",
    "RepositorioSesionesPostgres",
    "alinear_secuencias",
    "verificar_esquema",
]
