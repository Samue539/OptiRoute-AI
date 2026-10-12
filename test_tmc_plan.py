import urllib.request, json
def get(u): return json.loads(urllib.request.urlopen(u).read().decode())
routes=get('http://127.0.0.1:8000/api/nodos')
print([r for r in routes if 'TMC' in r['nombre']])
pedidos=get('http://127.0.0.1:8000/api/pedidos')
pending=[p for p in pedidos if p['estado']=='PENDIENTE']
veh=get('http://127.0.0.1:8000/api/vehiculos')
bodega=[n for n in routes if 'TMC' in n['nombre']][0]
print('bodega', bodega)
payload=json.dumps({'origen': bodega['id_nodo'], 'pedidos': [p['id_pedido'] for p in pending[:4]], 'id_vehiculo': veh[0]['id_vehiculo']}).encode()
req=urllib.request.Request('http://127.0.0.1:8000/api/optimizacion/planificar', data=payload, headers={'Content-Type':'application/json'})
res=json.loads(urllib.request.urlopen(req).read().decode())
print('orden', res['orden_optimo'], 'dist', res['distancia_total_km'], 'recorrido', res['recorrido'][:10])
print('origen nombre', res['origen']['nombre'])
