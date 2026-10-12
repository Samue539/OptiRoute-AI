"""Centro de Distribucion y Entregas: guias, zonas, eventos y evidencias.

Acceso en dos niveles:
1. RBAC global (el endpoint exige el permiso).
2. Asignacion: con 007+008 aplicadas, OPERADOR y CONDUCTOR solo ven las
   rutas/guias vinculadas a sus membresias (por RUTA, ZONA o GUIA). Sin
   asignaciones (modo bootstrap / 007 ausente), rige la regla legada:
   quien ve todas ve todas y el conductor ve las propias. En cuanto el
   ADMINISTRADOR asigna, el acceso se restringe a lo asignado.

Todo lo que decide el servidor (fecha/hora, validacion de fotos, rangos
GPS, unicidad de entrega) se recalcula aqui: el frontend nunca es prueba.
"""

from __future__ import annotations

from backend.app.core.database import obtener_conexion
from backend.app.schemas.distribucion import (
    MOTIVOS_FALLA,
    RELACIONES_RECEPTOR,
)
from backend.app.services.evidencias_storage import (
    ErrorEvidencia,
    validar_imagen,
)


ESTADOS_GUIA_ENTREGABLES = frozenset({"PENDIENTE", "EN_RUTA", "FALLIDA"})
ESTADOS_GUIA_CERRADOS = frozenset({"ENTREGADA", "CANCELADA", "DEVUELTA"})


class ErrorDistribucion(Exception):
    def __init__(self, mensaje: str, codigo: int = 400) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


class TablasDistribucionNoInstaladas(ErrorDistribucion):
    def __init__(self) -> None:
        super().__init__(
            "El modulo de distribucion no esta instalado en este entorno. "
            "Aplique database/scripts/007_multiempresa_base.sql y "
            "database/scripts/008_guias_evidencias_zonas.sql en desarrollo.",
            503,
        )


def _numero(valor):
    return float(valor) if valor is not None else None


def _a_iso(valor):
    if valor is None:
        return None
    return valor.isoformat() if hasattr(valor, "isoformat") else str(valor)


# ------------------------------------------------------------------
# Presencia de migraciones y resolucion de asignaciones
# ------------------------------------------------------------------


def _migracion_aplicada(cursor, nombre: str) -> bool:
    try:
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM plataforma.migraciones WHERE nombre = %s);",
            (nombre,),
        )
        fila = cursor.fetchone()
        return bool(fila and fila[0])
    except Exception:
        return False


def exigir_008(cursor) -> None:
    if not _migracion_aplicada(cursor, "008_guias_evidencias_zonas"):
        raise TablasDistribucionNoInstaladas()


def _membresias_activas(cursor, id_cuenta: int) -> list:
    """Membresias activas de la cuenta (requiere 007)."""
    try:
        cursor.execute(
            """
            SELECT id_membresia, id_empresa
            FROM plataforma.empresa_usuarios
            WHERE id_cuenta = %s AND activa = TRUE;
            """,
            (id_cuenta,),
        )
        return cursor.fetchall() or []
    except Exception:
        return []


def _asignaciones_por_tipo(cursor, membresias: list) -> dict[str, set[int]]:
    resultado: dict[str, set[int]] = {"RUTA": set(), "ZONA": set(), "GUIA": set()}
    if not membresias:
        return resultado
    ids = [str(m[0]) for m in membresias]
    try:
        cursor.execute(
            """
            SELECT tipo_recurso, id_recurso
            FROM plataforma.asignaciones_operativas
            WHERE activa = TRUE AND (
                id_membresia = ANY(%s)
            );
            """,
            (ids,),
        )
        for tipo, id_recurso in cursor.fetchall() or []:
            if tipo in resultado:
                resultado[tipo].add(int(id_recurso))
    except Exception:
        pass
    return resultado


def _rutas_de_zonas(cursor, ids_zona: set[int]) -> set[int]:
    if not ids_zona:
        return set()
    cursor.execute(
        """
        SELECT r.id_ruta FROM logistica.rutas r
        LEFT JOIN operaciones.guias g ON g.id_ruta = r.id_ruta
        WHERE r.id_zona = ANY(%s) OR g.id_zona = ANY(%s);
        """,
        (list(ids_zona), list(ids_zona)),
    )
    return {int(f[0]) for f in (cursor.fetchall() or [])}


