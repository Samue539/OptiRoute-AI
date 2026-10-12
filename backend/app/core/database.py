import os

from dotenv import load_dotenv


load_dotenv()

_psycopg = None
_import_error = None

try:
    import psycopg as _psycopg  # type: ignore
except Exception as exc:  # pragma: no cover - entorno sin psycopg-binary
    _import_error = exc
    _psycopg = None

# Compatibilidad: exponer `psycopg` si esta disponible, None si esta bloqueado.
psycopg = _psycopg  # type: ignore

# Fallback puro-Python para entornos con WDAC/SAC que bloquean psycopg-binary.
_pg8000 = None
try:
    import pg8000.dbapi as _pg8000  # type: ignore
except Exception:
    _pg8000 = None


class _Pg8000Cursor:
    """Adaptador para que pg8000.Cursor soporte `with` como psycopg."""

    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self._cursor.close()
        except Exception:
            pass
        return False

    def execute(self, query, params=None):
        if params is None:
            return self._cursor.execute(query)
        return self._cursor.execute(query, params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass


class _Pg8000Connection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _Pg8000Cursor(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def obtener_conexion():
    if _psycopg is not None:
        try:
            conexion = _psycopg.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
            )
            return conexion
        except Exception as exc:
            # Si psycopg falla por WDAC, intentar pg8000 antes de propagar.
            if _pg8000 is None:
                raise
            # Verificar si es el error de wrapper bloqueado.
            if "Control de aplicaciones" not in str(exc) and "no pq wrapper" not in str(exc):
                raise

    if _pg8000 is not None:
        conn = _pg8000.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT") or 5432),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
        return _Pg8000Connection(conn)

    raise RuntimeError(
        "psycopg no disponible: "
        f"{_import_error}. "
        "Driver bloqueado por WDAC/SAC o libpq no encontrado. "
        "En tests usar mock de obtener_conexion."
    )