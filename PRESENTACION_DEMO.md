# Guion Demo — OptiRoute AI (5-7 min)

## 1. Qué abrir primero
- Terminal 1: `.venv\Scripts\uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000` → http://127.0.0.1:8000/docs
- Terminal 2: `cd frontend && npm run dev` → http://127.0.0.1:5173
- Navegador con DevTools a mano para vista móvil al final

## 2. Qué decir al iniciar (30s)
“OptiRoute AI es un SaaS logístico que planifica entregas sobre un grafo real almacenado en PostgreSQL. Usa Dijkstra para caminos mínimos y TSP exacto para el orden óptimo, valida peso/volumen y analiza riesgo con un motor determinista. Frontend React, backend FastAPI, mapas Leaflet OSM.”

## 3. Login
- Primera vez: aparece la pantalla **Crear cuenta propietaria** (nombres y correo precargados; elige y confirma tu contraseña) → el sistema muestra el login y entras con ese correo.
- Si ya existe la cuenta propietaria: login con el correo del DESARROLLADOR y su contraseña.

## 4. Dashboard (60s)
- Señalar 4 tarjetas superiores: Pedidos hoy, Entregas completadas, Distancia total, Tiempo total (datos reales de BD)
- Mapa principal: “Leaflet + OSM, gratuito, sin claves. Cada color es una ruta activa, marcadores numerados, bodega en oscuro”
- Panel derecho: Rutas activas (PLANIFICADA/ASIGNADA/EN_RUTA) con conductor/vehículo/distancia
- Abajo: Entregas por estado (barras), distancia reciente por ruta, tabla actividad

## 5. Pedidos (30s)
- Clic Pedidos → buscar “PED-DEMO” → filtrar PENDIENTE → Ver detalle (cliente, dirección, peso/volumen, prioridad)
- Clic + Nuevo pedido → seleccionar cliente DEMO-OPT-001 → dirección → peso 80 volumen 0.8 URGENTE → Crear → “valida cliente/dirección, inserta en operaciones.pedidos y entregas”

## 6. Optimización — corazón del sistema (90s)
- Clic Optimización → explicar flujo: 1) origen Bodega Principal (nodo real), 2) seleccionar 2-3 pedidos PENDIENTE, 3) vehículo DEM-OR-001 (500kg/5m³), 4) conductor Ana Demo, 5) regresar_origen opcional
- Clic Planificar entregas → “Backend valida capacidad, construye grafo desde logistica.conexiones, ejecuta Dijkstra entre cada par y TSP evalúa todas las permutaciones (≤8, O(n!))”
- Mostrar resultado: barras capacidad, métricas distancia/algoritmo/permutaciones, orden óptimo (chips), recorrido físico (línea), mapa Leaflet con ruta, pedidos y prioridad
- Clic Analizar planificación → explicar IA: “No es LLM; son reglas REGLAS_LOGISTICAS_V1: >90% capacidad alerta, urgentes, TSP cerca límite → nivel BAJO/MEDIO/ALTO/CRITICO + recomendaciones”
- Clic Guardar como ruta → “Crea logistica.rutas PLANIFICADA, asigna conductor/vehículo, inserta ruta_pedidos”

## 7. Rutas Detalle (45s)
- Clic Rutas → Ver detalle de la recién creada → mostrar encabezado con estado, conductor, vehículo
- Mapa: punto inicial bodega + paradas numeradas + polilínea
- Panel lateral: lista ordenada con cliente/dirección/hora estimada implícita, distancia acumulada
- Resumen: paradas, distancia, tiempo estimado, progreso % según estado
- Cambiar a EN_RUTA → “transición controlada PLANIFICADA→ASIGNADA→EN_RUTA→COMPLETADA”

## 8. IA Asistente (30s)
- Clic IA Asistente → mostrar chat
- Preguntar “¿cuál es la ruta más larga?” → respuesta basada en datos reales
- Preguntar “pedidos pendientes” → conteo
- Preguntar “explica Dijkstra y TSP” → explicación pedagógica
- Si hay análisis previo, mostrar tarjetas de riesgo arriba

## 9. Mapa en vivo y Reportes (30s)
- Mapa en vivo: “Sin GPS hardware, mostramos planificación vigente; arquitectura lista para WebSocket”
- Reportes: filtros fecha, métricas totales, gráfico distancia por día, entregas por estado, botón Descargar CSV

## 10. Vista conductor móvil (30s)
- Clic Vista Conductor → abrir DevTools → toggle device toolbar (iPhone SE)
- Mostrar MI RUTA: código, estado, mapa compacto, lista paradas con botón Navegar (abre Google Maps), botón Iniciar navegación / Marcar entrega → cambia estado

## 11. Cierre técnico (30s)
- **PostgreSQL:** “3 esquemas, 11 tablas, claves foráneas, checks, índices, seeds idempotentes”
- **FastAPI:** “Endpoints /api/rutas, /api/optimizacion/planificar, /api/ia/analizar-planificacion, validación Pydantic, manejo errores 400/404/409”
- **React:** “Vite, TypeScript tipado, componentes, manejo loading/empty/error, Leaflet”
- **Algoritmos:** “Dijkstra O((V+E) log V) para camino mínimo; TSP exacto O(n!) garantiza óptimo global hasta 8 destinos; BFS/DFS para conectividad”

## 12. Botones clave a presionar en orden
1. Login con la cuenta DESARROLLADOR (creada en la pantalla inicial o ya existente)
2. Dashboard → Crear planificación
3. Pedidos → Nuevo pedido → Crear
4. Optimización → seleccionar pedidos + vehículo → Planificar → Analizar → Guardar como ruta
5. Rutas → Ver detalle → Iniciar
6. IA → enviar “resumen del día”
7. Mapa en vivo, Reportes → Descargar CSV
8. Vista Conductor → DevTools móvil → Iniciar navegación

## 13. Frases para explicar algoritmos
- **Dijkstra:** “Como un GPS matemático: explora vecinos con cola de prioridad y siempre elige la distancia acumulada menor hasta destino”
- **TSP:** “Si tienes 3 clientes, hay 6 órdenes posibles; probamos las 6 con Dijkstra y nos quedamos con la más corta. Por eso hasta 8 destinos: 40320 permutaciones aún es computable”
- **Grafo:** “Nodos son bodega/clientes/intersecciones, conexiones son aristas con distancia; está en PostgreSQL y se carga a memoria para calcular”

¡Listo para preguntas!
