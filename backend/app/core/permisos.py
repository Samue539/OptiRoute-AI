"""Matriz central de permisos por perfil (rol).

Esta matriz es la unica fuente de verdad de lo que puede hacer cada perfil.
El backend valida cada permiso en las dependencias de FastAPI. El frontend
reutiliza la misma informacion (``frontend/src/auth/permissions.ts`` y el
catalogo expuesto por ``GET /api/auth/permisos``) solo para mostrar u ocultar
opciones: ocultar un boton nunca sustituye la validacion del backend.

Reglas de diseno (principio de minimo privilegio):

* Todo permiso se declara aqui, con su modulo, su nombre legible y su alcance.
* Los permisos de estado se separan en tres niveles: ``*:estado`` (cambiar
  cualquier estado de cualquier recurso), ``*:estado_limitado`` (solo ciertos
  estados) y ``*:estado_propio`` (solo recursos propios y unas transiciones
  concretas). Tener ``pedidos:estado`` **no** autoriza a modificar cualquier
  otro dato del pedido.
* La denegacion es el valor por defecto: un rol solo puede lo listado.

Catalogo expuesto por la API (consumido por la matriz de permisos del
frontend): :func:`catalogo_permisos`.
"""

from __future__ import annotations

from enum import Enum


class Rol(str, Enum):
    """Perfiles soportados por el sistema."""

    OPERADOR = "OPERADOR"
    ADMINISTRADOR = "ADMINISTRADOR"
    DESARROLLADOR = "DESARROLLADOR"
    CONDUCTOR = "CONDUCTOR"


class Permiso(str, Enum):
    """Permisos granulares verificables de forma centralizada."""

    # Panel
    PANEL_VER = "panel:ver"

    # Pedidos
    PEDIDOS_VER = "pedidos:ver"
    PEDIDOS_CREAR = "pedidos:crear"
    PEDIDOS_EDITAR = "pedidos:editar"
    PEDIDOS_ESTADO = "pedidos:estado"
    PEDIDOS_ESTADO_LIMITADO = "pedidos:estado_limitado"
    PEDIDOS_VER_PROPIOS = "pedidos:ver_propios"
    PEDIDOS_ESTADO_PROPIO = "pedidos:estado_propio"

    # Clientes
    CLIENTES_VER = "clientes:ver"

    # Flota y mapa
    RECURSOS_VER = "recursos:ver"

    # Rutas
    RUTAS_VER_TODAS = "rutas:ver_todas"
    RUTAS_VER_PROPIAS = "rutas:ver_propias"
    RUTAS_PLANIFICAR = "rutas:planificar"
    RUTAS_CREAR = "rutas:crear"
    RUTAS_ASIGNAR = "rutas:asignar"
    RUTAS_ESTADO = "rutas:estado"
    RUTAS_ESTADO_LIMITADO = "rutas:estado_limitado"
    RUTAS_VER_ASIGNADAS = "rutas:ver_asignadas"

    # Distribucion y entregas (Centro de Distribucion, Fase 1)
    GUIAS_VER_ASIGNADAS = "guias:ver_asignadas"
    GUIAS_ENTREGAR = "guias:entregar"
    GUIAS_NOVEDAD = "guias:novedad"
    EVIDENCIAS_VER = "evidencias:ver"

    # Asistente
    IA_USAR = "ia:usar"

    # Gestion administrativa
    REPORTES_VER = "reportes:ver"
    CONFIGURACION_OPERATIVA = "configuracion:operativa"
    FLOTA_GESTIONAR = "flota:gestionar"
    CUENTAS_OPERATIVAS = "cuentas:operativas"

    # Administracion tecnica (exclusiva del DESARROLLADOR)
    PERFILES_ADMINISTRAR = "perfiles:administrar"
    CUENTAS_ADMINISTRADORES = "cuentas:administradores"
    CONFIGURACION_TECNICA = "configuracion:tecnica"
    DIAGNOSTICO_VER = "diagnostico:ver"
    AUDITORIA_VER = "auditoria:ver"


# ---------------------------------------------------------------------------
# Modulos agrupadores (orden en que se muestran en la matriz)
# ---------------------------------------------------------------------------

MODULOS: dict[str, str] = {
    "panel": "Panel y tablero",
    "pedidos": "Pedidos",
    "clientes": "Clientes",
    "recursos": "Flota y mapa",
    "rutas": "Rutas",
    "distribucion": "Distribución y entregas",
    "ia": "Asistente logistico",
    "reportes": "Reportes",
    "cuentas": "Cuentas y accesos",
    "sistema": "Sistema y diagnostico",
}

