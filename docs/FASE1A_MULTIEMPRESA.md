# FASE 1A — Base multiempresa aditiva

## Alcance y estado

Esta fase prepara la arquitectura multiempresa sin ejecutarla sobre la base
de datos actual. No cambia el almacenamiento de autenticacion, no rellena
empresas automaticamente y no modifica rutas, pedidos, usuarios ni paneles.

La migracion `database/scripts/007_multiempresa_base.sql` se entrega como
artefacto versionado e idempotente. El backend no la aplica al arrancar. Si
se invoca un endpoint empresarial antes de instalarla en un entorno
autorizado, responde `503` y no degrada a un almacenamiento sin aislamiento.

## Identidad canonica

1. `seguridad.cuentas_acceso.id_usuario` sera la identidad de autenticacion
   canonica de plataforma cuando se autorice la migracion desde JSON.
2. Los JSON siguen siendo la fuente activa en esta fase.
3. `seguridad.usuarios` se conserva como identidad logistica legada; no se
   fusiona por coincidencia numerica ni de nombre.
4. `plataforma.empresa_usuarios` enlaza una cuenta canonica con una empresa.
5. `DESARROLLADOR` conserva alcance de plataforma y no es un rol de membresia.
6. `ADMINISTRADOR`, `OPERADOR` y `CONDUCTOR` actuan dentro de una empresa y su
   rol empresarial debe coincidir con el rol autenticado durante la transicion.

La coincidencia numerica entre un ID JSON y un ID de `seguridad.usuarios` no
demuestra identidad. Una futura migracion debe usar una tabla de equivalencias
verificada y nunca inferir el vinculo automaticamente.

## Entidades propuestas

### `plataforma.empresas`

Organizacion propietaria de los datos operativos. Usa UUID generado por la
aplicacion, codigo estable, nombre, identificacion fiscal opcional y estado.

### `plataforma.empresa_usuarios`

Membresia entre empresa y cuenta canonica. Contiene rol empresarial, estado y
marca de propietario empresarial. No admite `DESARROLLADOR`, porque ese rol
pertenece a la plataforma.

### `plataforma.recursos_empresa`

Vinculo transitorio para recursos legados. Permite asociar clientes,
conductores, vehiculos, pedidos y rutas sin añadir columnas ni actualizar las
tablas actuales. Tambien reserva los tipos `ZONA` y `GUIA` para fases futuras.
Un recurso solo puede pertenecer a una empresa.

### `plataforma.asignaciones_operativas`

Asigna un recurso empresarial a una membresia activa. Es la base para limitar
las futuras entregas de OPERADOR y CONDUCTOR a rutas, pedidos o guias
asignadas. La asignacion exige que membresia y recurso pertenezcan a la misma
empresa.

### `plataforma.migraciones`

Registro de versiones aplicadas para la capa de plataforma.

## Autorizacion empresarial

El RBAC existente no fue reemplazado ni reducido. La nueva autorizacion se
evalua despues de autenticar la cuenta:

- DESARROLLADOR: alcance de plataforma; crea empresas y administradores.
- ADMINISTRADOR: administra membresias y recursos solo de su empresa. No puede
  crear otro ADMINISTRADOR.
- OPERADOR: ve su empresa y solo accede a recursos expresamente asignados.
- CONDUCTOR: ve su empresa y solo accede a recursos expresamente asignados.

Toda comprobacion usa el ID de empresa del servidor, una membresia activa y el
vinculo del recurso. Recibir un `id_empresa`, `id_ruta` o `id_pedido` del
cliente nunca autoriza por si mismo.

Las acciones empresariales viven en un catalogo independiente para no alterar
los permisos RBAC historicos:

- `empresa:ver`
- `empresa:membresias_ver`
- `empresa:membresias_administrar`
- `empresa:recursos_vincular`
- `empresa:recursos_asignar`
- `empresa:recurso_acceder`
- `empresa:entregas_ver_asignadas`
- `empresa:entregas_registrar_asignada`

Los dos permisos de entrega son independientes de los permisos
administrativos. OPERADOR y CONDUCTOR los reciben, pero su uso futuro exige
ademas que la guia, pedido o ruta pertenezca a su empresa y tenga una
asignacion activa. En FASE 1A no se implementa todavia el registro de entrega.

## Endpoints preparados

| Metodo | Ruta | Regla principal |
|---|---|---|
| GET | `/api/empresas/permisos` | Cualquier sesion valida; solo catalogo |
| GET | `/api/empresas` | DESARROLLADOR ve todas; otros solo membresias activas |
| POST | `/api/empresas` | Solo DESARROLLADOR |
| GET | `/api/empresas/{id_empresa}` | Plataforma o membresia activa |
| GET | `/api/empresas/{id_empresa}/membresias` | DESARROLLADOR o ADMINISTRADOR de esa empresa |
| POST | `/api/empresas/{id_empresa}/membresias` | Sin escalamiento de privilegios |
| PATCH | `/api/empresas/{id_empresa}/membresias/{id}` | Protege propietarios y auto-desactivacion |
| POST | `/api/empresas/{id_empresa}/recursos` | Vinculo explicito y unico |
| POST | `/api/empresas/{id_empresa}/asignaciones` | Membresia y recurso de la misma empresa |
| GET | `/api/empresas/{id_empresa}/recursos/{tipo}/{id}/acceso` | Denegacion por defecto y asignacion activa |

