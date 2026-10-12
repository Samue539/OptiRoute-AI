"""Pruebas del sistema RBAC: minimo privilegio y autorizacion real.

Verifican que el backend (no los botones del frontend) deniega por defecto:

* OPERADOR solo lee: no crea ni edita pedidos, clientes ni rutas, no
  planifica ni asigna recursos.
* OPERADOR y CONDUCTOR solo pueden fijar los estados expresamente
  autorizados.
* CONDUCTOR no accede a rutas ni pedidos ajenos.
* ADMINISTRADOR no accede a funciones tecnicas del DESARROLLADOR.
* DESARROLLADOR conserva la administracion completa.
* Los endpoints responden 403 ante operaciones no autorizadas.
* La matriz de permisos expuesta por la API coincide con la del backend.
* Un cambio de perfil invalida las sesiones anteriores.
"""

from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from backend.app.api import pedidos as pedidos_api
from backend.app.api import rutas as rutas_api
from backend.app.api import optimizacion as optimizacion_api
from backend.app.core.permisos import (
    Permiso,
    Rol,
    alcance_estado_pedido,
    alcance_estado_ruta,
    catalogo_permisos,
    estado_pedido_autorizado,
    estado_ruta_autorizado,
    estados_pedido_permitidos,
    estados_ruta_permitidos,
    permisos_de,
)
from backend.app.main import app