def _conjunto_rutas_accesibles(
    cursor, id_cuenta: int, id_conductor: int | None, ver_todas: bool
) -> set[int] | None:
    """IDs de ruta accesibles, o None si rige la regla legada sin restriccion.

    None significa: el endpoint aplicara el filtro legado (todas si
    ver_todas, propias del conductor si no). Un conjunto (incluso vacio)
    significa: solo esas rutas.
    """

    if not _migracion_aplicada(cursor, "007_multiempresa_base"):
        return None
    membresias = _membresias_activas(cursor, id_cuenta)
    if not membresias:
        return None
    asignadas = _asignaciones_por_tipo(cursor, membresias)
    if not any(asignadas.values()):
        return None
    rutas = set(asignadas["RUTA"])
    rutas |= _rutas_de_zonas(cursor, asignadas["ZONA"])
    if asignadas["GUIA"]:
        cursor.execute(
            "SELECT DISTINCT id_ruta FROM operaciones.guias WHERE id_guia = ANY(%s) AND id_ruta IS NOT NULL;",
            (list(asignadas["GUIA"]),),
        )
        rutas |= {int(f[0]) for f in (cursor.fetchall() or [])}
    return rutas


def _actor_o_nulo(cursor, id_cuenta: int | None):
    """Actor auditable o NULL si la cuenta canonica no existe en PG.

    En entornos con almacenamiento de acceso local (provisional), la
    auditoria de negocio la lleva el endpoint; la FK nunca debe bloquear
    la entrega.
    """

    if id_cuenta is None:
        return None
    try:
        cursor.execute(
            "SELECT 1 FROM seguridad.cuentas_acceso WHERE id_usuario = %s;",
            (id_cuenta,),
        )
        return id_cuenta if cursor.fetchone() else None
    except Exception:
        return None


# ------------------------------------------------------------------
# Lecturas
# ------------------------------------------------------------------


def _zona_desde_fila(fila, inicio: int):
    if fila[inicio] is None:
        return None
    return {
        "id_zona": fila[inicio],
        "codigo": fila[inicio + 1],
        "nombre": fila[inicio + 2],
        "ciudad": fila[inicio + 3],
        "activa": fila[inicio + 4],
    }


def listar_zonas() -> list[dict]:
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            exigir_008(cursor)
            cursor.execute(
                """
                SELECT id_zona, codigo, nombre, ciudad, provincia, pais, activa
                FROM operaciones.zonas
                WHERE activa = TRUE
                ORDER BY nombre;
                """
            )
            return [
                {
                    "id_zona": f[0],
                    "codigo": f[1],
                    "nombre": f[2],
                    "ciudad": f[3],
                    "provincia": f[4],
                    "pais": f[5],
                    "activa": f[6],
                }
                for f in (cursor.fetchall() or [])
            ]
    finally:
        conexion.close()


