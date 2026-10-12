"""Servicio de autenticacion, sesiones y administracion de cuentas.

Orquesta el hashing de contrasenas, la emision/revocacion de sesiones y las
reglas de negocio de perfiles. Toda la persistencia se delega en los
repositorios (interfaces en ``backend/app/repositories``): JSON provisional o
PostgreSQL, segun ``OPTIROUTE_AUTH_STORAGE``.
"""

from __future__ import annotations

import os
from datetime import timedelta
from typing import Callable

from backend.app.core.permisos import Permiso, Rol, permisos_de
from backend.app.core.seguridad import (
    ErrorPasswordDebil,
    generar_token,
    hashear_metadato,
    hashear_password,
    hashear_token,
    verificar_password,
)
from backend.app.repositories import (
    Cuenta,
    ErrorCuentaDuplicada,
    ErrorNoEncontrado,
    Sesion,
    ahora_utc,
    estado_almacenamiento,
    repositorio_auditoria,
    repositorio_cuentas,
    repositorio_sesiones,
)
from backend.app.repositories.errores import ErrorTablaInexistente

DURACION_SESION_HORAS = int(os.getenv("AUTH_SESSION_HORAS", "8"))

# Endurecimiento opcional: si esta activo, una sesion cuyo User-Agent o prefijo
# de red no coincida con los del inicio de sesion se revoca automaticamente.
SESION_ESTRICTA = os.getenv("AUTH_SESION_ESTRICTA", "").strip().lower() in {
    "1",
    "true",
    "si",
    "yes",
}


def metadatos_peticion(solicitud: object | None) -> tuple[str | None, str | None]:
    """Extrae (hash del User-Agent, prefijo de red) de la peticion HTTP.

    Acepta cualquier objeto con ``headers`` y ``client`` (la ``Request`` de
    Starlette o un doble de pruebas). Devuelve ``(None, None)`` si no hay
    peticion o si no se puede leer nada.
    """

    if solicitud is None:
        return None, None
    cabeceras = getattr(solicitud, "headers", None)
    agente = None
    if cabeceras is not None:
        try:
            agente = cabeceras.get("user-agent")
        except Exception:  # pragma: no cover - cabeceras no indexables
            agente = None
    cliente = getattr(solicitud, "client", None)
    ip = getattr(cliente, "host", None) if cliente is not None else None
    agente_hash = hashear_metadato(agente) if agente else None
    return agente_hash, prefijo_ip(ip)


def prefijo_ip(ip: str | None) -> str | None:
    """Conserva solo el prefijo de red (nunca la direccion completa)."""

    if not ip:
        return None
    valor = str(ip).strip()
    if ":" in valor:  # IPv6
        return ":".join(valor.split(":")[:4])
    partes = valor.split(".")
    if len(partes) == 4:
        return ".".join(partes[:2] + ["0", "0"])
    return valor


class ErrorAutenticacion(Exception):
    """Error de autenticacion o autorizacion con codigo HTTP sugerido."""

    def __init__(self, mensaje: str, codigo: int = 401) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def _auditar(accion: str, actor: str | None, actor_id: int | None, **detalle) -> None:
    repositorio_auditoria().registrar(
        {
            "accion": accion,
            "actor": actor,
            "actor_id": actor_id,
            **detalle,
        }
    )


def auditar_evento(
    accion: str, actor: str | None, actor_id: int | None, **detalle
) -> None:
    """Registra un evento sensible en la bitacora (uso transversal).

    Lo usan tambien las operaciones criticas del negocio (por ejemplo,
    cancelar un pedido o una ruta) para dejar rastro de quien lo hizo y por
    que. Nunca se registran contrasenas, hashes ni tokens.
    """

    _auditar(accion, actor, actor_id, **detalle)


def auditar_evento_seguro(
    accion: str, actor: str | None, actor_id: int | None, **detalle
) -> None:
    """Como :func:`auditar_evento` pero sin interrumpir la operacion.

    La accion de negocio ya esta confirmada cuando se registra: si la
    bitacora falla se pierde el rastro, pero no se informa un fallo falso al
    usuario.
    """

    try:
        _auditar(accion, actor, actor_id, **detalle)
    except Exception:  # pragma: no cover - la bitacora no debe romper la API
        pass