## Procedimiento futuro de migracion

Requiere una autorizacion posterior. No se ha ejecutado en FASE 1A.

1. Crear y verificar un nuevo respaldo de PostgreSQL y de los JSON.
2. Clonar el respaldo en una base aislada y registrar sus conteos.
3. Verificar que `006_seguridad_acceso.sql` esta aplicado en el clon.
4. Ejecutar en modo de verificacion la migracion de cuentas JSON y resolver
   colisiones de identidad sin cambiar IDs automaticamente.
5. Migrar y comprobar cuentas canonicas en el clon.
6. Aplicar `007_multiempresa_base.sql` solamente en el clon.
7. Crear una empresa de transicion y proponer, sin automatismos, el mapa de
   recursos legados hacia esa empresa.
8. Resolver previamente el conductor y el vehiculo presentes en varias rutas
   activas.
9. Validar conteos, claves foraneas, propietario, roles y aislamiento con dos
   empresas.
10. Generar un informe de diferencias y solicitar autorizacion antes de repetir
    el procedimiento en otro entorno.

No debe activarse la capa empresarial sobre datos parcialmente vinculados. La
politica es detener y corregir, nunca continuar en modo abierto.

## Reversion futura

La reversion solo es segura mientras ningun modulo posterior dependa de estas
tablas. Debe aprobarse expresamente y ejecutarse primero en un clon:

1. Deshabilitar el acceso a endpoints empresariales.
2. Exportar por separado las cuatro tablas de negocio de `plataforma`.
3. Verificar que ningun dato nuevo depende de empresas o asignaciones.
4. Eliminar en orden inverso: `asignaciones_operativas`,
   `recursos_empresa`, `empresa_usuarios`, `empresas` y finalmente el registro
   de migraciones.
5. Eliminar el esquema solo si esta vacio.
6. Ejecutar las pruebas completas y comparar los datos legados con el respaldo.

La reversion no debe borrar ni modificar `seguridad.cuentas_acceso`,
`seguridad.usuarios`, `logistica.*` u `operaciones.*`. No se incluye un script
automatico destructivo para evitar una ejecucion accidental.

## Riesgos pendientes

- La autenticacion activa continua en JSON; las membresias PostgreSQL no deben
  activarse hasta migrar y verificar las cuentas canonicas.
- Todavia no existe un mapa autorizado para los datos legados.
- Los endpoints operativos historicos aun no exigen contexto empresarial; se
  integraran solo despues del vinculado verificado para no bloquear ni exponer
  datos existentes.
- Falta definir si placas, licencias, codigos de pedido y codigos de ruta son
  unicos globalmente o dentro de cada empresa.
- Altas, cambios de membresia, vinculos y asignaciones se registran en la
  auditoria de autenticacion actual. Falta llevar esa bitacora provisional a
  persistencia empresarial transaccional cuando se autorice la migracion.
- Zonas, guias, evidencias, GPS y almacenamiento privado quedan fuera de esta
  fase. Solo se reservaron sus vinculos futuros.
- PostGIS y Supabase no fueron instalados ni conectados.

## Verificacion realizada

- Se restauro el respaldo verificado de FASE 0 en la base temporal
  `optiroute_fase1a_20261011184619`.
- La migracion 007 se aplico dos veces sobre esa base: creo cinco tablas y
  mantuvo una sola entrada de version, sin empresas ni membresias automaticas.
- La base temporal fue eliminada al finalizar.
- En una segunda base temporal se ejercito el repositorio PostgreSQL con dos
  empresas, tres membresias, un recurso y una asignacion. El acceso asignado
  fue aceptado, el acceso cruzado fue denegado y la base tambien fue eliminada.
- La base de desarrollo original conserva 9 rutas, 14 pedidos, 4 usuarios
  logisticos y 0 cuentas en `seguridad.cuentas_acceso`; no contiene el esquema
  `plataforma`.
- Se recopilaron 285 pruebas: 274 aprobaron y 11 integraciones PostgreSQL
  opcionales quedaron omitidas. No hubo fallos.
- Las 14 pruebas nuevas usan un repositorio en memoria con dos empresas y
  cubren aislamiento, asignaciones, cuatro roles, no escalamiento y proteccion
  de propietarios.
- `npm run lint` y `npm run build` finalizaron correctamente. El frontend y el
  Centro de control del DESARROLLADOR no recibieron cambios funcionales.
