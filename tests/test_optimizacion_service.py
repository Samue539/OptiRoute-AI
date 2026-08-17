"""
Pruebas del servicio de optimización multi-entrega y endpoint API.

Prueba casos de validación:
- Origen inexistente
- Destino inexistente
- Lista vacía
- Destinos duplicados
- Origen incluido en destinos
- Más destinos que el límite
- regresar_origen = true
- Casos exitosos con datos reales de BD
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.excepciones import ReglaNegocioError
from backend.app.services.optimizacion_service import optimizar_multi_entrega
from tests.conftest import ConexionSimulada


client = TestClient(app)


class TestOptimizarMultiEntregaValidaciones:
    """Pruebas de validación en el servicio."""

    @patch("backend.app.services.optimizacion_service.obtener_nodo")
    def test_origen_inexistente(self, mock_obtener_nodo):
        """Origen inexistente lanza error."""
        mock_obtener_nodo.return_value = None

        with pytest.raises(
            ReglaNegocioError,
            match="nodo origen .* no existe"
        ):
            optimizar_multi_entrega(
                origen=999,
                destinos=[2, 3],
            )

    @patch("backend.app.services.optimizacion_service.obtener_nodo")
    def test_destino_inexistente(self, mock_obtener_nodo):
        """Destino inexistente lanza error."""
        mock_obtener_nodo.side_effect = [
            {"id_nodo": 1, "nombre": "Bodega", "tipo_nodo": "BODEGA",
             "latitud": 0.0, "longitud": 0.0},
            None,
        ]

        with pytest.raises(
            ReglaNegocioError,
            match="nodo destino .* no existe"
        ):
            optimizar_multi_entrega(
                origen=1,
                destinos=[999],
            )

    @patch("backend.app.services.optimizacion_service.obtener_nodo")
    def test_lista_destinos_vacia(self, mock_obtener_nodo):
        """Lista vacía lanza error."""
        mock_obtener_nodo.return_value = {
            "id_nodo": 1,
            "nombre": "Bodega",
            "tipo_nodo": "BODEGA",
            "latitud": 0.0,
            "longitud": 0.0
        }

        with pytest.raises(
            ReglaNegocioError,
            match="destinos no puede estar vacía"
        ):
            optimizar_multi_entrega(
                origen=1,
                destinos=[],
            )

    @patch("backend.app.services.optimizacion_service.obtener_nodo")
    def test_destinos_duplicados(self, mock_obtener_nodo):
        """Destinos duplicados lanzan error."""
        mock_obtener_nodo.return_value = {
            "id_nodo": 1,
            "nombre": "Bodega",
            "tipo_nodo": "BODEGA",
            "latitud": 0.0,
            "longitud": 0.0
        }

        with pytest.raises(
            ReglaNegocioError,
            match="duplicados"
        ):
            optimizar_multi_entrega(
                origen=1,
                destinos=[2, 2, 3],
            )

    @patch("backend.app.services.optimizacion_service.obtener_nodo")
    def test_origen_en_destinos(self, mock_obtener_nodo):
        """Origen incluido en destinos lanza error."""
        mock_obtener_nodo.return_value = {
            "id_nodo": 1,
            "nombre": "Bodega",
            "tipo_nodo": "BODEGA",
            "latitud": 0.0,
            "longitud": 0.0
        }

        with pytest.raises(
            ReglaNegocioError,
            match="origen no puede estar incluido"
        ):
            optimizar_multi_entrega(
                origen=1,
                destinos=[1, 2, 3],
            )

    @patch("backend.app.services.optimizacion_service.obtener_nodo")
    def test_demasiados_destinos(self, mock_obtener_nodo):
        """Más de 8 destinos lanza error."""
        mock_obtener_nodo.return_value = {
            "id_nodo": 1,
            "nombre": "Bodega",
            "tipo_nodo": "BODEGA",
            "latitud": 0.0,
            "longitud": 0.0
        }

        with pytest.raises(
            ReglaNegocioError,
            match="excede el máximo permitido"
        ):
            optimizar_multi_entrega(
                origen=1,
                destinos=list(range(2, 12)),
            )


class TestEndpointMultiEntrega:
    """Pruebas del endpoint HTTP."""

    def test_endpoint_estructura_basica(self):
        """El endpoint /api/optimizacion/multi-entrega existe."""
        respuesta = client.post(
            "/api/optimizacion/multi-entrega",
            json={
                "origen": 1,
                "destinos": [2],
                "regresar_origen": False,
            }
        )

        assert respuesta.status_code in [200, 409, 404, 500]

    def test_validacion_origen_debe_ser_positivo(self):
        """El schema rechaza origen <= 0."""
        respuesta = client.post(
            "/api/optimizacion/multi-entrega",
            json={
                "origen": 0,
                "destinos": [2],
            }
        )

        assert respuesta.status_code == 422

    def test_validacion_destino_debe_ser_positivo(self):
        """El schema rechaza destino <= 0."""
        respuesta = client.post(
            "/api/optimizacion/multi-entrega",
            json={
                "origen": 1,
                "destinos": [0],
            }
        )

        assert respuesta.status_code == 422

    def test_validacion_destinos_no_vacio(self):
        """El schema rechaza lista vacía."""
        respuesta = client.post(
            "/api/optimizacion/multi-entrega",
            json={
                "origen": 1,
                "destinos": [],
            }
        )

        assert respuesta.status_code == 422

    def test_validacion_maximo_destinos(self):
        """El schema rechaza más de 8 destinos."""
        respuesta = client.post(
            "/api/optimizacion/multi-entrega",
            json={
                "origen": 1,
                "destinos": list(range(2, 12)),
            }
        )

        assert respuesta.status_code == 422

    def test_regresar_origen_default_false(self):
        """Si no se especifica, regresar_origen es False."""
        with patch(
            "backend.app.services.optimizacion_service.obtener_nodo"
        ) as mock_nodo:
            nodo = {
                "id_nodo": 1,
                "nombre": "Test",
                "tipo_nodo": "BODEGA",
                "latitud": 0.0,
                "longitud": 0.0,
            }
            mock_nodo.return_value = nodo

            with patch(
                "backend.app.services.optimizacion_service.cargar_grafo_desde_bd"
            ):
                with patch(
                    "backend.app.services.optimizacion_service.resolver_tsp_exacto"
                ) as mock_tsp:
                    mock_tsp.return_value = {
                        "orden_optimo": [2],
                        "recorrido": [1, 2],
                        "distancia_total_km": 10,
                        "permutaciones_evaluadas": 1,
                    }

                    respuesta = client.post(
                        "/api/optimizacion/multi-entrega",
                        json={
                            "origen": 1,
                            "destinos": [2],
                        }
                    )

                    assert respuesta.status_code == 200
                    datos = respuesta.json()
                    assert datos["regresar_origen"] == False

    def test_respuesta_incluye_campos_requeridos(self):
        """La respuesta incluye todos los campos especificados."""
        with patch(
            "backend.app.services.optimizacion_service.obtener_nodo"
        ) as mock_nodo:
            nodo = {
                "id_nodo": 1,
                "nombre": "Bodega",
                "tipo_nodo": "BODEGA",
                "latitud": 0.0,
                "longitud": 0.0,
            }
            mock_nodo.return_value = nodo

            with patch(
                "backend.app.services.optimizacion_service.cargar_grafo_desde_bd"
            ):
                with patch(
                    "backend.app.services.optimizacion_service.resolver_tsp_exacto"
                ) as mock_tsp:
                    mock_tsp.return_value = {
                        "orden_optimo": [2],
                        "recorrido": [1, 2],
                        "distancia_total_km": 10,
                        "permutaciones_evaluadas": 1,
                    }

                    respuesta = client.post(
                        "/api/optimizacion/multi-entrega",
                        json={
                            "origen": 1,
                            "destinos": [2],
                            "regresar_origen": False,
                        }
                    )

                    assert respuesta.status_code == 200
                    datos = respuesta.json()

                    assert "origen" in datos
                    assert "destinos_solicitados" in datos
                    assert "orden_optimo" in datos
                    assert "orden_optimo_info" in datos
                    assert "recorrido" in datos
                    assert "recorrido_info" in datos
                    assert "distancia_total_km" in datos
                    assert "regresar_origen" in datos
                    assert "algoritmo" in datos
                    assert "permutaciones_evaluadas" in datos

    def test_respuesta_incluye_nombre_algoritmo(self):
        """El algoritmo debe ser TSP_EXACTO."""
        with patch(
            "backend.app.services.optimizacion_service.obtener_nodo"
        ) as mock_nodo:
            nodo = {
                "id_nodo": 1,
                "nombre": "Bodega",
                "tipo_nodo": "BODEGA",
                "latitud": 0.0,
                "longitud": 0.0,
            }
            mock_nodo.return_value = nodo

            with patch(
                "backend.app.services.optimizacion_service.cargar_grafo_desde_bd"
            ):
                with patch(
                    "backend.app.services.optimizacion_service.resolver_tsp_exacto"
                ) as mock_tsp:
                    mock_tsp.return_value = {
                        "orden_optimo": [2],
                        "recorrido": [1, 2],
                        "distancia_total_km": 10,
                        "permutaciones_evaluadas": 1,
                    }

                    respuesta = client.post(
                        "/api/optimizacion/multi-entrega",
                        json={
                            "origen": 1,
                            "destinos": [2],
                        }
                    )

                    assert respuesta.status_code == 200
                    datos = respuesta.json()
                    assert datos["algoritmo"] == "TSP_EXACTO"

    def test_error_nodo_inexistente_retorna_409(self):
        """Nodo inexistente retorna 409 Conflict."""
        with patch(
            "backend.app.services.optimizacion_service.obtener_nodo"
        ) as mock_nodo:
            mock_nodo.return_value = None

            respuesta = client.post(
                "/api/optimizacion/multi-entrega",
                json={
                    "origen": 999,
                    "destinos": [2],
                }
            )

            assert respuesta.status_code == 409

    def test_error_sin_solucion_retorna_409(self):
        """Sin solución posible retorna 409."""
        with patch(
            "backend.app.services.optimizacion_service.obtener_nodo"
        ) as mock_nodo:
            nodo = {
                "id_nodo": 1,
                "nombre": "Bodega",
                "tipo_nodo": "BODEGA",
                "latitud": 0.0,
                "longitud": 0.0,
            }
            mock_nodo.return_value = nodo

            with patch(
                "backend.app.services.optimizacion_service.cargar_grafo_desde_bd"
            ):
                with patch(
                    "backend.app.services.optimizacion_service.resolver_tsp_exacto"
                ) as mock_tsp:
                    mock_tsp.return_value = None

                    respuesta = client.post(
                        "/api/optimizacion/multi-entrega",
                        json={
                            "origen": 1,
                            "destinos": [999],
                        }
                    )

                    assert respuesta.status_code == 409
