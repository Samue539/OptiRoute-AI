# Plan de migración del almacenamiento de acceso a PostgreSQL

> **Estado: propuesta de despliegue (no ejecutada).** La base actual **ya
> incluye** la implementación PostgreSQL (`backend/app/repositories/postgres.py`,
> seleccionable con `OPTIROUTE_AUTH_STORAGE=postgres`). Lo que falta es el
> **procedimiento de corte**: respaldo, migración de datos, conmutación y
> reversión. Este documento describe ese procedimiento. Supabase queda
> expresamente fuera del alcance de esta fase.

## 1. Situación actual

| Elemento | Implementación vigente |
|---|---|
| Cuentas | `RepositorioCuentasLocal` → `backend/data/seguridad/cuentas.json` |
| Sesiones | `RepositorioSesionesLocal` → `sesiones.json` |
| Auditoría | `RepositorioAuditoriaLocal` → `auditoria.jsonl` (append-only) |
| Contratos | `backend/app/repositories/contratos.py` (ABC independientes del backend) |
| Backend PostgreSQL | **Ya implementado**: `repositories/postgres.py` (`postgres` / `postgresql` / `bd` / `base_datos`) |
| Selección | `repositories/fabrica.py` lee `OPTIROUTE_AUTH_STORAGE` (`local` por defecto) |
| Fallback | `OPTIROUTE_AUTH_FALLBACK_LOCAL=1` degrada a JSON si la BD no responde |
| Hashes | PBKDF2-SHA256, formato autodescritivo `pbkdf2_sha256$<iter>$<salt>$<hash>` |
| Ventana favorable | **Hoy no existen cuentas reales** (`backend/data/seguridad` no existe): el corte puede hacerse en frío |

Gracias a los contratos, `auth_service.py` y los endpoints **no se modifican**:
el cambio es solo de variable de entorno. La suite ya cubre ambos backends:
`tests/test_auth_postgres_repos.py` (unitaria, siempre activa) y
`tests/test_auth_postgres_integracion.py` (requiere `OPTIROUTE_TEST_DB=1`).

## 2. Esquema requerido por el repositorio PostgreSQL

El repositorio espera las tablas de acceso en el esquema `seguridad`. La
migración SQL es **aditiva** (nunca destructiva). La tabla actual
`seguridad.usuarios` (`database/scripts/003_crear_tablas.sql`) solo permite
`ADMINISTRADOR|OPERADOR|CONDUCTOR` y no distingue la cuenta propietaria.

```sql
-- 006 (nueva, aditiva): ajustes para autenticación completa
ALTER TABLE seguridad.usuarios
  DROP CONSTRAINT IF EXISTS usuarios_tipo_usuario_check;      -- nombre a verificar en 003
ALTER TABLE seguridad.usuarios
  ADD CONSTRAINT usuarios_tipo_usuario_check
  CHECK (tipo_usuario IN ('OPERADOR','ADMINISTRADOR','DESARROLLADOR','CONDUCTOR'));

ALTER TABLE seguridad.usuarios
  ADD COLUMN IF NOT EXISTS es_propietario BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS ultimo_acceso  TIMESTAMPTZ;

-- Sesiones de acceso (los tokens se guardan solo como hash SHA-256)
CREATE TABLE IF NOT EXISTS seguridad.sesiones (
  token_hash  TEXT PRIMARY KEY,
  id_usuario  INTEGER NOT NULL REFERENCES seguridad.usuarios(id_usuario) ON DELETE CASCADE,
  creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expira_en   TIMESTAMPTZ NOT NULL,
  revocado    BOOLEAN NOT NULL DEFAULT FALSE,
  revocado_en TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS sesiones_usuario_idx ON seguridad.sesiones(id_usuario);
CREATE INDEX IF NOT EXISTS sesiones_vigencia_idx ON seguridad.sesiones(expira_en) WHERE NOT revocado;

-- Bitácora append-only (mismo contenido que auditoria.jsonl)
CREATE TABLE IF NOT EXISTS seguridad.auditoria (
  id         BIGSERIAL PRIMARY KEY,
  accion     TEXT NOT NULL,
  actor      TEXT,
  actor_id   INTEGER,
  objetivo   TEXT,
  rol        TEXT,
  detalle    TEXT,
  creado_en  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS auditoria_fecha_idx ON seguridad.auditoria(creado_en DESC);
```

