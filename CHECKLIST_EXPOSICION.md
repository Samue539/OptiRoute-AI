# Checklist Exposición — OptiRoute AI

## ANTES DE EXPONER
- [ ] PostgreSQL iniciado (servicio `postgresql` en 5432, `netstat -ano | findstr 5432` LISTENING)
- [ ] Backend iniciado (Terminal 1, ver abajo, `GET /health` 200)
- [ ] Frontend iniciado (Terminal 2, `http://127.0.0.1:5173` responde)
- [ ] localhost abre sin 404/CORS (DevTools Console sin rojo)
- [ ] Dashboard carga: 6 métricas, mapa con 🏢 TMC -0.09668,-78.47537 visible
- [ ] TMC aparece como `TMC Grupo Tramaco - Matriz Quito` en nodos y origen
- [ ] Pedidos demo disponibles: 10 PENDIENTE (PED-DEMO-012,009,008,007 entre ellos)

## DEMOSTRACIÓN
- [ ] explicar problema: última milla Quito, grafo con bodega + clientes
- [ ] explicar grafo: 11 nodos, 18 aristas, peso = distancia haversine
- [ ] mostrar TMC como nodo origen (id 1, BODEGA, Carcelén Industrial)
- [ ] mostrar nodos (8 CLIENTE + 2 INTERSECCION) en mapa
- [ ] mostrar aristas (conexiones TMC 1→2 2.606km, 1→17 0.904km, etc.)
- [ ] explicar pesos: distancias geográficas estimadas (no vial)
- [ ] seleccionar pedidos: PED-DEMO-012 (E), 009 (A), 008 (H), 007 (G) — 4 destinos distintos
- [ ] ejecutar optimización: TMC + 4 pedidos + DEM-OR-001 + Ana → Optimizar
- [ ] explicar Dijkstra: camino TMC→A [1,2] 2.606km, TMC→E [1,17] 0.904km
- [ ] explicar TSP: 24 permutaciones, orden [17,2,20,19] 15.314km, `TSP_EXACTO_DIJKSTRA`
- [ ] mostrar ruta: mapa con 🏢 + 4 paradas numeradas + polyline
- [ ] guardar ruta → RUT-00XXXX ASIGNADA con 3-4 puntos
- [ ] mapa: fitBounds TMC+paradas, no mundo
- [ ] IA: preguntar “¿Cuál es la bodega?” y “¿y la más corta?” (contexto)
- [ ] reportes: métricas y Descargar CSV

## CIERRE
- [ ] Vista Conductor responsive (DevTools iPhone) → Iniciar ruta
- [ ] Recordar: origen TMC real referencial intersección, demás DEMO, pesos haversine