def _con_error_persistencia(operacion: Callable[[], object]) -> object:
    """Traduce errores de almacenamiento a errores de autenticacion.

    Evita que una condicion de carrera (dos altas simultaneas con el mismo
    correo) devuelva un error 500: el repositorio informa duplicado y el
    servicio responde 409.
    """

    try:
        return operacion()
    except ErrorCuentaDuplicada as error:
        raise ErrorAutenticacion(str(error) or "Cuenta duplicada.", 409) from error
    except ErrorNoEncontrado as error:
        raise ErrorAutenticacion("La cuenta no existe.", 404) from error
    except ErrorTablaInexistente as error:
        raise ErrorAutenticacion(
            "Las tablas de acceso no existen. Aplique "
            "database/scripts/006_seguridad_acceso.sql.",
            503,
        ) from error


def _limpiar_sesiones_expiradas() -> None:
    """Mantenimiento best-effort: purga sesiones caducas o revocadas."""

    try:
        repositorio_sesiones().limpiar_expiradas()
    except Exception:  # pragma: no cover - nunca bloquea el login
        pass


def _crear_sesion(
    cuenta: Cuenta,
    metadatos: tuple[str | None, str | None] | None = None,
) -> tuple[str, Sesion]:
    agente_hash, ip_prefijo = metadatos or (None, None)
    token = generar_token()
    expira = ahora_utc() + timedelta(hours=DURACION_SESION_HORAS)
    sesion = Sesion(
        token_hash=hashear_token(token),
        id_usuario=cuenta.id_usuario,
        expira_en=expira,
        agente_hash=agente_hash,
        ip_prefijo=ip_prefijo,
    )
    sesion = repositorio_sesiones().crear(sesion)
    return token, sesion


def _respuesta_sesion(token: str, sesion: Sesion, cuenta: Cuenta) -> dict:
    return {
        "token": token,
        "expira_en": sesion.expira_en.isoformat(),
        "usuario": cuenta.info_publica(),
        "permisos": sorted(permiso.value for permiso in permisos_de(cuenta.rol)),
    }


def estado_bootstrap() -> dict:
    """Indica si ya existe la cuenta propietaria de desarrollador."""

    existe = repositorio_cuentas().existe_rol(Rol.DESARROLLADOR.value)
    return {
        "propietario_creado": existe,
        "almacenamiento": estado_almacenamiento()["backend"],
    }


def crear_propietario(
    nombres: str,
    apellidos: str,
    correo: str,
    password: str,
    metadatos: tuple[str | None, str | None] | None = None,
) -> dict:
    """Crea la primera cuenta DESARROLLADOR. Solo valida una vez."""

    repositorio = repositorio_cuentas()
    if repositorio.existe_rol(Rol.DESARROLLADOR.value):
        raise ErrorAutenticacion(
            "Ya existe una cuenta propietaria de desarrollador.", 409
        )
    try:
        hash_password = hashear_password(password)
    except ErrorPasswordDebil as error:
        raise ErrorAutenticacion(str(error), 400) from error

    cuenta = Cuenta(
        id_usuario=0,
        nombres=nombres.strip(),
        apellidos=apellidos.strip(),
        correo=correo,
        password_hash=hash_password,
        rol=Rol.DESARROLLADOR.value,
        activo=True,
        es_propietario=True,
        ultimo_acceso=ahora_utc(),
    )
    cuenta = _con_error_persistencia(lambda: repositorio.crear(cuenta))
    token, sesion = _crear_sesion(cuenta, metadatos=metadatos)
    _auditar(
        "bootstrap_propietario",
        correo,
        cuenta.id_usuario,
        detalle="Cuenta propietaria creada.",
    )
    return _respuesta_sesion(token, sesion, cuenta)


