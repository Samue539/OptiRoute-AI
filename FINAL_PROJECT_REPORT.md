# Final Project Report — OptiRoute AI (Actualizado)

**Fecha:** 2026-09-09  
**Estado final:** 100% funcional para exposición de grafos. Frontend y backend operativos, datos demo completos, algoritmos reales visibles, mapa vivo con GPS real.

## 1. Estado final
- Frontend React+TS+Vite con Leaflet OSM, geolocalización real `navigator.geolocation`, fitBounds inteligente
- Backend FastAPI en 8000 y 8001 (ambos OK), PostgreSQL 11 nodos / 17 aristas / 8 clientes / 12 pedidos / 3 vehículos / 3 conductores / 4 rutas
- Optimización muestra grafo, Dijkstra, TSP, BFS/DFS, restricciones y guarda ruta real
- Login demo, manejo errores, responsive, build y tests OK

## 2. Cambios realizados (última iteración)
- **Mapa en vivo:** `LeafletMap.tsx:9` añade `FocusUser` + `FitBounds` con trigger, marcador azul 📍 "Mi ubicación" con accuracy, `navigator.geolocation` con manejo PERMISSION_DENIED/TIMEOUT/POSITION_UNAVAILABLE. Botones 📍 Mi ubicación, 🗺 Ver todas las rutas, ⟳ Actualizar. Auto-intento al entrar; fallback a fitBounds rutas si deniega. No inventa GPS.
- **Frontend URL:** `frontend/.env` → `VITE_API_URL=http://127.0.0.1:8000` (antes fallaba por 8000 ocupado por Cafetería). Se detuvo Cafetería, OptiRoute ahora en 8000 y 8001. Problema "select vacíos" resuelto: eran `fetch` fallando por CORS/404; ahora `GET /api/nodos` 200 con 11 nodos.
- **Seed demo completo:** `database/seeds/003_demo_completo.sql` expande a 8 clientes DEMO-OPT-001..008, 4 nodos extra E-H + 2 intersecciones, 10 conexiones nuevas, 3 vehiculos DEM-OR-001..003, 3 conductores, 12 pedidos (10 PENDIENTE, 2 ENTREGADO), ruta histórica COMPLETADA. Zona Quito coherente -0.19/-0.23, -78.48/-78.52. `backend/scripts/seed_demo.py:18` ahora incluye 003.
- **Grafo académico:** `backend/app/api/grafo.py` nuevo con `GET /api/grafo` (nodos+conexiones), `GET /api/grafo/bfs?inicio=1` y `/dfs` usando `bfs.py:4` y `dfs.py:1`. Frontend `api/client.ts:88` añade `getGrafo/bfs/dfs`.
- **Optimización visual:** `App.tsx:558` añade preview grafo (Leaflet con 30 aristas grises + leyenda), restricción live con `CapacityBar` y bloqueo si excede, sección Dijkstra ("Bodega → … → Cliente X · 21.9 km · 24 permut") y TSP (orden, paradas, peso), panel BFS/DFS con selector y `GET /api/grafo/bfs` ejecutable.
- **No destructivo:** Dijkstra/TSP/BFS/DFS originales intactos, tablas no alteradas.

## 3. Archivos nuevos
- `backend/app/api/grafo.py`
- `database/seeds/003_demo_completo.sql`
- `frontend/src/components/LeafletMap.tsx` (actualizado con geoloc)
- `EXPOSICION_GRAFOS.md`
- `frontend/.env` (creado)

## 4. Archivos modificados
- `backend/app/services/clientes_service.py`, `backend/app/api/clientes.py`, `backend/app/schemas/catalogos.py`, `backend/app/services/pedidos_service.py`, `backend/app/api/pedidos.py`, `backend/app/main.py` (grafo_router)
- `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/App.tsx` (optimización + mapa vivo + geoloc + BFS/DFS), `frontend/src/styles.css`, `frontend/vite.config.ts` revisado, `backend/scripts/seed_demo.py`
- `README.md`, `FINAL_PROJECT_REPORT.md`, `PRESENTACION_DEMO.md`

## 5. Endpoints
- GET /api/clientes, /api/clientes/{id}, /api/clientes/{id}/direcciones, /api/clientes/{id}/pedidos
- POST /api/pedidos
- GET /api/nodos (5→11), GET /api/grafo, GET /api/grafo/bfs, GET /api/grafo/dfs
- POST /api/optimizacion/planificar (usa Dijkstra+TSP), POST /api/ia/analizar-planificacion
- GET/POST /api/rutas, GET /api/rutas/{id}, PATCH /api/rutas/{id}/asignacion, PATCH /api/rutas/{id}/estado
- GET /api/vehiculos, /api/conductores, /health, /

