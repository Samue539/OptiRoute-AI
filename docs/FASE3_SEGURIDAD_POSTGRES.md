# Fase 3: Seguridad y autenticacion profesional

Objetivo de esta fase: sustituir de forma **progresiva y reversible** el
almacenamiento provisional de cuentas en archivos JSON
(`backend/data/seguridad/cuentas.json`) por persistencia segura en PostgreSQL,
sin modificar el inicio de sesion, los tokens Bearer, la jerarquia de perfiles
ni los endpoints que consume el frontend.

## 1. Que se conserva igual

| Aspecto | Estado |
|---|---|
| Endpoints de `/api/auth/*` | Sin cambios (mismos paths, metodos y cuerpos) |
| Formato del token | Opaco `token_urlsafe(48)`, se guarda solo su SHA-256 |
| Cabecera de autorizacion | `Authorization: Bearer <token>` |
| TTL de sesion | 8 horas (`AUTH_SESSION_HORAS`) |
| Hash de contrasena | `pbkdf2_sha256$iteraciones$salt$hash` (mismo formato verificable) |
| Politica de contrasena | Minimo 10 caracteres, letras y numeros |
| Perfiles y permisos | `CONDUCTOR < OPERADOR < ADMINISTRADOR < DESARROLLADOR` (matriz intacta) |
| Frontend | Sin cambios: consume exactamente los mismos endpoints |

## 2. Arquitectura despues de la Fase 3

```
backend/app/repositories/
├── contratos.py   interfaces (RepositorioCuentas/Sesiones/Auditoria)
├── local.py       backend JSON provisional (desarrollo) + unicidad
├── postgres.py    backend PostgreSQL (produccion)          <- NUEVO
├── errores.py     errores de persistencia                  <- NUEVO
├── modelos.py     Cuenta / Sesion (+ metadatos de sesion)
└── fabrica.py     selector OPTIROUTE_AUTH_STORAGE          <- AMPLIADO
```

El selector de backend (`OPTIROUTE_AUTH_STORAGE`) decide la implementacion:

* `local` (por defecto): archivos JSON. Sigue siendo valido para desarrollo.
* `postgres`: tablas nuevas e independientes de las existentes.
* `supabase`: sigue sin implementarse (error explicito, sin simulacion).

### Tablas creadas (`database/scripts/006_seguridad_acceso.sql`)

| Tabla | Contenido |
|---|---|
| `seguridad.cuentas_acceso` | Cuentas de acceso: `id_usuario`, `correo` unico, `password_hash`, `rol` (incluye `DESARROLLADOR`), `activo`, `es_propietario`, `id_conductor`, `origen`, `migrado_en` |
| `seguridad.sesiones_acceso` | `token_hash` (SHA-256, PK), `id_usuario` (FK con borrado en cascada), `expira_en`, `revocado`, `revocado_en`, `agente_hash`, `ip_prefijo` |
| `seguridad.auditoria_acceso` | Bitacora: `accion`, `actor`, `actor_id`, `detalle JSONB`, `creado_en` |
| `seguridad.migraciones_acceso` | Registro de scripts de acceso aplicados |

Propiedades de la migracion SQL:

* **Aditiva**: no altera ni borra `seguridad.usuarios` (usuarios logisticos),
  `logistica.*` ni `operaciones.*`.
* **Idempotente**: `CREATE TABLE IF NOT EXISTS`, indices `IF NOT EXISTS` e
  `INSERT ... ON CONFLICT (nombre) DO NOTHING`; puede ejecutarse varias veces.
* **Sin bloques `DO $$ ... $$`**: en equipos con politicas de control de
  aplicaciones (WDAC/SAC) la libreria `plpgsql` puede estar bloqueada. Este
  script funciona igual.

## 3. Configuracion

Variables nuevas (documentadas en `.env.example`; **no** modificar `.env` sin
revisar el procedimiento de este documento):

| Variable | Valor por defecto | Efecto |
|---|---|---|
| `OPTIROUTE_AUTH_STORAGE` | `local` | `local` o `postgres` |
| `AUTH_SESSION_HORAS` | `8` | Duracion de las sesiones |
| `AUTH_PBKDF2_ITERACIONES` | `210000` | Iteraciones para hashes nuevos |
| `AUTH_SESION_ESTRICTA` | `0` | `1` = revocar la sesion si cambia el navegador o la red |
| `OPTIROUTE_AUTH_FALLBACK_LOCAL` | `0` | `1` = degradar a JSON si PostgreSQL no responde |
| `OPTIROUTE_AUTH_DATA_DIR` | `backend/data/seguridad` | Directorio del backend local |
| `OPTIROUTE_TEST_DB` | `0` | `1` = ejecutar pruebas de integracion reales |