MODULO_DE_PERMISO: dict[Permiso, str] = {
    Permiso.PANEL_VER: "panel",
    Permiso.PEDIDOS_VER: "pedidos",
    Permiso.PEDIDOS_CREAR: "pedidos",
    Permiso.PEDIDOS_EDITAR: "pedidos",
    Permiso.PEDIDOS_ESTADO: "pedidos",
    Permiso.PEDIDOS_ESTADO_LIMITADO: "pedidos",
    Permiso.PEDIDOS_VER_PROPIOS: "pedidos",
    Permiso.PEDIDOS_ESTADO_PROPIO: "pedidos",
    Permiso.CLIENTES_VER: "clientes",
    Permiso.RECURSOS_VER: "recursos",
    Permiso.RUTAS_VER_TODAS: "rutas",
    Permiso.RUTAS_VER_PROPIAS: "rutas",
    Permiso.RUTAS_PLANIFICAR: "rutas",
    Permiso.RUTAS_CREAR: "rutas",
    Permiso.RUTAS_ASIGNAR: "rutas",
    Permiso.RUTAS_ESTADO: "rutas",
    Permiso.RUTAS_ESTADO_LIMITADO: "rutas",
    Permiso.RUTAS_VER_ASIGNADAS: "distribucion",
    Permiso.GUIAS_VER_ASIGNADAS: "distribucion",
    Permiso.GUIAS_ENTREGAR: "distribucion",
    Permiso.GUIAS_NOVEDAD: "distribucion",
    Permiso.EVIDENCIAS_VER: "distribucion",
    Permiso.IA_USAR: "ia",
    Permiso.REPORTES_VER: "reportes",
    Permiso.CONFIGURACION_OPERATIVA: "reportes",
    Permiso.FLOTA_GESTIONAR: "recursos",
    Permiso.CUENTAS_OPERATIVAS: "cuentas",
    Permiso.PERFILES_ADMINISTRAR: "cuentas",
    Permiso.CUENTAS_ADMINISTRADORES: "cuentas",
    Permiso.CONFIGURACION_TECNICA: "sistema",
    Permiso.DIAGNOSTICO_VER: "sistema",
    Permiso.AUDITORIA_VER: "sistema",
}

NOMBRE_PERMISO: dict[Permiso, str] = {
    Permiso.PANEL_VER: "Ver panel principal",
    Permiso.PEDIDOS_VER: "Ver todos los pedidos",
    Permiso.PEDIDOS_CREAR: "Crear pedidos",
    Permiso.PEDIDOS_EDITAR: "Editar datos de pedidos",
    Permiso.PEDIDOS_ESTADO: "Cambiar cualquier estado de pedido",
    Permiso.PEDIDOS_ESTADO_LIMITADO: "Cancelar pedidos",
    Permiso.PEDIDOS_VER_PROPIOS: "Ver mis pedidos asignados",
    Permiso.PEDIDOS_ESTADO_PROPIO: "Confirmar entrega de mis pedidos",
    Permiso.CLIENTES_VER: "Ver clientes",
    Permiso.RECURSOS_VER: "Ver flota, nodos y mapa",
    Permiso.RUTAS_VER_TODAS: "Ver todas las rutas",
    Permiso.RUTAS_VER_PROPIAS: "Ver mis rutas asignadas",
    Permiso.RUTAS_PLANIFICAR: "Calcular planificaciones (TSP + Dijkstra)",
    Permiso.RUTAS_CREAR: "Crear rutas y guardar planes",
    Permiso.RUTAS_ASIGNAR: "Asignar conductor y vehiculo",
    Permiso.RUTAS_ESTADO: "Cambiar cualquier estado de ruta",
    Permiso.RUTAS_ESTADO_LIMITADO: "Cancelar rutas",
    Permiso.RUTAS_VER_ASIGNADAS: "Ver mis rutas asignadas",
    Permiso.GUIAS_VER_ASIGNADAS: "Ver mis guías asignadas",
    Permiso.GUIAS_ENTREGAR: "Registrar entregas de mis guías",
    Permiso.GUIAS_NOVEDAD: "Registrar novedades de mis guías",
    Permiso.EVIDENCIAS_VER: "Ver evidencias con acceso temporal",
    Permiso.IA_USAR: "Usar el asistente logistico",
    Permiso.REPORTES_VER: "Ver reportes",
    Permiso.CONFIGURACION_OPERATIVA: "Configuracion operativa",
    Permiso.FLOTA_GESTIONAR: "Gestionar flota",
    Permiso.CUENTAS_OPERATIVAS: "Gestionar cuentas operativas",
    Permiso.PERFILES_ADMINISTRAR: "Administrar perfiles de cuenta",
    Permiso.CUENTAS_ADMINISTRADORES: "Crear cuentas administrativas",
    Permiso.CONFIGURACION_TECNICA: "Configuracion tecnica",
    Permiso.DIAGNOSTICO_VER: "Ver diagnostico del sistema",
    Permiso.AUDITORIA_VER: "Ver auditoria de accesos",
}

