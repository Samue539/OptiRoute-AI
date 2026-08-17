from backend.app.algorithms.dijkstra import dijkstra
from backend.app.core.database import obtener_conexion
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
    RutaNoEncontradaError,
)
from backend.app.services.grafo_service import (
    cargar_grafo_desde_bd,
    obtener_nodo,
)


TRANSICIONES_ESTADO = {
    "PLANIFICADA": {"ASIGNADA", "CANCELADA"},
    "ASIGNADA": {"EN_RUTA", "CANCELADA"},
    "EN_RUTA": {"COMPLETADA", "CANCELADA"},
    "COMPLETADA": set(),
    "CANCELADA": set(),
}


def _numero(valor):
    return float(valor) if valor is not None else None


def _conductor_desde_fila(fila, inicio):
    if fila[inicio] is None:
        return None

    return {
        "id_conductor": fila[inicio],
        "nombres": fila[inicio + 1],
        "apellidos": fila[inicio + 2],
        "numero_licencia": fila[inicio + 3],
    }


def _vehiculo_desde_fila(fila, inicio):
    if fila[inicio] is None:
        return None

    return {
        "id_vehiculo": fila[inicio],
        "placa": fila[inicio + 1],
        "marca": fila[inicio + 2],
        "modelo": fila[inicio + 3],
    }


def crear_ruta(origen: int, destino: int):
    nodo_origen = obtener_nodo(origen)
    nodo_destino = obtener_nodo(destino)

    if nodo_origen is None:
        raise ValueError("El nodo de origen no existe.")

    if nodo_destino is None:
        raise ValueError("El nodo de destino no existe.")

    if origen == destino:
        raise ValueError("El origen y el destino deben ser diferentes.")

    grafo = cargar_grafo_desde_bd()
    resultado = dijkstra(grafo, origen, destino)

    if resultado is None:
        raise ValueError("No existe una ruta entre los nodos indicados.")

    conexion = obtener_conexion()

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO logistica.rutas (
                    codigo,
                    id_nodo_origen,
                    id_nodo_destino,
                    estado,
                    distancia_total_km
                )
                VALUES ('TEMP', %s, %s, 'PLANIFICADA', %s)
                RETURNING id_ruta;
                """,
                (origen, destino, resultado["distancia"]),
            )

            id_ruta = cursor.fetchone()[0]
            codigo = f"RUT-{id_ruta:06d}"

            cursor.execute(
                """
                UPDATE logistica.rutas
                SET codigo = %s
                WHERE id_ruta = %s;
                """,
                (codigo, id_ruta),
            )

            distancia_acumulada = 0.0
            nodo_anterior = None

            for orden, id_nodo in enumerate(resultado["camino"], start=1):
                if nodo_anterior is not None:
                    pesos = [
                        peso
                        for vecino, peso in grafo.obtener_vecinos(nodo_anterior)
                        if vecino == id_nodo
                    ]
                    distancia_acumulada += min(pesos)

                cursor.execute(
                    """
                    INSERT INTO logistica.ruta_puntos (
                        id_ruta,
                        id_nodo,
                        orden,
                        distancia_acumulada_km
                    )
                    VALUES (%s, %s, %s, %s);
                    """,
                    (id_ruta, id_nodo, orden, distancia_acumulada),
                )
                nodo_anterior = id_nodo

        conexion.commit()

        return {
            "id_ruta": id_ruta,
            "codigo": codigo,
            "origen": nodo_origen,
            "destino": nodo_destino,
            "camino": resultado["camino"],
            "distancia_total_km": resultado["distancia"],
            "estado": "PLANIFICADA",
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()


def obtener_ruta(id_ruta: int):
    conexion = obtener_conexion()

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.id_ruta,
                    r.codigo,
                    r.id_nodo_origen,
                    no.nombre,
                    r.id_nodo_destino,
                    nd.nombre,
                    r.estado,
                    r.distancia_total_km,
                    r.tiempo_estimado_min,
                    r.costo_estimado,
                    c.id_conductor,
                    u.nombres,
                    u.apellidos,
                    c.numero_licencia,
                    v.id_vehiculo,
                    v.placa,
                    v.marca,
                    v.modelo,
                    r.fecha_planificada,
                    r.fecha_inicio,
                    r.fecha_fin,
                    r.creado_en,
                    r.actualizado_en
                FROM logistica.rutas r
                JOIN logistica.nodos no
                    ON no.id_nodo = r.id_nodo_origen
                JOIN logistica.nodos nd
                    ON nd.id_nodo = r.id_nodo_destino
                LEFT JOIN logistica.conductores c
                    ON c.id_conductor = r.id_conductor
                LEFT JOIN seguridad.usuarios u
                    ON u.id_usuario = c.id_usuario
                LEFT JOIN logistica.vehiculos v
                    ON v.id_vehiculo = r.id_vehiculo
                WHERE r.id_ruta = %s;
                """,
                (id_ruta,),
            )

            ruta = cursor.fetchone()

            if ruta is None:
                return None

            cursor.execute(
                """
                SELECT
                    rp.orden,
                    n.id_nodo,
                    n.nombre,
                    n.tipo_nodo,
                    n.latitud,
                    n.longitud,
                    rp.distancia_acumulada_km
                FROM logistica.ruta_puntos rp
                JOIN logistica.nodos n
                    ON n.id_nodo = rp.id_nodo
                WHERE rp.id_ruta = %s
                ORDER BY rp.orden;
                """,
                (id_ruta,),
            )

            puntos = [
                {
                    "orden": punto[0],
                    "id_nodo": punto[1],
                    "nombre": punto[2],
                    "tipo_nodo": punto[3],
                    "latitud": float(punto[4]),
                    "longitud": float(punto[5]),
                    "distancia_acumulada_km": _numero(punto[6]),
                }
                for punto in cursor.fetchall()
            ]

            return {
                "id_ruta": ruta[0],
                "codigo": ruta[1],
                "origen": {"id_nodo": ruta[2], "nombre": ruta[3]},
                "destino": {"id_nodo": ruta[4], "nombre": ruta[5]},
                "estado": ruta[6],
                "distancia_total_km": _numero(ruta[7]),
                "tiempo_estimado_min": _numero(ruta[8]),
                "costo_estimado": _numero(ruta[9]),
                "conductor": _conductor_desde_fila(ruta, 10),
                "vehiculo": _vehiculo_desde_fila(ruta, 14),
                "fecha_planificada": ruta[18],
                "fecha_inicio": ruta[19],
                "fecha_fin": ruta[20],
                "creado_en": ruta[21],
                "actualizado_en": ruta[22],
                "puntos": puntos,
            }

    finally:
        conexion.close()