def listar_mis_rutas(id_cuenta: int, id_conductor: int | None, ver_todas: bool) -> list[dict]:
    """Rutas del Centro de Distribucion para la cuenta autenticada."""

    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            exigir_008(cursor)
            restringidas = _conjunto_rutas_accesibles(cursor, id_cuenta, id_conductor, ver_todas)
            if restringidas is not None:
                if not restringidas:
                    return []
                cursor.execute(
                    """
                    SELECT r.id_ruta, r.codigo, r.nombre_ruta, r.estado,
                        r.distancia_total_km,
                        c.id_conductor, u.nombres, u.apellidos,
                        v.id_vehiculo, v.placa,
                        z.id_zona, z.codigo, z.nombre, z.ciudad, z.activa
                    FROM logistica.rutas r
                    LEFT JOIN logistica.conductores c ON c.id_conductor = r.id_conductor
                    LEFT JOIN seguridad.usuarios u ON u.id_usuario = c.id_usuario
                    LEFT JOIN logistica.vehiculos v ON v.id_vehiculo = r.id_vehiculo
                    LEFT JOIN operaciones.zonas z ON z.id_zona = r.id_zona
                    WHERE r.id_ruta = ANY(%s)
                    ORDER BY r.creado_en DESC, r.id_ruta DESC;
                    """,
                    (list(restringidas),),
                )
            elif ver_todas:
                cursor.execute(
                    """
                    SELECT r.id_ruta, r.codigo, r.nombre_ruta, r.estado,
                        r.distancia_total_km,
                        c.id_conductor, u.nombres, u.apellidos,
                        v.id_vehiculo, v.placa,
                        z.id_zona, z.codigo, z.nombre, z.ciudad, z.activa
                    FROM logistica.rutas r
                    LEFT JOIN logistica.conductores c ON c.id_conductor = r.id_conductor
                    LEFT JOIN seguridad.usuarios u ON u.id_usuario = c.id_usuario
                    LEFT JOIN logistica.vehiculos v ON v.id_vehiculo = r.id_vehiculo
                    LEFT JOIN operaciones.zonas z ON z.id_zona = r.id_zona
                    ORDER BY r.creado_en DESC, r.id_ruta DESC;
                    """
                )
            else:
                if id_conductor is None:
                    return []
                cursor.execute(
                    """
                    SELECT r.id_ruta, r.codigo, r.nombre_ruta, r.estado,
                        r.distancia_total_km,
                        c.id_conductor, u.nombres, u.apellidos,
                        v.id_vehiculo, v.placa,
                        z.id_zona, z.codigo, z.nombre, z.ciudad, z.activa
                    FROM logistica.rutas r
                    LEFT JOIN logistica.conductores c ON c.id_conductor = r.id_conductor
                    LEFT JOIN seguridad.usuarios u ON u.id_usuario = c.id_usuario
                    LEFT JOIN logistica.vehiculos v ON v.id_vehiculo = r.id_vehiculo
                    LEFT JOIN operaciones.zonas z ON z.id_zona = r.id_zona
                    WHERE r.id_conductor = %s
                    ORDER BY r.creado_en DESC, r.id_ruta DESC;
                    """,
                    (id_conductor,),
                )
            filas = cursor.fetchall() or []
            rutas = []
            for f in filas:
                rutas.append(
                    {
                        "id_ruta": f[0],
                        "codigo": f[1],
                        "nombre_ruta": f[2],
                        "estado": f[3],
                        "distancia_total_km": _numero(f[4]),
                        "conductor": (
                            {
                                "id_conductor": f[5],
                                "nombres": f[6],
                                "apellidos": f[7],
                            }
                            if f[5] is not None
                            else None
                        ),
                        "vehiculo": (
                            {"id_vehiculo": f[8], "placa": f[9]} if f[8] is not None else None
                        ),
                        "zona": _zona_desde_fila(f, 10),
                        "progreso": _progreso_ruta(cursor, f[0]),
                    }
                )
            return rutas
    finally:
        conexion.close()


def _progreso_ruta(cursor, id_ruta: int) -> dict:
    """Conteos reales de guias por estado (cero si la ruta aun no tiene)."""

    cursor.execute(
        """
        SELECT estado, COUNT(*) FROM operaciones.guias
        WHERE id_ruta = %s GROUP BY estado;
        """,
        (id_ruta,),
    )
    conteo = {estado: 0 for estado in ("PENDIENTE", "EN_RUTA", "ENTREGADA", "FALLIDA", "CANCELADA", "DEVUELTA")}
    total = 0
    for estado, cantidad in cursor.fetchall() or []:
        conteo[estado] = int(cantidad)
        total += int(cantidad)
    return {
        "total": total,
        "pendientes": conteo["PENDIENTE"],
        "en_ruta": conteo["EN_RUTA"],
        "entregadas": conteo["ENTREGADA"],
        "fallidas": conteo["FALLIDA"],
    }


def _verificar_acceso_ruta(cursor, id_ruta: int, id_cuenta: int, id_conductor: int | None, ver_todas: bool) -> dict:
    cursor.execute(
        """
        SELECT r.id_ruta, r.codigo, r.estado, r.id_conductor, r.id_zona
        FROM logistica.rutas r WHERE r.id_ruta = %s;
        """,
        (id_ruta,),
    )
    fila = cursor.fetchone()
    if fila is None:
        raise ErrorDistribucion("La ruta no existe.", 404)
    ruta = {
        "id_ruta": fila[0],
        "codigo": fila[1],
        "estado": fila[2],
        "id_conductor": fila[3],
        "id_zona": fila[4],
    }
    restringidas = _conjunto_rutas_accesibles(cursor, id_cuenta, id_conductor, ver_todas)
    if restringidas is not None:
        if id_ruta not in restringidas:
            raise ErrorDistribucion("No tienes acceso a esta ruta.", 403)
        return ruta
    if ver_todas:
        return ruta
    if id_conductor is not None and ruta["id_conductor"] == id_conductor:
        return ruta
    raise ErrorDistribucion("No tienes acceso a esta ruta.", 403)


