"""Pruebas de autenticacion, permisos por perfil y scoping de conductor.

Estas pruebas NO usan dependencias simuladas: crean cuentas reales en el
almacenamiento local provisional (directorio temporal) y ejercitan los
endpoints HTTP completos.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.api import pedidos as pedidos_api
from backend.app.api import rutas as rutas_api
from backend.app.main import app

CORREO_DUENO = "dueno@optiroute.test"
PASSWORD_DUENO = "Propietario123"


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("OPTIROUTE_AUTH_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("OPTIROUTE_AUTH_STORAGE", raising=False)
    monkeypatch.delenv("OPTIROUTE_DEMO", raising=False)
    return TestClient(app)


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


def _cabecera(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _crear_cuenta(cliente, token, correo, rol, id_conductor=None):
    cuerpo = {
        "nombres": "Persona",
        "apellidos": "Prueba",
        "correo": correo,
        "password": "Segura12345",
        "rol": rol,
    }
    if id_conductor is not None:
        cuerpo["id_conductor"] = id_conductor
    respuesta = cliente.post(
        "/api/auth/usuarios", json=cuerpo, headers=_cabecera(token)
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _login(cliente, correo, password="Segura12345"):
    respuesta = cliente.post(
        "/api/auth/login", json={"correo": correo, "password": password}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


class TestBootstrap:
    def test_estado_inicial_y_creacion_propietario(self, cliente):
        estado = cliente.get("/api/auth/estado").json()
        assert estado["propietario_creado"] is False

        sesion = _bootstrap(cliente)
        assert sesion["usuario"]["rol"] == "DESARROLLADOR"
        assert sesion["usuario"]["es_propietario"] is True
        assert "perfiles:administrar" in sesion["permisos"]

        assert cliente.get("/api/auth/estado").json()["propietario_creado"] is True

    def test_no_se_puede_crear_dos_propietarios(self, cliente):
        _bootstrap(cliente)
        repetido = cliente.post(
            "/api/auth/bootstrap",
            json={
                "nombres": "Otro",
                "apellidos": "Dueno",
                "correo": "otro@optiroute.test",
                "password": PASSWORD_DUENO,
            },
        )
        assert repetido.status_code == 409

    def test_password_debil_rechazada(self, cliente):
        respuesta = cliente.post(
            "/api/auth/bootstrap",
            json={
                "nombres": "Dueno",
                "apellidos": "Sistema",
                "correo": CORREO_DUENO,
                "password": "corta",
            },
        )
        assert respuesta.status_code == 400


class TestLogin:
    def test_login_ok(self, cliente):
        _bootstrap(cliente)
        respuesta = cliente.post(
            "/api/auth/login",
            json={"correo": CORREO_DUENO, "password": PASSWORD_DUENO},
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["token"]

    def test_login_password_incorrecta(self, cliente):
        _bootstrap(cliente)
        respuesta = cliente.post(
            "/api/auth/login",
            json={"correo": CORREO_DUENO, "password": "Incorrecta123"},
        )
        assert respuesta.status_code == 401

    def test_login_cuenta_desactivada(self, cliente):
        sesion = _bootstrap(cliente)
        token = sesion["token"]
        operador = _crear_cuenta(cliente, token, "oper@optiroute.test", "OPERADOR")
        cliente.patch(
            f"/api/auth/usuarios/{operador['id_usuario']}/estado",
            json={"activo": False},
            headers=_cabecera(token),
        )
        respuesta = cliente.post(
            "/api/auth/login",
            json={"correo": "oper@optiroute.test", "password": "Segura12345"},
        )
        assert respuesta.status_code == 403


class TestSesionYProteccion:
    def test_endpoint_protegido_sin_sesion_devuelve_401(self, cliente):
        _bootstrap(cliente)
        for ruta in ("/api/rutas", "/api/pedidos", "/api/clientes"):
            respuesta = cliente.get(ruta)
            assert respuesta.status_code == 401, ruta
            assert respuesta.headers.get("www-authenticate") == "Bearer"

    def test_sesion_actual_devuelve_usuario_y_permisos(self, cliente):
        sesion = _bootstrap(cliente)
        respuesta = cliente.get("/api/auth/session", headers=_cabecera(sesion["token"]))
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["usuario"]["correo"] == CORREO_DUENO
        assert cuerpo["token"] is None

    def test_logout_revoca_la_sesion(self, cliente):
        sesion = _bootstrap(cliente)
        cabecera = _cabecera(sesion["token"])
        assert cliente.post("/api/auth/logout", headers=cabecera).status_code == 200
        assert cliente.get("/api/auth/session", headers=cabecera).status_code == 401

    def test_cambio_de_password_revoca_sesiones(self, cliente):
        sesion = _bootstrap(cliente)
        cabecera = _cabecera(sesion["token"])
        respuesta = cliente.post(
            "/api/auth/cambiar-password",
            json={"password_actual": PASSWORD_DUENO, "password_nueva": "NuevaClave123"},
            headers=cabecera,
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["sesiones_revocadas"] >= 1
        assert cliente.get("/api/auth/session", headers=cabecera).status_code == 401
        assert cliente.post(
            "/api/auth/login",
            json={"correo": CORREO_DUENO, "password": "NuevaClave123"},
        ).status_code == 200

    def test_token_invalido_devuelve_401(self, cliente):
        _bootstrap(cliente)
        respuesta = cliente.get(
            "/api/auth/session", headers=_cabecera("token-falso")
        )
        assert respuesta.status_code == 401


class TestJerarquiaDePerfiles:
    def test_desarrollador_crea_cuentas_operativas(self, cliente):
        sesion = _bootstrap(cliente)
        token = sesion["token"]
        admin = _crear_cuenta(cliente, token, "admin@optiroute.test", "ADMINISTRADOR")
        conductor = _crear_cuenta(
            cliente, token, "conductor@optiroute.test", "CONDUCTOR", id_conductor=7
        )
        assert admin["rol"] == "ADMINISTRADOR"
        assert conductor["id_conductor"] == 7

    def test_conductor_requiere_id_conductor(self, cliente):
        sesion = _bootstrap(cliente)
        respuesta = cliente.post(
            "/api/auth/usuarios",
            json={
                "nombres": "Sin",
                "apellidos": "Vinculo",
                "correo": "sin@optiroute.test",
                "password": "Segura12345",
                "rol": "CONDUCTOR",
            },
            headers=_cabecera(sesion["token"]),
        )
        assert respuesta.status_code == 400

    def test_administrador_no_puede_crear_desarrollador(self, cliente):
        sesion = _bootstrap(cliente)
        _crear_cuenta(cliente, sesion["token"], "admin@optiroute.test", "ADMINISTRADOR")
        admin = _login(cliente, "admin@optiroute.test")
        respuesta = cliente.post(
            "/api/auth/usuarios",
            json={
                "nombres": "Nuevo",
                "apellidos": "Dev",
                "correo": "dev2@optiroute.test",
                "password": "Segura12345",
                "rol": "DESARROLLADOR",
            },
            headers=_cabecera(admin["token"]),
        )
        assert respuesta.status_code == 403

    def test_administrador_no_puede_crear_administrador(self, cliente):
        sesion = _bootstrap(cliente)
        _crear_cuenta(cliente, sesion["token"], "admin@optiroute.test", "ADMINISTRADOR")
        admin = _login(cliente, "admin@optiroute.test")
        respuesta = cliente.post(
            "/api/auth/usuarios",
            json={
                "nombres": "Otro",
                "apellidos": "Admin",
                "correo": "admin2@optiroute.test",
                "password": "Segura12345",
                "rol": "ADMINISTRADOR",
            },
            headers=_cabecera(admin["token"]),
        )
        assert respuesta.status_code == 403

    def test_no_auto_cambio_de_rol_ni_estado(self, cliente):
        sesion = _bootstrap(cliente)
        cabecera = _cabecera(sesion["token"])
        id_dueno = sesion["usuario"]["id_usuario"]

        assert cliente.patch(
            f"/api/auth/usuarios/{id_dueno}/rol",
            json={"rol": "OPERADOR"},
            headers=cabecera,
        ).status_code == 403
        assert cliente.patch(
            f"/api/auth/usuarios/{id_dueno}/estado",
            json={"activo": False},
            headers=cabecera,
        ).status_code == 403

    def test_cambio_de_rol_revoca_sesiones_del_objetivo(self, cliente):
        sesion = _bootstrap(cliente)
        operador = _crear_cuenta(
            cliente, sesion["token"], "oper@optiroute.test", "OPERADOR"
        )
        sesion_oper = _login(cliente, "oper@optiroute.test")

        cliente.patch(
            f"/api/auth/usuarios/{operador['id_usuario']}/rol",
            json={"rol": "ADMINISTRADOR"},
            headers=_cabecera(sesion["token"]),
        )
        assert cliente.get(
            "/api/auth/session", headers=_cabecera(sesion_oper["token"])
        ).status_code == 401

    def test_cambio_de_rol_a_conductor_exige_vinculo(self, cliente):
        sesion = _bootstrap(cliente)
        operador = _crear_cuenta(
            cliente, sesion["token"], "oper@optiroute.test", "OPERADOR"
        )
        respuesta = cliente.patch(
            f"/api/auth/usuarios/{operador['id_usuario']}/rol",
            json={"rol": "CONDUCTOR"},
            headers=_cabecera(sesion["token"]),
        )
        assert respuesta.status_code == 400

    def test_administrador_no_puede_cambiar_roles(self, cliente):
        # Cambiar perfil exige perfiles:administrar (solo DESARROLLADOR).
        sesion = _bootstrap(cliente)
        _crear_cuenta(cliente, sesion["token"], "admin@optiroute.test", "ADMINISTRADOR")
        operador = _crear_cuenta(
            cliente, sesion["token"], "oper@optiroute.test", "OPERADOR"
        )
        admin = _login(cliente, "admin@optiroute.test")
        assert cliente.patch(
            f"/api/auth/usuarios/{operador['id_usuario']}/rol",
            json={"rol": "CONDUCTOR"},
            headers=_cabecera(admin["token"]),
        ).status_code == 403
        # El desarrollador si puede cambiar el perfil (aqui falla por el vinculo).
        assert cliente.patch(
            f"/api/auth/usuarios/{operador['id_usuario']}/rol",
            json={"rol": "CONDUCTOR"},
            headers=_cabecera(sesion["token"]),
        ).status_code == 400

    def test_listado_nunca_expone_hashes(self, cliente):
        sesion = _bootstrap(cliente)
        _crear_cuenta(cliente, sesion["token"], "oper@optiroute.test", "OPERADOR")
        listado = cliente.get(
            "/api/auth/usuarios", headers=_cabecera(sesion["token"])
        ).json()
        assert listado
        for cuenta in listado:
            assert "password_hash" not in cuenta
            assert "password" not in cuenta


class TestPermisosEndpoints:
    def test_operador_no_accede_a_administracion_de_cuentas(self, cliente):
        sesion = _bootstrap(cliente)
        _crear_cuenta(cliente, sesion["token"], "oper@optiroute.test", "OPERADOR")
        oper = _login(cliente, "oper@optiroute.test")
        cabecera = _cabecera(oper["token"])
        assert cliente.get("/api/auth/usuarios", headers=cabecera).status_code == 403
        assert cliente.get("/api/auth/diagnostico", headers=cabecera).status_code == 403

    def test_desarrollador_accede_a_diagnostico_y_auditoria(self, cliente):
        sesion = _bootstrap(cliente)
        cabecera = _cabecera(sesion["token"])
        assert cliente.get("/api/auth/diagnostico", headers=cabecera).status_code == 200
        assert cliente.get("/api/auth/auditoria", headers=cabecera).status_code == 200


class TestRestablecerPassword:
    def test_desarrollador_restablece_y_revoca_sesiones(self, cliente):
        sesion = _bootstrap(cliente)
        operador = _crear_cuenta(
            cliente, sesion["token"], "oper@optiroute.test", "OPERADOR"
        )
        sesion_oper = _login(cliente, "oper@optiroute.test")

        respuesta = cliente.post(
            f"/api/auth/usuarios/{operador['id_usuario']}/password",
            json={"password_nueva": "ClaveNueva2025"},
            headers=_cabecera(sesion["token"]),
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["sesiones_revocadas"] >= 1
        assert (
            cliente.get(
                "/api/auth/session", headers=_cabecera(sesion_oper["token"])
            ).status_code
            == 401
        )
        assert _login(cliente, "oper@optiroute.test", "ClaveNueva2025")["token"]

    def test_no_se_restablece_la_propia_cuenta(self, cliente):
        sesion = _bootstrap(cliente)
        respuesta = cliente.post(
            f"/api/auth/usuarios/{sesion['usuario']['id_usuario']}/password",
            json={"password_nueva": "ClaveNueva2025"},
            headers=_cabecera(sesion["token"]),
        )
        assert respuesta.status_code == 400

    def test_password_debil_rechazada(self, cliente):
        sesion = _bootstrap(cliente)
        operador = _crear_cuenta(
            cliente, sesion["token"], "oper@optiroute.test", "OPERADOR"
        )
        respuesta = cliente.post(
            f"/api/auth/usuarios/{operador['id_usuario']}/password",
            json={"password_nueva": "corta"},
            headers=_cabecera(sesion["token"]),
        )
        assert respuesta.status_code == 400

    def test_administrador_restablece_operador(self, cliente):
        sesion = _bootstrap(cliente)
        _crear_cuenta(cliente, sesion["token"], "admin@optiroute.test", "ADMINISTRADOR")
        operador = _crear_cuenta(
            cliente, sesion["token"], "oper@optiroute.test", "OPERADOR"
        )
        admin = _login(cliente, "admin@optiroute.test")
        respuesta = cliente.post(
            f"/api/auth/usuarios/{operador['id_usuario']}/password",
            json={"password_nueva": "ClaveNueva2025"},
            headers=_cabecera(admin["token"]),
        )
        assert respuesta.status_code == 200
        assert _login(cliente, "oper@optiroute.test", "ClaveNueva2025")["token"]

    def test_administrador_no_restablece_desarrollador(self, cliente):
        sesion = _bootstrap(cliente)
        _crear_cuenta(cliente, sesion["token"], "admin@optiroute.test", "ADMINISTRADOR")
        admin = _login(cliente, "admin@optiroute.test")
        respuesta = cliente.post(
            f"/api/auth/usuarios/{sesion['usuario']['id_usuario']}/password",
            json={"password_nueva": "ClaveNueva2025"},
            headers=_cabecera(admin["token"]),
        )
        assert respuesta.status_code == 403

    def test_operador_no_puede_restablecer(self, cliente):
        sesion = _bootstrap(cliente)
        operador = _crear_cuenta(
            cliente, sesion["token"], "oper@optiroute.test", "OPERADOR"
        )
        oper = _login(cliente, "oper@optiroute.test")
        respuesta = cliente.post(
            f"/api/auth/usuarios/{operador['id_usuario']}/password",
            json={"password_nueva": "ClaveNueva2025"},
            headers=_cabecera(oper["token"]),
        )
        assert respuesta.status_code == 403


class TestUltimoDesarrolladorActivo:
    """El sistema jamas puede quedarse sin un desarrollador activo."""

    def _escenario_un_solo_dev_activo(self):
        from backend.app.core.seguridad import hashear_password
        from backend.app.repositories import repositorio_cuentas
        from backend.app.repositories.modelos import Cuenta

        repo = repositorio_cuentas()
        unico = repo.crear(
            Cuenta(
                id_usuario=0,
                nombres="Unico",
                apellidos="Dev",
                correo="unico@optiroute.test",
                password_hash=hashear_password("Segura12345"),
                rol="DESARROLLADOR",
                activo=True,
            )
        )
        # Segundo desarrollador inactivo: no cuenta como respaldo activo.
        repo.crear(
            Cuenta(
                id_usuario=0,
                nombres="Inactivo",
                apellidos="Dev",
                correo="inactivo@optiroute.test",
                password_hash=hashear_password("Segura12345"),
                rol="DESARROLLADOR",
                activo=False,
            )
        )
        return unico

    def test_no_desactiva_ni_cambia_rol_del_ultimo_dev_activo(self, cliente):
        from backend.app.repositories import repositorio_cuentas
        from backend.app.services import auth_service

        unico = self._escenario_un_solo_dev_activo()
        repo = repositorio_cuentas()
        # Solicitante desarrollador (inactivo): el guarda debe impedir dejar al
        # sistema sin ningun desarrollador activo de respaldo.
        solicitante = repo.obtener_por_correo("inactivo@optiroute.test")

        with pytest.raises(auth_service.ErrorAutenticacion) as desactivar:
            auth_service.cambiar_estado(solicitante, unico.id_usuario, False)
        assert desactivar.value.codigo == 409

        with pytest.raises(auth_service.ErrorAutenticacion) as cambiar:
            auth_service.cambiar_rol(solicitante, unico.id_usuario, "OPERADOR")
        assert cambiar.value.codigo == 409

        # El desarrollador sigue activo con su perfil intacto.
        assert repo.obtener(unico.id_usuario).activo is True
        assert repo.obtener(unico.id_usuario).rol == "DESARROLLADOR"

    def test_con_respaldo_si_permite_desactivar_desarrollador(self, cliente):
        from backend.app.repositories import repositorio_cuentas
        from backend.app.repositories.modelos import Cuenta
        from backend.app.services import auth_service

        unico = self._escenario_un_solo_dev_activo()
        repo = repositorio_cuentas()
        respaldo = repo.crear(
            Cuenta(
                id_usuario=0,
                nombres="Respaldo",
                apellidos="Dev",
                correo="respaldo@optiroute.test",
                password_hash=unico.password_hash,
                rol="DESARROLLADOR",
                activo=True,
            )
        )
        solicitante = repo.obtener_por_correo("inactivo@optiroute.test")

        respuesta = auth_service.cambiar_estado(solicitante, unico.id_usuario, False)
        assert respuesta["activo"] is False
        assert respuesta["id_usuario"] == unico.id_usuario
        assert repo.obtener(respaldo.id_usuario).activo is True
        assert repo.obtener(respaldo.id_usuario).rol == "DESARROLLADOR"


class TestScopingConductor:
    def _crear_conductor_logueado(self, cliente):
        sesion = _bootstrap(cliente)
        _crear_cuenta(
            cliente,
            sesion["token"],
            "conductor@optiroute.test",
            "CONDUCTOR",
            id_conductor=5,
        )
        return _login(cliente, "conductor@optiroute.test")

    def test_conductor_solo_ve_sus_rutas(self, cliente, monkeypatch):
        conductor = self._crear_conductor_logueado(cliente)
        monkeypatch.setattr(
            rutas_api,
            "listar_rutas",
            lambda: [
                {"id_ruta": 1, "codigo": "R1", "conductor": {"id_conductor": 5}},
                {"id_ruta": 2, "codigo": "R2", "conductor": {"id_conductor": 9}},
                {"id_ruta": 3, "codigo": "R3", "conductor": None},
            ],
        )
        respuesta = cliente.get(
            "/api/rutas", headers=_cabecera(conductor["token"])
        )
        assert respuesta.status_code == 200
        assert [ruta["id_ruta"] for ruta in respuesta.json()] == [1]

    def test_conductor_no_accede_a_ruta_ajena(self, cliente, monkeypatch):
        conductor = self._crear_conductor_logueado(cliente)
        monkeypatch.setattr(
            rutas_api,
            "obtener_ruta",
            lambda id_ruta: {
                "id_ruta": id_ruta,
                "codigo": "R2",
                "conductor": {"id_conductor": 9},
            },
        )
        respuesta = cliente.get(
            "/api/rutas/2", headers=_cabecera(conductor["token"])
        )
        assert respuesta.status_code == 403

    def test_conductor_solo_ve_sus_pedidos(self, cliente, monkeypatch):
        conductor = self._crear_conductor_logueado(cliente)
        capturado = {}

        def fake_listar(id_conductor):
            capturado["id_conductor"] = id_conductor
            return []

        monkeypatch.setattr(
            pedidos_api, "listar_pedidos_por_conductor", fake_listar
        )
        respuesta = cliente.get(
            "/api/pedidos", headers=_cabecera(conductor["token"])
        )
        assert respuesta.status_code == 200
        assert respuesta.json() == []
        assert capturado["id_conductor"] == 5

    def test_conductor_no_accede_a_pedido_ajeno(self, cliente, monkeypatch):
        conductor = self._crear_conductor_logueado(cliente)
        monkeypatch.setattr(
            pedidos_api, "obtener_pedido", lambda id_pedido: {"id_pedido": id_pedido}
        )
        monkeypatch.setattr(pedidos_api, "conductor_de_pedido", lambda id_pedido: 9)
        respuesta = cliente.get(
            "/api/pedidos/99", headers=_cabecera(conductor["token"])
        )
        assert respuesta.status_code == 403


class TestAlmacenamiento:
    def test_storage_supabase_no_esta_implementado(self, cliente, monkeypatch):
        from backend.app.services import auth_service

        monkeypatch.setenv("OPTIROUTE_AUTH_STORAGE", "supabase")
        with pytest.raises(NotImplementedError):
            auth_service.login("x@optiroute.test", "Segura12345")