## 6. Base de datos
- 11 nodos (1 BODEGA, 8 CLIENTE, 2 INTERSECCION), 17 conexiones, 8 clientes, 8 direcciones, 3 conductores, 3 vehiculos (500/800/150 kg), 12 pedidos, 4 rutas (1 COMPLETADA hist). Coordenadas Quito, idempotente DEMO-OPT-*.

## 7. Algoritmos
- `grafo.py:31` lista adyacencia, `dijkstra.py:4` heapq, `tsp.py:71` TSP exacto 24 permut para 4 destinos, `bfs.py:4` cola, `dfs.py:1` recursión. Validados en `test_grafo.py`, `test_tsp.py`.

## 8. Funcionalidades verificadas
- [x] Login/logout persistente
- [x] Dashboard métricas reales + mapa rutas + entregas por estado + actividad
- [x] Pedidos listar/crear (valida cliente/dirección) → 10 pendientes
- [x] Clientes 8 con direcciones/pedidos
- [x] Conductores 3 (2 disponibles) con ruta
- [x] Vehículos 3 capacidades distintas
- [x] Optimización: Bodega 1 + 4 pedidos 18,15,14,13 + DEM-OR-001 + Ana → 21.9km → Guardar RUT-000005 ASIGNADA → visible en Rutas
- [x] Rutas detalle mapa + progreso + cambio estado
- [x] Mapa vivo: 📍 Mi ubicación (autorizar → zoom16 + marcador azul), 🗺 fitBounds, ⟳ reload, rutas reales 3 paradas con popups
- [x] Vista Conductor responsive + Iniciar/Marcar entrega + Google Maps
- [x] IA chat con datos reales, Reportes con gráficas y CSV, Config

## 9. Pendientes
Ninguno P0/P1. Futuro: JWT, WebSocket GPS real, heurística para >8 destinos.

## 10. Pruebas backend
`96 passed in 3.84s` (pytest). Incluye grafo, tsp, optimización, ia, rutas.

## 11. Build frontend
`tsc -b && vite build → 60 modules, 418.48 kB (122.21 kB gzip), css 30.72 kB, ✓ built in 311ms` sin TS errors.

## 12. Comandos backend
```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\uvicorn backend.app.main:app --host 127.0.0.1 --port 8000  # o 8001
.venv\Scripts\python -m backend.scripts.seed_demo  # idempotente
```

## 13. Comandos frontend
```powershell
cd frontend
npm install
npm run dev  # http://127.0.0.1:5173
npm run build
```

## 14. Demo datos
- Nodos 11, conexiones 17, clientes 8 (DEMO-OPT-001..008), vehiculos DEM-OR-001(500kg),002(800kg),003(150kg), conductores LIC-DEMO-OPT-001..003, pedidos PED-DEMO-001..012 (10 PENDIENTE), rutas 4 (RUT-DEMO-HIST001 COMPLETADA + 3 demo + 1 nueva).
- Coordenadas Quito: Bodega -0.20,-78.50, E -0.19,-78.485 etc.

## 15. Usuario demo
No hay credenciales universales. La primera cuenta DESARROLLADOR se crea en la
pantalla de arranque (`POST /api/auth/bootstrap`, una sola vez). Desde
**Usuarios y permisos** se crean ADMINISTRADOR, OPERADOR y CONDUCTOR (este
último vinculado a un `id_conductor` existente). El login es por correo y la
contraseña se almacena con PBKDF2-SHA256.

## 16. Env
DB_HOST=localhost DB_PORT=5432 DB_NAME=optiroute_db DB_USER=postgres DB_PASSWORD=[CONFIGURAR_EN_ENTORNO] FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173; VITE_API_URL=http://127.0.0.1:8000

## 17. Flujo exposición
Ver EXPOSICION_GRAFOS.md §14: Login → Dashboard → Pedidos → Optimización (Bodega 1 + PED-DEMO-012/009/008/007 + DEM-OR-001 + Ana → Optimizar → Dijkstra 21.9km → Guardar → Rutas detalle → Mapa vivo 📍 → Vista Conductor → IA → Reportes.