def _guia_desde_fila(fila) -> dict:
    return {
        "id_guia": fila[0],
        "numero_guia": fila[1],
        "estado": fila[9],
        "destinatario_nombre": fila[5],
        "direccion_texto": fila[6],
        "telefono_autorizado": fila[7],
        "id_pedido": fila[3],
        "id_ruta": fila[4],
        "ruta_codigo": fila[12],
        "zona": (
            {
                "id_zona": fila[13],
                "codigo": fila[14],
                "nombre": fila[15],
                "ciudad": fila[16],
                "activa": True,
            }
            if fila[13] is not None
            else None
        ),
        "intentos_entrega": fila[10],
        "fecha_entrega": _a_iso(fila[11]),
    }


_COLUMNAS_GUIA = """
    g.id_guia, g.numero_guia, g.id_empresa, g.id_pedido, g.id_ruta,
    g.destinatario_nombre, g.direccion_texto, g.telefono_autorizado,
    g.id_zona, g.estado, g.intentos_entrega, g.fecha_entrega,
    r.codigo, z.id_zona, z.codigo, z.nombre, z.ciudad
"""


def listar_guias_de_ruta(
    id_cuenta: int,
    id_conductor: int | None,
    ver_todas: bool,
    id_ruta: int,
    search: str | None = None,
    estado: str | None = None,
) -> list[dict]:
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            exigir_008(cursor)
            _verificar_acceso_ruta(cursor, id_ruta, id_cuenta, id_conductor, ver_todas)
            consulta = (
                f"SELECT {_COLUMNAS_GUIA} FROM operaciones.guias g "
                "LEFT JOIN logistica.rutas r ON r.id_ruta = g.id_ruta "
                "LEFT JOIN operaciones.zonas z ON z.id_zona = g.id_zona "
                "WHERE g.id_ruta = %s"
            )
            params: list = [id_ruta]
            if search:
                consulta += " AND g.numero_guia ILIKE %s"
                params.append(f"%{search.strip()}%")
            if estado:
                consulta += " AND g.estado = %s"
                params.append(estado.upper())
            consulta += " ORDER BY g.id_guia;"
            cursor.execute(consulta, tuple(params))
            return [_guia_desde_fila(f) for f in (cursor.fetchall() or [])]
    finally:
        conexion.close()


def obtener_guia_por_numero(
    id_cuenta: int, id_conductor: int | None, ver_todas: bool, numero: str
) -> dict:
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            exigir_008(cursor)
            cursor.execute(
                f"SELECT {_COLUMNAS_GUIA} FROM operaciones.guias g "
                "LEFT JOIN logistica.rutas r ON r.id_ruta = g.id_ruta "
                "LEFT JOIN operaciones.zonas z ON z.id_zona = g.id_zona "
                "WHERE UPPER(g.numero_guia) = UPPER(%s);",
                (numero.strip(),),
            )
            fila = cursor.fetchone()
            if fila is None:
                raise ErrorDistribucion("La guia no existe.", 404)
            guia = _guia_desde_fila(fila)
            if guia["id_ruta"] is not None:
                _verificar_acceso_ruta(cursor, guia["id_ruta"], id_cuenta, id_conductor, ver_todas)
            elif not ver_todas:
                raise ErrorDistribucion("No tienes acceso a esta guia.", 403)
            return guia
    finally:
        conexion.close()


