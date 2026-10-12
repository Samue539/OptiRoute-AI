import type {
  AIAnalysis,
  CatalogoPermisos,
  CatalogNode,
  ClienteItem,
  DireccionItem,
  DriverCatalogItem,
  EmpresaItem,
  EstadoBootstrap,
  GuiaEvento,
  GuiaItem,
  OrderCatalogItem,
  PlanningRequest,
  PlanningResponse,
  ResumenGuias,
  RutaAsignada,
  SavePlanningRequest,
  SavedRoutePlan,
  RouteDetail,
  RouteOrder,
  RouteSummary,
  SesionRespuesta,
  UsuarioCrearPayload,
  UsuarioInfo,
  VehicleCatalogItem,
  ZonaItem,
} from "./types";

const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function getAuthToken() {
  return authToken;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  if (authToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers,
    });
  } catch {
    throw new ApiError(
      `No fue posible conectar con la API en ${API_URL}. Verifica que FastAPI esté en ejecución.`,
      0,
    );
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(" · ")
      : detail || `La API respondió con estado ${response.status}.`;
    throw new ApiError(message, response.status);
  }

  return payload as T;
}

async function apiRequestForm<T>(path: string, form: FormData): Promise<T> {
  const headers = new Headers();
  if (authToken) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }
  // Sin Content-Type: el navegador fija multipart/form-data con su boundary.
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      body: form,
      headers,
    });
  } catch {
    throw new ApiError(
      `No fue posible conectar con la API en ${API_URL}. Verifica que FastAPI esté en ejecución.`,
      0,
    );
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(" · ")
      : detail || `La API respondió con estado ${response.status}.`;
    throw new ApiError(message, response.status);
  }
  return payload as T;
}

export const authApi = {
  estado: () => apiRequest<EstadoBootstrap>("/api/auth/estado"),
  bootstrap: (datos: {
    nombres: string;
    apellidos: string;
    correo: string;
    password: string;
  }) => apiRequest<SesionRespuesta>("/api/auth/bootstrap", { method: "POST", body: JSON.stringify(datos) }),
  login: (datos: { correo: string; password: string }) =>
    apiRequest<SesionRespuesta>("/api/auth/login", { method: "POST", body: JSON.stringify(datos) }),
  session: () => apiRequest<SesionRespuesta>("/api/auth/session"),
  logout: () => apiRequest<{ cerrado: boolean }>("/api/auth/logout", { method: "POST" }),
  cambiarPassword: (datos: { password_actual: string; password_nueva: string }) =>
    apiRequest<{ actualizado: boolean; sesiones_revocadas: number; mensaje: string }>(
      "/api/auth/cambiar-password",
      { method: "POST", body: JSON.stringify(datos) },
    ),
  listarUsuarios: () => apiRequest<UsuarioInfo[]>("/api/auth/usuarios"),
  crearUsuario: (datos: UsuarioCrearPayload) =>
    apiRequest<UsuarioInfo>("/api/auth/usuarios", { method: "POST", body: JSON.stringify(datos) }),
  cambiarEstado: (id: number, activo: boolean) =>
    apiRequest<UsuarioInfo>(`/api/auth/usuarios/${id}/estado`, { method: "PATCH", body: JSON.stringify({ activo }) }),
  cambiarRol: (id: number, rol: string) =>
    apiRequest<UsuarioInfo>(`/api/auth/usuarios/${id}/rol`, { method: "PATCH", body: JSON.stringify({ rol }) }),
  restablecerPassword: (id: number, passwordNueva: string) =>
    apiRequest<{ actualizado: boolean; sesiones_revocadas: number; mensaje: string }>(
      `/api/auth/usuarios/${id}/password`,
      { method: "POST", body: JSON.stringify({ password_nueva: passwordNueva }) },
    ),
  diagnostico: () => apiRequest<any>("/api/auth/diagnostico"),
  auditoria: (limite = 100) => apiRequest<any[]>(`/api/auth/auditoria?limite=${limite}`),
  permisos: () => apiRequest<CatalogoPermisos>("/api/auth/permisos"),
};

