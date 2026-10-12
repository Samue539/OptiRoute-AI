export type Screen =
  | "dashboard"
  | "pedidos"
  | "pedido-detalle"
  | "clientes"
  | "rutas"
  | "ruta-detalle"
  | "vehiculos"
  | "conductores"
  | "optimizacion"
  | "ia"
  | "mapa-vivo"
  | "reportes"
  | "configuracion"
  | "conductor-movil"
  | "distribucion"
  | "usuarios";

export interface NodeInfo {
  id_nodo: number;
  nombre: string;
  tipo_nodo: string;
  latitud: number;
  longitud: number;
}

export interface UsuarioInfo {
  id_usuario: number;
  nombres: string;
  apellidos: string;
  correo: string;
  rol: string;
  activo: boolean;
  id_conductor: number | null;
  es_propietario: boolean;
  creado_en: string | null;
  ultimo_acceso: string | null;
}

export interface SesionRespuesta {
  token: string | null;
  expira_en: string;
  usuario: UsuarioInfo;
  permisos: string[];
}

export interface EstadoBootstrap {
  propietario_creado: boolean;
  almacenamiento: string;
}

/** Catalogo de permisos expuesto por `GET /api/auth/permisos`. */
export interface PermisoCatalogo {
  codigo: string;
  nombre: string;
  descripcion: string;
  modulo: string;
  ambito: "general" | "limitado" | "propio";
  limite: string | null;
}

export interface RolCatalogo {
  rol: string;
  descripcion: string;
  total_permisos: number;
  permisos: string[];
  estados_pedido: string;
  estados_ruta: string;
}

export interface ModuloCatalogo {
  id: string;
  nombre: string;
}

export interface ReglaCatalogo {
  titulo: string;
  detalle: string;
}

export interface CatalogoPermisos {
  roles: RolCatalogo[];
  modulos: ModuloCatalogo[];
  permisos: PermisoCatalogo[];
  reglas: ReglaCatalogo[];
  rol_actual: string;
  efectivos: string[];
}

export interface UsuarioCrearPayload {
  nombres: string;
  apellidos: string;
  correo: string;
  password: string;
  rol: string;
  id_conductor?: number | null;
}

export interface CatalogNode extends NodeInfo {
  activo: boolean;
}

export interface OrderCatalogItem {
  id_pedido: number;
  codigo: string;
  id_cliente: number;
  id_direccion_entrega: number;
  descripcion: string | null;
  peso_kg: number | null;
  volumen_m3: number | null;
  prioridad: string;
  estado: string;
  fecha_solicitada: string | null;
  destino: CatalogNode | null;
  estado_entrega: string | null;
  creado_en: string;
}

export interface VehicleCatalogItem {
  id_vehiculo: number;
  placa: string;
  marca: string | null;
  modelo: string | null;
  anio: number | null;
  tipo_vehiculo: string;
  capacidad_kg: number | null;
  capacidad_volumen_m3: number | null;
  estado: string;
  activo: boolean;
  disponible: boolean;
}

export interface DriverCatalogItem {
  id_conductor: number;
  nombres: string;
  apellidos: string;
  numero_licencia: string;
  tipo_licencia: string | null;
  telefono: string | null;
  activo: boolean;
  disponible: boolean;
}

export interface RouteSummary {
  id_ruta: number;
  codigo: string;
  origen: Pick<NodeInfo, "id_nodo" | "nombre">;
  destino: Pick<NodeInfo, "id_nodo" | "nombre">;
  estado: string;
  distancia_total_km: number | null;
  conductor: { id_conductor: number; nombres: string; apellidos: string } | null;
  vehiculo: { id_vehiculo: number; placa: string } | null;
  fecha_planificada: string | null;
  creado_en: string;
}

export interface RouteDetail {
  id_ruta: number;
  codigo: string;
  origen: { id_nodo: number; nombre: string };
  destino: { id_nodo: number; nombre: string };
  estado: string;
  distancia_total_km: number | null;
  tiempo_estimado_min: number | null;
  costo_estimado: number | null;
  conductor: { id_conductor: number; nombres: string; apellidos: string; numero_licencia: string } | null;
  vehiculo: { id_vehiculo: number; placa: string; marca: string | null; modelo: string | null } | null;
  fecha_planificada: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  creado_en: string;
  actualizado_en: string;
  puntos: Array<{
    orden: number;
    id_nodo: number;
    nombre: string;
    tipo_nodo: string;
    latitud: number;
    longitud: number;
    distancia_acumulada_km: number | null;
  }>;
}

export interface RouteOrder {
  id_ruta_pedido: number;
  orden_entrega: number;
  id_pedido: number;
  codigo: string;
  descripcion: string | null;
  prioridad: string;
  estado: string;
}

