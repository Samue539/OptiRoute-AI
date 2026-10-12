"""Servicio de guias: entrega real, idempotencia, aislamiento y evidencias.

Usa ConexionSimulada (sin PostgreSQL real). Cubre:
* entrega exitosa con sus dos fotos, receptor y GPS;
* reintento con la misma clave -> una sola entrega (duplicada);
* guia ya ENTREGADA -> 409 (no se entrega dos veces);
* conductor ante ruta ajena -> 403;
* validacion de imagenes (firma magica, tamano, tipo).
"""

import pytest

from backend.app.services import guias_service
from backend.app.services.evidencias_storage import ErrorEvidencia, validar_imagen
from tests.conftest import ConexionSimulada


JPEG = b"\xff\xd8\xff" + b"\x00" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200


class AlmacenFalso:
    def __init__(self):
        self.guardadas = []

    def guardar(self, sha256, extension, contenido):
        self.guardadas.append((sha256, extension, len(contenido)))
        return f"{sha256}{extension}"


def _conexion(respuestas):
    return ConexionSimulada(respuestas)


def _guia_fila(estado="PENDIENTE", id_ruta=3, id_pedido=10):
    return (7, "GUI-TEST-001", id_pedido, id_ruta, estado)


def _ruta_fila(estado_ruta="EN_RUTA", id_conductor=5):
    return (3, "RUT-000003", estado_ruta, id_conductor, 1)


def _parche_conexion(monkeypatch, conexion):
    monkeypatch.setattr(
        guias_service, "obtener_conexion", lambda: conexion
    )


def test_entrega_exitosa_guarda_dos_evidencias(monkeypatch):
    conexion = _conexion(
        [
            (True,),  # 008 aplicada
            _guia_fila(),  # guia FOR UPDATE
            None,  # sin evento previo con esa clave
            _ruta_fila(),  # ruta
            (False,),  # 007 ausente -> regla legada
            (None,),  # cuenta canonica ausente -> actor NULL
            (55, "2026-01-01T00:00:00+00:00"),  # INSERT evento
            None,  # INSERT evidencia 1
            None,  # INSERT evidencia 2
            None,  # UPDATE guia
            None,  # UPDATE pedido
            None,  # UPSERT entrega
        ]
    )
    _parche_conexion(monkeypatch, conexion)
    almacen = AlmacenFalso()

    resultado = guias_service.registrar_entrega(
        1, None, True, 7,
        receptor_nombre="Maria Perez",
        relacion_destinatario="FAMILIAR",
        gps_latitud=-0.18, gps_longitud=-78.48,
        gps_precision_m=12.5, gps_origen="GPS",
        observaciones="Timbre 2",
        clave_idempotencia="clave-unica-1",
        fotos=[
            ("FOTO_GUIA", JPEG, "guia.jpg", "image/jpeg"),
            ("FOTO_PAQUETE", PNG, "paquete.png", "image/png"),
        ],
        storage=almacen,
    )

    assert resultado["estado"] == "ENTREGADA"
    assert resultado["duplicada"] is False
    assert resultado["numero_guia"] == "GUI-TEST-001"
    assert len(almacen.guardadas) == 2
    assert conexion.commits == 1
    consultas = " ".join(c[0] for c in conexion.cursor_simulado.consultas)
    assert "CURRENT_TIMESTAMP" in consultas  # la hora la pone el servidor


def test_reintento_misma_clave_no_duplica(monkeypatch):
    conexion = _conexion(
        [
            (True,),
            _guia_fila(estado="PENDIENTE"),
            (55, "ENTREGADA", "2026-01-01T00:00:00+00:00"),  # evento previo
        ]
    )
    _parche_conexion(monkeypatch, conexion)

    resultado = guias_service.registrar_entrega(
        1, None, True, 7,
        receptor_nombre="Maria Perez",
        relacion_destinatario="DESTINATARIO",
        clave_idempotencia="clave-unica-1",
        fotos=[
            ("FOTO_GUIA", JPEG, "g.jpg", "image/jpeg"),
            ("FOTO_PAQUETE", JPEG, "p.jpg", "image/jpeg"),
        ],
        storage=AlmacenFalso(),
    )

    assert resultado["duplicada"] is True
    assert resultado["estado"] == "ENTREGADA"
    assert conexion.commits == 0


