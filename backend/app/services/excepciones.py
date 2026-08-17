class RutaNoEncontradaError(Exception):
    """La ruta solicitada no existe."""


class RecursoNoEncontradoError(Exception):
    """Un recurso relacionado con la ruta no existe."""


class ReglaNegocioError(Exception):
    """La operacion no cumple una regla del dominio logistico."""
