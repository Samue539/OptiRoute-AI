"""Pruebas de endurecimiento de sesiones y concurrencia.

Cubren el control de sesiones endurecido (metadatos de sesion, modo
estricto, cierre en todos los equipos, purga de sesiones caducas) y el
comportamiento concurrente de la autenticacion: altas simultaneas,
inicios de sesion paralelos y revocacion mientras se emiten tokens.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.core.seguridad import hashear_metadato, hashear_password
from backend.app.main import app
from backend.app.repositories.modelos import Cuenta, Sesion, ahora_utc
from backend.app.repositories.postgres import _a_utc
from backend.app.services import auth_service

CORREO_DUENO = "dueno@optiroute.test"
PASSWORD_DUENO = "Propietario123"


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("OPTIROUTE_AUTH_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("OPTIROUTE_AUTH_STORAGE", raising=False)
    monkeypatch.delenv("OPTIROUTE_DEMO", raising=False)
    return TestClient(app)


@pytest.fixture
def dueno(tmp_path, monkeypatch):
    """Una cuenta DESARROLLADOR ya persistida (solicitante de pruebas)."""

    monkeypatch.setenv("OPTIROUTE_AUTH_DATA_DIR", str(tmp_path))
    from backend.app.repositories import repositorio_cuentas

    return repositorio_cuentas().crear(
        Cuenta(
            id_usuario=0,
            nombres="Dueno",
            apellidos="Sistema",
            correo=CORREO_DUENO,
            password_hash=hashear_password(PASSWORD_DUENO),
            rol="DESARROLLADOR",
            activo=True,
            es_propietario=True,
        )
    )


def _bootstrap(cliente: TestClient) -> dict:
    respuesta = cliente.post(
        "/api/auth/bootstrap",
        json={
            "nombres": "Dueno",
            "apellidos": "Sistema",
            "correo": CORREO_DUENO,
            "password": PASSWORD_DUENO,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _cabecera(token: str, agente: str | None = None) -> dict:
    cabecera = {"Authorization": f"Bearer {token}"}
    if agente:
        cabecera["User-Agent"] = agente
    return cabecera


class _PeticionFalsa:
    """Doble de la Request de Starlette (solo lo que usa el servicio)."""

    def __init__(self, agente=None, ip=None):
        self.headers = {"user-agent": agente} if agente else {}
        self.client = type("Cliente", (), {"host": ip})() if ip else None


class TestMetadatosDeSesion:
    def test_metadatos_no_guardan_el_user_agent_original(self):
        agente_hash, ip_prefijo = auth_service.metadatos_peticion(
            _PeticionFalsa(agente="Mozilla/5.0 (X11; Linux)", ip="192.168.10.20")
        )
        assert agente_hash == hashear_metadato("Mozilla/5.0 (X11; Linux)")
        assert ip_prefijo == "192.168.0.0"
        assert "192.168.10.20" not in (agente_hash or "")

    def test_prefijo_ip_enmascara_IPv4(self):
        assert auth_service.prefijo_ip("10.0.0.5") == "10.0.0.0"
        assert auth_service.prefijo_ip("2001:db8:85a3::8a2e:370:7334").startswith(
            "2001:db8:85a3"
        )
        assert auth_service.prefijo_ip(None) is None
        assert auth_service.prefijo_ip("localhost") == "localhost"

    def test_sin_peticion_no_hay_metadatos(self):
        assert auth_service.metadatos_peticion(None) == (None, None)


class TestCierreGlobalDeSesiones:
    def test_logout_todo_invalida_sesiones_anteriores_y_renueva_la_actual(
        self, cliente
    ):
        sesion_a = _bootstrap(cliente)
        inicio_b = cliente.post(
            "/api/auth/login",
            json={"correo": CORREO_DUENO, "password": PASSWORD_DUENO},
        ).json()

        respuesta = cliente.post(
            "/api/auth/logout-todo", headers=_cabecera(inicio_b["token"])
        )
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["cerrado"] is True
        assert cuerpo["sesiones_revocadas"] >= 1
        assert cuerpo["token"]  # token nuevo para seguir operando

        # El token antiguo queda inutilizable.
        assert (
            cliente.get(
                "/api/auth/session", headers=_cabecera(inicio_b["token"])
            ).status_code
            == 401
        )
        assert (
            cliente.get(
                "/api/auth/session", headers=_cabecera(sesion_a["token"])
            ).status_code
            == 401
        )
        # El token nuevo si funciona.
        assert (
            cliente.get(
                "/api/auth/session", headers=_cabecera(cuerpo["token"])
            ).status_code
            == 200
        )

    def test_logout_todo_exige_sesion_valida(self, cliente):
        _bootstrap(cliente)
        respuesta = cliente.post("/api/auth/logout-todo")
        assert respuesta.status_code == 401


class TestSesionEstricta:
    def test_agente_distinto_invalida_la_sesion(self, cliente, monkeypatch):
        monkeypatch.setattr(auth_service, "SESION_ESTRICTA", True)
        _bootstrap(cliente)
        inicio = cliente.post(
            "/api/auth/login",
            json={"correo": CORREO_DUENO, "password": PASSWORD_DUENO},
            headers={"User-Agent": "Navegador-A"},
        ).json()
        assert inicio["token"]

        assert (
            cliente.get(
                "/api/auth/session",
                headers=_cabecera(inicio["token"], agente="Navegador-A"),
            ).status_code
            == 200
        )
        # Otro navegador o cliente reutilizando el token: se rechaza y revoca.
        assert (
            cliente.get(
                "/api/auth/session",
                headers=_cabecera(inicio["token"], agente="Navegador-B"),
            ).status_code
            == 401
        )
        assert (
            cliente.get(
                "/api/auth/session",
                headers=_cabecera(inicio["token"], agente="Navegador-B"),
            ).status_code
            == 401
        )

    def test_sesiones_antiguas_sin_metadatos_siguen_validas(
        self, cliente, monkeypatch
    ):
        monkeypatch.setattr(auth_service, "SESION_ESTRICTA", True)
        _bootstrap(cliente)

        # Sesion "legada": creada sin metadatos (como las emitidas antes de
        # esta fase). Debe seguir aceptandose desde cualquier navegador.
        from backend.app.core.seguridad import generar_token, hashear_token
        from backend.app.repositories import repositorio_sesiones

        token = generar_token()
        repositorio_sesiones().crear(
            Sesion(
                token_hash=hashear_token(token),
                id_usuario=1,
                expira_en=ahora_utc() + timedelta(hours=8),
            )
        )
        assert cliente.get(
            "/api/auth/session", headers=_cabecera(token, agente="Cualquiera")
        ).status_code == 200


class TestExpiracionYPurga:
    def test_sesion_caduca_segun_la_duracion_configurada(
        self, cliente, monkeypatch
    ):
        sesion = _bootstrap(cliente)
        monkeypatch.setattr(auth_service, "DURACION_SESION_HORAS", 0)
        nueva = cliente.post(
            "/api/auth/login",
            json={"correo": CORREO_DUENO, "password": PASSWORD_DUENO},
        ).json()
        assert (
            cliente.get("/api/auth/session", headers=_cabecera(nueva["token"]))
            .status_code
            == 401
        )
        # La sesion anterior (8h) sigue vigente.
        assert (
            cliente.get("/api/auth/session", headers=_cabecera(sesion["token"]))
            .status_code
            == 200
        )

    def test_login_purga_sesiones_caducas(self, cliente, monkeypatch):
        from backend.app.repositories import repositorio_sesiones

        _bootstrap(cliente)
        monkeypatch.setattr(auth_service, "DURACION_SESION_HORAS", 0)
        caduca = cliente.post(
            "/api/auth/login",
            json={"correo": CORREO_DUENO, "password": PASSWORD_DUENO},
        ).json()

        monkeypatch.setattr(auth_service, "DURACION_SESION_HORAS", 8)
        vigente = cliente.post(
            "/api/auth/login",
            json={"correo": CORREO_DUENO, "password": PASSWORD_DUENO},
        ).json()

        assert (
            cliente.get("/api/auth/session", headers=_cabecera(caduca["token"]))
            .status_code
            == 401
        )
        assert (
            cliente.get("/api/auth/session", headers=_cabecera(vigente["token"]))
            .status_code
            == 200
        )
        # La sesion del bootstrap y la nueva siguen vigentes; la caduca se purgo.
        assert repositorio_sesiones().contar_activas() == 2


class TestNormalizacionDeFechas:
    def test_datetimes_naive_se_tratan_como_utc(self):
        naive = datetime(2026, 1, 1, 12)
        assert _a_utc(naive).tzinfo is not None


class TestConcurrencia:
    def test_altas_simultaneas_con_correos_distintos_no_se_pierden(
        self, tmp_path, monkeypatch, dueno
    ):
        monkeypatch.setenv("OPTIROUTE_AUTH_DATA_DIR", str(tmp_path))
        total = 8
        resultados: list[dict] = []
        candado = threading.Lock()

        def crear(indice: int) -> None:
            try:
                respuesta = auth_service.crear_usuario(
                    dueno,
                    {
                        "nombres": "Persona",
                        "apellidos": "Prueba",
                        "correo": f"concurrente{indice}@optiroute.test",
                        "password": "Segura12345",
                        "rol": "OPERADOR",
                    },
                )
            except Exception as error:  # pragma: no cover
                respuesta = {"error": error}
            with candado:
                resultados.append(respuesta)

        hilos = [
            threading.Thread(target=crear, args=(indice,))
            for indice in range(total)
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        assert len(resultados) == total
        ids = [item.get("id_usuario") for item in resultados]
        assert None not in ids
        assert len(set(ids)) == total

        from backend.app.repositories import repositorio_cuentas

        assert len(repositorio_cuentas().listar()) == total + 1

    def test_altas_simultaneas_con_el_mismo_correo_solo_una_tiene_exito(
        self, tmp_path, monkeypatch, dueno
    ):
        monkeypatch.setenv("OPTIROUTE_AUTH_DATA_DIR", str(tmp_path))
        correo = "mismocorreo@optiroute.test"
        errores: list[auth_service.ErrorAutenticacion] = []
        exitos: list[dict] = []
        candado = threading.Lock()

        def crear() -> None:
            try:
                respuesta = auth_service.crear_usuario(
                    dueno,
                    {
                        "nombres": "Persona",
                        "apellidos": "Prueba",
                        "correo": correo,
                        "password": "Segura12345",
                        "rol": "OPERADOR",
                    },
                )
            except auth_service.ErrorAutenticacion as error:
                with candado:
                    errores.append(error)
                return
            with candado:
                exitos.append(respuesta)

        hilos = [threading.Thread(target=crear) for _ in range(6)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        assert len(exitos) == 1
        assert len(errores) == 5
        assert all(error.codigo == 409 for error in errores)

    def test_inicios_de_sesion_paralelos_emiten_tokens_distintos(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("OPTIROUTE_AUTH_DATA_DIR", str(tmp_path))
        from backend.app.repositories import repositorio_cuentas

        repositorio_cuentas().crear(
            Cuenta(
                id_usuario=0,
                nombres="Persona",
                apellidos="Paralela",
                correo="paralelo@optiroute.test",
                password_hash=hashear_password(PASSWORD_DUENO),
                rol="OPERADOR",
            )
        )
        tokens: list[str] = []
        candado = threading.Lock()

        def entrar() -> None:
            sesion = auth_service.login("paralelo@optiroute.test", PASSWORD_DUENO)
            with candado:
                tokens.append(sesion["token"])

        hilos = [threading.Thread(target=entrar) for _ in range(6)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        assert len(tokens) == 6
        assert len(set(tokens)) == 6
        from backend.app.repositories import repositorio_sesiones

        assert repositorio_sesiones().contar_activas() == 6

    def test_revocacion_concurrente_deja_todas_las_sesiones_invalidas(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("OPTIROUTE_AUTH_DATA_DIR", str(tmp_path))
        from backend.app.repositories import repositorio_cuentas, repositorio_sesiones

        cuenta = repositorio_cuentas().crear(
            Cuenta(
                id_usuario=0,
                nombres="Persona",
                apellidos="Revocada",
                correo="revocada@optiroute.test",
                password_hash=hashear_password(PASSWORD_DUENO),
                rol="OPERADOR",
            )
        )
        tokens = [
            auth_service.login("revocada@optiroute.test", PASSWORD_DUENO)["token"]
            for _ in range(5)
        ]

        def revocar() -> None:
            auth_service.cerrar_sesiones_usuario(cuenta)

        hilos = [threading.Thread(target=revocar) for _ in range(4)]
        hilos.append(threading.Thread(target=lambda: tokens.append(
            auth_service.login("revocada@optiroute.test", PASSWORD_DUENO)["token"]
        )))
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        cuenta_guardada = repositorio_cuentas().obtener(cuenta.id_usuario)
        assert cuenta_guardada is not None and cuenta_guardada.activo
        # Cierre final: ninguna sesion previa (ni la del login concurrente)
        # debe seguir aceptandose.
        auth_service.cerrar_sesiones_usuario(cuenta_guardada)
        for token in tokens:
            assert auth_service.resolver_sesion(token) is None
        assert repositorio_sesiones().contar_activas() == 0
