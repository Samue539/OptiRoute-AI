# Guion Final 10 Minutos — OptiRoute AI

**Tono:** sencillo, estudiante, sin adornos. TMC es origen real referencial, demás DEMO.

### 0:00-1:00 Introducción y problema
“Hola, OptiRoute AI resuelve la última milla en Quito: desde una bodega central se deben entregar múltiples pedidos minimizando distancia y respetando peso/volumen del vehículo. El problema es un grafo: ¿en qué orden visitar a los clientes?”

### 1:00-2:00 Qué es OptiRoute AI
“Frontend React + Vite, backend FastAPI, base PostgreSQL con 11 nodos y 18 aristas. Motor determinista REGLAS_LOGISTICAS_V1, sin IA generativa externa. Mapa Leaflet OSM sin claves, todo con datos reales de la BD.”

### 2:00-3:00 Qué es un grafo y cómo se representa aquí
“Un grafo son vértices (nodos) y aristas (conexiones). Aquí: nodo = ubicación importante (BODEGA, CLIENTE, INTERSECCION) con lat/lng en `logistica.nodos`. Arista = conexión posible con peso `distancia_km` en `logistica.conexiones`. 11 nodos, 18 aristas, todo en Quito.”

### 3:00-4:30 Nodo TMC, nodos de destino, aristas y pesos
“Nuestro nodo origen es la **Matriz Central de TMC Grupo Tramaco, Manuel Najas OE1-346 y Joaquín Mancheno, Carcelén Industrial** (`id 1`, `-0.0966838,-78.4753787` coordenada referencial intersección verificada vía Nominatim OSM). Es tipo BODEGA, aparece como 🏢. Los demás son 8 clientes demo en Ponceano, Cotocollao, etc., y 2 intersecciones. Peso = distancia geográfica estimada con haversine (no vial), ej TMC→E 0.904km, TMC→A 2.606km.”

### 4:30-6:30 Demostración Optimización
*Acción:* Optimización → Origen `TMC Grupo Tramaco - Matriz Quito` (por defecto) → seleccionar **PED-DEMO-012 (E Carcelén 130kg), 009 (A Ponceano 50kg), 008 (H La Carolina 30kg), 007 (G Iñaquito 90kg)** → 4 destinos distintos → Vehículo **DEM-OR-001 500kg/5m³** (soporta 300kg/2.95m³) → Conductor **Ana LIC-DEMO-OPT-001** → `Optimizar ruta` (loading).
“Valida capacidad, luego ejecuta backend.”

### 6:30-7:30 Dijkstra
“Resultado: Dijkstra calcula camino mínimo entre cada par con cola de prioridad `O((V+E)logV)`. Ej TMC→A camino `[1,2]` distancia **2.606km**, TMC→E `[1,17]` **0.904km**. Se ve en panel ‘Algoritmo de camino mínimo: Dijkstra’ y en el recorrido físico `[1,17,1,2,3,4,20,22,19]`.”

### 7:30-8:30 TSP
“TSP multi-entrega prueba todas las permutaciones `O(n!) ≤8` (aquí 4! =24) sumando Dijkstras y elige la menor. Orden resultante **1.TMC →2.E →3.A →4.H →5.G** distancia **15.314km** tiempo **34min**, algoritmo `TSP_EXACTO_DIJKSTRA` (óptimo exacto, no heurística). Si fueran 9 destinos usaríamos heurística y diríamos ‘orden calculado’.”

### 8:30-9:15 Mapa / ruta / conductor
*Acción:* `Guardar ruta` → `RUT-0000XX ASIGNADA` → Rutas → Ver → mapa con 🏢 + 4 paradas numeradas, fitBounds, distancia, conductor/vehículo. Mapa en vivo → `🏢 Ir a TMC Matriz` centra `-0.09668,-78.47537` sobre Tramaco Express (no GRI), `📍 Mi ubicación` pide permiso Chrome “Permitir” y pone marcador azul.

### 9:15-9:45 IA y reportes
*Acción:* IA → “¿Cuál es la bodega?” → “TMC Grupo Tramaco... intersección...”. Luego “¿y la más corta?” (contexto). Reportes → Generar, Descargar CSV.

### 9:45-10:00 Conclusión
“Desde un nodo real TMC, con grafo en PostgreSQL, FastAPI expone Dijkstra+TSP, React visualiza. Origen real, demás DEMO, pesos haversine. Listo para escalar a heurística si >8 destinos.”

---

## Preguntas del profesor — respuestas breves

**¿Qué es un grafo?** Conjunto de nodos conectados por aristas que modela una red.

**¿Qué es un nodo?** Ubicación importante: aquí BODEGA (TMC 1), CLIENTE, INTERSECCION, con lat/lng en `logistica.nodos`.

**¿Qué es una arista?** Conexión posible entre nodos, fila en `logistica.conexiones` con `origen, destino, distancia_km`.

**¿Qué representa el peso?** Distancia geográfica estimada con haversine entre nodos, usada para minimizar.

**¿Por qué utiliza Dijkstra?** Para camino mínimo entre dos nodos exacta y eficientemente, base para TSP.

**¿Qué diferencia existe entre Dijkstra y TSP?** Dijkstra 1→1, TSP 1→N orden óptimo sumando Dijkstras; Dijkstra es subrutina de TSP.

**¿Para qué sirven BFS y DFS?** Solo académicos: BFS por niveles `[1,2,3,17...]`, DFS en profundidad `[1,2,3,4,5...]`, demuestran conectividad, no se usan para ruta.

**¿Por qué PostgreSQL?** Persiste grafo y operación con relaciones y checks, 11/18/12/8 filas, idempotente DEMO.

**¿Por qué FastAPI?** Endpoints tipados Pydantic, validación capacidad, `GET /api/grafo`, `POST /api/optimizacion/planificar`.

**¿Por qué React?** Vite+TS, estado hooks, Leaflet OSM sin claves, responsive.

**¿La ubicación TMC es real?** Sí, referencial intersección Manuel Najas/Joaquín Mancheno `-0.0966838,-78.4753787` verificada vía Nominatim OSM, no puerta exacta OE1-346.

**¿Los clientes son reales?** No, 8 DEMO en sectores Quito (Ponceano etc.), sin datos personales.

**¿La distancia es vial exacta?** No, **pesos demo utilizan distancia geográfica estimada mediante Haversine, no distancia vial exacta** (aclarado en README/EXPOSICION).

