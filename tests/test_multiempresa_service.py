"""Aislamiento multiempresa en memoria: ninguna prueba toca PostgreSQL real."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.api.empresas import obtener_servicio_multiempresa
from backend.app.core.deps import Principal, sesion_actual
from backend.app.core.permisos import permisos_de
from backend.app.main import app
from backend.app.repositories.modelos import Cuenta, Sesion, ahora_utc
from backend.app.repositories.multiempresa_memoria import (
    RepositorioMultiempresaMemoria,
)
from backend.app.repositories.multiempresa_modelos import MembresiaEmpresa, RolEmpresa
from backend.app.services.multiempresa_service import (
    ACCIONES_POR_ROL_EMPRESA,
    AccionEmpresa,
    AccesoEmpresaDenegado,
    ConflictoMultiempresa,
    ServicioMultiempresa,
)


def cuenta(id_usuario: int, rol: str, propietario: bool = False) -> Cuenta:
    return Cuenta(
        id_usuario=id_usuario,
        nombres="Usuario",
        apellidos=str(id_usuario),
        correo=f"usuario{id_usuario}@prueba.local",
        password_hash="no-usado",
        rol=rol,
        activo=True,
        es_propietario=propietario,
    )


@pytest.fixture
def escenario_multiempresa():
    cuentas = {
        1: cuenta(1, "DESARROLLADOR", propietario=True),
        2: cuenta(2, "ADMINISTRADOR"),
        3: cuenta(3, "OPERADOR"),
        4: cuenta(4, "CONDUCTOR"),
        5: cuenta(5, "ADMINISTRADOR"),
        6: cuenta(6, "OPERADOR"),
    }
    repo = RepositorioMultiempresaMemoria()
    servicio = ServicioMultiempresa(
        repo,
        obtener_rol_cuenta=lambda id_cuenta: (
            cuentas[id_cuenta].rol if id_cuenta in cuentas else None
        ),
        es_cuenta_propietaria=lambda id_cuenta: bool(
            id_cuenta in cuentas and cuentas[id_cuenta].es_propietario
        ),
    )
    dev = cuentas[1]
    empresa_a = servicio.crear_empresa(dev, "EMP-A", "Empresa A")
    empresa_b = servicio.crear_empresa(dev, "EMP-B", "Empresa B")
    admin_a = servicio.crear_membresia(
        dev, empresa_a.id_empresa, 2, "ADMINISTRADOR", True
    )
    operador_a = servicio.crear_membresia(
        dev, empresa_a.id_empresa, 3, "OPERADOR"
    )
    conductor_a = servicio.crear_membresia(
        dev, empresa_a.id_empresa, 4, "CONDUCTOR"
    )
    admin_b = servicio.crear_membresia(
        dev, empresa_b.id_empresa, 5, "ADMINISTRADOR", True
    )
    operador_b = servicio.crear_membresia(
        dev, empresa_b.id_empresa, 6, "OPERADOR"
    )
    return {
        "cuentas": cuentas,
        "repo": repo,
        "servicio": servicio,
        "empresa_a": empresa_a,
        "empresa_b": empresa_b,
        "admin_a": admin_a,
        "operador_a": operador_a,
        "conductor_a": conductor_a,
        "admin_b": admin_b,
        "operador_b": operador_b,
    }


class TestAislamientoEmpresarial:
    def test_cada_usuario_solo_lista_sus_empresas(self, escenario_multiempresa):
        e = escenario_multiempresa
        servicio = e["servicio"]
        cuentas = e["cuentas"]
        assert len(servicio.listar_empresas(cuentas[1])) == 2
        assert servicio.listar_empresas(cuentas[2]) == [e["empresa_a"]]
        assert servicio.listar_empresas(cuentas[3]) == [e["empresa_a"]]
        assert servicio.listar_empresas(cuentas[4]) == [e["empresa_a"]]
        assert servicio.listar_empresas(cuentas[5]) == [e["empresa_b"]]

    @pytest.mark.parametrize("id_cuenta", [2, 3, 4])
    def test_deniega_empresa_ajena(self, escenario_multiempresa, id_cuenta):
        e = escenario_multiempresa
        with pytest.raises(AccesoEmpresaDenegado):
            e["servicio"].obtener_empresa(
                e["cuentas"][id_cuenta], e["empresa_b"].id_empresa
            )

    def test_administrador_empresarial_no_crea_otro_admin(self, escenario_multiempresa):
        e = escenario_multiempresa
        with pytest.raises(AccesoEmpresaDenegado):
            e["servicio"].crear_membresia(
                e["cuentas"][2], e["empresa_a"].id_empresa, 5, "ADMINISTRADOR"
            )

    def test_recurso_de_otra_empresa_siempre_se_deniega(self, escenario_multiempresa):
        e = escenario_multiempresa
        s = e["servicio"]
        s.vincular_recurso(e["cuentas"][1], e["empresa_a"].id_empresa, "RUTA", 10)
        s.vincular_recurso(e["cuentas"][1], e["empresa_b"].id_empresa, "RUTA", 20)
        s.asignar_recurso(
            e["cuentas"][2],
            e["empresa_a"].id_empresa,
            e["operador_a"].id_membresia,
            "RUTA",
            10,
        )
        s.autorizar_recurso_asignado(
            e["cuentas"][3], e["empresa_a"].id_empresa, "RUTA", 10
        )
        with pytest.raises(AccesoEmpresaDenegado):
            s.autorizar_recurso_asignado(
                e["cuentas"][3], e["empresa_a"].id_empresa, "RUTA", 20
            )
        with pytest.raises(AccesoEmpresaDenegado):
            s.autorizar_recurso_asignado(
                e["cuentas"][3], e["empresa_b"].id_empresa, "RUTA", 20
            )

    def test_recurso_no_puede_pertenecer_a_dos_empresas(self, escenario_multiempresa):
        e = escenario_multiempresa
        e["servicio"].vincular_recurso(
            e["cuentas"][1], e["empresa_a"].id_empresa, "PEDIDO", 77
        )
        with pytest.raises(ConflictoMultiempresa):
            e["servicio"].vincular_recurso(
                e["cuentas"][1], e["empresa_b"].id_empresa, "PEDIDO", 77
            )


class TestProtecciones:
    def test_no_desactiva_ultimo_propietario_empresarial(self, escenario_multiempresa):
        e = escenario_multiempresa
        with pytest.raises(ConflictoMultiempresa):
            e["servicio"].cambiar_estado_membresia(
                e["cuentas"][1],
                e["empresa_a"].id_empresa,
                e["admin_a"].id_membresia,
                False,
            )

    def test_cuenta_propietaria_de_plataforma_permanece_protegida(
        self, escenario_multiempresa
    ):
        e = escenario_multiempresa
        # Simula un vinculo legado irregular: el servicio debe seguir negando
        # cualquier intento de desactivar la cuenta propietaria.
        irregular = MembresiaEmpresa(
            id_empresa=e["empresa_a"].id_empresa,
            id_cuenta=1,
            rol="ADMINISTRADOR",
        )
        e["repo"].crear_membresia(irregular)
        with pytest.raises(AccesoEmpresaDenegado):
            e["servicio"].cambiar_estado_membresia(
                e["cuentas"][1],
                e["empresa_a"].id_empresa,
                irregular.id_membresia,
                False,
            )

    def test_rol_empresarial_no_puede_escalar_el_rol_global(
        self, escenario_multiempresa
    ):
        e = escenario_multiempresa
        with pytest.raises(ConflictoMultiempresa):
            e["servicio"].crear_membresia(
                e["cuentas"][1], e["empresa_b"].id_empresa, 6, "ADMINISTRADOR"
            )

    def test_entrega_es_permiso_independiente_sin_privilegios_administrativos(self):
        for rol in (RolEmpresa.OPERADOR, RolEmpresa.CONDUCTOR):
            acciones = ACCIONES_POR_ROL_EMPRESA[rol]
            assert AccionEmpresa.VER_ENTREGAS_ASIGNADAS in acciones
            assert AccionEmpresa.REGISTRAR_ENTREGA_ASIGNADA in acciones
            assert AccionEmpresa.ADMINISTRAR_MEMBRESIAS not in acciones
            assert AccionEmpresa.VINCULAR_RECURSOS not in acciones


class TestAPIEnEntornoAislado:
    def _principal(self, cuenta_actor: Cuenta) -> Principal:
        return Principal(
            cuenta=cuenta_actor,
            sesion=Sesion(
                token_hash="prueba",
                id_usuario=cuenta_actor.id_usuario,
                expira_en=ahora_utc() + timedelta(hours=1),
            ),
            permisos=permisos_de(cuenta_actor.rol),
        )

    def test_endpoint_lista_solo_empresa_del_operador(self, escenario_multiempresa):
        e = escenario_multiempresa
        app.dependency_overrides[obtener_servicio_multiempresa] = lambda: e["servicio"]
        app.dependency_overrides[sesion_actual] = lambda: self._principal(e["cuentas"][3])
        try:
            respuesta = TestClient(app).get("/api/empresas")
        finally:
            app.dependency_overrides.clear()
        assert respuesta.status_code == 200, respuesta.text
        assert [item["codigo"] for item in respuesta.json()] == ["EMP-A"]

    def test_endpoint_deniega_empresa_ajena(self, escenario_multiempresa):
        e = escenario_multiempresa
        app.dependency_overrides[obtener_servicio_multiempresa] = lambda: e["servicio"]
        app.dependency_overrides[sesion_actual] = lambda: self._principal(e["cuentas"][4])
        try:
            respuesta = TestClient(app).get(
                f"/api/empresas/{e['empresa_b'].id_empresa}"
            )
        finally:
            app.dependency_overrides.clear()
        assert respuesta.status_code == 403


def test_migracion_007_es_aditiva_idempotente_y_no_destructiva():
    from pathlib import Path

    ruta = Path(__file__).resolve().parents[1] / "database" / "scripts" / "007_multiempresa_base.sql"
    sql = ruta.read_text(encoding="utf-8").upper()
    assert "CREATE SCHEMA IF NOT EXISTS" in sql
    assert sql.count("CREATE TABLE IF NOT EXISTS") == 5
    assert "ON CONFLICT (NOMBRE) DO NOTHING" in sql
    for sentencia in ("ALTER TABLE", "DROP TABLE", "DELETE FROM", "TRUNCATE"):
        assert sentencia not in sql