def login(
    correo: str,
    password: str,
    metadatos: tuple[str | None, str | None] | None = None,
) -> dict:
    """Valida credenciales y emite una sesion nueva."""

    repositorio = repositorio_cuentas()
    cuenta = repositorio.obtener_por_correo(correo)
    if cuenta is None or not verificar_password(password, cuenta.password_hash):
        _auditar("login_fallido", correo, cuenta.id_usuario if cuenta else None)
        raise ErrorAutenticacion("Credenciales invalidas.", 401)
    if not cuenta.activo:
        _auditar("login_cuenta_inactiva", correo, cuenta.id_usuario)
        raise ErrorAutenticacion("La cuenta esta desactivada.", 403)

    cuenta.ultimo_acceso = ahora_utc()
    cuenta = _con_error_persistencia(lambda: repositorio.actualizar(cuenta))
    _limpiar_sesiones_expiradas()
    token, sesion = _crear_sesion(cuenta, metadatos=metadatos)
    _auditar("login", correo, cuenta.id_usuario, rol=cuenta.rol)
    return _respuesta_sesion(token, sesion, cuenta)


def resolver_sesion(
    token: str,
    metadatos: tuple[str | None, str | None] | None = None,
) -> tuple[Sesion, Cuenta] | None:
    """Devuelve la sesion y cuenta vigentes, o ``None`` si no son validas.

    La cuenta se relee en cada peticion: desactivar una cuenta o cambiar su
    perfil surte efecto de inmediato aunque el token siga existiendo.
    """

    if not token:
        return None
    sesiones = repositorio_sesiones()
    sesion = sesiones.obtener(hashear_token(token))
    if sesion is None or not sesion.esta_vigente():
        return None
    if SESION_ESTRICTA and metadatos is not None:
        if not _metadatos_coinciden(sesion, *metadatos):
            sesiones.revocar(sesion.token_hash)
            _auditar(
                "sesion_metadatos_divergentes",
                None,
                sesion.id_usuario,
            )
            return None
    cuenta = repositorio_cuentas().obtener(sesion.id_usuario)
    if cuenta is None:
        return None
    if not cuenta.activo:
        sesiones.revocar(sesion.token_hash)
        return None
    return sesion, cuenta


def _metadatos_coinciden(
    sesion: Sesion,
    agente_hash: str | None,
    ip_prefijo: str | None,
) -> bool:
    """Compara los metadatos de la sesion con los de la peticion actual.

    Solo compara los datos que la sesion tenga registrados; si la sesion es
    anterior a esta mejora (sin metadatos) se acepta.
    """

    if not (sesion.agente_hash or sesion.ip_prefijo):
        return True
    if sesion.agente_hash and agente_hash and sesion.agente_hash != agente_hash:
        return False
    if sesion.ip_prefijo and ip_prefijo and sesion.ip_prefijo != ip_prefijo:
        return False
    return True


def cerrar_sesion(token: str) -> bool:
    """Revoca la sesion asociada al token."""

    if not token:
        return False
    revocada = repositorio_sesiones().revocar(hashear_token(token))
    if revocada:
        _auditar("logout", None, None)
    return revocada


def cerrar_sesiones_usuario(
    cuenta: Cuenta,
    conservar_token: str | None = None,
    metadatos: tuple[str | None, str | None] | None = None,
) -> dict:
    """Revoca todas las sesiones de una cuenta (cierre en todos los equipos).

    Si se indica ``conservar_token``, la sesion desde la que se ejecuta la
    accion se reemplaza por una nueva (token nuevo, mismo vencimiento) de modo
    que quien cierra las demas sesiones no quede desconectado. El token nuevo
    se devuelve en el resultado.
    """

    sesiones = repositorio_sesiones()
    token_nuevo: str | None = None
    sesion_nueva: Sesion | None = None
    vigencia = ahora_utc() + timedelta(hours=DURACION_SESION_HORAS)
    agente_guardado: str | None = None
    ip_guardado: str | None = None
    if conservar_token:
        actual = sesiones.obtener(hashear_token(conservar_token))
        if (
            actual is not None
            and actual.id_usuario == cuenta.id_usuario
            and actual.esta_vigente()
        ):
            vigencia = actual.expira_en
            agente_guardado = actual.agente_hash
            ip_guardado = actual.ip_prefijo

    # Primero se revocan TODAS las sesiones (incluida la actual) y despues se
    # emite el reemplazo, de modo que ninguna sesion previa sobreviva.
    revocadas = sesiones.revocar_por_usuario(cuenta.id_usuario)
    if conservar_token:
        token_nuevo = generar_token()
        sesion_nueva = sesiones.crear(
            Sesion(
                token_hash=hashear_token(token_nuevo),
                id_usuario=cuenta.id_usuario,
                expira_en=vigencia,
                agente_hash=agente_guardado,
                ip_prefijo=ip_guardado,
            )
        )
    _auditar(
        "cierre_sesiones_usuario",
        cuenta.correo,
        cuenta.id_usuario,
        revocadas=revocadas,
        sesion_renovada=sesion_nueva is not None,
    )
    return {
        "sesiones_revocadas": revocadas,
        "token": token_nuevo,
        "expira_en": sesion_nueva.expira_en.isoformat() if sesion_nueva else None,
    }


