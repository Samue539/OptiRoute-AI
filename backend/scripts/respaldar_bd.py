"""Respaldo de la base de datos (operacion de solo lectura).

Genera un respaldo completo antes de aplicar migraciones o la migracion de
cuentas. Usa ``pg_dump`` si esta disponible; si no, exporta los datos con
``COPY`` desde el propio conector de Python.

Uso::

    python -m backend.scripts.respaldar_bd                     # backups/respaldo-<marca>.dump
    python -m backend.scripts.respaldar_bd --formato plano     # .sql
    python -m backend.scripts.respaldar_bd --directorio D:\\respaldos

El archivo se escribe en ``backups/`` (ignorado por git, al igual que
``*.dump`` y ``*.sql`` de respaldo). No modifica la base de datos.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAIZ = Path(__file__).resolve().parents[2]
DIRECTORIO_PREDETERMINADO = RAIZ / "backups"

ESQUEMAS = ("seguridad", "operaciones", "logistica", "ia")


def _marca() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _pg_dump_disponible() -> str | None:
    """Busca pg_dump en PATH y en las rutas habituales de PostgreSQL."""

    ejecutable = shutil.which("pg_dump")
    if ejecutable:
        return ejecutable
    candidatos = [
        Path(os.environ.get("PG_BIN", "")) if os.environ.get("PG_BIN") else None
    ]
    candidatos += [
        Path(f"{prefijo}\\PostgreSQL\\{version}\\bin\\pg_dump.exe")
        for prefijo in ("C:\\Program Files", "C:\\Program Files (x86)")
        for version in (18, 17, 16, 15, 14)
    ]
    for candidato in candidatos:
        if candidato and Path(candidato).exists():
            return str(candidato)
    return None


def respaldo_pg_dump(destino: Path) -> Path | None:
    """Respaldo con pg_dump (formato comprimido custom)."""

    ejecutable = _pg_dump_disponible()
    if not ejecutable:
        return None
    archivo = destino / f"respaldo-{_marca()}.dump"
    entorno = os.environ.copy()
    entorno.setdefault("PGPASSWORD", os.getenv("DB_PASSWORD", ""))
    comando = [
        ejecutable,
        "-h", os.getenv("DB_HOST", "localhost"),
        "-p", os.getenv("DB_PORT", "5432"),
        "-U", os.getenv("DB_USER", "postgres"),
        "-d", os.getenv("DB_NAME", "optiroute_db"),
        "-F", "c",
        "-f", str(archivo),
    ]
    resultado = subprocess.run(
        comando, env=entorno, capture_output=True, text=True, check=False
    )
    if resultado.returncode != 0:
        print(f"[ERROR] pg_dump fallo: {resultado.stderr.strip()[:300]}")
        return None
    return archivo


def respaldo_copy(destino: Path) -> Path:
    """Respaldo de datos en CSV con el conector del proyecto (sin DDL).

    Es un plan B cuando ``pg_dump`` no esta disponible: conserva todos los
    datos de los esquemas del sistema, pero no el DDL.
    """

    import csv

    from backend.app.core.database import obtener_conexion

    archivo = destino / f"respaldo-datos-{_marca()}"
    archivo.mkdir(parents=True, exist_ok=True)
    conexion = obtener_conexion()
    try:
        lineas: list[str] = ["Respaldo de datos OptiRoute AI (CSV)"]
        with conexion.cursor() as cursor:
            for esquema in ESQUEMAS:
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s ORDER BY table_name",
                    (esquema,),
                )
                tablas = [fila[0] for fila in cursor.fetchall()]
                for tabla in tablas:
                    nombre = f"{esquema}.{tabla}"
                    destino_csv = archivo / f"{nombre}.csv"
                    with destino_csv.open(
                        "w", encoding="utf-8", newline=""
                    ) as archivo_csv:
                        escritor = csv.writer(archivo_csv)
                        cursor.execute(f"SELECT * FROM {nombre}")
                        escritor.writerow(
                            [descripcion[0] for descripcion in cursor.description]
                        )
                        filas = cursor.fetchall()
                        escritor.writerows(filas)
                    lineas.append(f"{nombre}\t{len(filas)} filas")
        conexion.commit()
        with (archivo / "indice.txt").open("w", encoding="utf-8") as salida:
            salida.write("\n".join(lineas) + "\n")
        for linea in lineas:
            print("  " + linea)
    finally:
        try:
            conexion.close()
        except Exception:
            pass
    return archivo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Respaldo de la base de datos.")
    parser.add_argument(
        "--directorio",
        default=str(DIRECTORIO_PREDETERMINADO),
        help="Carpeta destino del respaldo.",
    )
    parser.add_argument(
        "--formato",
        choices=["custom", "plano"],
        default="custom",
        help="custom (pg_dump -Fc) o plano (COPY a .sql).",
    )
    argumentos = parser.parse_args(argv)

    destino = Path(argumentos.directorio)
    destino.mkdir(parents=True, exist_ok=True)

    archivo = None
    if argumentos.formato == "custom":
        archivo = respaldo_pg_dump(destino)
        if archivo is None:
            print("[INFO] pg_dump no disponible: se usa respaldo plano.")
    if archivo is None:
        archivo = respaldo_copy(destino)

    tamano = archivo.stat().st_size
    print(f"[OK] Respaldo creado: {archivo} ({tamano} bytes)")
    print("[INFO] Conservelo fuera del repositorio para poder revertir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