def historial_guia(
    id_cuenta: int, id_conductor: int | None, ver_todas: bool, id_guia: int
) -> dict:
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            exigir_008(cursor)
            cursor.execute(
                f"SELECT {_COLUMNAS_GUIA} FROM operaciones.guias g "
                "LEFT JOIN logistica.rutas r ON r.id_ruta = g.id_ruta "
                "LEFT JOIN operaciones.zonas z ON z.id_zona = g.id_zona "
                "WHERE g.id_guia = %s;",
                (id_guia,),
            )
            fila = cursor.fetchone()
            if fila is None:
                raise ErrorDistribucion("La guia no existe.", 404)
            guia = _guia_desde_fila(fila)
            if guia["id_ruta"] is not None:
                _verificar_acceso_ruta(cursor, guia["id_ruta"], id_cuenta, id_conductor, ver_todas)
            elif not ver_todas:
                raise ErrorDistribucion("No tienes acceso a esta guia.", 403)
            cursor.execute(
                """
                SELECT id_evento, tipo, actor_cuenta, receptor_nombre,
                    relacion_destinatario, motivo_falla,
                    gps_latitud, gps_longitud, gps_precision_m, gps_origen,
                    observaciones, creado_en
                FROM operaciones.guia_eventos
                WHERE id_guia = %s ORDER BY creado_en, id_evento;
                """,
                (id_guia,),
            )
            eventos = []
            for e in cursor.fetchall() or []:
                cursor.execute(
                    """
                    SELECT id_evidencia, tipo, mime, tamano_bytes, sha256, creado_en
                    FROM operaciones.guia_evidencias WHERE id_evento = %s;
                    """,
                    (e[0],),
                )
                evidencias = [
                    {
                        "id_evidencia": v[0],
                        "tipo": v[1],
                        "mime": v[2],
                        "tamano_bytes": v[3],
                        "sha256": v[4],
                        "creado_en": _a_iso(v[5]),
                    }
                    for v in (cursor.fetchall() or [])
                ]
                eventos.append(
                    {
                        "id_evento": e[0],
                        "tipo": e[1],
                        "actor_cuenta": e[2],
                        "receptor_nombre": e[3],
                        "relacion_destinatario": e[4],
                        "motivo_falla": e[5],
                        "gps_latitud": _numero(e[6]),
                        "gps_longitud": _numero(e[7]),
                        "gps_precision_m": _numero(e[8]),
                        "gps_origen": e[9],
                        "observaciones": e[10],
                        "evidencias": evidencias,
                        "creado_en": _a_iso(e[11]),
                    }
                )
            return {"guia": guia, "eventos": eventos}
    finally:
        conexion.close()


def resumen_mis_guias(id_cuenta: int, id_conductor: int | None, ver_todas: bool) -> dict:
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            exigir_008(cursor)
            restringidas = _conjunto_rutas_accesibles(cursor, id_cuenta, id_conductor, ver_todas)
            if restringidas is not None:
                if not restringidas:
                    return {"total": 0, "pendientes": 0, "en_ruta": 0, "entregadas": 0, "fallidas": 0}
                cursor.execute(
                    "SELECT estado, COUNT(*) FROM operaciones.guias WHERE id_ruta = ANY(%s) GROUP BY estado;",
                    (list(restringidas),),
                )
            elif ver_todas:
                cursor.execute("SELECT estado, COUNT(*) FROM operaciones.guias GROUP BY estado;")
            else:
                if id_conductor is None:
                    return {"total": 0, "pendientes": 0, "en_ruta": 0, "entregadas": 0, "fallidas": 0}
                cursor.execute(
                    """
                    SELECT g.estado, COUNT(*) FROM operaciones.guias g
                    JOIN logistica.rutas r ON r.id_ruta = g.id_ruta
                    WHERE r.id_conductor = %s GROUP BY g.estado;
                    """,
                    (id_conductor,),
                )
            conteo = {"PENDIENTE": 0, "EN_RUTA": 0, "ENTREGADA": 0, "FALLIDA": 0}
            total = 0
            for estado, cantidad in cursor.fetchall() or []:
                total += int(cantidad)
                if estado in conteo:
                    conteo[estado] = int(cantidad)
            return {
                "total": total,
                "pendientes": conteo["PENDIENTE"],
                "en_ruta": conteo["EN_RUTA"],
                "entregadas": conteo["ENTREGADA"],
                "fallidas": conteo["FALLIDA"],
            }
    finally:
        conexion.close()


# ------------------------------------------------------------------
# Escrituras: entrega y novedades
# ------------------------------------------------------------------


def _validar_gps(lat, lng, precision, origen) -> None:
    if lat is not None and not (-90 <= lat <= 90):
        raise ErrorDistribucion("Latitud fuera de rango.", 400)
    if lng is not None and not (-180 <= lng <= 180):
        raise ErrorDistribucion("Longitud fuera de rango.", 400)
    if precision is not None and precision <= 0:
        raise ErrorDistribucion("La precision GPS debe ser positiva.", 400)
    if origen is not None and origen not in ("GPS", "RED", "MANUAL", "DESCONOCIDO"):
        raise ErrorDistribucion("Origen de ubicacion invalido.", 400)


def _validar_receptor(nombre: str | None, relacion: str | None) -> tuple[str, str]:
    nombre_limpio = (nombre or "").strip()
    if len(nombre_limpio) < 2:
        raise ErrorDistribucion("El nombre de quien recibe es obligatorio (minimo 2 caracteres).", 400)
    if relacion not in RELACIONES_RECEPTOR:
        raise ErrorDistribucion(
            f"Relacion invalida. Permitidas: {', '.join(RELACIONES_RECEPTOR)}.", 400
        )
    return nombre_limpio, relacion