export interface ClienteItem {
  id_cliente: number;
  tipo_cliente: string;
  nombres: string | null;
  apellidos: string | null;
  razon_social: string | null;
  identificacion: string | null;
  correo: string | null;
  telefono: string | null;
  activo: boolean;
  creado_en: string;
}

export interface DireccionItem {
  id_direccion: number;
  id_cliente: number;
  id_nodo: number | null;
  etiqueta: string;
  direccion_texto: string;
  ciudad: string;
  provincia: string | null;
  pais: string;
  latitud: number;
  longitud: number;
  referencia: string | null;
  es_principal: boolean;
  activo: boolean;
  nodo: CatalogNode | null;
}

export interface PlanningRequest {
  origen: number;
  pedidos: number[];
  id_vehiculo: number;
  regresar_origen: boolean;
}

export interface PlannedOrder {
  id_pedido: number;
  codigo: string;
  id_cliente: number;
  id_direccion_entrega: number;
  descripcion: string | null;
  peso_kg: number;
  volumen_m3: number;
  prioridad: string;
  estado: string;
  destino: NodeInfo;
}

export interface PlanningResponse {
  factible: boolean;
  vehiculo: {
    id_vehiculo: number;
    placa: string;
    marca: string | null;
    modelo: string | null;
    tipo_vehiculo: string;
    estado: string;
    capacidad_kg: number;
    capacidad_volumen_m3: number;
  };
  pedidos: PlannedOrder[];
  peso_total: number;
  capacidad_peso: number;
  volumen_total: number;
  capacidad_volumen: number;
  origen: NodeInfo;
  destinos: number[];
  orden_optimo: number[];
  recorrido: number[];
  distancia_total_km: number;
  regresar_origen: boolean;
  algoritmo: string;
  permutaciones_evaluadas: number;
}

export interface SavePlanningRequest extends PlanningRequest {
  id_conductor: number;
  clave_idempotencia: string;
}

export interface SavedRoutePlan {
  id_ruta: number;
  codigo: string;
  estado: string;
  distancia_total_km: number;
  recorrido: number[];
  pedidos: Array<number | { id_pedido: number; orden_entrega: number }>;
  duplicada: boolean;
}

/* -------- Centro de Distribución y Entregas -------- */

export interface ZonaItem {
  id_zona: number;
  codigo: string;
  nombre: string;
  ciudad: string;
  activa: boolean;
}

export interface ProgresoRuta {
  total: number;
  pendientes: number;
  en_ruta: number;
  entregadas: number;
  fallidas: number;
}

export interface RutaAsignada {
  id_ruta: number;
  codigo: string;
  nombre_ruta: string | null;
  estado: string;
  zona: ZonaItem | null;
  conductor: { id_conductor: number; nombres: string; apellidos: string } | null;
  vehiculo: { id_vehiculo: number; placa: string } | null;
  distancia_total_km: number | null;
  progreso: ProgresoRuta;
}

export interface GuiaItem {
  id_guia: number;
  numero_guia: string;
  estado: string;
  destinatario_nombre: string;
  direccion_texto: string;
  telefono_autorizado: string | null;
  id_ruta: number | null;
  ruta_codigo: string | null;
  zona: ZonaItem | null;
  intentos_entrega: number;
  fecha_entrega: string | null;
}

export interface GuiaEvidenciaMeta {
  id_evidencia: number;
  tipo: string;
  mime: string;
  tamano_bytes: number;
  sha256: string;
  creado_en: string | null;
}

export interface GuiaEvento {
  id_evento: number;
  tipo: string;
  actor_cuenta: number | null;
  receptor_nombre: string | null;
  relacion_destinatario: string | null;
  motivo_falla: string | null;
  gps_latitud: number | null;
  gps_longitud: number | null;
  gps_precision_m: number | null;
  gps_origen: string | null;
  observaciones: string | null;
  evidencias: GuiaEvidenciaMeta[];
  creado_en: string | null;
}

export interface ResumenGuias {
  total: number;
  pendientes: number;
  en_ruta: number;
  entregadas: number;
  fallidas: number;
}

export interface EmpresaItem {
  id_empresa: string;
  codigo: string;
  nombre: string;
  activa: boolean;
}

export type RiskLevel = "BAJO" | "MEDIO" | "ALTO" | "CRITICO";

export interface AIAnalysis {
  nivel_riesgo: RiskLevel;
  alertas: Array<{
    codigo: string;
    severidad: "INFORMATIVA" | "ADVERTENCIA" | "CRITICA";
    mensaje: string;
  }>;
  recomendaciones: string[];
  indicadores: {
    utilizacion_peso_pct: number;
    utilizacion_volumen_pct: number;
    cantidad_pedidos: number;
    cantidad_destinos: number;
    cantidad_nodos_recorrido: number;
    pedidos_urgentes: number;
    distancia_total_km: number;
    regresar_origen: boolean;
    factible: boolean;
    distribucion_prioridades: Record<string, number>;
  };
  resumen: string;
  motor: string;
}
