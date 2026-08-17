class CursorSimulado:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.actual = None
        self.consultas = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, consulta, parametros=None):
        self.consultas.append((consulta, parametros))
        if not self.respuestas:
            raise AssertionError("No se preparo una respuesta para la consulta SQL.")
        self.actual = self.respuestas.pop(0)

    def fetchone(self):
        return self.actual

    def fetchall(self):
        return self.actual


class ConexionSimulada:
    def __init__(self, respuestas):
        self.cursor_simulado = CursorSimulado(respuestas)
        self.commits = 0
        self.rollbacks = 0
        self.cerrada = False

    def cursor(self):
        return self.cursor_simulado

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.cerrada = True
