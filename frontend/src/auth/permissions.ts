import type { Screen } from "../api/types";

/**
 * Espejo del catalogo de permisos del backend
 * (`backend/app/core/permisos.py`).
 *
 * IMPORTANTE: esto solo controla que se muestra en la interfaz. La seguridad
 * real la impone el backend en cada endpoint; ocultar un boton nunca
 * sustituye esa validacion.
 *
 * La pantalla "Gestion de roles y permisos" no usa este espejo: consume el
 * catalogo real de `GET /api/auth/permisos` (ver `PermissionMatrix.tsx`), de
 * modo que la matriz jamas puede divergir del backend.
 */

export type Role =
  | "OPERADOR"
  | "ADMINISTRADOR"
  | "DESARROLLADOR"
  | "CONDUCTOR";

export type Permission =
  | "panel:ver"
  | "pedidos:ver"
  | "pedidos:crear"
  | "pedidos:editar"
  | "pedidos:estado"
  | "pedidos:estado_limitado"
  | "pedidos:ver_propios"
  | "pedidos:estado_propio"
  | "clientes:ver"
  | "recursos:ver"
  | "rutas:ver_todas"
  | "rutas:ver_propias"
  | "rutas:planificar"
  | "rutas:crear"
  | "rutas:asignar"
  | "rutas:estado"
  | "rutas:estado_limitado"
  | "rutas:ver_asignadas"
  | "guias:ver_asignadas"
  | "guias:entregar"
  | "guias:novedad"
  | "evidencias:ver"
  | "ia:usar"
  | "reportes:ver"
  | "configuracion:operativa"
  | "flota:gestionar"
  | "cuentas:operativas"
  | "perfiles:administrar"
  | "cuentas:administradores"
  | "configuracion:tecnica"
  | "diagnostico:ver"
  | "auditoria:ver";

const PERMISOS_OPERACION: Permission[] = [
  "panel:ver",
  "pedidos:ver",
  "pedidos:estado_limitado",
  "clientes:ver",
  "recursos:ver",
  "rutas:ver_todas",
  "rutas:estado_limitado",
  "rutas:ver_asignadas",
  "guias:ver_asignadas",
  "guias:entregar",
  "guias:novedad",
  "evidencias:ver",
  "ia:usar",
];

const PERMISOS_ADMINISTRADOR: Permission[] = [
  ...PERMISOS_OPERACION,
  "pedidos:crear",
  "pedidos:editar",
  "pedidos:estado",
  "rutas:planificar",
  "rutas:crear",
  "rutas:asignar",
  "rutas:estado",
  "reportes:ver",
  "configuracion:operativa",
  "flota:gestionar",
  "cuentas:operativas",
];

const PERMISOS_DESARROLLADOR: Permission[] = [
  ...PERMISOS_ADMINISTRADOR,
  "perfiles:administrar",
  "cuentas:administradores",
  "configuracion:tecnica",
  "diagnostico:ver",
  "auditoria:ver",
];

const PERMISOS_CONDUCTOR: Permission[] = [
  "rutas:ver_propias",
  "rutas:estado",
  "pedidos:ver_propios",
  "pedidos:estado_propio",
  "rutas:ver_asignadas",
  "guias:ver_asignadas",
  "guias:entregar",
  "guias:novedad",
  "evidencias:ver",
];

export const PERMISOS_POR_ROL: Record<Role, Permission[]> = {
  OPERADOR: PERMISOS_OPERACION,
  ADMINISTRADOR: PERMISOS_ADMINISTRADOR,
  DESARROLLADOR: PERMISOS_DESARROLLADOR,
  CONDUCTOR: PERMISOS_CONDUCTOR,
};

/** Descripcion corta de cada rol (mismo texto que el backend). */
export const DESCRIPCION_ROL: Record<Role, string> = {
  OPERADOR:
    "Consulta y seguimiento de pedidos, clientes y rutas. Puede cancelar pedidos y rutas, pero no crear ni modificar datos operativos.",
  ADMINISTRADOR:
    "Gestion operativa completa: pedidos, clientes, rutas, flota, reportes y cuentas operativas. Sin acceso a la configuracion tecnica.",
  DESARROLLADOR:
    "Administracion tecnica total: diagnosticos, auditoria, perfiles, cuentas administrativas y configuracion del sistema.",
  CONDUCTOR:
    "Acceso exclusivo a sus rutas y pedidos asignados. Confirma entregas y registra novedades; no consulta datos administrativos.",
};

