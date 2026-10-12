# OptiRoute AI

Sistema inteligente de optimización de rutas logísticas mediante grafos e inteligencia artificial. Calcula rutas óptimas usando **Dijkstra** para caminos mínimos y **TSP exacto** para multi-entrega, con validación de restricciones de capacidad y análisis determinista de riesgo.

## Origen real
**Bodega principal: TMC Grupo Tramaco - Matriz Quito**, Manuel Najas OE1-346 y Joaquín Mancheno, Carcelén Industrial, Quito, Ecuador. Coordenadas **-0.094867, -78.483472** geocodificadas vía OpenStreetMap Nominatim. Proyecto académico: solo la ubicación de origen es real; pedidos, clientes, conductores y vehículos son datos DEMO.

## Objetivo
Centralizar la planificación operativa de entregas: pedidos, clientes, vehículos, conductores y rutas sobre un grafo logístico real persistido en PostgreSQL, con visualización cartográfica profesional y asistente IA.

## Tecnologías
- **Frontend:** React 19 + TypeScript + Vite
- **Backend:** FastAPI + Python, Pydantic, Uvicorn
- **Base de datos:** PostgreSQL (esquemas `seguridad`, `operaciones`, `logistica`)
- **Mapas:** Leaflet + React-Leaflet + OpenStreetMap (sin claves)
- **Algoritmos:** Grafo, Dijkstra, BFS, DFS, TSP exacto (O(n!), ≤8 destinos)

## Arquitectura
```
frontend (Vite) → FastAPI (/api/*) → PostgreSQL
               → algoritmos/grafo.py, dijkstra.py, tsp.py, bfs.py, dfs.py
               → services/planificacion_service, restricciones, ia_service
```

- `backend/app/api/*` expone rutas REST
- `backend/app/services/*` orquesta validaciones y grafo
- `frontend/src/components/LeafletMap.tsx` renderiza polilíneas y marcadores por ruta
- Motor IA `REGLAS_LOGISTICAS_V1` es determinista (sin LLM externo)

## Requisitos
- Node >=22.12, Python 3.11+, PostgreSQL 14+
- `psycopg[binary]` o `pg8000` (fallback WDAC)

## Instalación Backend
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env  # completar credenciales
# crear BD
psql -U postgres -f database/scripts/001_crear_base.sql
psql -U postgres -d optiroute_db -f database/scripts/002_crear_esquemas.sql
psql -U postgres -d optiroute_db -f database/scripts/003_crear_tablas.sql
psql -U postgres -d optiroute_db -f database/scripts/004_indices.sql
psql -U postgres -d optiroute_db -f database/scripts/005_restricciones.sql
# datos demo
.venv\Scripts\python -m backend.scripts.seed_demo
# o
psql -U postgres -d optiroute_db -f database/seeds/001_grafo_prueba.sql
psql -U postgres -d optiroute_db -f database/seeds/002_datos_demo.sql

.venv\Scripts\uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Instalación Frontend
```powershell
cd frontend
npm install
copy .env.example .env   # VITE_API_URL=http://127.0.0.1:8000
npm run dev   # http://127.0.0.1:5173
npm run build # producción
```

