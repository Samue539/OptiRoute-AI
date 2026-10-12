from backend.app.core.database import obtener_conexion
import pathlib
p = pathlib.Path('database/seeds/004_tmc_matriz.sql')
sql = p.read_text(encoding='utf-8')
conn = obtener_conexion()
cur = conn.cursor()
try:
    cur.execute(sql)
    conn.commit()
    print('004 ok')
    cur.execute("SELECT id_nodo, nombre, latitud, longitud FROM logistica.nodos WHERE tipo_nodo='BODEGA' ORDER BY id_nodo")
    for r in cur.fetchall():
        print(r)
    cur.execute("SELECT nombre, latitud, longitud FROM logistica.nodos WHERE nombre LIKE 'Cliente%' ORDER BY nombre")
    for r in cur.fetchall():
        print(r)
except Exception as e:
    conn.rollback()
    print('ERR', e)
    import traceback; traceback.print_exc()
finally:
    try: cur.close()
    except: pass
    conn.close()
