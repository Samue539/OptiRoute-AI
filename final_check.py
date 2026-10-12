import urllib.request, json, sys
def get(u): return json.loads(urllib.request.urlopen(u, timeout=10).read().decode())
def post(u,data,method='POST'):
    payload=json.dumps(data).encode()
    req=urllib.request.Request(u, data=payload, headers={'Content-Type':'application/json'}, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
def patch(u,data):
    return post(u,data,method='PATCH')

base='http://127.0.0.1:8000'
# 1 dashboard not via api but check routes etc
print('1. Check TMC node')
nodos=get(base+'/api/nodos')
tmc=[n for n in nodos if 'TMC' in n['nombre']][0]
print(f"TMC {tmc['nombre']} {tmc['latitud']},{tmc['longitud']} tipo {tmc['tipo_nodo']}")
assert str(tmc['latitud']).startswith('-0.09668'), 'lat wrong'
assert str(tmc['longitud']).startswith('-78.47537'), 'lon wrong'
print('TMC OK')

# grafo
grafo=get(base+'/api/grafo')
print(f"Nodos {len(grafo['nodos'])} Aristas {len(grafo['conexiones'])}")
tmc_conns=[c for c in grafo['conexiones'] if c['origen']==1 or c['destino']==1]
print('Aristas TMC', len(tmc_conns))
for c in tmc_conns:
    print(f"  {c['origen']}->{c['destino']} {c['distancia_km']}km")
# Dijkstra
from backend.app.algorithms.dijkstra import dijkstra
from backend.app.services.grafo_service import cargar_grafo_desde_bd
grafo_obj=cargar_grafo_desde_bd()
res=dijkstra(grafo_obj,1,2)
print(f"Dijkstra TMC->Cliente A camino {res['camino']} dist {res['distancia']}")
assert res['distancia']>0 and res['distancia']<10
# TSP
orders=get(base+'/api/pedidos')
pending=[o for o in orders if o['estado']=='PENDIENTE'][:4]
veh=get(base+'/api/vehiculos')
drivers=get(base+'/api/conductores')
print(f"Pedidos {len(orders)} pending {len(pending)} veh {len(veh)} drivers {len(drivers)}")
plan=post(base+'/api/optimizacion/planificar', {'origen': tmc['id_nodo'], 'pedidos': [p['id_pedido'] for p in pending], 'id_vehiculo': veh[0]['id_vehiculo'], 'regresar_origen': False})
print(f"TSP orden {plan['orden_optimo']} dist {plan['distancia_total_km']} alg {plan['algoritmo']} origen {plan['origen']['nombre']}")
assert 'TMC' in plan['origen']['nombre']
# guardar ruta
ruta=post(base+'/api/rutas', {'origen': plan['origen']['id_nodo'], 'destino': plan['orden_optimo'][-1]})
print(f"Ruta creada {ruta['codigo']} {ruta['id_ruta']}")
# asignar
assign=patch(f"{base}/api/rutas/{ruta['id_ruta']}/asignacion", {'id_conductor': drivers[0]['id_conductor'], 'id_vehiculo': veh[0]['id_vehiculo']})
print(f"Asignada {assign['codigo']} {assign['estado']}")
# verificar ruta detalle
det=get(f"{base}/api/rutas/{ruta['id_ruta']}")
print(f"Detalle ruta {det['codigo']} puntos {len(det['puntos'])} origen {det['origen']['nombre']}")
assert 'TMC' in det['origen']['nombre']
# pedidos ver
ped=get(base+f"/api/pedidos/{pending[0]['id_pedido']}")
print(f"Pedido ver {ped['codigo']} {ped['estado']} destino {ped['destino']['nombre']}")
# pedidos nuevo
clientes=get(base+'/api/clientes')
cli=clientes[0]
dirs=get(base+f"/api/clientes/{cli['id_cliente']}/direcciones")
new=post(base+'/api/pedidos', {'id_cliente': cli['id_cliente'], 'id_direccion_entrega': dirs[0]['id_direccion'], 'descripcion':'TEST FINAL CHECK','peso_kg':10,'volumen_m3':0.1,'prioridad':'NORMAL'})
print(f"Nuevo pedido {new['codigo']}")
# clientes ver
c=get(base+f"/api/clientes/{cli['id_cliente']}")
print(f"Cliente ver {c['id_cliente']} {c['nombres'] or c['razon_social']}")
# reporte like
routes=get(base+'/api/rutas')
print(f"Rutas total {len(routes)}")
# IA grafo
bfs=get(base+'/api/grafo/bfs?inicio=1')
print(f"BFS {bfs['recorrido'][:5]}")
dfs=get(base+'/api/grafo/dfs?inicio=1')
print(f"DFS {dfs['recorrido'][:5]}")

print('ALL CHECKS OK')