## Variables de entorno
`.env` (raíz):
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=optiroute_db
DB_USER=postgres
DB_PASSWORD=***
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```
`frontend/.env`:
```
VITE_API_URL=http://127.0.0.1:8000
```

## Configuración PostgreSQL
Ver `database/scripts/*.sql`. Esquemas: `seguridad.usuarios`, `operaciones.clientes/direcciones/pedidos/entregas`, `logistica.nodos/conexiones/rutas/ruta_puntos/ruta_pedidos/vehiculos/conductores`.

## Cómo ejecutar
1. Backend: `uvicorn backend.app.main:app --reload`
2. Frontend: `npm run dev`
3. Inicia sesión con una cuenta creada mediante el bootstrap o el panel de acceso; no hay credenciales universales en el código.

## Cómo cargar datos demo
```powershell
.venv\Scripts\python -m backend.scripts.seed_demo
```
Idempotente: usa `DEMO-OPT-*`, `DEM-OR-001`, nodos `Bodega Principal`, `Cliente A/B/C`.

## Cómo ejecutar pruebas
```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m pytest tests/test_grafo.py -v
```

## Funcionalidades
- Dashboard con métricas (pedidos hoy, completadas, distancia/tiempo), mapa Leaflet multi-ruta, panel activas, entregas por estado, rendimiento
- Pedidos: listar, buscar, filtrar estado, ver detalle, crear (valida cliente/dirección), estado
- Clientes: listar, buscar, detalle con direcciones y pedidos
- Rutas: lista, detalle con mapa, paradas numeradas, resumen distancia/tiempo/progreso, cambio estado, asignación conductor/vehículo
- Optimización real: selección pedidos pendientes, vehículo, conductor, origen, TSP exacto + Dijkstra, guardar como ruta
- Conductores/Vehículos: listado, disponibilidad, ruta asignada
- Mapa en vivo: rutas activas, progreso, sin GPS (arquitectura lista para WebSocket)
- Reportes: totales, % completado, distancia/tiempo, distancia por día, entregas por estado, export CSV
- IA Asistente: chat con reglas, análisis riesgo (BAJO/MEDIO/ALTO/CRITICO), alertas y recomendaciones
- Configuración, vista móvil conductor (responsive), login/logout

## Algoritmos
- **Grafo** (`grafo.py`): lista adyacencia, aristas bidireccionales
- **Dijkstra** (`dijkstra.py`): cola prioridad, camino mínimo
- **TSP exacto** (`tsp.py`): permutaciones, usa Dijkstra inter-nodos, hasta 8 destinos, `permutaciones_evaluadas`
- **BFS/DFS** (`bfs.py`, `dfs.py`): recorridos y conectividad, testeados
- **Restricciones**: peso/volumen, destino activo, vehículo disponible

## Estructura
```
backend/app/{api,services,algorithms,core,schemas}
database/{scripts,seeds}
frontend/src/{api,components,styles.css,App.tsx}
tests/test_*.py
```

## Demo rápida
1. Inicia sesión con un perfil `OPERADOR` o `ADMINISTRADOR` creado previamente.
2. Dashboard → mapa y métricas
3. Pedidos → crear pedido
4. Optimización → seleccionar 2-3 pedidos, vehículo DEM-OR-001, planificar, analizar IA, guardar ruta
5. Rutas → abrir detalle, ver mapa Leaflet, cambiar a EN_RUTA
6. IA Asistente → preguntar “¿ruta más larga?”
7. Mapa en vivo y Reportes

## Segunda etapa: paneles y flujo operativo

Antes de iniciar una base ya existente, aplica la migración aditiva (no elimina registros):

```powershell
psql -U postgres -d optiroute_db -f database/scripts/005_restricciones.sql
```

El guardado desde **Optimización** recalcula el plan en el servidor y persiste en una sola transacción el recorrido físico completo, el retorno a bodega, todos los pedidos y la asignación. La clave idempotente evita rutas duplicadas por doble clic o reintento.

- `OPERADOR`: consulta y seguimiento de pedidos, clientes y rutas; solo puede cancelar pedidos y rutas (permisos `*:estado_limitado`).
- `ADMINISTRADOR`: operación completa (crear, editar, planificar y asignar), cuentas operativas, conductores, vehículos, asignaciones y reportes.
- `DESARROLLADOR`: administradores, matriz de permisos, auditoría, diagnóstico y configuración técnica sin secretos.
- `CONDUCTOR`: únicamente rutas/pedidos propios, inicio, confirmación individual y novedades.

Para probar perfiles, inicia con la cuenta propietaria `DESARROLLADOR`, abre **Usuarios y permisos** y crea las cuentas requeridas. El administrador solo puede crear `OPERADOR` y `CONDUCTOR`; el desarrollador también puede crear `ADMINISTRADOR`. Para una cuenta `CONDUCTOR`, vincula el `id_conductor` existente. No hay credenciales universales incluidas en el código.

La matriz de permisos es de **solo lectura** y se alimenta de `GET /api/auth/permisos`, el mismo catálogo con el que el backend autoriza; el modelo completo (roles, ámbitos, límites de estado y endpoints afectados) está en `docs/FASE4_RBAC_PERMISOS.md`.

El perfil `DESARROLLADOR` dispone además del **Centro de control** (módulos de Resumen con métricas reales, Usuarios, Roles y permisos, Auditoría, Diagnóstico y Configuración técnica). El almacenamiento de acceso puede conmutarse entre JSON local provisional y PostgreSQL con `OPTIROUTE_AUTH_STORAGE`; el procedimiento de migración y reversión está documentado en `docs/FASE3_SEGURIDAD_POSTGRES.md`.

### Acceso y gestión de cuentas

1. **Primera ejecución:** si no existe cuenta propietaria, la app muestra la pantalla *Crear cuenta propietaria* → `POST /api/auth/bootstrap` (endpoint público de un solo uso; devuelve 409 si ya existe un `DESARROLLADOR`). Luego se muestra el login por correo.
2. **Usuarios y permisos:** el `DESARROLLADOR` y el `ADMINISTRADOR` listan cuentas (`GET /api/auth/usuarios`) y crean cuentas (`POST /api/auth/usuarios`) conforme a la jerarquía. La interfaz nunca muestra hashes ni contraseñas.
3. **Perfiles:** solo el `DESARROLLADOR` cambia perfiles (`PATCH /api/auth/usuarios/{id}/rol`, permiso `perfiles:administrar`); al cambiar el perfil se cierran las sesiones de la cuenta.
4. **Contraseñas:** cada cuenta cambia la suya en **Usuarios y permisos → Mi cuenta** (`POST /api/auth/cambiar-password`, requiere la contraseña actual y cierra las sesiones activas). Un administrador puede **restablecer** la de sus cuentas operativas (`POST /api/auth/usuarios/{id}/password`), que también cierra sus sesiones; nunca se restablece la propia cuenta por esta vía.
5. **Protecciones:** no se puede desactivar ni degradar al último `DESARROLLADOR` activo (HTTP 409), ni modificar la cuenta propietaria, ni ascender privilegios sin el permiso correspondiente (HTTP 403).

Flujo de prueba recomendado:

1. Como operador, crea o selecciona pedidos pendientes y calcula una planificación.
2. Selecciona vehículo y conductor disponibles y usa **Guardar y asignar ruta**.
3. Como conductor asignado, abre **Vista Conductor**, inicia la ruta y confirma cada entrega.
4. Comprueba que **Completar ruta** permanece deshabilitado mientras haya entregas pendientes.
5. Registra una novedad; al completar o cancelar, comprueba que los recursos quedan disponibles y el historial permanece.

## Autoría y propiedad intelectual

- **Creador e impulsor:** Samuel Patricio Simbaña Gualacata
- **GitHub:** [Samue539](https://github.com/Samue539)
- **País:** Ecuador
- **Año:** 2026
- **Derechos:** todos los derechos reservados sobre las contribuciones de su titularidad.

Consulta [LICENSE](LICENSE), [AUTHORS.md](AUTHORS.md) y [COPYRIGHT.md](COPYRIGHT.md) para conocer el alcance de esta declaración y el reconocimiento de contribuciones.