## 4. Procedimiento de migracion (orden recomendado)

> Requisito previo: **respaldo de la base de datos**.

```powershell
# 0. Respaldo (no modifica la base de datos)
.\.venv\Scripts\python.exe -m backend.scripts.respaldar_bd

# 1. Aplicar el script de tablas (idempotente, aditivo)
psql -h <host> -U postgres -d optiroute_db -f database\scripts\006_seguridad_acceso.sql

# 2. Verificar compatibilidad SIN escribir nada
.\.venv\Scripts\python.exe -m backend.scripts.migrar_cuentas_json_a_postgres

# 3. Copiar los archivos JSON a backend\data\seguridad\respaldos\ y migrar
.\.venv\Scripts\python.exe -m backend.scripts.migrar_cuentas_json_a_postgres --aplicar --respaldar

# 4. Cambiar el backend en .env
#    OPTIROUTE_AUTH_STORAGE=postgres

# 5. Reiniciar el backend y comprobar
#    GET /api/auth/diagnostico   -> "backend": "postgres", "provisional": false
```

### Que conserva la migracion de cuentas

* Identificadores (`id_usuario`) exactos.
* Hash de contrasena tal cual (sigue verificando con `verificar_password`).
* Rol, `activo`, `es_propietario`, `id_conductor`.
* Fechas de creacion, actualizacion y ultimo acceso.
* Las secuencias se realinean (`setval`) para que las cuentas nuevas no
  choquen con las migradas.

### Idempotencia y duplicados

* Una cuenta ya migrada se omite (`ON CONFLICT DO NOTHING`).
* Si el correo JSON coincide con otra cuenta de PostgreSQL con distinto
  `id_usuario`, la migracion **se detiene** y lo informa; no sobrescribe nada.
* Si el hash difiere, tampoco se sobrescribe: se marca como conflicto.
* Las sesiones solo se migran si esten vigentes y su cuenta exista.
* Los archivos JSON de origen nunca se borran ni se modifican.

Codigos de salida del script: `0` correcto, `1` error tecnico, `2` conflictos
(no se migro nada), `3` faltan tablas (aplicar el script 006).

## 5. Endurecimiento anadido (sin romper nada)

1. **Unicidad real de cuentas**: el backend local ahora rechaza dentro del
   candado un correo duplicado; el de PostgreSQL usa la restriccion `UNIQUE`.
   Dos altas simultaneas con el mismo correo devuelven `409`, no `500`.
2. **Metadatos de sesion**: se guarda el hash SHA-256 del User-Agent y el
   prefijo de red (nunca la IP completa). Con `AUTH_SESION_ESTRICTA=1` una
   sesion reutilizada desde otro navegador o red se revoca y se audita.
   Las sesiones anteriores (sin metadatos) siguen siendo validas.
3. **Cierre global**: `POST /api/auth/logout-todo` revoca las sesiones de los
   demas equipos y devuelve un token nuevo (mismo vencimiento) para no
   desconectarte. Endpoint nuevo; el front actual sigue funcionando igual.
4. **Purga de sesiones caducas**: cada login correcto elimina sesiones
   revocadas o expiradas (best-effort; nunca bloquea el acceso).
5. **Consultas parametrizadas**: todo el acceso a PostgreSQL usa `%s`.
6. **Errores traducidos**: cuenta duplicada `409`, cuenta inexistente `404`,
   tabla sin crear `503` con instrucciones.

## 6. Reversion segura

**Reversion de la aplicacion (inmediata, sin tocar datos):**

```powershell
# .env
OPTIROUTE_AUTH_STORAGE=local
```

El frontend y el login vuelven a usar los archivos JSON, que siguen intactos
(la migracion no los borra). Ninguna sesion se pierde: se emiten nuevas al
iniciar sesion.

**Reversion de la base de datos (solo si es necesario):**

