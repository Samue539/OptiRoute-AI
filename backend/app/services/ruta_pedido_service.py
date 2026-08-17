from psycopg.errors import UniqueViolation

from backend.app.core.database import obtener_conexion
from backend.app.services.excepciones import (
    RecursoNoEncontradoError,
    ReglaNegocioError,
    RutaNoEncontradaError,
)


def _numero(valor):
    return float(valor) if valor is not None else None


def agregar_pedido_ruta(
    id_ruta: int,
    id_pedido: int,
    orden_entrega: int,
):
    if orden_entrega < 1:
        raise ReglaNegocioError("El orden de entrega debe ser mayor que cero.")

    conexion = obtener_conexion()

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT id_ruta
                FROM logistica.rutas
                WHERE id_ruta = %s
                FOR UPDATE;
                """,
                (id_ruta,),
            )
            if cursor.fetchone() is None:
                raise RutaNoEncontradaError("La ruta no existe.")

            cursor.execute(
                """
                SELECT id_pedido, codigo, estado
                FROM operaciones.pedidos
                WHERE id_pedido = %s;
                """,
                (id_pedido,),
            )
            pedido = cursor.fetchone()
            if pedido is None:
                raise RecursoNoEncontradoError("El pedido no existe.")

            cursor.execute(
                """
                SELECT id_ruta_pedido
                FROM logistica.ruta_pedidos
                WHERE id_ruta = %s AND id_pedido = %s;
                """,
                (id_ruta, id_pedido),
            )
            if cursor.fetchone() is not None:
                raise ReglaNegocioError(
                    "El pedido ya esta asociado a esta ruta."
                )

            cursor.execute(
                """
                SELECT id_ruta_pedido
                FROM logistica.ruta_pedidos
                WHERE id_ruta = %s AND orden_entrega = %s;
                """,
                (id_ruta, orden_entrega),
            )
            if cursor.fetchone() is not None:
                raise ReglaNegocioError(
                    "El orden de entrega ya esta ocupado en esta ruta."
                )

            cursor.execute(
                """
                INSERT INTO logistica.ruta_pedidos (
                    id_ruta,
                    id_pedido,
                    orden_entrega
                )
                VALUES (%s, %s, %s)
                RETURNING id_ruta_pedido, creado_en;
                """,
                (id_ruta, id_pedido, orden_entrega),
            )
            asociacion = cursor.fetchone()

        conexion.commit()

        return {
            "id_ruta_pedido": asociacion[0],
            "id_ruta": id_ruta,
            "id_pedido": pedido[0],
            "codigo_pedido": pedido[1],
            "estado_pedido": pedido[2],
            "orden_entrega": orden_entrega,
            "creado_en": asociacion[1],
        }

    except UniqueViolation as error:
        conexion.rollback()
        raise ReglaNegocioError(
            "El pedido o el orden de entrega ya existe en esta ruta."
        ) from error
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def listar_pedidos_ruta(id_ruta: int):
    conexion = obtener_conexion()

    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM logistica.rutas
                WHERE id_ruta = %s;
                """,
                (id_ruta,),
            )
            if cursor.fetchone() is None:
                raise RutaNoEncontradaError("La ruta no existe.")

            cursor.execute(
                """
                SELECT
                    rp.id_ruta_pedido,
                    rp.orden_entrega,
                    p.id_pedido,
                    p.codigo,
                    p.id_cliente,
                    p.id_direccion_entrega,
                    p.descripcion,
                    p.peso_kg,
                    p.volumen_m3,
                    p.prioridad,
                    p.estado,
                    p.fecha_solicitada,
                    rp.creado_en
                FROM logistica.ruta_pedidos rp
                JOIN operaciones.pedidos p
                    ON p.id_pedido = rp.id_pedido
                WHERE rp.id_ruta = %s
                ORDER BY rp.orden_entrega, rp.id_ruta_pedido;
                """,
                (id_ruta,),
            )

            return [
                {
                    "id_ruta_pedido": fila[0],
                    "orden_entrega": fila[1],
                    "id_pedido": fila[2],
                    "codigo": fila[3],
                    "id_cliente": fila[4],
                    "id_direccion_entrega": fila[5],
                    "descripcion": fila[6],
                    "peso_kg": _numero(fila[7]),
                    "volumen_m3": _numero(fila[8]),
                    "prioridad": fila[9],
                    "estado": fila[10],
                    "fecha_solicitada": fila[11],
                    "creado_en": fila[12],
                }
                for fila in cursor.fetchall()
            ]

    finally:
        conexion.close()