def cambiar_password(cuenta: Cuenta, password_actual: str, password_nueva: str) -> int:
    """Cambia la contrasena y revoca todas las sesiones del usuario."""

    if not verificar_password(password_actual, cuenta.password_hash):
        raise ErrorAutenticacion("La contrasena actual no es correcta.", 400)
    try:
        cuenta.password_hash = hashear_password(password_nueva)
    except ErrorPasswordDebil as error:
        raise ErrorAutenticacion(str(error), 400) from error

    _con_error_persistencia(
        lambda: repositorio_cuentas().actualizar(cuenta)
    )
    revocadas = repositorio_sesiones().revocar_por_usuario(cuenta.id_usuario)
    _auditar("cambio_password", cuenta.correo, cuenta.id_usuario, revocadas=revocadas)
    return revocadas


def listar_usuarios() -> list[dict]:
    return [cuenta.info_publica() for cuenta in repositorio_cuentas().listar()]


def _obtener_o_error(id_usuario: int) -> Cuenta:
    cuenta = repositorio_cuentas().obtener(id_usuario)
    if cuenta is None:
        raise ErrorAutenticacion("La cuenta no existe.", 404)
    return cuenta


def _queda_desarrollador_activo(excluir_id: int) -> bool:
    """Indica si, excluyendo una cuenta, queda al menos un desarrollador activo."""

    cuentas = repositorio_cuentas().listar()
    return any(
        cuenta.id_usuario != excluir_id
        and cuenta.rol == Rol.DESARROLLADOR.value
        and cuenta.activo
        for cuenta in cuentas
    )


def _asegurar_desarrollador_respaldo(objetivo: Cuenta, cambio: str) -> None:
    """Evita dejar el sistema sin ningun desarrollador activo."""

    if (
        objetivo.rol == Rol.DESARROLLADOR.value
        and objetivo.activo
        and not _queda_desarrollador_activo(objetivo.id_usuario)
    ):
        raise ErrorAutenticacion(
            f"No se puede {cambio} al ultimo desarrollador activo del sistema.",
            409,
        )


def _validar_creacion(solicitante: Cuenta, rol_objetivo: Rol) -> None:
    """Impide el escalamiento de privilegios al crear cuentas.

    La regla se apoya en permisos (no en comparaciones de texto) para que el
    catalogo de :mod:`backend.app.core.permisos` siga siendo la unica fuente
    de verdad: crear cuentas administrativas exige
    ``cuentas:administradores``, que solo tiene el DESARROLLADOR.
    """

    permisos = permisos_de(solicitante.rol)
    if rol_objetivo in (Rol.DESARROLLADOR, Rol.ADMINISTRADOR) and (
        Permiso.CUENTAS_ADMINISTRADORES not in permisos
    ):
        raise ErrorAutenticacion(
            "Solo un desarrollador puede crear cuentas administrativas.", 403
        )
    if solicitante.rol == Rol.ADMINISTRADOR.value and rol_objetivo not in (
        Rol.OPERADOR,
        Rol.CONDUCTOR,
    ):
        raise ErrorAutenticacion(
            "Un administrador solo puede crear cuentas de operador o conductor.",
            403,
        )


