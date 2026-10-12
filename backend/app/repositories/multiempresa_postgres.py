"""Persistencia PostgreSQL para la migracion aditiva 007.

El repositorio nunca crea tablas automaticamente. Si la migracion no existe,
falla de forma explicita y no usa ni modifica el almacenamiento JSON.
"""

from __future__ import annotations

from datetime import timezone
from typing import Callable
from uuid import UUID

from backend.app.core.database import obtener_conexion
from backend.app.repositories.multiempresa_contratos import RepositorioMultiempresa
from backend.app.repositories.multiempresa_modelos import (
    ArquitecturaMultiempresaNoInstalada,
    AsignacionEmpresa,
    Empresa,
    MembresiaEmpresa,
    RegistroMultiempresaDuplicado,
    VinculoRecursoEmpresa,
)


def _utc(valor):
    if valor is not None and getattr(valor, "tzinfo", None) is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor


def _empresa(fila) -> Empresa:
    return Empresa(
        id_empresa=UUID(str(fila[0])),
        codigo=fila[1],
        nombre=fila[2],
        identificacion_fiscal=fila[3],
        activa=bool(fila[4]),
        creado_en=_utc(fila[5]),
        actualizado_en=_utc(fila[6]),
    )


def _membresia(fila) -> MembresiaEmpresa:
    return MembresiaEmpresa(
        id_membresia=UUID(str(fila[0])),
        id_empresa=UUID(str(fila[1])),
        id_cuenta=int(fila[2]),
        rol=fila[3],
        activa=bool(fila[4]),
        es_propietario_empresa=bool(fila[5]),
        creado_en=_utc(fila[6]),
        actualizado_en=_utc(fila[7]),
    )


def _vinculo(fila) -> VinculoRecursoEmpresa:
    return VinculoRecursoEmpresa(
        id_vinculo=UUID(str(fila[0])),
        id_empresa=UUID(str(fila[1])),
        tipo_recurso=fila[2],
        id_recurso=int(fila[3]),
        creado_en=_utc(fila[4]),
    )


def _asignacion(fila) -> AsignacionEmpresa:
    return AsignacionEmpresa(
        id_asignacion=UUID(str(fila[0])),
        id_empresa=UUID(str(fila[1])),
        id_membresia=UUID(str(fila[2])),
        tipo_recurso=fila[3],
        id_recurso=int(fila[4]),
        asignado_por=int(fila[5]),
        activa=bool(fila[6]),
        creado_en=_utc(fila[7]),
        finalizado_en=_utc(fila[8]),
    )


