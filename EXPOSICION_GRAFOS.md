# Exposición Grafos — OptiRoute AI

Guía sencilla para demostración académica. Lenguaje directo, sin adornos.

## 1. Qué es un grafo
Conjunto de **vértices (nodos)** conectados por **aristas (conexiones)**. Sirve para modelar redes: calles, rutas logísticas. En OptiRoute, el grafo representa Quito con bodega y clientes.

## 2. Qué representa un nodo
Fila en `logistica.nodos`:
- `id_nodo`, `nombre`, `tipo_nodo` (BODEGA, CLIENTE, INTERSECCION), `latitud`, `longitud`, `activo`
Ejemplo real: `1 TMC Grupo Tramaco - Matriz Quito (-0.094867, -78.483472) — Manuel Najas OE1-346 y Joaquín Mancheno, Carcelén Industrial`, `2 Cliente A Ponceano (-0.115, -78.49)`, `17 Cliente E Carcelén (-0.090, -78.48)`. Total demo: 11 nodos, todos en Quito, no dispersos. Proyecto académico: solo origen TMC es real, demás DEMO.

## 3. Qué representa una arista
Fila en `logistica.conexiones`: `id_nodo_origen`, `id_nodo_destino`, `distancia_km`, `tiempo_minutos`, `bidireccional`. Ejemplo: `TMC Matriz (1) → Cliente E Carcelén (17) = 1.2 km`, `TMC → Interseccion Norte = 1.0 km`, `Cliente A (2) → Cliente B (3) = 3.0 km`. 17 aristas conectan todo el grafo desde TMC.

## 4. Peso de la arista
`distancia_km` es el peso principal. Dijkstra y TSP minimizan suma de pesos. También existe `tiempo_minutos` y `costo`, pero el algoritmo usa distancia. Si `bidireccional=TRUE`, la arista sirve en ambos sentidos.

## 5. Cómo usa Dijkstra
Archivo `backend/app/algorithms/dijkstra.py:4`. Usa cola de prioridad (heapq):
- Inicializa distancias INF, origen 0
- Extrae nodo con menor distancia, relaja vecinos `nueva = actual + peso`
- Guarda `anteriores` para reconstruir camino
En OptiRoute: `dijkstra(grafo, 1, 3)` → `{camino:[1,2,3], distancia:7.0}`. Se usa para cada par origen→destino dentro de TSP, y para `POST /api/rutas` y `GET /api/rutas/{id}` (puntos con distancia_acumulada).

## 6. Ejemplo real del seed (con TMC Matriz)
Grafo Quito (ver `database/seeds/004_tmc_matriz.sql` + `003_demo_completo.sql`):
- Origen: **TMC Grupo Tramaco - Matriz Quito (1) -0.094867,-78.483472** — Manuel Najas OE1-346, Carcelén Industrial.
- Ruta: TMC(1) -1.2km- Cliente E Carcelén(17) -1.0km- Interseccion Norte -2.8km- Cliente A Ponceano(2) -3km- Cliente B Cotocollao(3) ...
- Clientes en sectores Quito: A Ponceano (-0.115,-78.49), B Cotocollao (-0.11,-78.495), E Carcelén (-0.09,-78.48), H La Carolina (-0.18,-78.485) etc.
Plan demo: origen TMC (1), pedidos a nodos 17(E),2(A),20(H),19(G). Dijkstra: TMC→E 1.2km, E→A vía Norte, etc. TSP elige orden `[17,2,20,19]` con distancia **16.1 km** (24 permutaciones) — visible en Optimización → Dijkstra + mapa con 🏢 TMC.

## 7. BFS (Breadth First)
`backend/app/algorithms/bfs.py:4`. Recorrido por niveles usando cola `deque`:
`bfs(grafo,1)` demo → `[1,2,3,17,21,22,4,18,5,19,20]`. Visita primero vecinos directos de Bodega, luego segundo nivel. Demostrable en Optimización → BFS, `GET /api/grafo/bfs?inicio=1`. No se usa para ruta, solo académico para mostrar conectividad.

## 8. DFS (Depth First)
`backend/app/algorithms/dfs.py:1`. Recursivo por profundidad:
`dfs(grafo,1)` → `[1,2,3,4,5,19,22,20,18,21,17]`. Va profundo por una rama antes de retroceder. Mismo endpoint `GET /api/grafo/dfs?inicio=1`.

## 9. TSP / Multi-entrega
`backend/app/algorithms/tsp.py:71` `resolver_tsp_exacto`: prueba todas las permutaciones `O(n!)`, para cada orden usa `calcular_distancia_recorrido` que encadena Dijkstras. Limitado a ≤8 destinos (factorial). Demo: 4 destinos → 24 permutaciones, elige `[17,2,20,19]` con 21.9 km. Mostrado en Optimización como "Orden óptimo" y "Recorrido físico" `[1,17,1,2,3,4,20,22,19]`. Tiempo estimado = distancia *2.2 min/km.

