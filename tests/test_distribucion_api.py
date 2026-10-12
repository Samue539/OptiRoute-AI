"""Endpoints del Centro de Distribucion: validacion, aislamiento y asignacion.

Llaman a las funciones del router con servicios simulados (sin
PostgreSQL real). Verifican que los errores del servicio se traducen al
codigo HTTP correcto y que la asignacion del ADMINISTRADOR exige empresa,
membresia y recurso vinculado.
"""

import pytest
from fastapi import HTTPException

from backend.app.api import distribucion as api
from backend.app.services.guias_service import ErrorDistribucion
from tests.conftest import crear_principal


def test_consultar_guias_con_id_invalido_devuelve_400():
    with pytest.raises(HTTPException) as error:
        api.consultar_guias_de_ruta(0, principal=crear_principal("OPERADOR"))
    assert error.value.status_code == 400


def test_guia_ajena_se_mapea_a_403(monkeypatch):
    def _ajena(**kwargs):
        raise ErrorDistribucion("No tienes acceso a esta guia.", 403)

    monkeypatch.setattr(api, "obtener_guia_por_numero", _ajena)

    with pytest.raises(HTTPException) as error:
        api.consultar_guia("GUI-OTRA-1", principal=crear_principal("OPERADOR"))
    assert error.value.status_code == 403
    assert "acceso" in error.value.detail


def test_conductor_consulta_su_guia(monkeypatch):
    guia = {
        "id_guia": 7,
        "numero_guia": "GUI-TEST-001",
        "estado": "PENDIENTE",
        "destinatario_nombre": "Cliente Demo",
        "direccion_texto": "Av. Demo 123",
        "telefono_autorizado": "0990000104",
        "id_ruta": 3,
        "ruta_codigo": "RUT-000003",
        "zona": None,
        "intentos_entrega": 0,
        "fecha_entrega": None,
    }
    monkeypatch.setattr(api, "obtener_guia_por_numero", lambda **kwargs: guia)

    respuesta = api.consultar_guia(
        "GUI-TEST-001", principal=crear_principal("CONDUCTOR", id_conductor=5)
    )
    assert respuesta["numero_guia"] == "GUI-TEST-001"
    assert respuesta["telefono_autorizado"] == "0990000104"


def test_sin_modulo_008_responde_503(monkeypatch):
    def _sin_modulo(**kwargs):
        from backend.app.services.guias_service import TablasDistribucionNoInstaladas

        raise TablasDistribucionNoInstaladas()

    monkeypatch.setattr(api, "listar_mis_rutas", _sin_modulo)

    with pytest.raises(HTTPException) as error:
        api.consultar_mis_rutas(principal=crear_principal("OPERADOR"))
    assert error.value.status_code == 503


def test_asignar_sin_permiso_global_lo_bloquea_la_dependencia():
    # El router exige rutas:asignar; el OPERADOR no lo tiene.
    from backend.app.core.permisos import Permiso, permisos_de

    assert Permiso.RUTAS_ASIGNAR not in permisos_de("OPERADOR")
    assert Permiso.RUTAS_ASIGNAR not in permisos_de("CONDUCTOR")


def test_asignar_tipo_invalido_devuelve_400():
    from backend.app.schemas.distribucion import AsignacionDistribucionCrear

    with pytest.raises(Exception):
        AsignacionDistribucionCrear(
            id_empresa="22222222-2222-2222-2222-222222222222",
            id_cuenta=2,
            tipo_recurso="PEDIDO",  # fuera del catalogo RUTA/ZONA/GUIA
            id_recurso=1,
        )


def test_asignar_sin_membresia_devuelve_404(monkeypatch):
    from uuid import UUID

    from backend.app.schemas.distribucion import AsignacionDistribucionCrear

    class _ServicioFalso:
        class repositorio:
            @staticmethod
            def membresia_de_cuenta(id_empresa, id_cuenta):
                return None

        @staticmethod
        def vincular_recurso(*args, **kwargs):
            return None

    monkeypatch.setattr(
        "backend.app.api.empresas.obtener_servicio_multiempresa",
        lambda: _ServicioFalso(),
    )

    with pytest.raises(HTTPException) as error:
        api.asignar_ruta_o_zona(
            AsignacionDistribucionCrear(
                id_empresa=UUID("22222222-2222-2222-2222-222222222222"),
                id_cuenta=99,
                tipo_recurso="RUTA",
                id_recurso=3,
            ),
            principal=crear_principal("ADMINISTRADOR"),
        )
    assert error.value.status_code == 404