Notas de diseño:

- `password_hash` (VARCHAR 255) admite sin cambios el formato PBKDF2 actual:
  **las contraseñas se migran tal cual, sin reseteo**.
- `ON DELETE CASCADE` en sesiones; la auditoría **nunca** se borra.
- No se almacenan tokens en claro: solo su hash SHA-256 (igual que hoy).
- Antes de aplicar la 006, verificar el nombre real del constraint en
  `003_crear_tablas.sql` (evita errores de `DROP CONSTRAINT IF EXISTS`).

## 3. Migración de datos (cuando existan cuentas)

Procedimiento **idempotente y verificable**, ejecutado una sola vez:

1. **Respaldos previos (obligatorios):**
   - `pg_dump -Fc -d optiroute_db > respaldo_pre_migracion.dump`
   - Copia de `backend/data/seguridad/` completa (cuentas, sesiones, auditoría).
2. Exportar `cuentas.json` a un script SQL/COPY con las columnas:
   `nombres, apellidos, correo, password_hash, tipo_usuario, activo, id_conductor, es_propietario, creado_en, ultimo_acceso`.
   - Los hashes se copian **literalmente** (mismo algoritmo e iteraciones).
   - Conflicto por correo duplicado → `ON CONFLICT (correo) DO NOTHING` y
     reporte de los omitidos (nunca sobrescribir).
3. Validación post-export (antes de la conmutación):
   - `SELECT COUNT(*)` por `tipo_usuario` igual al conteo del JSON.
   - Verificar **todas** las cuentas migradas: comparar `password_hash`
     contra el JSON (consulta de diferencias, debe devolver 0 filas).
   - Prueba de humo: iniciar sesión con una cuenta migrada (sin cambiarla).
4. Sesiones: **no se migran** (expiran solas en ≤ `AUTH_SESSION_HORAS`).
   Los usuarios deberán iniciar sesión de nuevo tras el cambio; es aceptable y
   evita arrastrar tokens.
5. Auditoría: importar `auditoria.jsonl` a `seguridad.auditoria` conservando
   `creado_en` original.
6. Conmutación: `OPTIROUTE_AUTH_STORAGE=postgres` en `.env` del backend y
   reinicio del servicio.

## 4. Plan de pruebas

- **Paridad de backends:** ejecutar la suite completa con cada backend:
  - `OPTIROUTE_AUTH_STORAGE=local pytest -q` (JSON, ya en verde).
  - `set OPTIROUTE_TEST_DB=1 && python -m pytest tests/test_auth_postgres_integracion.py -q`
    (integración real contra PostgreSQL).
- **Migración:** exportación → importación → verificación de hashes → login
  real, sobre una copia de la base (nunca sobre producción).
- **Concurrencia:** `tests/test_sesiones.py::TestConcurrencia` contra
  PostgreSQL (constraint `UNIQUE` en `correo` reemplaza los candados de
  archivo).
- **Rendimiento:** `listar_usuarios`, `resolver_sesion` ( PK por `token_hash`)
  y `revocar_por_usuario` con ≥ 1 000 sesiones.
- **Reversión:** `OPTIROUTE_AUTH_STORAGE=local` y reinicio; los datos JSON
  originales permanecen intactos (no se borran).

## 5. Criterios de aceptación

1. Toda la suite en verde contra PostgreSQL (integración incluida).
2. 0 diferencias de hashes entre el respaldo JSON y la tabla migrada.
3. Ningún usuario necesita cambiar su contraseña por la migración.
4. Rollback probado y documentado (≤ 5 minutos).
5. Sin credenciales nuevas en el repositorio; `.env` sigue fuera de git.

## 6. Fuera de alcance (explícito)

- **Supabase** (se evaluará después).
- Cambios destructivos en `seguridad.usuarios` o en cualquier dato real.
- Modificación del formato de hash (PBKDF2-SHA256 se mantiene).
- Ejecución automática de la migración: requiere autorización escrita.