DESCRIPCION_PERMISO: dict[Permiso, str] = {
    Permiso.PANEL_VER: "Acceso al tablero con indicadores de la operacion.",
    Permiso.PEDIDOS_VER: "Consulta de todos los pedidos del sistema.",
    Permiso.PEDIDOS_CREAR: "Dar de alta pedidos nuevos.",
    Permiso.PEDIDOS_EDITAR: "Modificar cliente, direccion, peso, volumen o prioridad.",
    Permiso.PEDIDOS_ESTADO: "Cualquier transicion de estado sobre cualquier pedido.",
    Permiso.PEDIDOS_ESTADO_LIMITADO: "Solo permite cancelar pedidos propios de la operacion.",
    Permiso.PEDIDOS_VER_PROPIOS: "Unicamente los pedidos de las rutas asignadas.",
    Permiso.PEDIDOS_ESTADO_PROPIO: "Confirmar la entrega de un pedido de una ruta propia.",
    Permiso.CLIENTES_VER: "Consulta de clientes, direcciones e historial.",
    Permiso.RECURSOS_VER: "Vehiculos, conductores, nodos del grafo y recorridos BFS/DFS.",
    Permiso.RUTAS_VER_TODAS: "Consulta de todas las rutas registradas.",
    Permiso.RUTAS_VER_PROPIAS: "Unicamente las rutas donde el conductor esta asignado.",
    Permiso.RUTAS_PLANIFICAR: "Ejecutar optimizacion multi-entrega sin persistir.",
    Permiso.RUTAS_CREAR: "Crear rutas, guardar planes y asociar pedidos.",
    Permiso.RUTAS_ASIGNAR: "Asignar o reasignar conductor y vehiculo a una ruta.",
    Permiso.RUTAS_ESTADO: "Cualquier transicion de estado sobre cualquier ruta.",
    Permiso.RUTAS_ESTADO_LIMITADO: "Solo permite cancelar rutas.",
    Permiso.RUTAS_VER_ASIGNADAS: "Rutas vinculadas a la membresia (por RUTA o ZONA).",
    Permiso.GUIAS_VER_ASIGNADAS: "Solo guias de rutas o zonas asignadas a la membresia.",
    Permiso.GUIAS_ENTREGAR: "Una entrega por guia (idempotente); valida fotos, receptor y GPS.",
    Permiso.GUIAS_NOVEDAD: "Entregas fallidas y novedades con motivo obligatorio.",
    Permiso.EVIDENCIAS_VER: "Fotos privadas con acceso temporal auditado, nunca publico.",
    Permiso.IA_USAR: "Analizar planificaciones con el asistente basado en reglas.",
    Permiso.REPORTES_VER: "Reportes operativos y exportacion de metricas.",
    Permiso.CONFIGURACION_OPERATIVA: "Parametros operativos del sistema.",
    Permiso.FLOTA_GESTIONAR: "Alta y mantenimiento de vehiculos y conductores.",
    Permiso.CUENTAS_OPERATIVAS: "Crear y administrar cuentas OPERADOR y CONDUCTOR.",
    Permiso.PERFILES_ADMINISTRAR: "Cambiar el perfil de cualquier cuenta.",
    Permiso.CUENTAS_ADMINISTRADORES: "Crear cuentas ADMINISTRADOR o DESARROLLADOR.",
    Permiso.CONFIGURACION_TECNICA: "Parametros tecnicos, ajustes de nodos y semillas.",
    Permiso.DIAGNOSTICO_VER: "Estado del almacenamiento, cuentas y sesiones.",
    Permiso.AUDITORIA_VER: "Bitacora de eventos de seguridad.",
}

