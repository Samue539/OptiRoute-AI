# Fase 4: RBAC profesional y matriz de permisos efectiva

Reorganiza el control de acceso del sistema sobre el principio de **mínimo
privilegio** y rediseña la pantalla *Matriz de permisos efectiva* para que
refleje, sin duplicar reglas, lo que el backend autoriza de verdad.

## 1. Modelo de roles

| Rol | Alcance | Permisos |
|---|---|---|
| **DESARROLLADOR** (24) | Administración técnica completa | Todo lo de ADMINISTRADOR + `perfiles:administrar`, `cuentas:administradores`, `configuracion:tecnica`, `diagnostico:ver`, `auditoria:ver` |
| **ADMINISTRADOR** (19) | Gestión operativa + cuentas operativas | Todo lo de OPERADOR + `pedidos:crear`, `pedidos:editar`, `pedidos:estado`, `rutas:planificar`, `rutas:crear`, `rutas:asignar`, `rutas:estado`, `reportes:ver`, `configuracion:operativa`, `flota:gestionar`, `cuentas:operativas` |
| **OPERADOR** (8) | Consulta y seguimiento | `panel:ver`, `pedidos:ver`, `clientes:ver`, `recursos:ver`, `rutas:ver_todas`, `ia:usar`, `pedidos:estado_limitado`, `rutas:estado_limitado` |
| **CONDUCTOR** (4) | Solo lo propio | `rutas:ver_propias`, `rutas:estado`, `pedidos:ver_propios`, `pedidos:estado_propio` |

### Permisos eliminados

| Permiso | Motivo |
|---|---|
| `clientes:crear`, `clientes:editar` | Ningún endpoint los usaba (no existen altas ni edición de clientes). Solo falseaban la matriz. |

### Permisos nuevos

| Permiso | Alcance | Qué permite |
|---|---|---|
| `pedidos:estado_limitado` | OPERADOR | Únicamente fijar el estado `CANCELADO` en pedidos |
| `rutas:estado_limitado` | OPERADOR | Únicamente fijar el estado `CANCELADA` en rutas |

Tener `pedidos:estado` o `rutas:estado` **no** autoriza a modificar cualquier
dato: esos permisos solo hablan de estados. La edición de datos exige
`pedidos:editar`, `rutas:crear` o `rutas:asignar`.

### Transiciones autorizadas por estado

| Rol | Estados de pedido | Estados de ruta |
|---|---|---|
| DESARROLLADOR / ADMINISTRADOR | Cualquiera (reglas del sistema) | Cualquiera (reglas del sistema) |
| OPERADOR | Solo `CANCELADO` | Solo `CANCELADA` |
| CONDUCTOR | Solo `ENTREGADO` (entregas propias) | `EN_RUTA`, `COMPLETADA`, `CANCELADA` (rutas propias) |

Las reglas de negocio siguen aplicándose después
(`pedidos_service.TRANSICIONES`, `ruta_service.TRANSICIONES_ESTADO`): el
permiso decide *si* se puede intentar, la regla decide *si* la transición
existe.

## 2. Endpoints afectados

| Endpoint | Antes | Ahora para OPERADOR |
|---|---|---|
| `POST /api/pedidos` | 201 | **403** |
| `PATCH /api/pedidos/{id}` | 200 | **403** |
| `PATCH /api/pedidos/{id}/estado` | cualquier cambio | 403 salvo `CANCELADO` |
| `POST /api/rutas` | 201 | **403** |
| `POST /api/rutas/planificada` | 201 | **403** |
| `POST /api/rutas/{id}/pedidos` | 201 | **403** |
| `PATCH /api/rutas/{id}/asignacion` | 200 | **403** |
| `PATCH /api/rutas/{id}/estado` | cualquier cambio | 403 salvo `CANCELADA` |
| `POST /api/optimizacion/multi-entrega` | 200 | **403** |
| `POST /api/optimizacion/planificar` | 200 | **403** |

Para el CONDUCTOR: `PATCH /api/rutas/{id}/estado` solo admite
`EN_RUTA`, `COMPLETADA` y `CANCELADA`, y exclusivamente sobre rutas propias
(`ASIGNADA` ya no se acepta: es una decisión administrativa).

Ningún endpoint nuevo salvo `GET /api/auth/permisos` (consultivo).

## 3. Endpoint del catálogo

```
GET /api/auth/permisos        (requiere sesión válida)
```

Devuelve:

* `roles`: perfil, descripción, número de permisos, lista de permisos y las
  transiciones de estado que le corresponden.
* `modulos`: agrupación usada por la matriz.
* `permisos`: código, nombre legible, descripción, módulo, ámbito
  (`general` / `limitado` / `propio`) y texto del límite.
* `reglas`: garantías de seguridad verificadas por el backend.
* `rol_actual` y `efectivos`: permisos efectivos de la sesión consultante.

La pantalla del frontend consume este endpoint, así que la matriz no puede
desalinearse del backend. El espejo estático `frontend/src/auth/permissions.ts`
sigue existiendo para el gating de menús en tiempo de carga.

## 4. Pantalla «Gestión de roles y permisos»

Ubicación: Centro de control (DESARROLLADOR) → pestaña **Roles y permisos**.
Componente: `frontend/src/components/panels/PermissionMatrix.tsx`.

Incluye:

* Encabezado «Gestión de roles y permisos».
* Cuatro tarjetas de resumen (una por rol) con descripción, total de permisos
  y marca de «Tu perfil».
* Leyenda de estados: **Permitido**, **Limitado**, **Denegado**.
* Matriz por módulos, con nombres legibles y código técnico de cada permiso.
* Filtros por rol, por módulo y búsqueda por texto.
* Detalle desplegable por permiso (descripción, límite y módulo).
* Tabla de reglas verificadas por el servidor.
* Diseño responsive (a 1100px y 640px) y contraste alto en las etiquetas.
* **Solo lectura**: no edita permisos ni crea roles personalizados.

## 5. Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_rbac.py -q     # 45 pruebas nuevas
.\.venv\Scripts\python.exe -m pytest -q                       # suite completa
npm --prefix frontend run lint && npm --prefix frontend run build
```

Cubren: OPERADOR sin creación/edición/planificación/asignación, estados
limitados, CONDUCTOR sin acceso a recursos ajenos, ADMINISTRADOR sin funciones
técnicas, DESARROLLADOR con acceso completo, 403 en endpoints no autorizados,
matriz coherente con el backend y sesiones invalidadas al cambiar de perfil.

## 6. Notas de compatibilidad

* El frontend no cambia sus llamadas: los endpoints y sus respuestas son las
  mismas; solo cambian los códigos de estado ante acciones ya no permitidas.
* Tres pruebas previas usaban un principal `OPERADOR` para ejercitar
  planificación (TSP + Dijkstra). Como planificar pasó a ser privilegio del
  ADMINISTRADOR, esas pruebas ahora usan `ADMINISTRADOR`
  (`tests/test_optimizacion_service.py`, `tests/test_planificacion_service.py`).
  El servicio planificado no cambia.
* Riesgo conocido: una cuenta OPERADOR existente que dependiera de crear o
  asignar perderá esa capacidad. Migración documentada: cambiar su perfil a
  ADMINISTRADOR desde el Centro de control (el cambio cierra sus sesiones).
