"""Script manual para verificar la conexion a PostgreSQL.

No es una prueba de pytest: no contiene funciones test_*. Se protege con
`if __name__ == "__main__":` para que pytest pueda recolectar este archivo
sin abrir una conexion real a la base de datos durante el import.

Ejecucion manual:
    python -m tests.test_database
"""

from backend.app.core.database import obtener_conexion


def main():
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("SELECT version();")
    version = cursor.fetchone()

    print("CONEXION A POSTGRESQL")
    print("---------------------")
    print("Conexion correcta")
    print(version[0])

    cursor.close()
    conexion.close()


if __name__ == "__main__":
    main()