def crear_usuario(solicitante: Cuenta, datos: dict) -> dict:
    """Crea una cuenta aplicando las reglas de jerarquia de perfiles."""

    try:
        rol_objetivo = Rol(str(datos["rol"]).upper())
    except ValueError as error:
        raise ErrorAutenticacion(f"Perfil no soportado: {datos.get('rol')}", 400) from error

    _validar_creacion(solicitante, rol_objetivo)

    if rol_objetivo is Rol.CONDUCTOR and not datos.get("id_conductor"):
        raise ErrorAutenticacion(
            "Una cuenta de conductor debe vincular un id_conductor.", 400
        )

    repositorio = repositorio_cuentas()
    if repositorio.obtener_por_correo(datos["correo"]) is not None:
        raise ErrorAutenticacion("Ya existe una cuenta con ese correo.", 409)

    try:
        hash_password = hashear_password(datos["password"])
    except ErrorPasswordDebil as error:
        raise ErrorAutenticacion(str(error), 400) from error

    cuenta = Cuenta(
        id_usuario=0,
        nombres=datos["nombres"].strip(),
        apellidos=datos["apellidos"].strip(),
        correo=datos["correo"],
        password_hash=hash_password,
        rol=rol_objetivo.value,
        activo=True,
        id_conductor=datos.get("id_conductor"),
    )
    cuenta = _con_error_persistencia(lambda: repositorio.crear(cuenta))
    _auditar(
        "creacion_cuenta",
        solicitante.correo,
        solicitante.id_usuario,
        objetivo=cuenta.correo,
        rol=cuenta.rol,
    )
    return cuenta.info_publica()


def cambiar_estado(solicitante: Cuenta, id_usuario: int, activo: bool) -> dict:
    objetivo = _obtener_o_error(id_usuario)
    if objetivo.es_propietario:
        raise ErrorAutenticacion(
            "No se puede desactivar la cuenta propietaria.", 403
        )
    if objetivo.id_usuario == solicitante.id_usuario:
        raise ErrorAutenticacion("No puedes cambiar el estado de tu propia cuenta.", 400)
    if solicitante.rol == Rol.ADMINISTRADOR.value and objetivo.rol in (
        Rol.ADMINISTRADOR.value,
        Rol.DESARROLLADOR.value,
    ):
        raise ErrorAutenticacion(
            "Un administrador no puede modificar cuentas administrativas.", 403
        )
    _asegurar_desarrollador_respaldo(objetivo, "desactivar")

    objetivo.activo = activo
    _con_error_persistencia(
        lambda: repositorio_cuentas().actualizar(objetivo)
    )
    revocadas = 0
    if not activo:
        revocadas = repositorio_sesiones().revocar_por_usuario(objetivo.id_usuario)
    _auditar(
        "cambio_estado",
        solicitante.correo,
        solicitante.id_usuario,
        objetivo=objetivo.correo,
        activo=activo,
        sesiones_revocadas=revocadas,
    )
    return objetivo.info_publica()


def cambiar_rol(solicitante: Cuenta, id_usuario: int, rol_nuevo: str) -> dict:
    objetivo = _obtener_o_error(id_usuario)
    if objetivo.es_propietario:
        raise ErrorAutenticacion(
            "No se puede modificar el perfil de la cuenta propietaria.", 403
        )
    if objetivo.id_usuario == solicitante.id_usuario:
        raise ErrorAutenticacion("No puedes cambiar tu propio perfil.", 403)

    try:
        rol_objetivo = Rol(str(rol_nuevo).upper())
    except ValueError as error:
        raise ErrorAutenticacion(f"Perfil no soportado: {rol_nuevo}", 400) from error

    if solicitante.rol == Rol.ADMINISTRADOR.value:
        if objetivo.rol in (Rol.ADMINISTRADOR.value, Rol.DESARROLLADOR.value):
            raise ErrorAutenticacion(
                "Un administrador no puede modificar cuentas administrativas.", 403
            )
        if rol_objetivo in (Rol.ADMINISTRADOR, Rol.DESARROLLADOR):
            raise ErrorAutenticacion(
                "Un administrador no puede ascender cuentas a administrador o "
                "desarrollador.",
                403,
            )

    if rol_objetivo is Rol.CONDUCTOR and objetivo.id_conductor is None:
        raise ErrorAutenticacion(
            "Para asignar el perfil conductor la cuenta debe tener id_conductor.",
            400,
        )
    if rol_objetivo.value != Rol.DESARROLLADOR.value and objetivo.rol == Rol.DESARROLLADOR.value:
        _asegurar_desarrollador_respaldo(objetivo, "cambiar el perfil de")

    objetivo.rol = rol_objetivo.value
    _con_error_persistencia(
        lambda: repositorio_cuentas().actualizar(objetivo)
    )
    revocadas = repositorio_sesiones().revocar_por_usuario(objetivo.id_usuario)
    _auditar(
        "cambio_rol",
        solicitante.correo,
        solicitante.id_usuario,
        objetivo=objetivo.correo,
        rol=objetivo.rol,
        sesiones_revocadas=revocadas,
    )
    return objetivo.info_publica()