def _guardar_fotos(storage, fotos: list[tuple[str, bytes, str | None, str | None]]) -> list[dict]:
    """Valida cada foto por firma magica y la guarda. Devuelve metadatos."""

    metas = []
    for tipo, contenido, nombre_archivo, content_type in fotos:
        if tipo not in ("FOTO_GUIA", "FOTO_PAQUETE", "OTRO"):
            raise ErrorDistribucion(f"Tipo de evidencia invalido: {tipo}.", 400)
        try:
            validada = validar_imagen(contenido, nombre_archivo, content_type)
        except ErrorEvidencia as error:
            raise ErrorDistribucion(error.mensaje, error.codigo) from error
        try:
            clave = storage.guardar(validada.sha256, validada.extension, contenido)
        except ErrorEvidencia as error:
            raise ErrorDistribucion(error.mensaje, error.codigo) from error
        metas.append(
            {
                "tipo": tipo,
                "storage_key": clave,
                "mime": validada.mime,
                "tamano_bytes": validada.tamano_bytes,
                "sha256": validada.sha256,
            }
        )
    return metas


def registrar_entrega(
    id_cuenta: int,
    id_conductor: int | None,
    ver_todas: bool,
    id_guia: int,
    receptor_nombre: str | None,
    relacion_destinatario: str | None,
    gps_latitud=None,
    gps_longitud=None,
    gps_precision_m=None,
    gps_origen=None,
    observaciones: str | None = None,
    clave_idempotencia: str | None = None,
    fotos: list | None = None,
    storage=None,
) -> dict:
    from backend.app.services.evidencias_storage import repositorio_evidencias

    storage = storage or repositorio_evidencias()
    receptor, relacion = _validar_receptor(receptor_nombre, relacion_destinatario)
    _validar_gps(gps_latitud, gps_longitud, gps_precision_m, gps_origen)
    fotos = fotos or []
    tipos = sorted(t for t, *_ in fotos)
    if tipos != ["FOTO_GUIA", "FOTO_PAQUETE"]:
        raise ErrorDistribucion(
            "La entrega exige las dos fotografias: guia y paquete.", 400
        )

    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            exigir_008(cursor)
            cursor.execute(
                """
                SELECT id_guia, numero_guia, id_pedido, id_ruta, estado
                FROM operaciones.guias WHERE id_guia = %s FOR UPDATE;
                """,
                (id_guia,),
            )
            fila = cursor.fetchone()
            if fila is None:
                raise ErrorDistribucion("La guia no existe.", 404)
            _, numero_guia, id_pedido, id_ruta, estado = fila

            if clave_idempotencia:
                cursor.execute(
                    """
                    SELECT id_evento, tipo, creado_en FROM operaciones.guia_eventos
                    WHERE id_guia = %s AND clave_idempotencia = %s;
                    """,
                    (id_guia, clave_idempotencia),
                )
                previa = cursor.fetchone()
                if previa is not None:
                    conexion.rollback()
                    return {
                        "id_guia": id_guia,
                        "numero_guia": numero_guia,
                        "estado": "ENTREGADA",
                        "duplicada": True,
                        "id_evento": previa[0],
                        "creado_en": _a_iso(previa[2]),
                    }

            if id_ruta is not None:
                ruta = _verificar_acceso_ruta(cursor, id_ruta, id_cuenta, id_conductor, ver_todas)
                if ruta["estado"] != "EN_RUTA":
                    raise ErrorDistribucion(
                        f"La ruta {ruta['codigo']} no esta EN_RUTA: inicia la ruta antes de entregar.",
                        409,
                    )
            elif not ver_todas:
                raise ErrorDistribucion("No tienes acceso a esta guia.", 403)

            if estado in ESTADOS_GUIA_CERRADOS:
                raise ErrorDistribucion(
                    f"La guia ya esta en estado {estado}: no se puede entregar dos veces.", 409
                )
            if estado not in ESTADOS_GUIA_ENTREGABLES:
                raise ErrorDistribucion(f"La guia no admite entrega desde {estado}.", 409)

            metas = _guardar_fotos(storage, fotos)
            actor = _actor_o_nulo(cursor, id_cuenta)
            cursor.execute(
                """
                INSERT INTO operaciones.guia_eventos
                    (id_guia, tipo, actor_cuenta, receptor_nombre,
                     relacion_destinatario, gps_latitud, gps_longitud,
                     gps_precision_m, gps_origen, clave_idempotencia, observaciones)
                VALUES (%s, 'ENTREGADA', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_evento, creado_en;
                """,
                (
                    id_guia, actor, receptor, relacion,
                    gps_latitud, gps_longitud, gps_precision_m, gps_origen,
                    clave_idempotencia, (observaciones or "").strip() or None,
                ),
            )
            id_evento, creado_en = cursor.fetchone()
            for meta in metas:
                cursor.execute(
                    """
                    INSERT INTO operaciones.guia_evidencias
                        (id_guia, id_evento, tipo, storage_key, mime, tamano_bytes, sha256)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        id_guia, id_evento, meta["tipo"], meta["storage_key"],
                        meta["mime"], meta["tamano_bytes"], meta["sha256"],
                    ),
                )
            cursor.execute(
                """
                UPDATE operaciones.guias
                SET estado = 'ENTREGADA', fecha_entrega = CURRENT_TIMESTAMP,
                    intentos_entrega = intentos_entrega + 1,
                    clave_idempotencia = %s, actualizado_en = CURRENT_TIMESTAMP
                WHERE id_guia = %s;
                """,
                (clave_idempotencia, id_guia),
            )
            if id_pedido is not None:
                cursor.execute(
                    "UPDATE operaciones.pedidos SET estado = 'ENTREGADO', actualizado_en = CURRENT_TIMESTAMP WHERE id_pedido = %s AND estado IN ('PENDIENTE', 'PLANIFICADO', 'EN_RUTA');",
                    (id_pedido,),
                )
                cursor.execute(
                    """
                    INSERT INTO operaciones.entregas
                        (id_pedido, estado, fecha_salida, fecha_entrega, nombre_receptor, observaciones)
                    VALUES (%s, 'ENTREGADO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s)
                    ON CONFLICT (id_pedido) DO UPDATE SET
                        estado = 'ENTREGADO', fecha_entrega = CURRENT_TIMESTAMP,
                        nombre_receptor = EXCLUDED.nombre_receptor,
                        observaciones = EXCLUDED.observaciones,
                        actualizado_en = CURRENT_TIMESTAMP;
                    """,
                    (id_pedido, f"{receptor} ({relacion})", (observaciones or "").strip() or None),
                )
        conexion.commit()
        return {
            "id_guia": id_guia,
            "numero_guia": numero_guia,
            "estado": "ENTREGADA",
            "duplicada": False,
            "id_evento": id_evento,
            "creado_en": _a_iso(creado_en),
        }
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def registrar_novedad(
    id_cuenta: int,
    id_conductor: int | None,
    ver_todas: bool,
    id_guia: int,
    tipo: str = "FALLIDA",
    motivo_falla: str | None = None,
    gps_latitud=None,
    gps_longitud=None,
    gps_precision_m=None,
    gps_origen=None,
    observaciones: str | None = None,
    clave_idempotencia: str | None = None,
    fotos: list | None = None,
    storage=None,
) -> dict:
    from backend.app.services.evidencias_storage import repositorio_evidencias

    if tipo not in ("FALLIDA", "NOVEDAD"):
        raise ErrorDistribucion("Tipo de novedad invalido.", 400)
    if tipo == "FALLIDA":
        motivo = (motivo_falla or "").strip()
        if len(motivo) < 5:
            raise ErrorDistribucion("La entrega fallida exige un motivo (minimo 5 caracteres).", 400)
    else:
        motivo = (motivo_falla or "").strip() or None
        if motivo is None and not ((observaciones or "").strip()):
            raise ErrorDistribucion("La novedad exige motivo u observaciones.", 400)
    _validar_gps(gps_latitud, gps_longitud, gps_precision_m, gps_origen)
    storage = storage or repositorio_evidencias()

    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            exigir_008(cursor)
            cursor.execute(
                """
                SELECT id_guia, numero_guia, id_ruta, estado
                FROM operaciones.guias WHERE id_guia = %s FOR UPDATE;
                """,
                (id_guia,),
            )
            fila = cursor.fetchone()
            if fila is None:
                raise ErrorDistribucion("La guia no existe.", 404)
            _, numero_guia, id_ruta, estado = fila

            if clave_idempotencia:
                cursor.execute(
                    """
                    SELECT id_evento, tipo, creado_en FROM operaciones.guia_eventos
                    WHERE id_guia = %s AND clave_idempotencia = %s;
                    """,
                    (id_guia, clave_idempotencia),
                )
                previa = cursor.fetchone()
                if previa is not None:
                    conexion.rollback()
                    return {
                        "id_guia": id_guia,
                        "numero_guia": numero_guia,
                        "estado": estado,
                        "duplicada": True,
                        "id_evento": previa[0],
                        "creado_en": _a_iso(previa[2]),
                    }

            if id_ruta is not None:
                ruta = _verificar_acceso_ruta(cursor, id_ruta, id_cuenta, id_conductor, ver_todas)
                if ruta["estado"] in ("COMPLETADA", "CANCELADA"):
                    raise ErrorDistribucion("No se registran novedades en una ruta cerrada.", 409)
            elif not ver_todas:
                raise ErrorDistribucion("No tienes acceso a esta guia.", 403)

            if estado in ESTADOS_GUIA_CERRADOS:
                raise ErrorDistribucion(f"La guia esta en estado {estado}: no admite novedades.", 409)

            metas = _guardar_fotos(storage, fotos or [])
            actor = _actor_o_nulo(cursor, id_cuenta)
            cursor.execute(
                """
                INSERT INTO operaciones.guia_eventos
                    (id_guia, tipo, actor_cuenta, motivo_falla,
                     gps_latitud, gps_longitud, gps_precision_m, gps_origen,
                     clave_idempotencia, observaciones)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_evento, creado_en;
                """,
                (
                    id_guia, tipo, actor, motivo or None,
                    gps_latitud, gps_longitud, gps_precision_m, gps_origen,
                    clave_idempotencia, (observaciones or "").strip() or None,
                ),
            )
            id_evento, creado_en = cursor.fetchone()
            for meta in metas:
                cursor.execute(
                    """
                    INSERT INTO operaciones.guia_evidencias
                        (id_guia, id_evento, tipo, storage_key, mime, tamano_bytes, sha256)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        id_guia, id_evento, meta["tipo"], meta["storage_key"],
                        meta["mime"], meta["tamano_bytes"], meta["sha256"],
                    ),
                )
            if tipo == "FALLIDA":
                cursor.execute(
                    """
                    UPDATE operaciones.guias
                    SET estado = 'FALLIDA', fecha_entrega = CURRENT_TIMESTAMP,
                        intentos_entrega = intentos_entrega + 1,
                        clave_idempotencia = %s, actualizado_en = CURRENT_TIMESTAMP
                    WHERE id_guia = %s;
                    """,
                    (clave_idempotencia, id_guia),
                )
                estado_final = "FALLIDA"
            else:
                cursor.execute(
                    "UPDATE operaciones.guias SET actualizado_en = CURRENT_TIMESTAMP WHERE id_guia = %s;",
                    (id_guia,),
                )
                estado_final = estado
        conexion.commit()
        return {
            "id_guia": id_guia,
            "numero_guia": numero_guia,
            "estado": estado_final,
            "duplicada": False,
            "id_evento": id_evento,
            "creado_en": _a_iso(creado_en),
        }
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def asignar_distribucion(
    actor_cuenta,
    id_empresa,
    id_cuenta_destino: int,
    tipo_recurso: str,
    id_recurso: int,
) -> dict:
    """El ADMINISTRADOR vincula y asigna RUTA/ZONA/GUIA en una operacion."""

    from backend.app.api.empresas import obtener_servicio_multiempresa
    from backend.app.services.multiempresa_service import (
        ConflictoMultiempresa,
        ErrorMultiempresa,
    )

    tipo = (tipo_recurso or "").upper()
    if tipo not in ("RUTA", "ZONA", "GUIA"):
        raise ErrorDistribucion("Solo se asignan RUTA, ZONA o GUIA.", 400)
    servicio = obtener_servicio_multiempresa()
    try:
        try:
            servicio.vincular_recurso(actor_cuenta, id_empresa, tipo, id_recurso)
        except ConflictoMultiempresa:
            pass  # Ya vinculado a esta empresa: se continua con la asignacion.
        membresia = servicio.repositorio.membresia_de_cuenta(id_empresa, id_cuenta_destino)
        if not membresia or not membresia.activa:
            raise ErrorDistribucion(
                "La cuenta no tiene membresia activa en esta empresa.", 404
            )
        asignacion = servicio.asignar_recurso(
            actor_cuenta, id_empresa, membresia.id_membresia, tipo, id_recurso
        )
        return asignacion.to_dict()
    except ErrorMultiempresa as error:
        raise ErrorDistribucion(error.mensaje, error.codigo) from error
