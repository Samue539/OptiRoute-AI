"""Permisos del Centro de Distribucion: matriz aditiva y roles independientes.

* Los 5 permisos nuevos existen y estan asignados a OPERADOR y CONDUCTOR
  de forma independiente (ningun rol hereda los alcances del otro).
* ADMINISTRADOR los recibe por herencia operativa; DESARROLLADOR conserva
  intactos sus permisos tecnicos (sin regresion).
"""

from backend.app.core.permisos import (
    MODULOS,
    Permiso,
    catalogo_permisos,
    permisos_de,
    tiene_permiso,
)


NUEVOS = {
    Permiso.RUTAS_VER_ASIGNADAS,
    Permiso.GUIAS_VER_ASIGNADAS,
    Permiso.GUIAS_ENTREGAR,
    Permiso.GUIAS_NOVEDAD,
    Permiso.EVIDENCIAS_VER,
}

VALORES_NUEVOS = {
    "rutas:ver_asignadas",
    "guias:ver_asignadas",
    "guias:entregar",
    "guias:novedad",
    "evidencias:ver",
}


def test_nuevos_permisos_declarados_con_valores_esperados():
    assert {p.value for p in NUEVOS} == VALORES_NUEVOS


def test_operador_tiene_los_cinco_permisos_de_distribucion():
    permisos = permisos_de("OPERADOR")
    assert NUEVOS <= permisos


def test_conductor_tiene_los_cinco_permisos_de_distribucion():
    permisos = permisos_de("CONDUCTOR")
    assert NUEVOS <= permisos


def test_roles_independientes_no_comparten_alcances():
    operador = permisos_de("OPERADOR")
    conductor = permisos_de("CONDUCTOR")
    # El OPERADOR no ve ni confirma entregas como conductor.
    assert Permiso.RUTAS_VER_PROPIAS not in operador
    assert Permiso.PEDIDOS_VER_PROPIOS not in operador
    assert Permiso.PEDIDOS_ESTADO_PROPIO not in operador
    # El CONDUCTOR no hereda el alcance global del OPERADOR.
    assert Permiso.PEDIDOS_VER not in conductor
    assert Permiso.PANEL_VER not in conductor
    assert Permiso.RUTAS_VER_TODAS not in conductor
    assert Permiso.CLIENTES_VER not in conductor
    assert Permiso.PEDIDOS_ESTADO_LIMITADO not in conductor


def test_administrador_hereda_distribucion():
    assert NUEVOS <= permisos_de("ADMINISTRADOR")


def test_desarrollador_intacto_con_todo_lo_tecnico():
    permisos = permisos_de("DESARROLLADOR")
    assert NUEVOS <= permisos
    for tecnico in (
        Permiso.PERFILES_ADMINISTRAR,
        Permiso.CUENTAS_ADMINISTRADORES,
        Permiso.CONFIGURACION_TECNICA,
        Permiso.DIAGNOSTICO_VER,
        Permiso.AUDITORIA_VER,
    ):
        assert tecnico in permisos
    assert tiene_permiso("DESARROLLADOR", Permiso.RUTAS_ASIGNAR)


def test_modulo_distribucion_en_catalogo():
    catalogo = catalogo_permisos()
    assert any(m["id"] == "distribucion" for m in catalogo["modulos"])
    assert MODULOS["distribucion"] == "Distribución y entregas"
    codigos = {p["codigo"] for p in catalogo["permisos"]}
    assert VALORES_NUEVOS <= codigos