```powershell
# 1. Verificar que la aplicacion NO esta usando postgres
#    GET /api/auth/diagnostico -> backend: local

# 2. Respaldar antes de tocar nada
.\.venv\Scripts\python.exe -m backend.scripts.respaldar_bd

# 3. Eliminar unicamente las tablas de la fase 3 (orden inverso)
psql -h <host> -U postgres -d optiroute_db -c "DROP TABLE IF EXISTS seguridad.auditoria_acceso;"
psql -h <host> -U postgres -d optiroute_db -c "DROP TABLE IF EXISTS seguridad.sesiones_acceso;"
psql -h <host> -U postgres -d optiroute_db -c "DROP TABLE IF EXISTS seguridad.cuentas_acceso;"
psql -h <host> -U postgres -d optiroute_db -c "DELETE FROM seguridad.migraciones_acceso WHERE nombre = '006_seguridad_acceso';"
```

Esto **no** afecta a `seguridad.usuarios`, `operaciones.*` ni `logistica.*`.

**Reversion total desde un respaldo pg_dump:**

```powershell
& "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" -h <host> -U postgres -d optiroute_db --clean --if-exists .\backups\respaldo-<marca>.dump
```

## 7. Pruebas

| Comando | Que ejecuta |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest -q` | Suite completa (incluye Fase 3) |
| `.\.venv\Scripts\python.exe -m pytest tests\test_auth.py -q` | Autenticacion y jerarquia (141 pruebas base intactas) |
| `.\.venv\Scripts\python.exe -m pytest tests\test_auth_migracion.py -q` | Migracion: idempotencia, conflictos, respaldo |
| `.\.venv\Scripts\python.exe -m pytest tests\test_auth_postgres_repos.py -q` | Repositorios PostgreSQL (simulados) |
| `.\.venv\Scripts\python.exe -m pytest tests\test_sesiones.py -q` | Sesiones, modo estricto y concurrencia |
| `set OPTIROUTE_TEST_DB=1` + `pytest tests\test_auth_postgres_integracion.py` | Integracion real (revierte la transaccion) |

Las pruebas de integracion crean las tablas dentro de una transaccion y la
revierten al terminar: no dejan cambios permanentes.

### Preparar una base de pruebas aislada (recomendado)

Las pruebas usan la conexion de `DB_*`, asi que lo mas seguro es apuntarlas a
una base **dedicada** y nunca a la de produccion:

```powershell
# 1. Crear la base vacia (una sola vez; psql o cualquier cliente)
$env:DB_NAME = "optiroute_auth_test"

# 2. Crear los esquemas y las tablas de acceso en esa base
.\.venv\Scripts\python.exe -c "from pathlib import Path; from backend.app.core.database import obtener_conexion; c=obtener_conexion(); c.autocommit=True; cur=c.cursor(); [cur.execute(Path('database/scripts',s).read_text(encoding='utf-8')) for s in ('002_crear_esquemas.sql','006_seguridad_acceso.sql')]; print('esquemas y tablas de acceso listos')"

# 3. Ejecutar solo las pruebas de integracion contra esa base
$env:OPTIROUTE_TEST_DB = "1"
.\.venv\Scripts\python.exe -m pytest tests\test_auth_postgres_integracion.py -q
```

Verificado el 2026-10-11: **11/11 pruebas en verde** contra
`optiroute_auth_test`, con 0 filas residuales en `seguridad.cuentas_acceso`,
`seguridad.sesiones_acceso` y `seguridad.auditoria_acceso` (rollback efectivo).
La base de produccion (`optiroute_db`) no se toca.

## 8. Riesgos y decisiones pendientes

1. **Doble modelo de usuarios.** `seguridad.usuarios` (usuarios logisticos,
   referenciados por `logistica.conductores.id_usuario`) y
   `seguridad.cuentas_acceso` (cuentas de acceso) conviven. La unificacion
   exigiria anadir `DESARROLLADOR` a `chk_usuarios_tipo` y resolver el FK de
   conductores: se plantea como siguiente fase, **no** se hizo aqui para no
   arriesgar datos existentes.
2. **`cuentas_acceso.id_conductor` sin FOREIGN KEY.** Una cuenta `CONDUCTOR`
   puede apuntar a un `id_conductor` que aun no exista. La validacion la hace
   el servicio. Anadir el FK requiere limpiar antes los huerfanos.
3. **Datos propios del servidor.** `backend/data/seguridad/` se ha anadido a
   `.gitignore`: contiene hashes de contrasena y sesiones reales y nunca debe
   subirse al repositorio.
4. **Backend local y concurrencia multiproceso.** El candado protege el
   acceso concurrente dentro de un proceso; con varios procesos (varias
   instancias de uvicorn) se recomienda PostgreSQL.
5. **Modo estricto desactivado por defecto.** Activarlo expulsa sesiones
   validas si el usuario cambia de red movil o proxy. Se deja a decision del
   operador.