export const api = {
  listRoutes: () => apiRequest<RouteSummary[]>("/api/rutas"),
  getRoute: (id: number) => apiRequest<RouteDetail>(`/api/rutas/${id}`),
  createRoute: (origen: number, destino: number) =>
    apiRequest<any>("/api/rutas", { method: "POST", body: JSON.stringify({ origen, destino }) }),
  assignRoute: (id: number, id_conductor: number, id_vehiculo: number) =>
    apiRequest<any>(`/api/rutas/${id}/asignacion`, { method: "PATCH", body: JSON.stringify({ id_conductor, id_vehiculo }) }),
  changeRouteState: (id: number, estado: string, motivo?: string) =>
    apiRequest<any>(`/api/rutas/${id}/estado`, { method: "PATCH", body: JSON.stringify(motivo ? { estado, motivo } : { estado }) }),
  savePlannedRoute: (request: SavePlanningRequest) =>
    apiRequest<SavedRoutePlan>("/api/rutas/planificada", { method: "POST", body: JSON.stringify(request) }),
  listRouteOrders: (id: number) => apiRequest<RouteOrder[]>(`/api/rutas/${id}/pedidos`),
  confirmDelivery: (idRuta: number, idPedido: number, data: { nombre_receptor?: string; observaciones?: string } = {}) =>
    apiRequest<any>(`/api/rutas/${idRuta}/pedidos/${idPedido}/entrega`, { method: "POST", body: JSON.stringify(data) }),
  addRouteIncident: (idRuta: number, data: { tipo: string; descripcion: string; id_pedido?: number }) =>
    apiRequest<any>(`/api/rutas/${idRuta}/novedades`, { method: "POST", body: JSON.stringify(data) }),
  listOrders: () => apiRequest<OrderCatalogItem[]>("/api/pedidos"),
  getOrder: (id: number) => apiRequest<OrderCatalogItem>(`/api/pedidos/${id}`),
  createOrder: (data: any) => apiRequest<OrderCatalogItem>("/api/pedidos", { method: "POST", body: JSON.stringify(data) }),
  updateOrder: (id: number, data: any) => apiRequest<OrderCatalogItem>(`/api/pedidos/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  changeOrderState: (id: number, estado: string, motivo?: string) => apiRequest<OrderCatalogItem>(`/api/pedidos/${id}/estado`, { method: "PATCH", body: JSON.stringify(motivo ? { estado, motivo } : { estado }) }),
  getOrderRoute: (id: number) => apiRequest<any>(`/api/pedidos/${id}/ruta`),
  listVehicles: () => apiRequest<VehicleCatalogItem[]>("/api/vehiculos"),
  listDrivers: () => apiRequest<DriverCatalogItem[]>("/api/conductores"),
  listNodes: () => apiRequest<CatalogNode[]>("/api/nodos"),
  listClientes: () => apiRequest<ClienteItem[]>("/api/clientes"),
  getCliente: (id: number) => apiRequest<ClienteItem>(`/api/clientes/${id}`),
  getClienteDirecciones: (id: number) => apiRequest<DireccionItem[]>(`/api/clientes/${id}/direcciones`),
  getClientePedidos: (id: number) => apiRequest<OrderCatalogItem[]>(`/api/clientes/${id}/pedidos`),
  planDeliveries: (request: PlanningRequest) =>
    apiRequest<PlanningResponse>("/api/optimizacion/planificar", {
      method: "POST",
      body: JSON.stringify(request),
    }),
  analyzePlanning: (request: PlanningRequest) =>
    apiRequest<AIAnalysis>("/api/ia/analizar-planificacion", {
      method: "POST",
      body: JSON.stringify(request),
    }),
  getGrafo: () => apiRequest<{ nodos: CatalogNode[]; conexiones: Array<{ origen: number; destino: number; distancia_km: number; bidireccional: boolean }>; vertices: number[] }>("/api/grafo"),
  bfs: (inicio: number) => apiRequest<{ algoritmo: string; inicio: any; recorrido: number[]; detalles: CatalogNode[]; visitados: number }>("/api/grafo/bfs?inicio=" + inicio),
  dfs: (inicio: number) => apiRequest<{ algoritmo: string; inicio: any; recorrido: number[]; detalles: CatalogNode[]; visitados: number }>("/api/grafo/dfs?inicio=" + inicio),
  updateTmcLocation: (lat: number, lon: number) => apiRequest<any>(`/api/grafo/nodos/1/ubicacion`, { method: "PATCH", body: JSON.stringify({ latitud: lat, longitud: lon }) }),
};

export interface EntregaPayload {
  receptor_nombre: string;
  relacion_destinatario: string;
  gps_latitud?: number | null;
  gps_longitud?: number | null;
  gps_precision_m?: number | null;
  gps_origen?: string | null;
  observaciones?: string;
  clave_idempotencia: string;
  foto_guia: File;
  foto_paquete: File;
}

export interface NovedadPayload {
  tipo: "FALLIDA" | "NOVEDAD";
  motivo_falla?: string;
  gps_latitud?: number | null;
  gps_longitud?: number | null;
  gps_precision_m?: number | null;
  gps_origen?: string | null;
  observaciones?: string;
  clave_idempotencia: string;
  fotos?: File[];
}

function formDeEntrega(d: EntregaPayload): FormData {
  const form = new FormData();
  form.append("receptor_nombre", d.receptor_nombre);
  form.append("relacion_destinatario", d.relacion_destinatario);
  if (d.gps_latitud != null) form.append("gps_latitud", String(d.gps_latitud));
  if (d.gps_longitud != null) form.append("gps_longitud", String(d.gps_longitud));
  if (d.gps_precision_m != null) form.append("gps_precision_m", String(d.gps_precision_m));
  if (d.gps_origen) form.append("gps_origen", d.gps_origen);
  if (d.observaciones) form.append("observaciones", d.observaciones);
  form.append("clave_idempotencia", d.clave_idempotencia);
  form.append("foto_guia", d.foto_guia, d.foto_guia.name);
  form.append("foto_paquete", d.foto_paquete, d.foto_paquete.name);
  return form;
}

export const distribucionApi = {
  zonas: () => apiRequest<ZonaItem[]>("/api/distribucion/zonas"),
  misRutas: () => apiRequest<RutaAsignada[]>("/api/distribucion/mis-rutas"),
  guiasDeRuta: (idRuta: number, search = "", estado = "") =>
    apiRequest<GuiaItem[]>(
      `/api/distribucion/mis-rutas/${idRuta}/guias?search=${encodeURIComponent(search)}&estado=${encodeURIComponent(estado)}`,
    ),
  buscarGuia: (numero: string) =>
    apiRequest<GuiaItem>(`/api/distribucion/guias/${encodeURIComponent(numero.trim())}`),
  historial: (idGuia: number) =>
    apiRequest<{ guia: GuiaItem; eventos: GuiaEvento[] }>(
      `/api/distribucion/guias/${idGuia}/eventos`,
    ),
  resumen: () => apiRequest<ResumenGuias>("/api/distribucion/resumen"),
  registrarEntrega: (idGuia: number, datos: EntregaPayload) =>
    apiRequestForm<any>(`/api/distribucion/guias/${idGuia}/entrega`, formDeEntrega(datos)),
  registrarNovedad: (idGuia: number, datos: NovedadPayload) => {
    const form = new FormData();
    form.append("tipo", datos.tipo);
    if (datos.motivo_falla) form.append("motivo_falla", datos.motivo_falla);
    if (datos.gps_latitud != null) form.append("gps_latitud", String(datos.gps_latitud));
    if (datos.gps_longitud != null) form.append("gps_longitud", String(datos.gps_longitud));
    if (datos.gps_precision_m != null) form.append("gps_precision_m", String(datos.gps_precision_m));
    if (datos.gps_origen) form.append("gps_origen", datos.gps_origen);
    if (datos.observaciones) form.append("observaciones", datos.observaciones);
    form.append("clave_idempotencia", datos.clave_idempotencia);
    (datos.fotos || []).slice(0, 2).forEach((foto, i) =>
      form.append(i === 0 ? "foto_1" : "foto_2", foto, foto.name),
    );
    return apiRequestForm<any>(`/api/distribucion/guias/${idGuia}/novedad`, form);
  },
  urlEvidencia: (idEvidencia: number) =>
    apiRequest<{ url: string; expira?: number }>(`/api/distribucion/evidencias/${idEvidencia}/url`),
  asignar: (datos: { id_empresa: string; id_cuenta: number; tipo_recurso: string; id_recurso: number }) =>
    apiRequest<any>("/api/distribucion/asignaciones", { method: "POST", body: JSON.stringify(datos) }),
};

export const empresasApi = {
  listar: () => apiRequest<EmpresaItem[]>("/api/empresas"),
};
