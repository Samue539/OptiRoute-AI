"""Pruebas de los repositorios de acceso sobre PostgreSQL.

Verifican el mapeo de filas a modelos de dominio, el uso de consultas
parametrizadas (nunca valores interpolados en el SQL) y la idempotencia de
la revocacion de sesiones, sin necesidad de una base de datos real: la
conexion se inyecta (``conector``), igual que en el resto del proyecto.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.core.seguridad import hashear_metadato, hashear_token
from backend.app.repositories.errores import (
    ErrorCuentaDuplicada,
    ErrorNoEncontrado,
)
from backend.app.repositories.modelos import Cuenta, Sesion, ahora_utc
from backend.app.repositories.postgres import (
    RepositorioAuditoriaPostgres,
    RepositorioCuentasPostgres,
    RepositorioSesionesPostgres,
    _a_utc,
    _como_dict,
    _fila_cuenta,
    _fila_sesion,
    alinear_secuencias,
    verificar_esquema,
)

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


class CursSimulado:
    """Cursor que responde segun el prefijo de la consulta."""

    def __init__(self, respuestas: dict, registro: list):
        self.respuestas = respuestas
        self.registro = registro

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql: str, params=None):
        normalizada = " ".join(sql.split())
        clave = self._clave(normalizada)
        if clave is None:
            raise AssertionError(f"Consulta no simulada: {normalizada[:90]}")
        self.registro.append((clave, normalizada, tuple(params or ())))
        self.resultado = self.respuestas.get(clave, [])
        self.afectadas = len(self.resultado)

    @staticmethod
    def _clave(sql: str) -> str | None:
        if sql.startswith("INSERT INTO seguridad.cuentas_acceso"):
            return "insertar_cuenta"
        if sql.startswith("INSERT INTO seguridad.sesiones_acceso"):
            return "insertar_sesion"
        if sql.startswith("INSERT INTO seguridad.auditoria_acceso"):
            return "insertar_auditoria"
        if sql.startswith("UPDATE seguridad.cuentas_acceso"):
            return "actualizar_cuenta"
        if sql.startswith("UPDATE seguridad.sesiones_acceso"):
            if "SET revocado = TRUE" in sql:
                return "revocar_sesion"
            return "actualizar_sesion"
        if sql.startswith("DELETE FROM seguridad.sesiones_acceso"):
            return "limpiar_sesiones"
        if "COUNT(*)" in sql:
            return "contar_sesiones"
        if "to_regclass" in sql:
            return "to_regclass"
        if "setval(" in sql:
            return "setval"
        if "WHERE id_usuario = %s" in sql and "FROM seguridad.cuentas_acceso" in sql:
            return "cuenta_por_id"
        if "LOWER(correo) = %s" in sql:
            return "cuenta_por_correo"
        if "ORDER BY id_usuario" in sql:
            return "listar_cuentas"
        if "UPPER(rol) = %s" in sql:
            return "existe_rol"
        if "FROM seguridad.sesiones_acceso" in sql and "WHERE token_hash" in sql:
            return "sesion_por_hash"
        if "FROM seguridad.auditoria_acceso" in sql and "ORDER BY" in sql:
            return "listar_auditoria"
        return None

    def fetchone(self):
        return self.resultado[0] if self.resultado else None

    def fetchall(self):
        return list(self.resultado)

    @property
    def rowcount(self):
        return self.afectadas


class ConexSimulada:
    def __init__(self, respuestas: dict | None = None):
        self.respuestas = respuestas or {}
        self.registro: list[tuple[str, str, tuple]] = []
        self.commits = 0
        self.rollbacks = 0
        self.cerrada = False

    def cursor(self):
        return CursSimulado(self.respuestas, self.registro)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.cerrada = True

    def consultas(self, clave: str) -> list[tuple[str, tuple]]:
        """Devuelve ``(sql, parametros)`` de las consultas de ese tipo."""

        return [
            (sql, params)
            for tipo, sql, params in self.registro
            if tipo == clave
        ]


def _fila_cuenta_base(**cambios) -> tuple:
    valores = {
        "id_usuario": 4,
        "nombres": "Ana",
        "apellidos": "Lopez",
        "correo": "ana@optiroute.test",
        "password_hash": "pbkdf2_sha256$210000$aa$bb",
        "rol": "OPERADOR",
        "activo": True,
        "es_propietario": False,
        "id_conductor": None,
        "creado_en": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "actualizado_en": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "ultimo_acceso": None,
    }
    valores.update(cambios)
    return tuple(valores[columna] for columna in COLUMNAS_CUENTA)


def _fila_sesion_base(**cambios) -> tuple:
    valores = {
        "token_hash": "a" * 64,
        "id_usuario": 4,
        "creado_en": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "expira_en": datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
        "revocado": False,
        "revocado_en": None,
        "agente_hash": None,
        "ip_prefijo": None,
    }
    valores.update(cambios)
    return tuple(valores[columna] for columna in COLUMNAS_SESION)


@pytest.fixture
def conex():
    return ConexSimulada()


@pytest.fixture
def repo_cuentas(conex):
    return RepositorioCuentasPostgres(conector=lambda: conex)


@pytest.fixture
def repo_sesiones(conex):
    return RepositorioSesionesPostgres(conector=lambda: conex)


@pytest.fixture
def repo_auditoria(conex):
    return RepositorioAuditoriaPostgres(conector=lambda: conex)


class TestMapeoDeFilas:
    def test_fila_cuenta_devuelve_modelo_de_dominio(self):
        cuenta = _fila_cuenta(_fila_cuenta_base(id_conductor=9))
        assert cuenta.id_usuario == 4
        assert cuenta.correo == "ana@optiroute.test"
        assert cuenta.rol == "OPERADOR"
        assert cuenta.activo is True
        assert cuenta.id_conductor == 9
        assert cuenta.creado_en.tzinfo is not None

    def test_fila_sesion_devuelve_modelo_de_dominio(self):
        sesion = _fila_sesion(_fila_sesion_base(revocado=True, revocado_en=None))
        assert sesion.token_hash == "a" * 64
        assert sesion.revocado is True
        assert sesion.expira_en.tzinfo is not None

    def test_datetimes_naive_se_normalizan_a_utc(self):
        naive = datetime(2026, 1, 1, 12, 0, 0)
        assert _a_utc(naive) == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert _a_utc(None) is None

    def test_jsonb_como_texto_se_convierte_en_dict(self):
        assert _como_dict('{"rol": "OPERADOR"}') == {"rol": "OPERADOR"}
        assert _como_dict(None) == {}
        assert _como_dict("{no json}") == {}


class TestRepositorioCuentas:
    def test_obtener_devuelve_la_cuenta(self, repo_cuentas, conex):
        conex.respuestas["cuenta_por_id"] = [_fila_cuenta_base()]
        cuenta = repo_cuentas.obtener(4)
        assert cuenta is not None and cuenta.id_usuario == 4
        assert conex.consultas("cuenta_por_id")[0][1] == (4,)

    def test_obtener_sin_resultado_devuelve_none(self, repo_cuentas):
        assert repo_cuentas.obtener(999) is None

    def test_listar_ordena_por_identificador(self, repo_cuentas, conex):
        conex.respuestas["listar_cuentas"] = [
            _fila_cuenta_base(id_usuario=1),
            _fila_cuenta_base(id_usuario=2),
        ]
        cuentas = repo_cuentas.listar()
        assert [cuenta.id_usuario for cuenta in cuentas] == [1, 2]

    def test_crear_asigna_identificador_de_la_secuencia(self, repo_cuentas, conex):
        conex.respuestas["insertar_cuenta"] = [_fila_cuenta_base(id_usuario=12)]
        cuenta = Cuenta(
            id_usuario=0,
            nombres="Nueva",
            apellidos="Cuenta",
            correo="nueva@optiroute.test",
            password_hash="pbkdf2_sha256$210000$aa$bb",
            rol="OPERADOR",
        )
        creada = repo_cuentas.crear(cuenta)
        assert creada.id_usuario == 12
        (sql, params), = conex.consultas("insertar_cuenta")
        assert params[0] == "Nueva"  # se pasa como parametro, no interpolado
        assert "nueva@optiroute.test" not in sql

    def test_crear_con_correo_duplicado_falla_con_409_logico(self, repo_cuentas, conex):
        conex.respuestas["cuenta_por_correo"] = [_fila_cuenta_base()]
        cuenta = Cuenta(
            id_usuario=0,
            nombres="Otra",
            apellidos="Cuenta",
            correo="ana@optiroute.test",
            password_hash="pbkdf2_sha256$210000$aa$bb",
            rol="OPERADOR",
        )
        with pytest.raises(ErrorCuentaDuplicada):
            repo_cuentas.crear(cuenta)

    def test_crear_con_id_ya_ocupado_falla_sin_sobreescribir(
        self, repo_cuentas, conex
    ):
        conex.respuestas["insertar_cuenta"] = []
        cuenta = Cuenta(
            id_usuario=4,
            nombres="Ana",
            apellidos="Lopez",
            correo="ana@optiroute.test",
            password_hash="pbkdf2_sha256$210000$aa$bb",
            rol="OPERADOR",
        )
        with pytest.raises(ErrorCuentaDuplicada):
            repo_cuentas.crear(cuenta)

    def test_actualizar_devuelve_la_cuenta_persistida(self, repo_cuentas, conex):
        conex.respuestas["actualizar_cuenta"] = [
            _fila_cuenta_base(rol="ADMINISTRADOR")
        ]
        cuenta = _fila_cuenta(_fila_cuenta_base(rol="ADMINISTRADOR"))
        actualizada = repo_cuentas.actualizar(cuenta)
        assert actualizada.rol == "ADMINISTRADOR"

    def test_actualizar_cuenta_inexistente_falla(self, repo_cuentas):
        cuenta = _fila_cuenta(_fila_cuenta_base())
        with pytest.raises(ErrorNoEncontrado):
            repo_cuentas.actualizar(cuenta)

    def test_existe_rol(self, repo_cuentas, conex):
        conex.respuestas["existe_rol"] = [(1,)]
        assert repo_cuentas.existe_rol("DESARROLLADOR") is True

    def test_cierra_la_conexion_en_exito_y_error(self, repo_cuentas, conex):
        repo_cuentas.obtener(1)
        assert conex.cerrada is True
        assert conex.commits == 1


class TestRepositorioSesiones:
    def test_crear_devuelve_la_sesion_persistida(self, repo_sesiones, conex):
        conex.respuestas["insertar_sesion"] = [_fila_sesion_base()]
        sesion = Sesion(
            token_hash="a" * 64,
            id_usuario=4,
            expira_en=ahora_utc() + timedelta(hours=8),
        )
        creada = repo_sesiones.crear(sesion)
        assert creada.token_hash == "a" * 64
        (sql, params), = conex.consultas("insertar_sesion")
        assert params[0] == "a" * 64
        assert "a" * 64 not in sql

    def test_revocar_es_idempotente(self, repo_sesiones, conex):
        conex.respuestas["revocar_sesion"] = [_fila_sesion_base()]
        assert repo_sesiones.revocar("a" * 64) is True
        conex.respuestas["revocar_sesion"] = []
        assert repo_sesiones.revocar("a" * 64) is False

    def test_revocar_por_usuario_devuelve_cantidad(self, repo_sesiones, conex):
        conex.respuestas["revocar_sesion"] = [
            _fila_sesion_base(token_hash="a" * 64),
            _fila_sesion_base(token_hash="b" * 64),
        ]
        assert repo_sesiones.revocar_por_usuario(4) == 2

    def test_limpiar_expiradas_devuelve_cantidad(self, repo_sesiones, conex):
        conex.respuestas["limpiar_sesiones"] = [("a" * 64,)]
        assert repo_sesiones.limpiar_expiradas() == 1

    def test_contar_activas(self, repo_sesiones, conex):
        conex.respuestas["contar_sesiones"] = [(3,)]
        assert repo_sesiones.contar_activas() == 3

    def test_metadatos_se_persisten_junto_a_la_sesion(self, repo_sesiones, conex):
        conex.respuestas["insertar_sesion"] = [_fila_sesion_base()]
        sesion = Sesion(
            token_hash="a" * 64,
            id_usuario=4,
            expira_en=ahora_utc() + timedelta(hours=8),
            agente_hash=hashear_metadato("Mozilla/5.0"),
            ip_prefijo="192.168.0.0",
        )
        repo_sesiones.crear(sesion)
        (_sql, params), = conex.consultas("insertar_sesion")
        assert params[6] == hashear_metadato("Mozilla/5.0")
        assert params[7] == "192.168.0.0"

    def test_token_nunca_se_guarda_en_claro(self, repo_sesiones, conex):
        token = "cus8OSW8aMx9T7hDb2X3NBtXdlUkZiJEa4h1-LcIZ5Krrn9gMeLuqmgEGf_An2tR"
        conex.respuestas["insertar_sesion"] = [_fila_sesion_base()]
        sesion = Sesion(
            token_hash=hashear_token(token),
            id_usuario=4,
            expira_en=ahora_utc() + timedelta(hours=8),
        )
        repo_sesiones.crear(sesion)
        (_sql, params), = conex.consultas("insertar_sesion")
        assert params[0] == hashear_token(token)
        assert token not in str(params)


class TestRepositorioAuditoria:
    def test_registrar_mantiene_la_misma_forma_plana(self, repo_auditoria, conex):
        conex.respuestas["insertar_auditoria"] = [
            ("login", "ana@optiroute.test", 4, {"rol": "OPERADOR"})
        ]
        repo_auditoria.registrar(
            {
                "accion": "login",
                "actor": "ana@optiroute.test",
                "actor_id": 4,
                "rol": "OPERADOR",
            }
        )
        (sql, params), = conex.consultas("insertar_auditoria")
        assert params[0] == "login"
        assert params[1] == "ana@optiroute.test"
        assert params[2] == 4
        assert json.loads(params[3])["rol"] == "OPERADOR"
        assert "ana@optiroute.test" not in sql

    def test_listar_devuelve_eventos_planos_mas_nuevos_primero(
        self, repo_auditoria, conex
    ):
        conex.respuestas["listar_auditoria"] = [
            ("login", "ana@optiroute.test", 4, {"creado_en": "2026-01-01T00:00:00+00:00"}),
        ]
        eventos = repo_auditoria.listar(50)
        assert eventos == [
            {
                "accion": "login",
                "actor": "ana@optiroute.test",
                "actor_id": 4,
                "creado_en": "2026-01-01T00:00:00+00:00",
            }
        ]

    def test_listar_acepta_detalle_como_texto(self, repo_auditoria, conex):
        conex.respuestas["listar_auditoria"] = [
            ("logout", None, None, '{"creado_en": "2026-01-01T00:00:00+00:00"}')
        ]
        eventos = repo_auditoria.listar()
        assert eventos[0]["accion"] == "logout"
        assert "creado_en" in eventos[0]


class TestVerificacionDeEsquema:
    def test_conexion_exitosa_informa_tablas(self):
        conex = ConexSimulada({"to_regclass": [(True,)]})
        estado = verificar_esquema(conector=lambda: conex)
        assert estado["conectado"] is True
        assert estado["tablas"]["seguridad.cuentas_acceso"] is True

    def test_base_inaccesible_no_lanza(self):
        def explotar():
            raise RuntimeError("no hay red")

        estado = verificar_esquema(conector=explotar)
        assert estado["conectado"] is False
        assert estado["tablas"]["seguridad.cuentas_acceso"] is False

    def test_alinear_secuencias_no_falla_con_conexion_ok(self):
        conex = ConexSimulada({"setval": [(1,)]})
        alinear_secuencias(conector=lambda: conex)
        assert conex.commits == 1