def test_guia_entregada_no_se_entrega_dos_veces(monkeypatch):
    conexion = _conexion(
        [
            (True,),
            _guia_fila(estado="ENTREGADA"),
            None,
            _ruta_fila(),
            (False,),
        ]
    )
    _parche_conexion(monkeypatch, conexion)

    with pytest.raises(guias_service.ErrorDistribucion) as error:
        guias_service.registrar_entrega(
            1, None, True, 7,
            receptor_nombre="Maria Perez",
            relacion_destinatario="DESTINATARIO",
            clave_idempotencia="otra-clave-2",
            fotos=[
                ("FOTO_GUIA", JPEG, "g.jpg", "image/jpeg"),
                ("FOTO_PAQUETE", JPEG, "p.jpg", "image/jpeg"),
            ],
            storage=AlmacenFalso(),
        )

    assert error.value.codigo == 409


def test_conductor_no_entrega_ruta_ajena(monkeypatch):
    conexion = _conexion(
        [
            (True,),
            _guia_fila(),
            None,
            _ruta_fila(id_conductor=99),  # otro conductor
            (False,),  # sin 007 -> regla legada: solo propias
        ]
    )
    _parche_conexion(monkeypatch, conexion)

    with pytest.raises(guias_service.ErrorDistribucion) as error:
        guias_service.registrar_entrega(
            9, 7, False, 7,  # id_cuenta=9, id_conductor=7, sin ver_todas
            receptor_nombre="Maria Perez",
            relacion_destinatario="DESTINATARIO",
            clave_idempotencia="clave-3",
            fotos=[
                ("FOTO_GUIA", JPEG, "g.jpg", "image/jpeg"),
                ("FOTO_PAQUETE", JPEG, "p.jpg", "image/jpeg"),
            ],
            storage=AlmacenFalso(),
        )

    assert error.value.codigo == 403


def test_entrega_exige_las_dos_fotos():
    with pytest.raises(guias_service.ErrorDistribucion) as error:
        guias_service.registrar_entrega(
            1, None, True, 7,
            receptor_nombre="Maria Perez",
            relacion_destinatario="DESTINATARIO",
            clave_idempotencia="clave-4",
            fotos=[("FOTO_GUIA", JPEG, "g.jpg", "image/jpeg")],
            storage=AlmacenFalso(),
        )
    assert error.value.codigo == 400


def test_novedad_fallida_exige_motivo():
    with pytest.raises(guias_service.ErrorDistribucion) as error:
        guias_service.registrar_novedad(
            1, None, True, 7, tipo="FALLIDA", motivo_falla="x",
            clave_idempotencia="clave-5", storage=AlmacenFalso(),
        )
    assert error.value.codigo == 400


def test_imagen_con_firma_falsa_se_rechaza():
    with pytest.raises(ErrorEvidencia):
        validar_imagen(b"MZ\x90\x00no-es-imagen", "evil.exe", "image/jpeg")


def test_imagen_sospechosa_por_tipo_declarado_se_rechaza():
    with pytest.raises(ErrorEvidencia):
        validar_imagen(JPEG, "guia.jpg", "image/png")


def test_imagen_mayor_a_15_mb_se_rechaza():
    with pytest.raises(ErrorEvidencia):
        validar_imagen(b"\xff\xd8\xff" + b"\x00" * (15 * 1024 * 1024 + 1), "g.jpg", "image/jpeg")


def test_imagen_valida_devuelve_hash_y_mime():
    validada = validar_imagen(JPEG, "guia.jpg", "image/jpeg")
    assert validada.mime == "image/jpeg"
    assert len(validada.sha256) == 64