## 10. Diferencia Dijkstra vs TSP
- **Dijkstra**: un origen → un destino, camino mínimo entre dos nodos.
- **TSP**: un origen → muchos destinos, orden de visita que minimiza suma de Dijkstras. Ejemplo: Dijkstra dice Bodega→E es 3.5km, TSP decide si visitar E primero o al final para minimizar total.

## 11. PostgreSQL
Almacena grafo y operación:
- `seguridad.usuarios`, `logistica.conductores/vehiculos/nodos/conexiones/rutas/ruta_puntos/ruta_pedidos`, `operaciones.clientes/direcciones/pedidos/entregas`
- Seed idempotente `DEMO-OPT-*` en `database/seeds/003_demo_completo.sql` (8 clientes, 11 nodos, 17 conexiones, 12 pedidos, 3 vehiculos, 3 conductores, 4 rutas).  Carga: `.venv\Scripts\python -m backend.scripts.seed_demo`

## 12. FastAPI
Backend `backend/app/main.py:16` expone:
- `GET /api/nodos`, `GET /api/grafo`, `GET /api/grafo/bfs|dfs`, `GET /api/pedidos`, `GET /api/vehiculos`, `GET /api/conductores`, `GET /api/clientes`, `POST /api/optimizacion/planificar`, `POST /api/rutas`, `PATCH /api/rutas/{id}/asignacion|estado`, `POST /api/ia/analizar-planificacion`
Valida con Pydantic, controla capacidad y reglas.

## 13. React
`frontend/src/App.tsx:119` y `frontend/src/components/LeafletMap.tsx:39`:
- Vite + TS, estado con hooks, fetch a `VITE_API_URL` (http://127.0.0.1:8000)
- Leaflet OSM sin claves, marcadores por tipo, polyline por ruta, fitBounds, geolocalización `navigator.geolocation`
- Sidebar oscuro verde, tarjetas blancas, responsive.

## 14. Recorrido exacto demostración (2.5 min) — desde TMC Matriz
1. Login con la cuenta DESARROLLADOR (se crea en la pantalla inicial la primera vez) → Dashboard (mapa centrado en TMC 🏢, 6 rutas, métricas)
2. Pedidos → verifica 10 pendientes
3. Optimización → origen **TMC Grupo Tramaco - Matriz Quito (1)** (aparece como "TMC Grupo Tramaco - Matriz Quito" por defecto), pedidos **PED-DEMO-012(E Carcelén), PED-DEMO-009(A Ponceano), PED-DEMO-008(H La Carolina), PED-DEMO-007(G Iñaquito)** (ids 18,15,14,13), vehículo **DEM-OR-001 (500kg)**, conductor **Ana LIC-DEMO-OPT-001**, Regresar origen OFF → **Optimizar ruta**
4. Mostrar resultado: Capacidad 300/500 kg, Distancia **16.1 km** (desde TMC con nuevas distancias), **24 permutaciones**, Orden **1.TMC →2.E→3.A→4.H→5.G** → **Guardar ruta** → `RUT-0000XX ASIGNADA` (desde TMC)
5. Rutas → abrir nueva RUT → mapa con 🏢 TMC como punto 1, distancia, conductor/vehículo, cambiar a **EN_RUTA**
6. Mapa en vivo → **📍 Mi ubicación**, **🏢 Ir a TMC Matriz** (centra en -0.09487,-78.48347), **🗺 Ver ruta completa** (fitBounds TMC+paradas)
7. Vista Conductor (DevTools iPhone) → Mi ruta desde TMC, Iniciar navegación
8. IA → "¿Cuál es la bodega?" → "TMC Grupo Tramaco - Matriz Quito, Manuel Najas OE1-346..." y "¿cuál es la ruta más larga?"
9. Reportes → métricas y Descargar CSV

## 15. Preguntas posibles y respuestas
- **¿Por qué límite 8?** TSP exacto factorial; 8! =40320 evaluaciones, 9! ya 362k, no escala. Para más destinos usar heurística.
- **¿BFS/DFS para qué?** Solo académico para explicar exploración; la ruta usa Dijkstra+TSP, no BFS/DFS.
- **¿Prioridad afecta orden?** No altera Dijkstra; se muestra y la IA alerta si hay URGENTE, pero el orden sigue siendo mínima distancia (podría ponderarse en futuro).
- **¿Vehículo excedido?** Backend `restricciones_service.py:182` bloquea con 409 y frontend muestra rojo "capacidad insuficiente" antes de optimizar.
- **¿Cómo sabe distancia?** Peso de arista `distancia_km` en BD, no Haversine; es dato del grafo, verificable.
- **¿Qué pasa si grafo desconectado?** Dijkstra retorna None → TSP retorna None → API 409 "No existe ruta posible".
- **¿Dónde está el grafo?** No es imagen: es tabla `logistica.nodos` + `logistica.conexiones` cargada a `Grafo.adyacencia` en memoria.

Listo para exponer.