# Ambito del permiso: general (todo el sistema), limitado (solo algunos
# estados) o propio (solo recursos asignados al usuario).
AMBITO_PERMISO: dict[Permiso, str] = {
    Permiso.PEDIDOS_ESTADO_LIMITADO: "limitado",
    Permiso.RUTAS_ESTADO_LIMITADO: "limitado",
    Permiso.PEDIDOS_VER_PROPIOS: "propio",
    Permiso.PEDIDOS_ESTADO_PROPIO: "propio",
    Permiso.RUTAS_VER_PROPIAS: "propio",
}

DESCRIPCION_ROL: dict[Rol, str] = {
    Rol.OPERADOR: (
        "Consulta y seguimiento de pedidos, clientes y rutas. Puede cancelar "
        "pedidos y rutas, pero no crear ni modificar datos operativos."
    ),
    Rol.ADMINISTRADOR: (
        "Gestion operativa completa: pedidos, clientes, rutas, flota, reportes "
        "y cuentas operativas. Sin acceso a la configuracion tecnica."
    ),
    Rol.DESARROLLADOR: (
        "Administracion tecnica total: diagnosticos, auditoria, perfiles, "
        "cuentas administrativas y configuracion del sistema."
    ),
    Rol.CONDUCTOR: (
        "Acceso exclusivo a sus rutas y pedidos asignados. Confirma entregas "
        "y registra novedades; no consulta datos administrativos."
    ),
}

# ---------------------------------------------------------------------------
# Limites por estado: que transiciones permite cada permiso de estado.
# ---------------------------------------------------------------------------

#: Estados que puede fijar un OPERADOR sobre pedidos.
ESTADOS_PEDIDO_LIMITADO = frozenset({"CANCELADO"})

#: Estados que puede fijar un CONDUCTOR sobre sus propios pedidos.
ESTADOS_PEDIDO_PROPIO = frozenset({"ENTREGADO"})

#: Estados que puede fijar un OPERADOR sobre rutas.
ESTADOS_RUTA_LIMITADO = frozenset({"CANCELADA"})

#: Estados que puede fijar un CONDUCTOR sobre sus propias rutas.
ESTADOS_RUTA_PROPIO = frozenset({"EN_RUTA", "COMPLETADA", "CANCELADA"})

TEXTO_LIMITE_PERMISO: dict[Permiso, str] = {
    Permiso.PEDIDOS_ESTADO_LIMITADO: (
        "Solo permite el estado CANCELADO, nunca modificar datos del pedido."
    ),
    Permiso.RUTAS_ESTADO_LIMITADO: (
        "Solo permite el estado CANCELADA, nunca modificar la asignacion."
    ),
    Permiso.PEDIDOS_VER_PROPIOS: "Solo pedidos de rutas donde esta asignado.",
    Permiso.PEDIDOS_ESTADO_PROPIO: (
        "Solo entrega (ENTREGADO) de pedidos de rutas propias ya iniciadas."
    ),
    Permiso.RUTAS_VER_PROPIAS: "Solo rutas donde el conductor esta asignado.",
}


# ---------------------------------------------------------------------------
# Matriz de permisos por perfil
# ---------------------------------------------------------------------------

_PERMISOS_OPERACION = frozenset(
    {
        Permiso.PANEL_VER,
        Permiso.PEDIDOS_VER,
        Permiso.PEDIDOS_ESTADO_LIMITADO,
        Permiso.CLIENTES_VER,
        Permiso.RECURSOS_VER,
        Permiso.RUTAS_VER_TODAS,
        Permiso.RUTAS_ESTADO_LIMITADO,
        Permiso.IA_USAR,
        Permiso.RUTAS_VER_ASIGNADAS,
        Permiso.GUIAS_VER_ASIGNADAS,
        Permiso.GUIAS_ENTREGAR,
        Permiso.GUIAS_NOVEDAD,
        Permiso.EVIDENCIAS_VER,
    }
)

_PERMISOS_ADMINISTRADOR = _PERMISOS_OPERACION | frozenset(
    {
        Permiso.PEDIDOS_CREAR,
        Permiso.PEDIDOS_EDITAR,
        Permiso.PEDIDOS_ESTADO,
        Permiso.RUTAS_PLANIFICAR,
        Permiso.RUTAS_CREAR,
        Permiso.RUTAS_ASIGNAR,
        Permiso.RUTAS_ESTADO,
        Permiso.REPORTES_VER,
        Permiso.CONFIGURACION_OPERATIVA,
        Permiso.FLOTA_GESTIONAR,
        Permiso.CUENTAS_OPERATIVAS,
    }
)

