"""Pruebas de integracion contra PostgreSQL real (opcionales).

No se ejecutan en la suite normal: requieren una decision explicita porque
necesitan una base de datos PostgreSQL accesible::

    set OPTIROUTE_TEST_DB=1 && python -m pytest tests/test_auth_postgres_integracion.py -q

Diseno seguro:

* Las tablas de acceso se crean **dentro de una transaccion** que se revierte
  al terminar (``rollback``). PostgreSQL permite DDL transaccional, asi que no
  queda ningun cambio permanente en la base de datos.
* Todas las operaciones comparten la misma conexion; el envoltorio evita que
  los repositorios la cierren o confirmen antes de la verificacion final.
* Para no bloquear con otras conexiones, todo el trabajo se hace sobre esa
  unica conexion abierta durante la prueba.
"""

from __future__ import annotations

import os
import pathlib
from datetime import timedelta

import pytest

from backend.app.core.database import obtener_conexion
from backend.app.core.seguridad import hashear_password
from backend.app.repositories import repositorio_cuentas
from backend.app.repositories.errores import ErrorCuentaDuplicada, ErrorNoEncontrado
from backend.app.repositories.modelos import Cuenta, Sesion, ahora_utc
from backend.app.repositories.postgres import (
    RepositorioAuditoriaPostgres,
    RepositorioCuentasPostgres,
    RepositorioSesionesPostgres,
    alinear_secuencias,
)
from backend.app.services import auth_service

RAIZ = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_TABLAS = RAIZ / "database" / "scripts" / "006_seguridad_acceso.sql"

requiere_db = pytest.mark.skipif(
    os.getenv("OPTIROUTE_TEST_DB", "").strip().lower()
    not in {"1", "true", "si", "yes"},
    reason="Prueba de integracion: active OPTIROUTE_TEST_DB=1 para ejecutarla.",
)


class ConexionSinCierre:
    """Envoltorio que evita commit/close: la transaccion la cierra el test."""

    def __init__(self, real):
        self.real = real

    def cursor(self):
        return self.real.cursor()

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


@pytest.fixture
def conexion_transaccional(monkeypatch):
    """Crea las tablas de acceso dentro de una transaccion y la revierte."""

    real = obtener_conexion()
    compartida = ConexionSinCierre(real)
    monkeypatch.setattr(
        "backend.app.repositories.postgres.obtener_conexion", lambda: compartida
    )
    cursor = real.cursor()
    try:
        cursor.execute(SCRIPT_TABLAS.read_text(encoding="utf-8"))
        yield compartida
    finally:
        try:
            real.rollback()
        finally:
            real.close()


@pytest.fixture
def cuentas(conexion_transaccional):
    return RepositorioCuentasPostgres(conector=lambda: conexion_transaccional)


@pytest.fixture
def sesiones(conexion_transaccional):
    return RepositorioSesionesPostgres(conector=lambda: conexion_transaccional)


@pytest.fixture(autouse=True)
def _usar_postgres(monkeypatch):
    monkeypatch.setenv("OPTIROUTE_AUTH_STORAGE", "postgres")


def _cuenta(correo: str, rol: str = "OPERADOR", **cambios) -> Cuenta:
    valores = dict(
        id_usuario=0,
        nombres="Prueba",
        apellidos="Integracion",
        correo=correo,
        password_hash=hashear_password("Segura12345"),
        rol=rol,
        activo=True,
    )
    valores.update(cambios)
    return Cuenta(**valores)


@requiere_db
class TestCuentasEnPostgreSQL:
    def test_crear_y_leer(self, cuentas, conexion_transaccional):
        creada = cuentas.crear(_cuenta("alta@prueba.invalid"))
        assert creada.id_usuario > 0

        buscada = cuentas.obtener_por_correo("ALTA@prueba.invalid")
        assert buscada is not None
        assert buscada.correo == "alta@prueba.invalid"

        with conexion_transaccional.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM seguridad.cuentas_acceso "
                "WHERE correo = %s",
                ("alta@prueba.invalid",),
            )
            guardado = cursor.fetchone()[0]
        assert guardado.startswith("pbkdf2_sha256$")

    def test_correo_duplicado_falla(self, cuentas):
        cuentas.crear(_cuenta("duplicado@prueba.invalid"))
        with pytest.raises(ErrorCuentaDuplicada):
            cuentas.crear(_cuenta("duplicado@prueba.invalid"))

    def test_actualizar_y_existe_rol(self, cuentas):
        cuenta = cuentas.crear(_cuenta("estado@prueba.invalid"))
        cuenta.activo = False
        actualizada = cuentas.actualizar(cuenta)
        assert actualizada.activo is False
        assert cuentas.existe_rol("OPERADOR") is True

    def test_secuencia_sigue_a_los_ids_migrados(self, cuentas, conexion_transaccional):
        cuentas.crear(_cuenta("migrado@prueba.invalid", id_usuario=9001))
        alinear_secuencias(conector=lambda: conexion_transaccional)
        nueva = cuentas.crear(_cuenta("posterior@prueba.invalid"))
        assert nueva.id_usuario > 9001