/** Modulos del sistema, en el orden en que se muestra la matriz. */
export const MODULOS: Array<{ id: string; nombre: string }> = [
  { id: "panel", nombre: "Panel y tablero" },
  { id: "pedidos", nombre: "Pedidos" },
  { id: "clientes", nombre: "Clientes" },
  { id: "recursos", nombre: "Flota y mapa" },
  { id: "rutas", nombre: "Rutas" },
  { id: "distribucion", nombre: "Distribución y entregas" },
  { id: "ia", nombre: "Asistente logistico" },
  { id: "reportes", nombre: "Reportes" },
  { id: "cuentas", nombre: "Cuentas y accesos" },
  { id: "sistema", nombre: "Sistema y diagnostico" },
];

export function permisosDelRol(rol: string): Permission[] {
  return PERMISOS_POR_ROL[rol as Role] ?? [];
}

export function tienePermiso(
  permisos: readonly string[],
  permiso: Permission,
): boolean {
  return permisos.includes(permiso);
}

export function tieneAlguno(
  permisos: readonly string[],
  requeridos: readonly Permission[],
): boolean {
  return requeridos.some((permiso) => permisos.includes(permiso));
}

/** Permisos que habilitan cada pantalla (basta con cumplir uno). */
export const ACCESO_PANTALLA: Record<Screen, Permission[]> = {
  dashboard: ["panel:ver", "rutas:ver_propias"],
  pedidos: ["pedidos:ver", "pedidos:ver_propios"],
  "pedido-detalle": ["pedidos:ver", "pedidos:ver_propios"],
  clientes: ["clientes:ver"],
  rutas: ["rutas:ver_todas", "rutas:ver_propias"],
  "ruta-detalle": ["rutas:ver_todas", "rutas:ver_propias"],
  vehiculos: ["recursos:ver"],
  conductores: ["recursos:ver"],
  optimizacion: ["rutas:planificar"],
  ia: ["ia:usar"],
  "mapa-vivo": ["rutas:ver_todas", "rutas:ver_propias"],
  reportes: ["reportes:ver"],
  configuracion: ["configuracion:operativa", "configuracion:tecnica"],
  "conductor-movil": ["rutas:ver_propias"],
  distribucion: ["guias:ver_asignadas", "rutas:ver_asignadas"],
  usuarios: ["cuentas:operativas", "perfiles:administrar"],
};

export function puedeVerPantalla(
  permisos: readonly string[],
  pantalla: Screen,
): boolean {
  return tieneAlguno(permisos, ACCESO_PANTALLA[pantalla]);
}

/* ------------------------------------------------------------------ *
 * Estados que la interfaz ofrece para cambiar (espejo de los límites
 * del backend). El servidor vuelve a validarlos: esto solo evita
 * ofrecer acciones que terminarían en 403.
 * ------------------------------------------------------------------ */

const ESTADOS_PEDIDO = ["PENDIENTE", "PLANIFICADO", "EN_RUTA", "ENTREGADO", "CANCELADO"];
const ESTADOS_RUTA = ["PLANIFICADA", "ASIGNADA", "EN_RUTA", "COMPLETADA", "CANCELADA"];

export function estadosPedidoEditables(permisos: readonly string[]): string[] {
  if (permisos.includes("pedidos:estado")) return ESTADOS_PEDIDO;
  if (permisos.includes("pedidos:estado_limitado")) return ["CANCELADO"];
  if (permisos.includes("pedidos:estado_propio")) return ["ENTREGADO"];
  return [];
}

export function estadosRutaEditables(permisos: readonly string[]): string[] {
  if (permisos.includes("rutas:estado")) {
    return permisos.includes("rutas:ver_todas") ? ESTADOS_RUTA : ["EN_RUTA", "COMPLETADA", "CANCELADA"];
  }
  if (permisos.includes("rutas:estado_limitado")) return ["CANCELADA"];
  return [];
}

export function puedeCambiarEstadoRuta(permisos: readonly string[]): boolean {
  return estadosRutaEditables(permisos).length > 0;
}