CORREO_DUENO = "dueno@optiroute.test"
PASSWORD_DUENO = "Propietario123"


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("OPTIROUTE_AUTH_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("OPTIROUTE_AUTH_STORAGE", raising=False)
    monkeypatch.delenv("OPTIROUTE_DEMO", raising=False)
    return TestClient(app)


@pytest.fixture
def escenario(cliente):
    """Un DESARROLLADOR con un ADMINISTRADOR, OPERADOR y CONDUCTOR creados."""

    dueno = cliente.post(
        "/api/auth/bootstrap",
        json={
            "nombres": "Dueno",
            "apellidos": "Sistema",
            "correo": CORREO_DUENO,
            "password": PASSWORD_DUENO,
        },
    ).json()

    def _crear(correo: str, rol: str, id_conductor: int | None = None) -> dict:
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
            "/api/auth/usuarios", json=cuerpo, headers=_cabecera(dueno["token"])
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def _login(correo: str) -> dict:
        respuesta = cliente.post(
            "/api/auth/login", json={"correo": correo, "password": "Segura12345"}
        )
        assert respuesta.status_code == 200, respuesta.text
        return respuesta.json()

    return {
        "dueno": dueno["token"],
        "admin": _login(_crear("admin@optiroute.test", "ADMINISTRADOR")["correo"]),
        "oper": _login(_crear("oper@optiroute.test", "OPERADOR")["correo"]),
        "cond": _login(
            _crear("cond@optiroute.test", "CONDUCTOR", id_conductor=7)["correo"]
        ),
        "_crear": _crear,
        "_login": _login,
    }


def _cabecera(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _token(escenario: dict, clave: str) -> str:
    """Token de una cuenta del escenario (el dueño se guarda como texto)."""

    valor = escenario[clave]
    return valor if isinstance(valor, str) else valor["token"]


def _pedido_falso(**cambios) -> dict:
    """Pedido con la forma completa de ``PedidoCatalogo``."""

    pedido = {
        "id_pedido": 1,
        "codigo": "PED-001",
        "id_cliente": 1,
        "id_direccion_entrega": 1,
        "descripcion": "Prueba",
        "peso_kg": 5.0,
        "volumen_m3": 0.1,
        "prioridad": "NORMAL",
        "estado": "PENDIENTE",
        "fecha_solicitada": None,
        "destino": None,
        "estado_entrega": "PENDIENTE",
        "creado_en": "2026-10-10T00:00:00+00:00",
    }
    pedido.update(cambios)
    return pedido


# ---------------------------------------------------------------------------
# OBJETIVO 2 y 3: OPERADOR de minimo privilegio
# ---------------------------------------------------------------------------

class TestOperadorSoloLee:
    def test_no_puede_crear_pedidos(self, cliente, escenario):
        respuesta = cliente.post(
            "/api/pedidos",
            json={
                "codigo": "PED-001",
                "id_cliente": 1,
                "id_direccion_entrega": 1,
                "descripcion": "Prueba",
                "peso_kg": 5,
                "volumen_m3": 0.1,
                "prioridad": "NORMAL",
            },
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 403

    def test_no_puede_editar_pedidos(self, cliente, escenario):
        respuesta = cliente.patch(
            "/api/pedidos/1",
            json={"descripcion": "Cambio no autorizado"},
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 403

    def test_no_puede_crear_clientes(self, cliente, escenario):
        # No existe ni el endpoint ni el permiso: el catalogo ya no los declara.
        catalogo = cliente.get(
            "/api/auth/permisos", headers=_cabecera(escenario["dueno"])
        ).json()
        codigos = {permiso["codigo"] for permiso in catalogo["permisos"]}
        assert "clientes:crear" not in codigos
        assert "clientes:editar" not in codigos
        assert not hasattr(Permiso, "CLIENTES_CREAR")

    def test_no_puede_crear_rutas(self, cliente, escenario):
        respuesta = cliente.post(
            "/api/rutas",
            json={"origen": 1, "destino": 2},
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 403

    def test_no_puede_guardar_planificacion(self, cliente, escenario):
        respuesta = cliente.post(
            "/api/rutas/planificada",
            json={
                "origen": 1,
                "pedidos": [],
                "id_conductor": 7,
                "id_vehiculo": 1,
                "regresar_origen": True,
                "clave_idempotencia": "clave-1",
            },
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 403

    def test_no_puede_agregar_pedidos_a_una_ruta(self, cliente, escenario):
        respuesta = cliente.post(
            "/api/rutas/1/pedidos",
            json={"id_pedido": 1, "orden_entrega": 1},
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 403

    def test_no_puede_asignar_recursos(self, cliente, escenario):
        respuesta = cliente.patch(
            "/api/rutas/1/asignacion",
            json={"id_conductor": 7, "id_vehiculo": 1},
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 403

    def test_no_puede_planificar(self, cliente, escenario, monkeypatch):
        for ruta in ("/api/optimizacion/multi-entrega", "/api/optimizacion/planificar"):
            cuerpo = (
                {"origen": 1, "destinos": [2], "regresar_origen": True}
                if "multi" in ruta
                else {"origen": 1, "pedidos": [1], "id_vehiculo": 1}
            )
            respuesta = cliente.post(
                ruta, json=cuerpo, headers=_cabecera(escenario["oper"]["token"])
            )
            assert respuesta.status_code == 403, ruta

    def test_puede_consultar_pedidos_clientes_y_rutas(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(pedidos_api, "listar_pedidos", lambda: [])
        monkeypatch.setattr(pedidos_api, "obtener_pedido", lambda _: None)
        cabecera = _cabecera(escenario["oper"]["token"])
        assert cliente.get("/api/pedidos", headers=cabecera).status_code == 200
        assert cliente.get("/api/clientes", headers=cabecera).status_code in (200, 404)
        assert cliente.get("/api/vehiculos", headers=cabecera).status_code in (200, 500)
        assert cliente.get("/api/conductores", headers=cabecera).status_code in (200, 500)


class TestOperadorEstadosLimitados:
    def test_solo_puede_cancelar_pedidos(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(
            pedidos_api,
            "actualizar_estado_pedido",
            lambda id_pedido, estado: _pedido_falso(id_pedido=id_pedido, estado=estado),
        )
        cabecera = _cabecera(escenario["oper"]["token"])
        permitido = cliente.patch(
            "/api/pedidos/1/estado",
            json={"estado": "CANCELADO", "motivo": "El cliente anulo la compra."},
            headers=cabecera,
        )
        assert permitido.status_code == 200, permitido.text
        assert permitido.json()["estado"] == "CANCELADO"

        denegado = cliente.patch(
            "/api/pedidos/1/estado",
            json={"estado": "ENTREGADO"},
            headers=cabecera,
        )
        assert denegado.status_code == 403

    def test_solo_puede_cancelar_rutas(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(
            rutas_api,
            "obtener_ruta",
            lambda id_ruta: {
                "id_ruta": id_ruta,
                "codigo": "R1",
                "estado": "PLANIFICADA",
                "conductor": {"id_conductor": 9},
            },
        )
        monkeypatch.setattr(
            rutas_api,
            "actualizar_estado_ruta",
            lambda id_ruta, estado_nuevo: {
                "id_ruta": id_ruta,
                "estado": estado_nuevo,
            },
        )
        cabecera = _cabecera(escenario["oper"]["token"])
        permitido = cliente.patch(
            "/api/rutas/1/estado",
            json={"estado": "CANCELADA", "motivo": "El cliente reprogramo la entrega."},
            headers=cabecera,
        )
        assert permitido.status_code == 200, permitido.text

        for estado in ("ASIGNADA", "EN_RUTA", "COMPLETADA"):
            denegado = cliente.patch(
                "/api/rutas/1/estado", json={"estado": estado}, headers=cabecera
            )
            assert denegado.status_code == 403, estado


class TestConductorAlcancePropio:
    def _rutas(self, monkeypatch, id_conductor: int):
        monkeypatch.setattr(
            rutas_api,
            "listar_rutas",
            lambda: [
                {"id_ruta": 1, "codigo": "R1", "estado": "ASIGNADA", "conductor": {"id_conductor": id_conductor}},
                {"id_ruta": 2, "codigo": "R2", "estado": "ASIGNADA", "conductor": {"id_conductor": 99}},
            ],
        )

    def test_no_ve_rutas_ajenas(self, cliente, escenario, monkeypatch):
        self._rutas(monkeypatch, id_conductor=7)
        cabecera = _cabecera(escenario["cond"]["token"])
        rutas = cliente.get("/api/rutas", headers=cabecera).json()
        assert [ruta["id_ruta"] for ruta in rutas] == [1]

    def test_no_abre_ruta_ajena(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(
            rutas_api,
            "obtener_ruta",
            lambda id_ruta: {"id_ruta": id_ruta, "conductor": {"id_conductor": 99}},
        )
        respuesta = cliente.get(
            "/api/rutas/2", headers=_cabecera(escenario["cond"]["token"])
        )
        assert respuesta.status_code == 403

    def test_solo_estados_autorizados_en_sus_rutas(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(
            rutas_api,
            "obtener_ruta",
            lambda id_ruta: {"id_ruta": id_ruta, "conductor": {"id_conductor": 7}},
        )
        monkeypatch.setattr(
            rutas_api,
            "actualizar_estado_ruta",
            lambda id_ruta, estado_nuevo: {
                "id_ruta": id_ruta,
                "estado": estado_nuevo,
            },
        )
        cabecera = _cabecera(escenario["cond"]["token"])
        for estado in ("EN_RUTA", "COMPLETADA"):
            respuesta = cliente.patch(
                "/api/rutas/1/estado", json={"estado": estado}, headers=cabecera
            )
            assert respuesta.status_code == 200, estado
        # Estados operativos internos que no le corresponden.
        assert (
            cliente.patch(
                "/api/rutas/1/estado", json={"estado": "ASIGNADA"}, headers=cabecera
            ).status_code
            == 403
        )

    def test_no_cambia_estado_de_ruta_ajena(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(
            rutas_api,
            "obtener_ruta",
            lambda id_ruta: {"id_ruta": id_ruta, "conductor": {"id_conductor": 99}},
        )
        respuesta = cliente.patch(
            "/api/rutas/2/estado",
            json={"estado": "EN_RUTA"},
            headers=_cabecera(escenario["cond"]["token"]),
        )
        assert respuesta.status_code == 403

    def test_solo_confirma_entrega_de_sus_pedidos(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(pedidos_api, "conductor_de_pedido", lambda id_pedido: 7)
        monkeypatch.setattr(
            pedidos_api, "obtener_ruta_de_pedido", lambda id_pedido: {"id_ruta": 1}
        )
        monkeypatch.setattr(
            pedidos_api, "obtener_pedido", lambda id_pedido: _pedido_falso(id_pedido=id_pedido)
        )
        monkeypatch.setattr(pedidos_api, "confirmar_entrega_ruta", lambda *args: None)
        cabecera = _cabecera(escenario["cond"]["token"])

        assert (
            cliente.patch(
                "/api/pedidos/1/estado", json={"estado": "ENTREGADO"}, headers=cabecera
            ).status_code
            == 200
        )
        # Cualquier otro estado queda fuera de su alcance.
        assert (
            cliente.patch(
                "/api/pedidos/1/estado",
                json={"estado": "CANCELADO", "motivo": "Pedido duplicado por error."},
                headers=cabecera,
            ).status_code
            == 403
        )

    def test_no_confirma_entrega_de_pedido_ajeno(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(pedidos_api, "conductor_de_pedido", lambda id_pedido: 99)
        respuesta = cliente.patch(
            "/api/pedidos/1/estado",
            json={"estado": "ENTREGADO"},
            headers=_cabecera(escenario["cond"]["token"]),
        )
        assert respuesta.status_code == 403


# ---------------------------------------------------------------------------
# OBJETIVO 3: separacion ADMINISTRADOR / DESARROLLADOR
# ---------------------------------------------------------------------------

class TestAdministradorSinAccesoTecnico:
    def test_no_accede_a_diagnostico_ni_auditoria(self, cliente, escenario):
        cabecera = _cabecera(escenario["admin"]["token"])
        assert cliente.get("/api/auth/diagnostico", headers=cabecera).status_code == 403
        assert cliente.get("/api/auth/auditoria", headers=cabecera).status_code == 403

    def test_no_administra_perfiles(self, cliente, escenario):
        oper = escenario["_crear"]("oper2@optiroute.test", "OPERADOR")
        respuesta = cliente.patch(
            f"/api/auth/usuarios/{oper['id_usuario']}/rol",
            json={"rol": "ADMINISTRADOR"},
            headers=_cabecera(escenario["admin"]["token"]),
        )
        assert respuesta.status_code == 403

    def test_no_usa_configuracion_tecnica(self, cliente, escenario):
        respuesta = cliente.patch(
            "/api/grafo/nodos/1/ubicacion",
            json={"latitud": -0.1, "longitud": -78.5},
            headers=_cabecera(escenario["admin"]["token"]),
        )
        assert respuesta.status_code == 403

    def test_no_puede_crear_desarrollador(self, cliente, escenario):
        respuesta = cliente.post(
            "/api/auth/usuarios",
            json={
                "nombres": "Nuevo",
                "apellidos": "Dev",
                "correo": "dev2@optiroute.test",
                "password": "Segura12345",
                "rol": "DESARROLLADOR",
            },
            headers=_cabecera(escenario["admin"]["token"]),
        )
        assert respuesta.status_code == 403

    def test_si_gestiona_operacion_y_cuentas_operativas(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(
            pedidos_api,
            "crear_pedido",
            lambda datos: _pedido_falso(codigo=datos.get("codigo", "PED-777")),
        )
        monkeypatch.setattr(
            rutas_api,
            "obtener_ruta",
            lambda id_ruta: {"id_ruta": id_ruta, "conductor": {"id_conductor": 99}},
        )
        monkeypatch.setattr(
            rutas_api,
            "actualizar_estado_ruta",
            lambda id_ruta, estado_nuevo: {
                "id_ruta": id_ruta,
                "estado": estado_nuevo,
            },
        )
        cabecera = _cabecera(escenario["admin"]["token"])

        creacion = cliente.post(
            "/api/pedidos",
            json={
                "codigo": "PED-777",
                "id_cliente": 1,
                "id_direccion_entrega": 1,
                "descripcion": "Prueba",
                "peso_kg": 5,
                "volumen_m3": 0.1,
                "prioridad": "NORMAL",
            },
            headers=cabecera,
        )
        assert creacion.status_code == 201, creacion.text

        alta = cliente.post(
            "/api/auth/usuarios",
            json={
                "nombres": "Otra",
                "apellidos": "Cuenta",
                "correo": "oper4@optiroute.test",
                "password": "Segura12345",
                "rol": "OPERADOR",
            },
            headers=cabecera,
        )
        assert alta.status_code == 201, alta.text
        assert alta.json()["rol"] == "OPERADOR"


class TestDesarrolladorConservaAcceso:
    def test_crea_administradores_y_accede_a_tecnologia(self, cliente, escenario):
        cabecera = _cabecera(escenario["dueno"])
        alta = cliente.post(
            "/api/auth/usuarios",
            json={
                "nombres": "Otra",
                "apellidos": "Admin",
                "correo": "admin2@optiroute.test",
                "password": "Segura12345",
                "rol": "ADMINISTRADOR",
            },
            headers=cabecera,
        )
        assert alta.status_code == 201, alta.text
        assert cliente.get("/api/auth/diagnostico", headers=cabecera).status_code == 200
        assert cliente.get("/api/auth/auditoria", headers=cabecera).status_code == 200

    def test_permisos_efectivos_completos(self, cliente, escenario):
        sesion = cliente.get(
            "/api/auth/session", headers=_cabecera(escenario["dueno"])
        ).json()
        for permiso in (
            "perfiles:administrar",
            "cuentas:administradores",
            "configuracion:tecnica",
            "diagnostico:ver",
            "auditoria:ver",
            "rutas:planificar",
            "pedidos:crear",
        ):
            assert permiso in sesion["permisos"], permiso

    def test_no_puede_desactivar_al_ultimo_desarrollador(self, cliente, escenario):
        # El propietario es inmutable y el ultimo desarrollador activo.
        respuesta = cliente.patch(
            "/api/auth/usuarios/1/estado",
            json={"activo": False},
            headers=_cabecera(escenario["dueno"]),
        )
        assert respuesta.status_code == 403


# ---------------------------------------------------------------------------
# OBJETIVO 4: la matriz expuesta coincide con la matriz del backend
# ---------------------------------------------------------------------------

class TestMatrizDePermisos:
    def test_catalogo_requiere_sesion(self, cliente):
        assert cliente.get("/api/auth/permisos").status_code == 401

    def test_catalogo_coincide_con_la_matriz_interna(self, cliente, escenario):
        catalogo = cliente.get(
            "/api/auth/permisos", headers=_cabecera(escenario["dueno"])
        ).json()
        for rol in catalogo["roles"]:
            esperado = sorted(permiso.value for permiso in permisos_de(rol["rol"]))
            assert rol["permisos"] == esperado, rol["rol"]

    def test_catalogo_permisos_efectivos_del_usuario(self, cliente, escenario):
        for clave, rol in (
            ("oper", "OPERADOR"),
            ("admin", "ADMINISTRADOR"),
            ("cond", "CONDUCTOR"),
            ("dueno", "DESARROLLADOR"),
        ):
            catalogo = cliente.get(
                "/api/auth/permisos", headers=_cabecera(_token(escenario, clave))
            ).json()
            assert catalogo["rol_actual"] == rol
            assert catalogo["efectivos"] == sorted(
                permiso.value for permiso in permisos_de(rol)
            )

    def test_catalogo_tiene_nombres_modulos_y_limites(self, cliente, escenario):
        catalogo = cliente.get(
            "/api/auth/permisos", headers=_cabecera(escenario["dueno"])
        ).json()
        assert {modulo["id"] for modulo in catalogo["modulos"]} == {
            "panel",
            "pedidos",
            "clientes",
            "recursos",
            "rutas",
            "distribucion",
            "ia",
            "reportes",
            "cuentas",
            "sistema",
        }
        for permiso in catalogo["permisos"]:
            assert permiso["nombre"]
            assert permiso["descripcion"]
            assert permiso["modulo"] in {m["id"] for m in catalogo["modulos"]}
        limitados = {
            permiso["codigo"]: permiso["limite"]
            for permiso in catalogo["permisos"]
            if permiso["ambito"] == "limitado"
        }
        assert set(limitados) == {"pedidos:estado_limitado", "rutas:estado_limitado"}
        assert all(limitados.values())

    def test_catalogo_incluye_texto_de_estados_por_rol(self, cliente, escenario):
        catalogo = cliente.get(
            "/api/auth/permisos", headers=_cabecera(escenario["dueno"])
        ).json()
        por_rol = {rol["rol"]: rol for rol in catalogo["roles"]}
        assert "CANCELADO" in por_rol["OPERADOR"]["estados_pedido"]
        assert "ENTREGADO" in por_rol["CONDUCTOR"]["estados_pedido"]
        assert "EN_RUTA" in por_rol["CONDUCTOR"]["estados_ruta"]
        assert "CANCELADA" in por_rol["OPERADOR"]["estados_ruta"]
        assert "Cualquier" in por_rol["ADMINISTRADOR"]["estados_pedido"]

    def test_catalogo_expone_reglas_de_seguridad(self, cliente, escenario):
        catalogo = cliente.get(
            "/api/auth/permisos", headers=_cabecera(escenario["dueno"])
        ).json()
        titulos = {regla["titulo"] for regla in catalogo["reglas"]}
        assert {
            "Denegacion por defecto",
            "Minimo privilegio",
            "Ultimo desarrollador",
            "Sin escalamiento de privilegios",
            "Revocacion al cambiar de perfil",
        } <= titulos


class TestCancelacionConMotivoYAuditoria:
    """Las cancelaciones exigen motivo y quedan registradas."""

    def test_cancelar_pedido_sin_motivo_se_rechaza(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(
            pedidos_api,
            "actualizar_estado_pedido",
            lambda id_pedido, estado: _pedido_falso(id_pedido=id_pedido, estado=estado),
        )
        respuesta = cliente.patch(
            "/api/pedidos/1/estado",
            json={"estado": "CANCELADO"},
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 422
        assert "motivo" in respuesta.text

    def test_motivo_demasiado_corto_se_rechaza(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(
            pedidos_api,
            "actualizar_estado_pedido",
            lambda id_pedido, estado: _pedido_falso(id_pedido=id_pedido, estado=estado),
        )
        respuesta = cliente.patch(
            "/api/pedidos/1/estado",
            json={"estado": "CANCELADO", "motivo": "no"},
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 422

    def test_cancelar_pedido_genera_registro_de_auditoria(
        self, cliente, escenario, monkeypatch
    ):
        monkeypatch.setattr(
            pedidos_api,
            "actualizar_estado_pedido",
            lambda id_pedido, estado: _pedido_falso(id_pedido=id_pedido, estado=estado),
        )
        respuesta = cliente.patch(
            "/api/pedidos/1/estado",
            json={"estado": "CANCELADO", "motivo": "El cliente anulo la compra."},
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 200, respuesta.text

        eventos = cliente.get(
            "/api/auth/auditoria", headers=_cabecera(escenario["dueno"])
        ).json()
        cancelacion = [e for e in eventos if e["accion"] == "cancelacion_pedido"]
        assert cancelacion, eventos
        assert cancelacion[0]["actor"] == "oper@optiroute.test"
        assert cancelacion[0]["objetivo"] == 1
        assert cancelacion[0]["motivo"] == "El cliente anulo la compra."
        # La bitacora nunca guarda el hash ni la contrasena.
        assert "password_hash" not in cancelacion[0]

    def test_cancelar_ruta_sin_motivo_se_rechaza(self, cliente, escenario, monkeypatch):
        monkeypatch.setattr(
            rutas_api,
            "obtener_ruta",
            lambda id_ruta: {"id_ruta": id_ruta, "conductor": {"id_conductor": 9}},
        )
        monkeypatch.setattr(
            rutas_api,
            "actualizar_estado_ruta",
            lambda id_ruta, estado_nuevo: {
                "id_ruta": id_ruta,
                "estado": estado_nuevo,
            },
        )
        respuesta = cliente.patch(
            "/api/rutas/1/estado",
            json={"estado": "CANCELADA"},
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 422

    def test_cancelar_ruta_genera_registro_de_auditoria(
        self, cliente, escenario, monkeypatch
    ):
        monkeypatch.setattr(
            rutas_api,
            "obtener_ruta",
            lambda id_ruta: {"id_ruta": id_ruta, "conductor": {"id_conductor": 9}},
        )
        monkeypatch.setattr(
            rutas_api,
            "actualizar_estado_ruta",
            lambda id_ruta, estado_nuevo: {
                "id_ruta": id_ruta,
                "estado": estado_nuevo,
            },
        )
        respuesta = cliente.patch(
            "/api/rutas/1/estado",
            json={"estado": "CANCELADA", "motivo": "Cliente reprogramo la entrega."},
            headers=_cabecera(escenario["oper"]["token"]),
        )
        assert respuesta.status_code == 200, respuesta.text

        eventos = cliente.get(
            "/api/auth/auditoria", headers=_cabecera(escenario["dueno"])
        ).json()
        cancelacion = [e for e in eventos if e["accion"] == "cancelacion_ruta"]
        assert cancelacion, eventos
        assert cancelacion[0]["actor"] == "oper@optiroute.test"
        assert cancelacion[0]["motivo"] == "Cliente reprogramo la entrega."

    def test_estados_no_cancelables_no_exigen_motivo(
        self, cliente, escenario, monkeypatch
    ):
        monkeypatch.setattr(
            pedidos_api,
            "actualizar_estado_pedido",
            lambda id_pedido, estado: _pedido_falso(id_pedido=id_pedido, estado=estado),
        )
        respuesta = cliente.patch(
            "/api/pedidos/1/estado",
            json={"estado": "PLANIFICADO"},
            headers=_cabecera(escenario["admin"]["token"]),
        )
        assert respuesta.status_code == 200, respuesta.text


class TestCatalogoSinDatosSensibles:
    """GET /api/auth/permisos solo expone el modelo de permisos."""

    CLAVES_PROHIBIDAS = (
        "password",
        "hash",
        "token",
        "correo",
        "email",
        "sesiones",
        "almacenamiento",
        "supabase",
        "env",
        "credencial",
        "secreto",
        "id_usuario",
        "propietario",
        "ultimo_acceso",
    )

    def _respuesta(self, cliente: TestClient, escenario: dict) -> dict:
        return cliente.get(
            "/api/auth/permisos", headers=_cabecera(escenario["admin"]["token"])
        ).json()

    def _claves(self, valor, acumuladas: set | None = None) -> set:
        acumuladas = acumuladas if acumuladas is not None else set()
        if isinstance(valor, dict):
            for clave, contenido in valor.items():
                acumuladas.add(str(clave).lower())
                self._claves(contenido, acumuladas)
        elif isinstance(valor, list):
            for item in valor:
                self._claves(item, acumuladas)
        return acumuladas

    def test_no_hay_campos_sensibles(self, cliente, escenario):
        catalogo = self._respuesta(cliente, escenario)
        claves = self._claves(catalogo)
        for prohibida in self.CLAVES_PROHIBIDAS:
            assert prohibida not in claves, f"El catalogo expone el campo {prohibida!r}"

    def test_no_hay_valores_con_forma_de_secreto(self, cliente, escenario):
        texto = json.dumps(self._respuesta(cliente, escenario))
        assert "pbkdf2_" not in texto
        assert "@" not in texto
        # Ningun token opaco (64+ caracteres alfanumericos).
        assert not re.search(r"[A-Za-z0-9_-]{64,}", texto)

    def test_solo_contiene_el_modelo_de_permisos(self, cliente, escenario):
        catalogo = self._respuesta(cliente, escenario)
        assert set(catalogo) == {
            "roles",
            "modulos",
            "permisos",
            "reglas",
            "rol_actual",
            "efectivos",
        }
        assert catalogo["rol_actual"] == "ADMINISTRADOR"
        for rol in catalogo["roles"]:
            assert set(rol) == {
                "rol",
                "descripcion",
                "total_permisos",
                "permisos",
                "estados_pedido",
                "estados_ruta",
            }

    def test_el_administrador_puede_consultar_la_matriz(self, cliente, escenario):
        # La pantalla de Roles y permisos vive tambien en su panel.
        assert (
            cliente.get(
                "/api/auth/permisos", headers=_cabecera(escenario["admin"]["token"])
            ).status_code
            == 200
        )


# ---------------------------------------------------------------------------
# OBJETIVO 3: sesiones y cambios de perfil
# ---------------------------------------------------------------------------

class TestSesionesYCambiosDePerfil:
    def test_el_cambio_de_perfil_invalida_la_sesion_anterior(self, cliente, escenario):
        token_oper = escenario["oper"]["token"]
        cabecera = _cabecera(token_oper)

        # Antes del cambio: solo lectura.
        assert cliente.post(
            "/api/pedidos",
            json={
                "codigo": "PED-001",
                "id_cliente": 1,
                "id_direccion_entrega": 1,
                "descripcion": "Prueba",
                "peso_kg": 5,
                "volumen_m3": 0.1,
                "prioridad": "NORMAL",
            },
            headers=cabecera,
        ).status_code == 403

        cuenta = cliente.get(
            "/api/auth/usuarios", headers=_cabecera(escenario["dueno"])
        ).json()
        id_oper = next(
            c["id_usuario"] for c in cuenta if c["correo"] == "oper@optiroute.test"
        )

        cambio = cliente.patch(
            f"/api/auth/usuarios/{id_oper}/rol",
            json={"rol": "ADMINISTRADOR"},
            headers=_cabecera(escenario["dueno"]),
        )
        assert cambio.status_code == 200, cambio.text

        # La sesion previa queda revocada: no se reutilizan permisos antiguos.
        assert cliente.get("/api/auth/session", headers=cabecera).status_code == 401

        # Con la sesion nueva si dispone de los permisos del perfil nuevo.
        nuevo = escenario["_login"]("oper@optiroute.test")
        sesion = cliente.get("/api/auth/session", headers=_cabecera(nuevo["token"])).json()
        assert sesion["usuario"]["rol"] == "ADMINISTRADOR"
        assert "rutas:planificar" in sesion["permisos"]

    def test_la_desactivacion_revoca_sesiones_vigentes(self, cliente, escenario):
        token_oper = escenario["oper"]["token"]
        cuenta = cliente.get(
            "/api/auth/usuarios", headers=_cabecera(escenario["dueno"])
        ).json()
        id_oper = next(
            c["id_usuario"] for c in cuenta if c["correo"] == "oper@optiroute.test"
        )

        respuesta = cliente.patch(
            f"/api/auth/usuarios/{id_oper}/estado",
            json={"activo": False},
            headers=_cabecera(escenario["dueno"]),
        )
        assert respuesta.status_code == 200
        assert (
            cliente.get("/api/auth/session", headers=_cabecera(token_oper)).status_code
            == 401
        )


# ---------------------------------------------------------------------------
# Pruebas unitarias de las reglas de alcance y estados
# ---------------------------------------------------------------------------

class TestReglasDeAlcance:
    def test_alcance_estado_pedido(self):
        assert alcance_estado_pedido("OPERADOR") == "completo"
        assert alcance_estado_pedido("ADMINISTRADOR") == "completo"
        assert alcance_estado_pedido("DESARROLLADOR") == "completo"
        assert alcance_estado_pedido("CONDUCTOR") == "propio"

    def test_alcance_estado_ruta(self):
        assert alcance_estado_ruta("OPERADOR") == "completo"
        assert alcance_estado_ruta("ADMINISTRADOR") == "completo"
        assert alcance_estado_ruta("CONDUCTOR") == "propio"

    def test_estados_permitidos_por_rol(self):
        assert estados_pedido_permitidos("OPERADOR") == frozenset({"CANCELADO"})
        assert estados_pedido_permitidos("ADMINISTRADOR") is None
        assert estados_pedido_permitidos("DESARROLLADOR") is None
        assert estados_pedido_permitidos("CONDUCTOR") == frozenset({"ENTREGADO"})

        assert estados_ruta_permitidos("OPERADOR") == frozenset({"CANCELADA"})
        assert estados_ruta_permitidos("CONDUCTOR") == frozenset(
            {"EN_RUTA", "COMPLETADA", "CANCELADA"}
        )
        assert estados_ruta_permitidos("ADMINISTRADOR") is None

    def test_autorizacion_de_estados_concretos(self):
        assert estado_pedido_autorizado("OPERADOR", "CANCELADO") is True
        assert estado_pedido_autorizado("OPERADOR", "ENTREGADO") is False
        assert estado_ruta_autorizado("CONDUCTOR", "EN_RUTA") is True
        assert estado_ruta_autorizado("CONDUCTOR", "ASIGNADA") is False
        assert estado_ruta_autorizado("ADMINISTRADOR", "ASIGNADA") is True

    def test_operador_no_hereda_permisos_de_administrador(self):
        operador = permisos_de(Rol.OPERADOR)
        for permiso in (
            Permiso.PEDIDOS_CREAR,
            Permiso.PEDIDOS_EDITAR,
            Permiso.RUTAS_PLANIFICAR,
            Permiso.RUTAS_CREAR,
            Permiso.RUTAS_ASIGNAR,
            Permiso.CUENTAS_OPERATIVAS,
            Permiso.REPORTES_VER,
        ):
            assert permiso not in operador, permiso

    def test_administrador_no_hereda_permisos_tecnicos(self):
        administrador = permisos_de(Rol.ADMINISTRADOR)
        for permiso in (
            Permiso.PERFILES_ADMINISTRAR,
            Permiso.CUENTAS_ADMINISTRADORES,
            Permiso.CONFIGURACION_TECNICA,
            Permiso.DIAGNOSTICO_VER,
            Permiso.AUDITORIA_VER,
        ):
            assert permiso not in administrador, permiso

    def test_desarrollador_hereda_la_gestion_operativa(self):
        desarrollador = permisos_de(Rol.DESARROLLADOR)
        for permiso in (
            Permiso.PEDIDOS_CREAR,
            Permiso.PEDIDOS_ESTADO,
            Permiso.RUTAS_PLANIFICAR,
            Permiso.RUTAS_ASIGNAR,
            Permiso.FLOTA_GESTIONAR,
            Permiso.CUENTAS_OPERATIVAS,
        ):
            assert permiso in desarrollador, permiso

    def test_conductor_solo_ambito_propio(self):
        conductor = permisos_de(Rol.CONDUCTOR)
        assert conductor == frozenset(
            {
                Permiso.RUTAS_VER_PROPIAS,
                Permiso.RUTAS_ESTADO,
                Permiso.PEDIDOS_VER_PROPIOS,
                Permiso.PEDIDOS_ESTADO_PROPIO,
                Permiso.RUTAS_VER_ASIGNADAS,
                Permiso.GUIAS_VER_ASIGNADAS,
                Permiso.GUIAS_ENTREGAR,
                Permiso.GUIAS_NOVEDAD,
                Permiso.EVIDENCIAS_VER,
            }
        )
        assert Permiso.PEDIDOS_VER not in conductor
        assert Permiso.CLIENTES_VER not in conductor
        assert Permiso.RECURSOS_VER not in conductor

    def test_catalogo_completo_para_cada_permiso(self):
        catalogo = catalogo_permisos()
        assert len(catalogo["permisos"]) == len(Permiso)
        modulos = {modulo["id"] for modulo in catalogo["modulos"]}
        for permiso in catalogo["permisos"]:
            assert permiso["modulo"] in modulos
            assert permiso["ambito"] in {"general", "limitado", "propio"}