@requiere_db
class TestSesionesEnPostgreSQL:
    def test_ciclo_emision_vigencia_y_revocacion(self, cuentas, sesiones):
        cuenta = cuentas.crear(_cuenta("sesion@prueba.invalid"))
        sesiones.crear(
            Sesion(
                token_hash="f" * 64,
                id_usuario=cuenta.id_usuario,
                expira_en=ahora_utc() + timedelta(hours=8),
                agente_hash="a" * 64,
                ip_prefijo="127.0.0.0",
            )
        )

        recuperada = sesiones.obtener("f" * 64)
        assert recuperada is not None
        assert recuperada.agente_hash == "a" * 64
        assert recuperada.esta_vigente()

        assert sesiones.revocar("f" * 64) is True
        assert sesiones.revocar("f" * 64) is False  # idempotente
        assert sesiones.obtener("f" * 64).revocado is True

        with pytest.raises(ErrorNoEncontrado):
            sesiones.actualizar(
                Sesion(
                    token_hash="0" * 64,
                    id_usuario=cuenta.id_usuario,
                    expira_en=ahora_utc() + timedelta(hours=8),
                )
            )

    def test_contar_y_limpiar(self, cuentas, sesiones):
        cuenta = cuentas.crear(_cuenta("limpieza@prueba.invalid"))
        for indice, horas in enumerate((8, 8, -1)):
            sesiones.crear(
                Sesion(
                    token_hash=str(indice) * 64,
                    id_usuario=cuenta.id_usuario,
                    expira_en=ahora_utc() + timedelta(hours=horas),
                )
            )
        assert sesiones.contar_activas() == 2
        assert sesiones.limpiar_expiradas() == 1
        assert sesiones.contar_activas() == 2

    def test_revocar_por_usuario_devuelve_cantidad_real(self, cuentas, sesiones):
        cuenta = cuentas.crear(_cuenta("revocacion@prueba.invalid"))
        for indice in range(3):
            sesiones.crear(
                Sesion(
                    token_hash=f"{indice}" * 64,
                    id_usuario=cuenta.id_usuario,
                    expira_en=ahora_utc() + timedelta(hours=8),
                )
            )
        assert sesiones.revocar_por_usuario(cuenta.id_usuario) == 3
        assert sesiones.contar_activas() == 0


@requiere_db
class TestServicioCompletoEnPostgreSQL:
    def test_login_sesion_y_logout(self, conexion_transaccional):
        repositorio_cuentas().crear(_cuenta("servicio@prueba.invalid"))

        sesion = auth_service.login("servicio@prueba.invalid", "Segura12345")
        assert sesion["token"]

        resuelta = auth_service.resolver_sesion(sesion["token"])
        assert resuelta is not None
        _sesion_guardada, cuenta_resuelta = resuelta
        assert cuenta_resuelta.correo == "servicio@prueba.invalid"

        assert auth_service.cerrar_sesion(sesion["token"]) is True
        assert auth_service.resolver_sesion(sesion["token"]) is None

    def test_login_contrasena_invalida(self, conexion_transaccional):
        repositorio_cuentas().crear(_cuenta("clave-mala@prueba.invalid"))
        from backend.app.services.auth_service import ErrorAutenticacion

        with pytest.raises(ErrorAutenticacion):
            auth_service.login("clave-mala@prueba.invalid", "Incorrecta999")

    def test_cambio_de_password_revoca_sesiones(self, conexion_transaccional):
        repositorio_cuentas().crear(_cuenta("clave@prueba.invalid"))
        sesion = auth_service.login("clave@prueba.invalid", "Segura12345")

        cuenta = repositorio_cuentas().obtener_por_correo("clave@prueba.invalid")
        revocadas = auth_service.cambiar_password(
            cuenta, "Segura12345", "NuevaClave2025"
        )
        assert revocadas >= 1
        assert auth_service.login("clave@prueba.invalid", "NuevaClave2025")["token"]
        assert auth_service.resolver_sesion(sesion["token"]) is None

    def test_auditoria_registra_y_lista(self, conexion_transaccional):
        repositorio_cuentas().crear(_cuenta("auditoria@prueba.invalid"))
        auth_service.login("auditoria@prueba.invalid", "Segura12345")
        try:
            auth_service.login("auditoria@prueba.invalid", "ClaveIncorrecta999")
        except auth_service.ErrorAutenticacion:
            pass

        eventos = RepositorioAuditoriaPostgres(
            conector=lambda: conexion_transaccional
        ).listar(10)
        assert any(evento["accion"] == "login" for evento in eventos)
        assert any(evento["accion"] == "login_fallido" for evento in eventos)
        assert all("password_hash" not in evento for evento in eventos)
