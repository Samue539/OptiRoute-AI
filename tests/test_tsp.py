"""
Pruebas unitarias del algoritmo TSP (Traveling Salesman Problem).

Verifica:
- Casos con 1, 2 y 4 destinos
- Cálculo correcto de distancia
- Recorrido físico completo
- Opción regresar_origen
- Validación de límite máximo
- Casos donde no existe arista directa (usando Dijkstra)
- Casos imposibles (nodo inaccesible)
"""

import pytest
from backend.app.algorithms.grafo import Grafo
from backend.app.algorithms.dijkstra import dijkstra
from backend.app.algorithms.tsp import (
    resolver_tsp_exacto,
    calcular_distancia_recorrido,
)


@pytest.fixture
def grafo_simple():
    """
    Grafo de prueba simple:

    1 ---4--- 2
    |  \\      |
    5   \3   2
    |    \\   |
    3 ----1-- 4
    """
    grafo = Grafo()

    grafo.agregar_arista(1, 2, 4)
    grafo.agregar_arista(1, 3, 5)
    grafo.agregar_arista(1, 4, 3)
    grafo.agregar_arista(2, 4, 2)
    grafo.agregar_arista(3, 4, 1)

    return grafo


@pytest.fixture
def grafo_con_intermedios():
    """
    Grafo donde para ir de 1 a 3 hay que pasar por 2.
    No existe arista directa 1-3.

    1 --5-- 2 --3-- 3
    """
    grafo = Grafo()

    grafo.agregar_arista(1, 2, 5)
    grafo.agregar_arista(2, 3, 3)

    return grafo


@pytest.fixture
def grafo_desconexo():
    """
    Grafo con dos componentes desconexas.

    Componente 1: 1--2
    Componente 2: 3--4
    """
    grafo = Grafo()

    grafo.agregar_arista(1, 2, 5, bidireccional=False)
    grafo.agregar_arista(3, 4, 3, bidireccional=False)

    return grafo


class TestCalcularDistanciaRecorrido:
    """Pruebas de la función auxiliar calcular_distancia_recorrido."""

    def test_un_solo_nodo(self, grafo_simple):
        """Con un solo nodo, distancia es 0 y recorrido es [nodo]."""
        distancia, recorrido = calcular_distancia_recorrido(
            grafo_simple,
            dijkstra,
            [1]
        )

        assert distancia == 0
        assert recorrido == [1]

    def test_dos_nodos_conectados(self, grafo_simple):
        """Dos nodos conectados directamente."""
        distancia, recorrido = calcular_distancia_recorrido(
            grafo_simple,
            dijkstra,
            [1, 2]
        )

        assert distancia == 4
        assert recorrido == [1, 2]

    def test_tres_nodos(self, grafo_simple):
        """Recorrido de tres nodos."""
        distancia, recorrido = calcular_distancia_recorrido(
            grafo_simple,
            dijkstra,
            [1, 2, 4]
        )

        assert distancia == 4 + 2
        assert recorrido == [1, 2, 4]

    def test_recorrido_con_nodos_intermedios(self, grafo_con_intermedios):
        """Dijkstra incluye nodos intermedios en el recorrido."""
        distancia, recorrido = calcular_distancia_recorrido(
            grafo_con_intermedios,
            dijkstra,
            [1, 3]
        )

        assert distancia == 5 + 3
        assert recorrido == [1, 2, 3]

    def test_nodo_inaccesible(self, grafo_desconexo):
        """Si un nodo es inaccesible, retorna None."""
        resultado = calcular_distancia_recorrido(
            grafo_desconexo,
            dijkstra,
            [1, 3]
        )

        assert resultado is None