_PERMISOS_DESARROLLADOR = _PERMISOS_ADMINISTRADOR | frozenset(
    {
        Permiso.PERFILES_ADMINISTRAR,
        Permiso.CUENTAS_ADMINISTRADORES,
        Permiso.CONFIGURACION_TECNICA,
        Permiso.DIAGNOSTICO_VER,
        Permiso.AUDITORIA_VER,
    }
)

_PERMISOS_CONDUCTOR = frozenset(
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


MATRIZ_PERMISOS: dict[Rol, frozenset[Permiso]] = {
    Rol.OPERADOR: _PERMISOS_OPERACION,
    Rol.ADMINISTRADOR: _PERMISOS_ADMINISTRADOR,
    Rol.DESARROLLADOR: _PERMISOS_DESARROLLADOR,
    Rol.CONDUCTOR: _PERMISOS_CONDUCTOR,
}


def es_rol_valido(valor: str) -> bool:
    """Indica si ``valor`` corresponde a un perfil soportado."""

    return any(rol.value == valor for rol in Rol)


def normalizar_rol(valor: str | Rol) -> Rol:
    """Convierte texto en :class:`Rol` y valida su existencia."""

    if isinstance(valor, Rol):
        return valor
    try:
        return Rol(str(valor).upper())
    except ValueError as error:
        raise ValueError(f"Perfil no soportado: {valor}") from error


def permisos_de(rol: Rol | str) -> frozenset[Permiso]:
    """Devuelve el conjunto de permisos asociado a un perfil."""

    return MATRIZ_PERMISOS[normalizar_rol(rol)]


def tiene_permiso(rol: Rol | str, permiso: Permiso) -> bool:
    """Comprueba si un perfil incluye un permiso concreto."""

    return permiso in permisos_de(rol)


# ---------------------------------------------------------------------------
# Reglas de alcance y de estados permitidos (usadas por los endpoints)
# ---------------------------------------------------------------------------

_ALCANCE_COMPLETO = "completo"
_ALCANCE_PROPIO = "propio"
_ALCANCE_NINGUNO = "ninguno"


def alcance_estado_pedido(rol: Rol | str) -> str:
    """Alcance del permiso de cambio de estado de pedidos de un rol.

    * ``completo``: puede cambiar el estado de cualquier pedido (con o sin
      restriccion de estados, segun el permiso concreto que tenga).
    * ``propio``: solo de pedidos de sus propias rutas.
    * ``ninguno``: no puede cambiar estados.
    """

    permisos = permisos_de(rol)
    if Permiso.PEDIDOS_ESTADO in permisos:
        return _ALCANCE_COMPLETO
    if Permiso.PEDIDOS_ESTADO_LIMITADO in permisos:
        return _ALCANCE_COMPLETO
    if Permiso.PEDIDOS_ESTADO_PROPIO in permisos:
        return _ALCANCE_PROPIO
    return _ALCANCE_NINGUNO


def alcance_estado_ruta(rol: Rol | str) -> str:
    """Alcance del permiso de cambio de estado de rutas de un rol."""

    permisos = permisos_de(rol)
    if Permiso.RUTAS_ESTADO in permisos:
        if Permiso.RUTAS_VER_TODAS in permisos:
            return _ALCANCE_COMPLETO
        return _ALCANCE_PROPIO
    if Permiso.RUTAS_ESTADO_LIMITADO in permisos:
        return _ALCANCE_COMPLETO
    return _ALCANCE_NINGUNO


def estados_pedido_permitidos(rol: Rol | str) -> frozenset[str] | None:
    """Estados que el rol puede fijar en pedidos.

    Devuelve ``None`` cuando el rol tiene permiso pleno (cualquier estado)
    y un conjunto vacio cuando no puede cambiar estados.
    """

    permisos = permisos_de(rol)
    if Permiso.PEDIDOS_ESTADO in permisos:
        return None
    if Permiso.PEDIDOS_ESTADO_PROPIO in permisos:
        return ESTADOS_PEDIDO_PROPIO
    if Permiso.PEDIDOS_ESTADO_LIMITADO in permisos:
        return ESTADOS_PEDIDO_LIMITADO
    return frozenset()


def estados_ruta_permitidos(rol: Rol | str) -> frozenset[str] | None:
    """Estados que el rol puede fijar en rutas (``None`` = cualquiera)."""

    permisos = permisos_de(rol)
    if Permiso.RUTAS_ESTADO in permisos:
        if Permiso.RUTAS_VER_TODAS in permisos:
            return None
        return ESTADOS_RUTA_PROPIO
    if Permiso.RUTAS_ESTADO_LIMITADO in permisos:
        return ESTADOS_RUTA_LIMITADO
    return frozenset()


def estado_pedido_autorizado(rol: Rol | str, estado: str) -> bool:
    """Indica si el rol puede fijar ``estado`` en un pedido."""

    permitidos = estados_pedido_permitidos(rol)
    if permitidos is None:
        return True
    return estado in permitidos


def estado_ruta_autorizado(rol: Rol | str, estado: str) -> bool:
    """Indica si el rol puede fijar ``estado`` en una ruta."""

    permitidos = estados_ruta_permitidos(rol)
    if permitidos is None:
        return True
    return estado in permitidos


def texto_estados_permitidos(rol: Rol | str, tipo: str) -> str:
    """Texto legible de los estados que un rol puede fijar."""

    if tipo == "pedido":
        permitidos = estados_pedido_permitidos(rol)
    else:
        permitidos = estados_ruta_permitidos(rol)
    if permitidos is None:
        return "Cualquier estado permitido por las reglas del sistema."
    if not permitidos:
        return "Ninguno."
    return "Solo: " + ", ".join(sorted(permitidos)) + "."


# ---------------------------------------------------------------------------
# Catalogo para la matriz de permisos (fuente unica para el frontend)
# ---------------------------------------------------------------------------

def catalogo_permisos() -> dict:
    """Estructura completa del modelo de permisos, tal como la ve la API."""

    permisos = []
    for permiso in Permiso:
        permisos.append(
            {
                "codigo": permiso.value,
                "nombre": NOMBRE_PERMISO[permiso],
                "descripcion": DESCRIPCION_PERMISO[permiso],
                "modulo": MODULO_DE_PERMISO[permiso],
                "ambito": AMBITO_PERMISO.get(permiso, "general"),
                "limite": TEXTO_LIMITE_PERMISO.get(permiso),
            }
        )

    roles = []
    for rol in Rol:
        del_rol = MATRIZ_PERMISOS[rol]
        roles.append(
            {
                "rol": rol.value,
                "descripcion": DESCRIPCION_ROL[rol],
                "total_permisos": len(del_rol),
                "permisos": sorted(permiso.value for permiso in del_rol),
                "estados_pedido": texto_estados_permitidos(rol, "pedido"),
                "estados_ruta": texto_estados_permitidos(rol, "ruta"),
            }
        )

    modulos = [
        {"id": clave, "nombre": nombre} for clave, nombre in MODULOS.items()
    ]

    return {
        "roles": roles,
        "modulos": modulos,
        "permisos": permisos,
        "reglas": [
            {
                "titulo": "Denegacion por defecto",
                "detalle": (
                    "Cada endpoint exige un permiso explicito; si el perfil no "
                    "lo tiene, la API responde 403 aunque el boton sea visible."
                ),
            },
            {
                "titulo": "Minimo privilegio",
                "detalle": (
                    "OPERADOR solo lee y cancela; crear y asignar es del "
                    "ADMINISTRADOR. La configuracion tecnica es exclusiva del "
                    "DESARROLLADOR."
                ),
            },
            {
                "titulo": "Cuenta propietaria inmutable",
                "detalle": (
                    "No se puede desactivar ni cambiar de perfil la cuenta "
                    "creada por el bootstrap (HTTP 403)."
                ),
            },
            {
                "titulo": "Ultimo desarrollador",
                "detalle": (
                    "El sistema impide (HTTP 409) dejar sin ningun "
                    "DESARROLLADOR activo."
                ),
            },
            {
                "titulo": "Sin escalamiento de privilegios",
                "detalle": (
                    "Solo un DESARROLLADOR crea cuentas DESARROLLADOR o "
                    "ADMINISTRADOR; un ADMINISTRADOR no modifica cuentas "
                    "administrativas ni asciende perfiles (HTTP 403)."
                ),
            },
            {
                "titulo": "Revocacion al cambiar de perfil",
                "detalle": (
                    "Cambiar perfil, estado, contrasena o restablecerla cierra "
                    "las sesiones de la cuenta afectada: no se reutilizan "
                    "sesiones con permisos anteriores."
                ),
            },
        ],
    }