def listar_rutas():
    conexion = obtener_conexion()

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.id_ruta,
                    r.codigo,
                    r.id_nodo_origen,
                    no.nombre,
                    r.id_nodo_destino,
                    nd.nombre,
                    r.estado,
                    r.distancia_total_km,
                    c.id_conductor,
                    u.nombres,
                    u.apellidos,
                    c.numero_licencia,
                    v.id_vehiculo,
                    v.placa,
                    v.marca,
                    v.modelo,
                    r.fecha_planificada,
                    r.creado_en
                FROM logistica.rutas r
                JOIN logistica.nodos no
                    ON no.id_nodo = r.id_nodo_origen
                JOIN logistica.nodos nd
                    ON nd.id_nodo = r.id_nodo_destino
                LEFT JOIN logistica.conductores c
                    ON c.id_conductor = r.id_conductor
                LEFT JOIN seguridad.usuarios u
                    ON u.id_usuario = c.id_usuario
                LEFT JOIN logistica.vehiculos v
                    ON v.id_vehiculo = r.id_vehiculo
                ORDER BY r.creado_en DESC, r.id_ruta DESC;
                """
            )

            return [
                {
                    "id_ruta": fila[0],
                    "codigo": fila[1],
                    "origen": {"id_nodo": fila[2], "nombre": fila[3]},
                    "destino": {"id_nodo": fila[4], "nombre": fila[5]},
                    "estado": fila[6],
                    "distancia_total_km": _numero(fila[7]),
                    "conductor": _conductor_desde_fila(fila, 8),
                    "vehiculo": _vehiculo_desde_fila(fila, 12),
                    "fecha_planificada": fila[16],
                    "creado_en": fila[17],
                }
                for fila in cursor.fetchall()
            ]

    finally:
        conexion.close()


def asignar_conductor_vehiculo(
    id_ruta: int,
    id_conductor: int,
    id_vehiculo: int,
):
    conexion = obtener_conexion()

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT estado
                FROM logistica.rutas
                WHERE id_ruta = %s
                FOR UPDATE;
                """,
                (id_ruta,),
            )
            ruta = cursor.fetchone()

            if ruta is None:
                raise RutaNoEncontradaError("La ruta no existe.")

            if ruta[0] not in {"PLANIFICADA", "ASIGNADA"}:
                raise ReglaNegocioError(
                    "Solo se pueden asignar recursos a una ruta planificada o asignada."
                )

            cursor.execute(
                """
                SELECT
                    id_conductor,
                    numero_licencia,
                    tipo_licencia,
                    telefono,
                    disponible,
                    activo
                FROM logistica.conductores
                WHERE id_conductor = %s;
                """,
                (id_conductor,),
            )
            conductor = cursor.fetchone()

            if conductor is None:
                raise RecursoNoEncontradoError("El conductor no existe.")
            if not conductor[5]:
                raise ReglaNegocioError("El conductor no esta activo.")
            if not conductor[4]:
                raise ReglaNegocioError("El conductor no esta disponible.")

            cursor.execute(
                """
                SELECT
                    id_vehiculo,
                    placa,
                    marca,
                    modelo,
                    tipo_vehiculo,
                    estado,
                    activo
                FROM logistica.vehiculos
                WHERE id_vehiculo = %s;
                """,
                (id_vehiculo,),
            )
            vehiculo = cursor.fetchone()

            if vehiculo is None:
                raise RecursoNoEncontradoError("El vehiculo no existe.")
            if not vehiculo[6]:
                raise ReglaNegocioError("El vehiculo no esta activo.")
            if vehiculo[5] != "DISPONIBLE":
                raise ReglaNegocioError("El vehiculo no esta disponible.")

            cursor.execute(
                """
                UPDATE logistica.rutas
                SET
                    id_conductor = %s,
                    id_vehiculo = %s,
                    estado = 'ASIGNADA',
                    actualizado_en = CURRENT_TIMESTAMP
                WHERE id_ruta = %s
                RETURNING id_ruta, codigo, estado, actualizado_en;
                """,
                (id_conductor, id_vehiculo, id_ruta),
            )
            actualizada = cursor.fetchone()

        conexion.commit()

        return {
            "id_ruta": actualizada[0],
            "codigo": actualizada[1],
            "estado": actualizada[2],
            "conductor": {
                "id_conductor": conductor[0],
                "numero_licencia": conductor[1],
                "tipo_licencia": conductor[2],
                "telefono": conductor[3],
            },
            "vehiculo": {
                "id_vehiculo": vehiculo[0],
                "placa": vehiculo[1],
                "marca": vehiculo[2],
                "modelo": vehiculo[3],
                "tipo_vehiculo": vehiculo[4],
            },
            "actualizado_en": actualizada[3],
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()


def actualizar_estado_ruta(id_ruta: int, estado_nuevo: str):
    conexion = obtener_conexion()

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT estado, id_conductor, id_vehiculo
                FROM logistica.rutas
                WHERE id_ruta = %s
                FOR UPDATE;
                """,
                (id_ruta,),
            )
            ruta = cursor.fetchone()

            if ruta is None:
                raise RutaNoEncontradaError("La ruta no existe.")

            estado_actual, id_conductor, id_vehiculo = ruta

            if estado_nuevo not in TRANSICIONES_ESTADO[estado_actual]:
                raise ReglaNegocioError(
                    f"No se permite cambiar de {estado_actual} a {estado_nuevo}."
                )

            if estado_nuevo == "ASIGNADA" and (
                id_conductor is None or id_vehiculo is None
            ):
                raise ReglaNegocioError(
                    "La ruta necesita conductor y vehiculo antes de asignarse."
                )

            cursor.execute(
                """
                UPDATE logistica.rutas
                SET
                    estado = %s,
                    fecha_inicio = CASE
                        WHEN %s = 'EN_RUTA' THEN CURRENT_TIMESTAMP
                        ELSE fecha_inicio
                    END,
                    fecha_fin = CASE
                        WHEN %s = 'COMPLETADA' THEN CURRENT_TIMESTAMP
                        ELSE fecha_fin
                    END,
                    actualizado_en = CURRENT_TIMESTAMP
                WHERE id_ruta = %s
                RETURNING
                    id_ruta,
                    codigo,
                    estado,
                    fecha_inicio,
                    fecha_fin,
                    actualizado_en;
                """,
                (estado_nuevo, estado_nuevo, estado_nuevo, id_ruta),
            )
            actualizada = cursor.fetchone()

        conexion.commit()

        return {
            "id_ruta": actualizada[0],
            "codigo": actualizada[1],
            "estado": actualizada[2],
            "fecha_inicio": actualizada[3],
            "fecha_fin": actualizada[4],
            "actualizado_en": actualizada[5],
        }

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()