class TestResolverTSPExacto:
    """Pruebas del algoritmo TSP exacto."""

    def test_un_destino(self, grafo_simple):
        """Con un destino, la solución es directa."""
        resultado = resolver_tsp_exacto(
            grafo_simple,
            dijkstra,
            origen=1,
            destinos=[2],
            regresar_origen=False,
        )

        assert resultado is not None
        assert resultado["orden_optimo"] == [2]
        assert resultado["distancia_total_km"] == 4
        assert resultado["permutaciones_evaluadas"] == 1

    def test_dos_destinos(self, grafo_simple):
        """
        Con dos destinos, se evalúan 2! = 2 permutaciones.

        Orden 1: [2, 4] -> distancia 4 + 2 = 6
        Orden 2: [4, 2] -> distancia 3 + 2 = 5

        El óptimo es [4, 2].
        """
        resultado = resolver_tsp_exacto(
            grafo_simple,
            dijkstra,
            origen=1,
            destinos=[2, 4],
            regresar_origen=False,
        )

        assert resultado is not None
        assert resultado["orden_optimo"] == [4, 2]
        assert resultado["distancia_total_km"] == 5
        assert resultado["permutaciones_evaluadas"] == 2

    def test_cuatro_destinos(self, grafo_simple):
        """
        Con cuatro destinos, se evalúan 4! = 24 permutaciones.
        """
        resultado = resolver_tsp_exacto(
            grafo_simple,
            dijkstra,
            origen=1,
            destinos=[2, 3, 4],
            regresar_origen=False,
        )

        assert resultado is not None
        assert len(resultado["orden_optimo"]) == 3
        assert resultado["permutaciones_evaluadas"] == 6

    def test_regresar_origen_false(self, grafo_simple):
        """Sin regreso a origen."""
        resultado = resolver_tsp_exacto(
            grafo_simple,
            dijkstra,
            origen=1,
            destinos=[2, 4],
            regresar_origen=False,
        )

        assert resultado is not None
        assert resultado["regresar_origen"] == False

    def test_regresar_origen_true(self, grafo_simple):
        """Con regreso a origen, se suma la distancia de regreso."""
        resultado = resolver_tsp_exacto(
            grafo_simple,
            dijkstra,
            origen=1,
            destinos=[4],
            regresar_origen=True,
        )

        assert resultado is not None
        distancia_sin_regreso = 3
        distancia_con_regreso = 3 + 3
        assert resultado["distancia_total_km"] == distancia_con_regreso

    def test_grafo_con_nodos_intermedios(self, grafo_con_intermedios):
        """
        Cuando Dijkstra debe atravesar nodos intermedios,
        el recorrido debe incluirlos.
        """
        resultado = resolver_tsp_exacto(
            grafo_con_intermedios,
            dijkstra,
            origen=1,
            destinos=[3],
            regresar_origen=False,
        )

        assert resultado is not None
        assert resultado["distancia_total_km"] == 5 + 3
        assert 2 in resultado["recorrido"]

    def test_nodo_inaccesible(self, grafo_desconexo):
        """Si no hay camino, retorna None."""
        resultado = resolver_tsp_exacto(
            grafo_desconexo,
            dijkstra,
            origen=1,
            destinos=[3],
            regresar_origen=False,
        )

        assert resultado is None

    def test_limite_destinos_excedido(self, grafo_simple):
        """Exceder el límite de destinos lanza ValueError."""
        with pytest.raises(ValueError, match="excede el límite permitido"):
            resolver_tsp_exacto(
                grafo_simple,
                dijkstra,
                origen=1,
                destinos=list(range(2, 11)),
                limite_destinos=8,
            )

    def test_lista_destinos_vacia(self, grafo_simple):
        """Lista vacía de destinos retorna None."""
        resultado = resolver_tsp_exacto(
            grafo_simple,
            dijkstra,
            origen=1,
            destinos=[],
            regresar_origen=False,
        )

        assert resultado is None

    def test_recorrido_completo_incluye_origen(self, grafo_simple):
        """El recorrido debe incluir el origen como primer nodo."""
        resultado = resolver_tsp_exacto(
            grafo_simple,
            dijkstra,
            origen=1,
            destinos=[2],
            regresar_origen=False,
        )

        assert resultado is not None
        assert resultado["recorrido"][0] == 1

    def test_recorrido_completo_sin_regreso_no_incluye_origen_final(self, grafo_simple):
        """
        Sin regresar_origen, el último nodo del recorrido
        debe ser uno de los destinos, no el origen.
        """
        resultado = resolver_tsp_exacto(
            grafo_simple,
            dijkstra,
            origen=1,
            destinos=[4],
            regresar_origen=False,
        )

        assert resultado is not None
        assert resultado["recorrido"][-1] == 4

    def test_recorrido_completo_con_regreso_termina_en_origen(self, grafo_simple):
        """
        Con regresar_origen=True, el último nodo debe ser el origen.
        """
        resultado = resolver_tsp_exacto(
            grafo_simple,
            dijkstra,
            origen=1,
            destinos=[4],
            regresar_origen=True,
        )

        assert resultado is not None
        assert resultado["recorrido"][-1] == 1
