from backend.app.core.database import obtener_conexion


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