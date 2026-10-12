"""Migracion de cuentas de acceso: JSON provisional -> PostgreSQL.

Reemplaza de forma progresiva y reversible el almacenamiento provisional
(``backend/data/seguridad/cuentas.json``) por las tablas que crea
``database/scripts/006_seguridad_acceso.sql``.

Modo de uso (desde la raiz del proyecto)::

    # 1. Verificar compatibilidad SIN escribir nada (modo por defecto)
    python -m backend.scripts.migrar_cuentas_json_a_postgres

    # 2. Respaldar los archivos JSON antes de migrar
    python -m backend.scripts.migrar_cuentas_json_a_postgres --aplicar --respaldar

    # 3. Solo sesiones, sin cuentas
    python -m backend.scripts.migrar_cuentas_json_a_postgres --sesiones-solo

Garantias:

* **Idempotente**: ejecutarla dos veces no duplica ni sobreescribe cuentas.
  Una cuenta ya migrada se omite; si su hash difiere del JSON solo se informa.
* **No destructiva**: jamas borra ni modifica los archivos JSON de origen.
  Los datos originales siguen intactos como respaldo natural.
* **Conservadora**: preserva ``id_usuario``, ``password_hash`` (compatible con
  ``verificar_password``), ``rol``, ``activo``, ``es_propietario`` e
  ``id_conductor``.
* **Verificable**: el modo por defecto comprueba compatibilidad y no escribe.
* **Reversible**: basta con volver a ``OPTIROUTE_AUTH_STORAGE=local``.

Codigos de salida: 0 correcto, 1 error tecnico, 2 conflictos detectados
(no se migro nada), 3 faltan las tablas (aplicar el script 006).
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from backend.app.core.database import obtener_conexion  # noqa: E402
from backend.app.core.permisos import Rol  # noqa: E402
from backend.app.core.seguridad import ALGORITMO  # noqa: E402
from backend.app.repositories.postgres import (  # noqa: E402
    TABLA_CUENTAS,
    TABLA_SESIONES,
    alinear_secuencias,
)

RAIZ = Path(__file__).resolve().parents[2]
DIRECTORIO_PREDETERMINADO = RAIZ / "backend" / "data" / "seguridad"

ROLES_VALIDOS = tuple(rol.value for rol in Rol)

_SQL_TABLAS_EXISTEN = """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'seguridad'
      AND table_name IN ('cuentas_acceso', 'sesiones_acceso', 'auditoria_acceso')
"""

_SQL_CUENTA_POR_ID = (
    f"SELECT id_usuario, correo, password_hash FROM {TABLA_CUENTAS} "
    "WHERE id_usuario = %s"
)

_SQL_CUENTA_POR_CORREO = (
    f"SELECT id_usuario, correo, password_hash FROM {TABLA_CUENTAS} "
    "WHERE LOWER(correo) = LOWER(%s)"
)

_SQL_INSERTAR_CUENTA = f"""
    INSERT INTO {TABLA_CUENTAS} (
        id_usuario, nombres, apellidos, correo, password_hash, rol, activo,
        es_propietario, id_conductor, creado_en, actualizado_en,
        ultimo_acceso, origen, migrado_en
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'JSON', %s)
    ON CONFLICT (id_usuario) DO NOTHING