def restablecer_password(
    solicitante: Cuenta, id_usuario: int, password_nueva: str
) -> int:
    """Restablece la contrasena de otra cuenta y revoca todas sus sesiones.

    Cada cuenta gestiona su propia contrasena con
    :func:`cambiar_password`; esta funcion es solo para uso administrativo.
    La jerarquia replica la creacion de cuentas: un ADMINISTRADOR unicamente
    puede restablecer contrasenas de cuentas OPERADOR o CONDUCTOR.
    """

    objetivo = _obtener_o_error(id_usuario)
    if objetivo.id_usuario == solicitante.id_usuario:
        raise ErrorAutenticacion(
            "Usa el cambio personal de contrasena para tu propia cuenta.", 400
        )
    if solicitante.rol == Rol.ADMINISTRADOR.value and objetivo.rol not in (
        Rol.OPERADOR.value,
        Rol.CONDUCTOR.value,
    ):
        raise ErrorAutenticacion(
            "Un administrador solo puede restablecer contrasenas de cuentas "
            "operativas.",
            403,
        )
    try:
        objetivo.password_hash = hashear_password(password_nueva)
    except ErrorPasswordDebil as error:
        raise ErrorAutenticacion(str(error), 400) from error

    _con_error_persistencia(
        lambda: repositorio_cuentas().actualizar(objetivo)
    )
    revocadas = repositorio_sesiones().revocar_por_usuario(objetivo.id_usuario)
    _auditar(
        "restablecer_password",
        solicitante.correo,
        solicitante.id_usuario,
        objetivo=objetivo.correo,
        sesiones_revocadas=revocadas,
    )
    return revocadas


def listar_auditoria(limite: int = 100) -> list[dict]:
    return repositorio_auditoria().listar(limite)


def diagnostico() -> dict:
    cuentas = repositorio_cuentas().listar()
    por_rol: dict[str, int] = {}
    for cuenta in cuentas:
        por_rol[cuenta.rol] = por_rol.get(cuenta.rol, 0) + 1

    sesiones = repositorio_sesiones()
    propietario = next((cuenta for cuenta in cuentas if cuenta.es_propietario), None)
    return {
        "almacenamiento": estado_almacenamiento(),
        "cuentas": {
            "total": len(cuentas),
            "activas": sum(1 for cuenta in cuentas if cuenta.activo),
            "por_rol": por_rol,
            "propietario": propietario.info_publica() if propietario else None,
        },
        "sesiones": {
            "activas": sesiones.contar_activas(),
            "duracion_horas": DURACION_SESION_HORAS,
        },
        "modo_demo": os.getenv("OPTIROUTE_DEMO", "").strip().lower() in {"1", "true", "si"},
    }


__all__ = [
    "ErrorAutenticacion",
    "Permiso",
    "Rol",
    "auditar_evento",
    "auditar_evento_seguro",
    "cambiar_estado",
    "cambiar_password",
    "cambiar_rol",
    "cerrar_sesion",
    "cerrar_sesiones_usuario",
    "crear_propietario",
    "crear_usuario",
    "diagnostico",
    "estado_bootstrap",
    "listar_auditoria",
    "listar_usuarios",
    "login",
    "metadatos_peticion",
    "prefijo_ip",
    "resolver_sesion",
    "restablecer_password",
]
