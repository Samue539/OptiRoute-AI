class Grafo:

    def __init__(self):
        self.adyacencia = {}

    def agregar_vertice(self, vertice):
        if vertice not in self.adyacencia:
            self.adyacencia[vertice] = []

    def agregar_arista(self, origen, destino, peso, bidireccional=True):
        self.agregar_vertice(origen)
        self.agregar_vertice(destino)

        self.adyacencia[origen].append((destino, peso))

        if bidireccional:
            self.adyacencia[destino].append((origen, peso))

    def obtener_vecinos(self, vertice):
        return self.adyacencia.get(vertice, [])

    def obtener_vertices(self):
        return list(self.adyacencia.keys())

    def grado(self, vertice):
        return len(self.obtener_vecinos(vertice))

    def mostrar_lista_adyacencia(self):
        for vertice, vecinos in self.adyacencia.items():
            print(f"{vertice}: {vecinos}")

    def matriz_adyacencia(self):
        vertices = self.obtener_vertices()
        matriz = []

        for origen in vertices:
            fila = []

            for destino in vertices:
                peso = 0

                for vecino, peso_arista in self.obtener_vecinos(origen):
                    if vecino == destino:
                        peso = peso_arista
                        break

                fila.append(peso)

            matriz.append(fila)

        return vertices, matriz