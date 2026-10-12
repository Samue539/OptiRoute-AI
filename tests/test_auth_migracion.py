"""Pruebas de la migracion de cuentas JSON -> PostgreSQL.

Usan una base de datos simulada en memoria que reproduce las restricciones
relevantes (unicidad de id_usuario y de correo) para verificar:

* la verificacion previa no escribe nada;
* se conservan identificadores, hashes, roles, estados y permisos;
* la migracion es idempotente (ejecutarla dos veces no duplica cuentas);
* los conflictos detienen la migracion sin perder datos;
* los archivos JSON de origen nunca se modifican.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.scripts.migrar_cuentas_json_a_postgres import ejecutar, main

PASSWORD = "Propietario123"


class BaseSimulada:
    """Mini base de datos en memoria con las restricciones de la migracion."""

    def __init__(self, tablas: tuple[str, ...] | None = None) -> None:
        self.tablas = set(
            tablas
            if tablas is not None
            else ("cuentas_acceso", "sesiones_acceso", "auditoria_acceso")
        )
        self.cuentas: dict[int, tuple] = {}
        self.sesiones: dict[str, tuple] = {}
        self.consultas: list[tuple[str, tuple]] = []
        self.inserts_cuentas: list[tuple] = []
        self.inserts_sesiones: list[tuple] = []
        self.secuencias_alineadas = 0
        self.candado = threading.Lock()

    # ---- protocolo de conexion simulado -------------------------------
    def cursor(self):
        return _CursorSimulado(self)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None

    # ---- motor minimo -------------------------------------------------
    def ejecutar(self, sql: str, params: tuple) -> tuple[list[tuple], int]:
        self.consultas.append((sql, params))
        if "information_schema.tables" in sql:
            return ([(tabla,) for tabla in sorted(self.tablas)], 0)
        if "WHERE id_usuario = %s" in sql:
            fila = self.cuentas.get(int(params[0]))
            return ([fila], 0) if fila else ([], 0)
        if "LOWER(correo) = LOWER(%s)" in sql:
            objetivo = str(params[0]).lower()
            for fila in self.cuentas.values():
                if str(fila[1]).lower() == objetivo:
                    return ([fila], 0)
            return ([], 0)
        if "SELECT id_usuario FROM seguridad.cuentas_acceso" in sql:
            return ([(clave,) for clave in sorted(self.cuentas)], 0)
        if "SELECT setval(" in sql:
            self.secuencias_alineadas += 1
            return ([(1,)], 0)
        if sql.startswith("INSERT INTO seguridad.cuentas_acceso"):
            return self._insertar_cuenta(params)
        if sql.startswith("INSERT INTO seguridad.sesiones_acceso"):
            return self._insertar_sesion(params)
        return ([], 0)

    def _insertar_cuenta(self, params: tuple) -> tuple[list[tuple], int]:
        id_usuario = int(params[0])
        correo = str(params[3])
        with self.candado:
            if id_usuario in self.cuentas:
                return ([], 0)
            if any(str(fila[1]).lower() == correo.lower() for fila in self.cuentas.values()):
                # PostgreSQL lanzaria unique violation; se emula el rechazo.
                raise RuntimeError(
                    "duplicate key value violates unique constraint "
                    "uq_cuentas_acceso_correo"
                )
            self.cuentas[id_usuario] = (id_usuario, correo, params[4])
            self.inserts_cuentas.append(params)
            return ([(id_usuario, correo, params[4])], 1)

    def _insertar_sesion(self, params: tuple) -> tuple[list[tuple], int]:
        token_hash = str(params[0])
        with self.candado:
            if token_hash in self.sesiones:
                return ([], 0)
            self.sesiones[token_hash] = params
            self.inserts_sesiones.append(params)
            return ([params], 1)


class _CursorSimulado:
    def __init__(self, base: BaseSimulada) -> None:
        self.base = base
        self.filas: list[tuple] = []
        self.afectadas = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql: str, params=None):
        self.filas, self.afectadas = self.base.ejecutar(
            " ".join(sql.split()), tuple(params or ())
        )

    def fetchone(self):
        return self.filas[0] if self.filas else None

    def fetchall(self):
        return list(self.filas)

    @property
    def rowcount(self):
        return self.afectadas


def _hash(password: str = PASSWORD) -> str:
    sal = "a1b2c3d4e5f60718"
    derivada = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(sal), 210000, dklen=32
    )
    return f"pbkdf2_sha256$210000${sal}${derivada.hex()}"


def _escribir_cuentas(ruta: Path, cuentas: list[dict], siguiente_id: int) -> None:
    ruta.mkdir(parents=True, exist_ok=True)
    (ruta / "cuentas.json").write_text(
        json.dumps({"cuentas": cuentas, "siguiente_id": siguiente_id}),
        encoding="utf-8",
    )


def _cuentas_demo() -> list[dict]:
    ahora = datetime.now(timezone.utc)
    return [
        {
            "id_usuario": 1,
            "nombres": "Dueno",
            "apellidos": "Sistema",
            "correo": "dueno@optiroute.test",
            "password_hash": _hash(),
            "rol": "DESARROLLADOR",
            "activo": True,
            "id_conductor": None,
            "es_propietario": True,
            "creado_en": ahora.isoformat(),
            "actualizado_en": ahora.isoformat(),
            "ultimo_acceso": ahora.isoformat(),
        },
        {
            "id_usuario": 2,
            "nombres": "Persona",
            "apellidos": "Operador",
            "correo": "oper@optiroute.test",
            "password_hash": _hash("Segura12345"),
            "rol": "OPERADOR",
            "activo": True,
            "id_conductor": None,
            "es_propietario": False,
            "creado_en": ahora.isoformat(),
            "actualizado_en": ahora.isoformat(),
            "ultimo_acceso": None,
        },
        {
            "id_usuario": 3,
            "nombres": "Chofer",
            "apellidos": "Prueba",
            "correo": "conductor@optiroute.test",
            "password_hash": _hash("Segura12345"),
            "rol": "CONDUCTOR",
            "activo": False,
            "id_conductor": 5,
            "es_propietario": False,
            "creado_en": ahora.isoformat(),
            "actualizado_en": ahora.isoformat(),
            "ultimo_acceso": None,
        },
    ]


def _sesiones(ruta: Path) -> None:
    ahora = datetime.now(timezone.utc)
    datos = {
        "sesiones": [
            {
                "token_hash": "a" * 64,
                "id_usuario": 1,
                "creado_en": ahora.isoformat(),
                "expira_en": (ahora + timedelta(hours=8)).isoformat(),
                "revocado": False,
                "revocado_en": None,
            },
            {
                "token_hash": "b" * 64,
                "id_usuario": 2,
                "creado_en": ahora.isoformat(),
                "expira_en": (ahora - timedelta(hours=1)).isoformat(),
                "revocado": False,
                "revocado_en": None,
            },
            {
                "token_hash": "c" * 64,
                "id_usuario": 1,
                "creado_en": ahora.isoformat(),
                "expira_en": (ahora + timedelta(hours=8)).isoformat(),
                "revocado": True,
                "revocado_en": ahora.isoformat(),
            },
            {
                "token_hash": "d" * 64,
                "id_usuario": 99,
                "creado_en": ahora.isoformat(),
                "expira_en": (ahora + timedelta(hours=8)).isoformat(),
                "revocado": False,
                "revocado_en": None,
            },
        ]
    }
    (ruta / "sesiones.json").write_text(json.dumps(datos), encoding="utf-8")


@pytest.fixture
def origen(tmp_path):
    _escribir_cuentas(tmp_path / "data", _cuentas_demo(), 4)
    _sesiones(tmp_path / "data")
    return tmp_path / "data"


class TestVerificacionPrevia:
    def test_no_escribe_nada_en_modo_verificacion(self, origen):
        base = BaseSimulada()
        informe = ejecutar(directorio=str(origen), conector=lambda: base)

        assert informe["exito"] is True
        assert base.inserts_cuentas == []
        assert base.inserts_sesiones == []
        assert "no se escribio" in informe["mensajes"][-1]

    def test_informa_cuentas_nuevas_y_presentes(self, origen):
        base = BaseSimulada()
        # Se migra una cuenta antes: deberia figurar como ya presente.
        ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)

        informe = ejecutar(directorio=str(origen), conector=lambda: base)
        plan = informe["plan"]

        assert plan["total"] == 3
        assert plan["nuevas"] == []
        assert len(plan["presentes"]) == 3
        assert plan["conflictos"] == []
        assert plan["invalidas"] == []


class TestMigracionDeCuentas:
    def test_conserva_identificadores_hashes_roles_y_estados(self, origen):
        base = BaseSimulada()
        informe = ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)

        assert informe["exito"] is True
        assert informe["aplicado"] is True
        assert informe["cuentas_insertadas"] == 3

        insertados = {int(param[0]): param for param in base.inserts_cuentas}
        assert set(insertados) == {1, 2, 3}

        dueno = insertados[1]
        assert dueno[1] == "Dueno"
        assert dueno[2] == "Sistema"
        assert dueno[3] == "dueno@optiroute.test"
        assert dueno[4] == _hash()
        assert dueno[5] == "DESARROLLADOR"
        assert dueno[6] is True
        assert dueno[7] is True  # es_propietario

        conductor = insertados[3]
        assert conductor[5] == "CONDUCTOR"
        assert conductor[6] is False  # activo
        assert conductor[8] == 5  # id_conductor

    def test_hash_persistente_sigue_siendo_verificable(self, origen):
        from backend.app.core.seguridad import verificar_password

        base = BaseSimulada()
        ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)

        id_usuario, _correo, almacenado = base.cuentas[1]
        assert verificar_password(PASSWORD, almacenado) is True

    def test_alinea_secuencias_con_los_ids_migrados(self, origen):
        base = BaseSimulada()
        ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)
        assert base.secuencias_alineadas >= 1

    def test_no_toca_los_archivos_de_origen(self, origen):
        base = BaseSimulada()
        original = {
            nombre: (origen / nombre).read_bytes()
            for nombre in ("cuentas.json", "sesiones.json")
        }

        ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)

        for nombre, contenido in original.items():
            assert (origen / nombre).read_bytes() == contenido

    def test_respaldo_json_antes_de_migrar(self, origen):
        base = BaseSimulada()
        informe = ejecutar(
            directorio=str(origen), aplicar=True, respaldar=True,
            conector=lambda: base,
        )
        respaldos = list((origen / "respaldos").iterdir())
        assert len(respaldos) == 1
        assert (respaldos[0] / "cuentas.json").exists()
        assert (respaldos[0] / "sesiones.json").exists()
        assert cualquier_mensaje(informe, "Respaldo JSON creado")


def cualquier_mensaje(informe: dict, fragmento: str) -> bool:
    return any(fragmento in mensaje for mensaje in informe["mensajes"])


class TestIdempotencia:
    def test_ejecutar_dos_veces_no_duplica_cuentas(self, origen):
        base = BaseSimulada()
        primero = ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)
        segundo = ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)

        assert primero["cuentas_insertadas"] == 3
        assert segundo["cuentas_insertadas"] == 0
        assert segundo["cuentas_ya_presentes"] == 3
        assert len(base.cuentas) == 3
        assert len(base.inserts_cuentas) == 3

    def test_migracion_concurrente_no_duplica(self, origen):
        base = BaseSimulada()
        resultados: list[dict] = []
        candado = threading.Lock()

        def migrar():
            informe = ejecutar(
                directorio=str(origen), aplicar=True, conector=lambda: base
            )
            with candado:
                resultados.append(informe)

        hilos = [threading.Thread(target=migrar) for _ in range(4)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        assert len(resultados) == 4
        assert all(informe["exito"] for informe in resultados)
        assert len(base.cuentas) == 3
        assert len(base.inserts_cuentas) == 3


class TestConflictos:
    def test_correo_duplicado_con_otro_id_detiene_la_migracion(self, origen, tmp_path):
        base = BaseSimulada()
        # Existe en PostgreSQL la cuenta 7 con el mismo correo que la 2.
        base.cuentas[7] = (7, "oper@optiroute.test", _hash("OtraClave9999"))

        informe = ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)

        assert informe["exito"] is False
        assert informe["codigo_salida"] == 2
        assert base.inserts_cuentas == []
        conflicto = informe["plan"]["conflictos"][0]
        assert "oper@optiroute.test" in conflicto["correo"]

    def test_hash_distinto_no_se_sobreescribe(self, origen):
        base = BaseSimulada()
        ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)
        # Se modifica el hash en PostgreSQL (simulando otro origen legitimo).
        base.cuentas[1] = (1, "dueno@optiroute.test", _hash("ClaveNueva2025"))

        informe = ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)

        assert informe["exito"] is False
        assert informe["codigo_salida"] == 2
        assert base.cuentas[1][2] == _hash("ClaveNueva2025")

    def test_hash_incompatible_marca_la_cuenta_invalida(self, tmp_path):
        cuentas = _cuentas_demo()
        cuentas[1]["password_hash"] = "texto-plano-sin-formato"
        _escribir_cuentas(tmp_path / "data", cuentas, 4)
        base = BaseSimulada()

        informe = ejecutar(
            directorio=str(tmp_path / "data"), aplicar=True, conector=lambda: base
        )

        assert informe["exito"] is False
        assert informe["codigo_salida"] == 2
        assert informe["plan"]["invalidas"]
        assert base.inserts_cuentas == []

    def test_rol_no_soportado_se_informa(self, tmp_path):
        cuentas = _cuentas_demo()
        cuentas[0]["rol"] = "SUPERADMIN"
        _escribir_cuentas(tmp_path / "data", cuentas, 4)
        base = BaseSimulada()

        informe = ejecutar(
            directorio=str(tmp_path / "data"), conector=lambda: base
        )

        assert informe["exito"] is False
        assert informe["codigo_salida"] == 2


class TestPrerrequisitos:
    def test_sin_tablas_no_migra(self, origen):
        base = BaseSimulada(tablas=())
        informe = ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)

        assert informe["exito"] is False
        assert informe["codigo_salida"] == 3
        assert base.inserts_cuentas == []

    def test_sin_archivo_de_cuentas_no_hace_nada(self, tmp_path):
        base = BaseSimulada()
        informe = ejecutar(directorio=str(tmp_path / "vacio"), conector=lambda: base)
        assert informe["exito"] is True
        assert base.inserts_cuentas == []


class TestSesiones:
    def test_solo_migra_sesiones_vigentes_y_de_cuentas_validas(self, origen):
        base = BaseSimulada()
        informe = ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)

        migradas = {param[0] for param in base.inserts_sesiones}
        assert migradas == {"a" * 64}
        sesiones = informe["sesiones"]
        assert sesiones["migradas"] == 1
        assert sesiones["omitidas"] == 3

    def test_sesiones_solo_exige_cuentas_ya_migradas(self, origen):
        base = BaseSimulada()
        ejecutar(directorio=str(origen), aplicar=True, conector=lambda: base)
        base.inserts_sesiones.clear()

        informe = ejecutar(
            directorio=str(origen), aplicar=True, solo_sesiones=True,
            conector=lambda: base,
        )

        assert informe["exito"] is True
        # La sesion vigente ya estaba migrada: la operacion es idempotente.
        assert len(base.inserts_sesiones) == 0
        assert informe["sesiones"]["migradas"] == 0
        assert len(base.inserts_cuentas) == 3  # no se repiten altas

    def test_sesiones_solo_migra_para_cuentas_ya_persistidas(self, origen):
        base = BaseSimulada()
        # La cuenta 1 ya esta en PostgreSQL (migrada en una ejecucion previa).
        base.cuentas[1] = (1, "dueno@optiroute.test", _hash())
        base.sesiones.clear()

        informe = ejecutar(
            directorio=str(origen), aplicar=True, solo_sesiones=True,
            conector=lambda: base,
        )

        assert informe["exito"] is True
        assert len(base.inserts_sesiones) == 1
        assert len(base.inserts_cuentas) == 0


class TestInterfazDeLineaDeComandos:
    def test_por_defecto_verifica_y_devuelve_cero(self, origen, capsys):
        base = BaseSimulada()
        codigo = _ejecutar_cli(origen, base)
        salida = capsys.readouterr().out
        assert codigo == 0
        assert "Modo verificacion" in salida
        assert base.inserts_cuentas == []

    def test_json_imprime_informe_valido(self, origen, capsys):
        base = BaseSimulada()
        codigo = _ejecutar_cli(origen, base, ["--json"])
        carga = json.loads(capsys.readouterr().out)
        assert codigo == 0
        assert carga["exito"] is True
        assert carga["plan"]["total"] == 3


def _ejecutar_cli(origen: Path, base: BaseSimulada, extra: list[str] | None = None):
    import backend.scripts.migrar_cuentas_json_a_postgres as modulo

    original = modulo.obtener_conexion
    modulo.obtener_conexion = lambda: base
    try:
        return modulo.main(["--directorio", str(origen), *(extra or [])])
    finally:
        modulo.obtener_conexion = original