class RepositorioMultiempresaPostgres(RepositorioMultiempresa):
    TABLAS_RECURSO = {
        "CLIENTE": "operaciones.clientes",
        "CONDUCTOR": "logistica.conductores",
        "VEHICULO": "logistica.vehiculos",
        "PEDIDO": "operaciones.pedidos",
        "RUTA": "logistica.rutas",
        "ZONA": "operaciones.zonas",
        "GUIA": "operaciones.guias",
    }
    COLUMNAS_ID_RECURSO = {
        "CLIENTE": "id_cliente",
        "CONDUCTOR": "id_conductor",
        "VEHICULO": "id_vehiculo",
        "PEDIDO": "id_pedido",
        "RUTA": "id_ruta",
        "ZONA": "id_zona",
        "GUIA": "id_guia",
    }
    EMPRESA_COLUMNAS = (
        "id_empresa, codigo, nombre, identificacion_fiscal, activa, "
        "creado_en, actualizado_en"
    )
    MEMBRESIA_COLUMNAS = (
        "id_membresia, id_empresa, id_cuenta, rol, activa, "
        "es_propietario_empresa, creado_en, actualizado_en"
    )
    VINCULO_COLUMNAS = (
        "id_vinculo, id_empresa, tipo_recurso, id_recurso, creado_en"
    )
    ASIGNACION_COLUMNAS = (
        "id_asignacion, id_empresa, id_membresia, tipo_recurso, id_recurso, "
        "asignado_por, activa, creado_en, finalizado_en"
    )

    def __init__(self, conector: Callable[[], object] | None = None) -> None:
        self._conector = conector or obtener_conexion

    def _ejecutar(self, operacion):
        conexion = self._conector()
        try:
            with conexion.cursor() as cursor:
                resultado = operacion(cursor)
            conexion.commit()
            return resultado
        except Exception as error:
            try:
                conexion.rollback()
            except Exception:
                pass
            mensaje = str(error).lower()
            if "does not exist" in mensaje or "no existe la relaci" in mensaje:
                raise ArquitecturaMultiempresaNoInstalada(
                    "La migracion 007_multiempresa_base no esta aplicada."
                ) from error
            if "duplicate key" in mensaje or "llave duplicada" in mensaje:
                raise RegistroMultiempresaDuplicado(
                    "El registro multiempresa ya existe."
                ) from error
            raise
        finally:
            try:
                conexion.close()
            except Exception:
                pass

    def crear_empresa(self, empresa: Empresa) -> Empresa:
        def operacion(cursor):
            cursor.execute(
                f"""
                INSERT INTO plataforma.empresas
                    (id_empresa, codigo, nombre, identificacion_fiscal, activa)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING {self.EMPRESA_COLUMNAS}
                """,
                (
                    empresa.id_empresa,
                    empresa.codigo,
                    empresa.nombre,
                    empresa.identificacion_fiscal,
                    empresa.activa,
                ),
            )
            return _empresa(cursor.fetchone())

        return self._ejecutar(operacion)

    def obtener_empresa(self, id_empresa: UUID) -> Empresa | None:
        def operacion(cursor):
            cursor.execute(
                f"SELECT {self.EMPRESA_COLUMNAS} FROM plataforma.empresas "
                "WHERE id_empresa = %s",
                (id_empresa,),
            )
            fila = cursor.fetchone()
            return _empresa(fila) if fila else None

        return self._ejecutar(operacion)

    def listar_empresas(self) -> list[Empresa]:
        def operacion(cursor):
            cursor.execute(
                f"SELECT {self.EMPRESA_COLUMNAS} FROM plataforma.empresas "
                "ORDER BY nombre, id_empresa"
            )
            return [_empresa(fila) for fila in cursor.fetchall()]

        return self._ejecutar(operacion)

    def crear_membresia(self, membresia: MembresiaEmpresa) -> MembresiaEmpresa:
        def operacion(cursor):
            cursor.execute(
                f"""
                INSERT INTO plataforma.empresa_usuarios
                    (id_membresia, id_empresa, id_cuenta, rol, activa,
                     es_propietario_empresa)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING {self.MEMBRESIA_COLUMNAS}
                """,
                (
                    membresia.id_membresia,
                    membresia.id_empresa,
                    membresia.id_cuenta,
                    membresia.rol,
                    membresia.activa,
                    membresia.es_propietario_empresa,
                ),
            )
            return _membresia(cursor.fetchone())

        return self._ejecutar(operacion)

    def obtener_membresia(self, id_membresia: UUID) -> MembresiaEmpresa | None:
        def operacion(cursor):
            cursor.execute(
                f"SELECT {self.MEMBRESIA_COLUMNAS} "
                "FROM plataforma.empresa_usuarios WHERE id_membresia = %s",
                (id_membresia,),
            )
            fila = cursor.fetchone()
            return _membresia(fila) if fila else None

        return self._ejecutar(operacion)

    def membresia_de_cuenta(
        self, id_empresa: UUID, id_cuenta: int
    ) -> MembresiaEmpresa | None:
        def operacion(cursor):
            cursor.execute(
                f"SELECT {self.MEMBRESIA_COLUMNAS} "
                "FROM plataforma.empresa_usuarios "
                "WHERE id_empresa = %s AND id_cuenta = %s",
                (id_empresa, id_cuenta),
            )
            fila = cursor.fetchone()
            return _membresia(fila) if fila else None

        return self._ejecutar(operacion)

    def listar_membresias(self, id_empresa: UUID) -> list[MembresiaEmpresa]:
        def operacion(cursor):
            cursor.execute(
                f"SELECT {self.MEMBRESIA_COLUMNAS} "
                "FROM plataforma.empresa_usuarios WHERE id_empresa = %s "
                "ORDER BY creado_en, id_membresia",
                (id_empresa,),
            )
            return [_membresia(fila) for fila in cursor.fetchall()]

        return self._ejecutar(operacion)

    def listar_membresias_cuenta(self, id_cuenta: int) -> list[MembresiaEmpresa]:
        def operacion(cursor):
            cursor.execute(
                f"SELECT {self.MEMBRESIA_COLUMNAS} "
                "FROM plataforma.empresa_usuarios WHERE id_cuenta = %s "
                "ORDER BY creado_en, id_membresia",
                (id_cuenta,),
            )
            return [_membresia(fila) for fila in cursor.fetchall()]

        return self._ejecutar(operacion)

    def actualizar_membresia(self, membresia: MembresiaEmpresa) -> MembresiaEmpresa:
        def operacion(cursor):
            cursor.execute(
                f"""
                UPDATE plataforma.empresa_usuarios
                SET activa = %s, actualizado_en = CURRENT_TIMESTAMP
                WHERE id_membresia = %s
                RETURNING {self.MEMBRESIA_COLUMNAS}
                """,
                (membresia.activa, membresia.id_membresia),
            )
            fila = cursor.fetchone()
            if not fila:
                return membresia
            return _membresia(fila)

        return self._ejecutar(operacion)

    def contar_propietarios_activos(self, id_empresa: UUID) -> int:
        def operacion(cursor):
            cursor.execute(
                "SELECT count(*) FROM plataforma.empresa_usuarios "
                "WHERE id_empresa = %s AND activa = TRUE "
                "AND es_propietario_empresa = TRUE",
                (id_empresa,),
            )
            return int(cursor.fetchone()[0])

        return self._ejecutar(operacion)

    def vincular_recurso(
        self, vinculo: VinculoRecursoEmpresa
    ) -> VinculoRecursoEmpresa:
        def operacion(cursor):
            cursor.execute(
                f"""
                INSERT INTO plataforma.recursos_empresa
                    (id_vinculo, id_empresa, tipo_recurso, id_recurso)
                VALUES (%s, %s, %s, %s)
                RETURNING {self.VINCULO_COLUMNAS}
                """,
                (
                    vinculo.id_vinculo,
                    vinculo.id_empresa,
                    vinculo.tipo_recurso,
                    vinculo.id_recurso,
                ),
            )
            return _vinculo(cursor.fetchone())

        return self._ejecutar(operacion)

    def obtener_vinculo(
        self, tipo_recurso: str, id_recurso: int
    ) -> VinculoRecursoEmpresa | None:
        def operacion(cursor):
            cursor.execute(
                f"SELECT {self.VINCULO_COLUMNAS} "
                "FROM plataforma.recursos_empresa "
                "WHERE tipo_recurso = %s AND id_recurso = %s",
                (tipo_recurso, id_recurso),
            )
            fila = cursor.fetchone()
            return _vinculo(fila) if fila else None

        return self._ejecutar(operacion)

    def recurso_operativo_existe(self, tipo_recurso: str, id_recurso: int) -> bool:
        tipo = tipo_recurso.upper()
        tabla = self.TABLAS_RECURSO.get(tipo)
        columna = self.COLUMNAS_ID_RECURSO.get(tipo)
        if not tabla or not columna:
            # Tipos no catalogados en TABLAS_RECURSO (p. ej. futuros
            # modulos). ZONA y GUIA existen desde la migracion 008.
            return False

        def operacion(cursor):
            cursor.execute(
                f"SELECT EXISTS (SELECT 1 FROM {tabla} WHERE {columna} = %s)",
                (id_recurso,),
            )
            return bool(cursor.fetchone()[0])

        return self._ejecutar(operacion)

    def crear_asignacion(self, asignacion: AsignacionEmpresa) -> AsignacionEmpresa:
        def operacion(cursor):
            cursor.execute(
                f"""
                INSERT INTO plataforma.asignaciones_operativas
                    (id_asignacion, id_empresa, id_membresia, tipo_recurso,
                     id_recurso, asignado_por, activa)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING {self.ASIGNACION_COLUMNAS}
                """,
                (
                    asignacion.id_asignacion,
                    asignacion.id_empresa,
                    asignacion.id_membresia,
                    asignacion.tipo_recurso,
                    asignacion.id_recurso,
                    asignacion.asignado_por,
                    asignacion.activa,
                ),
            )
            return _asignacion(cursor.fetchone())

        return self._ejecutar(operacion)

    def existe_asignacion_activa(
        self,
        id_empresa: UUID,
        id_membresia: UUID,
        tipo_recurso: str,
        id_recurso: int,
    ) -> bool:
        def operacion(cursor):
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM plataforma.asignaciones_operativas "
                "WHERE id_empresa = %s AND id_membresia = %s "
                "AND tipo_recurso = %s AND id_recurso = %s AND activa = TRUE)",
                (id_empresa, id_membresia, tipo_recurso, id_recurso),
            )
            return bool(cursor.fetchone()[0])

        return self._ejecutar(operacion)