"""

_SQL_INSERTAR_SESION = f"""
    INSERT INTO {TABLA_SESIONES} (
        token_hash, id_usuario, creado_en, expira_en, revocado, revocado_en,
        agente_hash, ip_prefijo
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (token_hash) DO NOTHING
"""


def _directorio_origen(explicito: str | None) -> Path:
    if explicito:
        return Path(explicito)
    variable = os.getenv("OPTIROUTE_AUTH_DATA_DIR")
    if variable:
        return Path(variable)
    return DIRECTORIO_PREDETERMINADO


def _leer_json(ruta: Path) -> dict | list:
    if not ruta.exists():
        return {}
    contenido = ruta.read_text(encoding="utf-8").strip()
    if not contenido:
        return {}
    return json.loads(contenido)


def _cuentas_json(directorio: Path) -> list[dict]:
    datos = _leer_json(directorio / "cuentas.json")
    if isinstance(datos, list):  # formato antiguo: lista directa
        return datos
    return list(datos.get("cuentas", []))


def _sesiones_json(directorio: Path) -> list[dict]:
    datos = _leer_json(directorio / "sesiones.json")
    if isinstance(datos, list):
        return datos
    return list(datos.get("sesiones", []))


def _hash_compatible(valor: str) -> bool:
    """El hash debe mantener el formato que sabe verificar el sistema."""

    if not isinstance(valor, str):
        return False
    partes = valor.split("$")
    return len(partes) == 4 and partes[0] == ALGORITMO


def _a_datetime(valor):
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    if isinstance(valor, str) and valor:
        try:
            leido = datetime.fromisoformat(valor)
        except ValueError:
            return None
        return leido if leido.tzinfo else leido.replace(tzinfo=timezone.utc)
    return None


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def validar_cuenta(datos: dict) -> list[str]:
    """Devuelve la lista de problemas de una cuenta del JSON."""

    problemas: list[str] = []
    for campo in ("id_usuario", "nombres", "apellidos", "correo", "password_hash"):
        if not datos.get(campo):
            problemas.append(f"falta '{campo}'")
    rol = str(datos.get("rol", "")).upper()
    if rol not in ROLES_VALIDOS:
        problemas.append(f"rol no soportado: {datos.get('rol')!r}")
    if not _hash_compatible(datos.get("password_hash")):
        problemas.append("password_hash no compatible con pbkdf2_sha256")
    activo = datos.get("activo", True)
    if not isinstance(activo, bool):
        problemas.append("'activo' no es booleano")
    return problemas


def respaldar_json(directorio: Path, destino: Path | None = None) -> Path:
    """Copia los archivos de origen a una carpeta de respaldo."""

    marca = _ahora().strftime("%Y%m%d-%H%M%S")
    carpeta = destino or (directorio / "respaldos" / f"migracion-{marca}")
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in ("cuentas.json", "sesiones.json", "auditoria.jsonl"):
        origen = directorio / nombre
        if origen.exists():
            shutil.copy2(origen, carpeta / nombre)
    return carpeta


def _tablas_existen(cursor) -> list[str]:
    cursor.execute(_SQL_TABLAS_EXISTEN)
    return [fila[0] for fila in cursor.fetchall()]


def _estado_cuenta(cursor, cuenta: dict) -> dict:
    """Compara una cuenta del JSON con lo que ya hay en PostgreSQL."""

    cursor.execute(_SQL_CUENTA_POR_ID, (int(cuenta["id_usuario"]),))
    fila = cursor.fetchone()
    if fila is None:
        cursor.execute(
            _SQL_CUENTA_POR_CORREO, (str(cuenta["correo"]).strip().lower(),)
        )
        por_correo = cursor.fetchone()
        if por_correo is None:
            return {"estado": "nueva", "fila": None}
        return {
            "estado": "conflicto_correo",
            "fila": por_correo,
            "mensaje": (
                f"el correo {cuenta['correo']} ya existe con id_usuario "
                f"{por_correo[0]} (JSON trae id {cuenta['id_usuario']})"
            ),
        }
    id_existente, correo_existente, hash_existente = fila
    if hmac_igual(hash_existente, cuenta["password_hash"]):
        return {"estado": "presente", "fila": fila}
    if str(correo_existente).lower() != str(cuenta["correo"]).lower():
        return {
            "estado": "conflicto_correo",
            "fila": fila,
            "mensaje": (
                f"el id_usuario {id_existente} ya existe con otro correo "
                f"({correo_existente})"
            ),
        }
    return {
        "estado": "conflicto_hash",
        "fila": fila,
        "mensaje": (
            f"la cuenta {correo_existente} ya existe con un hash distinto; "
            "no se sobreescribe"
        ),
    }


def hmac_igual(izquierda, derecha) -> bool:
    """Comparacion en tiempo constante de hashes."""

    return hmac.compare_digest(str(izquierda or ""), str(derecha or ""))


def _filas_afectadas(cursor) -> int:
    """Filas afectadas por el ultimo INSERT (0 si el driver no informa)."""

    return getattr(cursor, "rowcount", -1)


def planificar(conexion, cuentas: list[dict]) -> dict:
    """Clasifica cada cuenta del JSON frente a PostgreSQL (sin escribir)."""

    plan: list[dict] = []
    with conexion.cursor() as cursor:
        for datos in cuentas:
            problemas = validar_cuenta(datos)
            if problemas:
                plan.append(
                    {
                        "correo": datos.get("correo"),
                        "estado": "invalida",
                        "mensaje": "; ".join(problemas),
                    }
                )
                continue
            estado = _estado_cuenta(cursor, datos)
            plan.append(
                {
                    "id_usuario": int(datos["id_usuario"]),
                    "correo": datos["correo"],
                    "rol": str(datos["rol"]).upper(),
                    "activo": bool(datos.get("activo", True)),
                    **estado,
                }
            )
    return {
        "total": len(cuentas),
        "nuevas": [item for item in plan if item["estado"] == "nueva"],
        "presentes": [item for item in plan if item["estado"] == "presente"],
        "conflictos": [
            item
            for item in plan
            if item["estado"].startswith("conflicto")
        ],
        "invalidas": [item for item in plan if item["estado"] == "invalida"],
    }


def insertar_cuentas(conexion, plan: dict, cuentas_json: dict[int, dict]) -> int:
    """Inserta unicamente las cuentas nuevas, con su identificador original."""

    insertadas = 0
    with conexion.cursor() as cursor:
        for item in plan["nuevas"]:
            datos = cuentas_json[item["id_usuario"]]
            creado = _a_datetime(datos.get("creado_en")) or _ahora()
            actualizado = _a_datetime(datos.get("actualizado_en")) or creado
            acceso = _a_datetime(datos.get("ultimo_acceso"))
            cursor.execute(
                _SQL_INSERTAR_CUENTA,
                (
                    int(datos["id_usuario"]),
                    datos["nombres"],
                    datos["apellidos"],
                    datos["correo"],
                    datos["password_hash"],
                    str(datos["rol"]).upper(),
                    bool(datos.get("activo", True)),
                    bool(datos.get("es_propietario", False)),
                    datos.get("id_conductor"),
                    creado,
                    actualizado,
                    acceso,
                    _ahora(),
                ),
            )
            afectadas = _filas_afectadas(cursor)
            insertadas += afectadas if afectadas > 0 else 0
    return insertadas


def migrar_sesiones(conexion, sesiones: list[dict], ids_validos: set[int]) -> dict:
    """Migra solo sesiones vigentes (ni revocadas ni caducadas)."""

    ahora = _ahora()
    migradas = 0
    omitidas = 0
    with conexion.cursor() as cursor:
        for datos in sesiones:
            token_hash = datos.get("token_hash")
            id_usuario = datos.get("id_usuario")
            expira = _a_datetime(datos.get("expira_en"))
            revocado = bool(datos.get("revocado", False))
            if not token_hash or not id_usuario:
                omitidas += 1
                continue
            if int(id_usuario) not in ids_validos or expira is None:
                omitidas += 1
                continue
            if revocado or expira <= ahora:
                omitidas += 1
                continue
            cursor.execute(
                _SQL_INSERTAR_SESION,
                (
                    token_hash,
                    int(id_usuario),
                    _a_datetime(datos.get("creado_en")) or ahora,
                    expira,
                    revocado,
                    _a_datetime(datos.get("revocado_en")),
                    datos.get("agente_hash"),
                    datos.get("ip_prefijo"),
                ),
            )
            afectadas = _filas_afectadas(cursor)
            migradas += afectadas if afectadas > 0 else 0
    return {"migradas": migradas, "omitidas": omitidas}


def ejecutar(
    aplicar: bool = False,
    respaldar: bool = False,
    directorio: str | None = None,
    solo_sesiones: bool = False,
    conector=None,
) -> dict:
    """Ejecuta la migracion y devuelve un informe estructurado."""

    origen = _directorio_origen(directorio)
    conectar = conector or obtener_conexion
    informe: dict = {
        "origen": str(origen),
        "aplicado": False,
        "exito": False,
        "mensajes": [],
    }

    if not (origen / "cuentas.json").exists():
        informe["mensajes"].append(
            f"No existe {origen / 'cuentas.json'}: no hay cuentas que migrar."
        )
        informe["exito"] = True
        return informe

    cuentas = _cuentas_json(origen)
    if not cuentas:
        informe["mensajes"].append("El archivo de cuentas esta vacio.")
        informe["exito"] = True
        return informe

    conexion = conectar()
    try:
        with conexion.cursor() as cursor:
            tablas = _tablas_existen(cursor)
        faltantes = {
            "cuentas_acceso",
            "sesiones_acceso",
            "auditoria_acceso",
        } - set(tablas)
        if faltantes:
            informe["codigo_salida"] = 3
            informe["mensajes"].append(
                "Faltan tablas de acceso en PostgreSQL: "
                + ", ".join(sorted(faltantes))
                + ". Aplique database/scripts/006_seguridad_acceso.sql."
            )
            return informe

        plan = planificar(conexion, cuentas)

        if not aplicar:
            informe["exito"] = not (plan["conflictos"] or plan["invalidas"])
            informe["codigo_salida"] = 0 if informe["exito"] else 2
            informe["plan"] = plan
            informe["mensajes"].append(
                "Modo verificacion: no se escribio nada en PostgreSQL."
            )
            return informe

        if plan["conflictos"] or plan["invalidas"]:
            informe["codigo_salida"] = 2
            informe["plan"] = plan
            informe["mensajes"].append(
                "Se detectaron conflictos o cuentas invalidas: no se migra "
                "nada hasta resolverlos."
            )
            return informe

        por_id = {int(datos["id_usuario"]): datos for datos in cuentas}

        if respaldar:
            carpeta = respaldar_json(origen)
            informe["mensajes"].append(f"Respaldo JSON creado en {carpeta}.")

        if solo_sesiones:
            # Sin altas nuevas: solo se migran sesiones de cuentas que ya
            # existen en PostgreSQL (restriccion de clave foranea).
            with conexion.cursor() as cursor:
                cursor.execute(f"SELECT id_usuario FROM {TABLA_CUENTAS}")
                ids_validos = {int(fila[0]) for fila in cursor.fetchall()}
        else:
            insertadas = insertar_cuentas(conexion, plan, por_id)
            informe["cuentas_insertadas"] = insertadas
            informe["cuentas_ya_presentes"] = len(plan["presentes"])
            informe["aplicado"] = True
            ids_validos = set(por_id)
            conexion.commit()

        sesiones = _sesiones_json(origen)
        if sesiones:
            informe["sesiones"] = migrar_sesiones(
                conexion, sesiones, ids_validos
            )
            conexion.commit()

        # Las secuencias se ajustan en una conexion aparte: por eso el commit
        # previo es obligatorio para no bloquear la transaccion abierta.
        alinear_secuencias(conector=conectar)
        informe["mensajes"].append("Secuencias alineadas con los ids migrados.")
        informe["exito"] = True
        informe["codigo_salida"] = 0
        return informe
    except Exception as error:  # pragma: no cover - rutas de fallo de E/S
        try:
            conexion.rollback()
        except Exception:
            pass
        informe["codigo_salida"] = 1
        informe["error"] = f"{type(error).__name__}: {error}"
        informe["mensajes"].append("Migracion abortada; no se aplico ningun cambio.")
        return informe
    finally:
        try:
            conexion.close()
        except Exception:
            pass


def _mostrar(informe: dict) -> None:
    print("=" * 62)
    print("Migracion de cuentas JSON -> PostgreSQL (OptiRoute AI)")
    print("=" * 62)
    print(f"Origen: {informe['origen']}")
    for mensaje in informe["mensajes"]:
        print(f"- {mensaje}")
    if "error" in informe:
        print(f"[ERROR] {informe['error']}")
    plan = informe.get("plan") or {}
    if plan:
        print(f"Cuentas en el archivo : {plan.get('total', 0)}")
        print(f"  nuevas              : {len(plan.get('nuevas', []))}")
        print(f"  ya migradas         : {len(plan.get('presentes', []))}")
        print(f"  en conflicto        : {len(plan.get('conflictos', []))}")
        print(f"  invalidas           : {len(plan.get('invalidas', []))}")
        for item in plan.get("conflictos", []):
            print(f"    [conflicto] {item.get('correo')}: {item.get('mensaje')}")
        for item in plan.get("invalidas", []):
            print(f"    [invalida] {item.get('correo')}: {item.get('mensaje')}")
    if "cuentas_insertadas" in informe:
        print(f"Cuentas insertadas    : {informe['cuentas_insertadas']}")
        print(f"Cuentas ya presentes  : {informe['cuentas_ya_presentes']}")
    if "sesiones" in informe:
        print(
            f"Sesiones migradas    : {informe['sesiones']['migradas']} "
            f"(omitidas {informe['sesiones']['omitidas']})"
        )
    print("=" * 62)
    if informe.get("exito"):
        print("Resultado: correcto.")
    else:
        print(
            "Resultado: con incidencias "
            f"(codigo {informe.get('codigo_salida', 1)})."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migra cuentas de acceso de JSON a PostgreSQL."
    )
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Escribe en PostgreSQL. Sin esta opcion solo se verifica.",
    )
    parser.add_argument(
        "--respaldar",
        action="store_true",
        help="Copia los archivos JSON a backend/data/seguridad/respaldos/ "
        "antes de migrar.",
    )
    parser.add_argument(
        "--directorio",
        default=None,
        help="Directorio con cuentas.json (por defecto OPTIROUTE_AUTH_DATA_DIR).",
    )
    parser.add_argument(
        "--sesiones-solo",
        action="store_true",
        help="Migra unicamente las sesiones vigentes.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime el informe en formato JSON.",
    )
    argumentos = parser.parse_args(argv)

    informe = ejecutar(
        aplicar=argumentos.aplicar,
        respaldar=argumentos.respaldar,
        directorio=argumentos.directorio,
        solo_sesiones=argumentos.sesiones_solo,
    )
    if argumentos.json:
        informe_serializable = json.loads(
            json.dumps(informe, ensure_ascii=False, default=str)
        )
        print(json.dumps(informe_serializable, ensure_ascii=False, indent=2))
    else:
        _mostrar(informe)
    return int(informe.get("codigo_salida", 0 if informe.get("exito") else 1))


if __name__ == "__main__":
    sys.exit(main())
