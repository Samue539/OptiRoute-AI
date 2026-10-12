from backend.app.core.database import obtener_conexion
import math

TMC_LAT = -0.0966838
TMC_LON = -78.4753787

def haversine(lat1, lon1, lat2, lon2):
    R=6371.0
    phi1=math.radians(lat1); phi2=math.radians(lat2)
    dphi=math.radians(lat2-lat1); dlambda=math.radians(lon2-lon1)
    a=math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.asin(math.sqrt(a))

conn=obtener_conexion()
cur=conn.cursor()
# 1. actualizar nodo TMC
cur.execute("UPDATE logistica.nodos SET nombre='TMC Grupo Tramaco - Matriz Quito', latitud=%s, longitud=%s, tipo_nodo='BODEGA' WHERE id_nodo=1", (TMC_LAT, TMC_LON))
print('nodo TMC actualizado', cur.rowcount)
# verificar
cur.execute("SELECT id_nodo, nombre, latitud, longitud FROM logistica.nodos WHERE id_nodo=1")
print(cur.fetchone())
# 2. recalcular todas las aristas donde origen=1 o destino=1
cur.execute("SELECT id_conexion, id_nodo_origen, id_nodo_destino FROM logistica.conexiones WHERE id_nodo_origen=1 OR id_nodo_destino=1")
conns=cur.fetchall()
print('conexiones TMC', len(conns))
for cid, o, d in conns:
    cur.execute("SELECT latitud, longitud FROM logistica.nodos WHERE id_nodo=%s", (o,))
    lat1, lon1 = cur.fetchone()
    cur.execute("SELECT latitud, longitud FROM logistica.nodos WHERE id_nodo=%s", (d,))
    lat2, lon2 = cur.fetchone()
    dist = haversine(float(lat1), float(lon1), float(lat2), float(lon2))
    # redondear a 3 decimales
    dist = round(dist, 3)
    tiempo = round(dist * 2.2, 2)  # estimado 2.2 min/km
    cur.execute("UPDATE logistica.conexiones SET distancia_km=%s, tiempo_minutos=%s WHERE id_conexion=%s", (dist, tiempo, cid))
    print(f'  conexion {cid}: {o}->{d} = {dist} km')
conn.commit()
# verificar nodos
cur.execute("SELECT id_nodo, nombre, latitud, longitud FROM logistica.nodos WHERE tipo_nodo='BODEGA'")
print('bodegas', cur.fetchall())
cur.execute("SELECT count(*) FROM logistica.nodos")
print('nodos', cur.fetchone()[0])
cur.execute("SELECT count(*) FROM logistica.conexiones")
print('aristas', cur.fetchone()[0])
# mostrar conexiones TMC actualizadas
cur.execute("SELECT id_nodo_origen, id_nodo_destino, distancia_km FROM logistica.conexiones WHERE id_nodo_origen=1 OR id_nodo_destino=1 ORDER BY id_conexion")
for r in cur.fetchall():
    cur.execute("SELECT nombre FROM logistica.nodos WHERE id_nodo=%s", (r[0],))
    n1 = cur.fetchone()[0]
    cur.execute("SELECT nombre FROM logistica.nodos WHERE id_nodo=%s", (r[1],))
    n2 = cur.fetchone()[0]
    print(f'TMC {n1} -> {n2} : {r[2]} km')
cur.close(); conn.close()
print('DONE')
