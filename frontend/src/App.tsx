import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { api, authApi, ApiError, setAuthToken } from "./api/client";
import type {
  AIAnalysis,
  CatalogNode,
  ClienteItem,
  DireccionItem,
  DriverCatalogItem,
  OrderCatalogItem,
  PlanningRequest,
  PlanningResponse,
  RiskLevel,
  RouteDetail,
  RouteSummary,
  Screen,
  SesionRespuesta,
  UsuarioInfo,
  VehicleCatalogItem,
} from "./api/types";
import { puedeVerPantalla, estadosPedidoEditables, estadosRutaEditables, puedeCambiarEstadoRuta, tienePermiso } from "./auth/permissions";
import LeafletMap from "./components/LeafletMap";
import AccessPanel from "./components/panels/AccessPanel";
import BootstrapPanel from "./components/panels/BootstrapPanel";
import CancelReasonModal from "./components/panels/CancelReasonModal";
import DeveloperConsole from "./components/panels/DeveloperConsole";
import DriverPanel from "./components/panels/DriverPanel";
import DistribucionPanel from "./components/panels/DistribucionPanel";
import ProfileDashboard from "./components/panels/ProfileDashboard";
import RouteIncidentForm from "./components/panels/RouteIncidentForm";
import { Icono } from "./components/Icono";

const navigation: Array<{ id: Screen; label: string; mark: string; icon: string; icono: string }> = [
  { id: "dashboard", label: "Dashboard", mark: "DB", icon: "🏠", icono: "dashboard" },
  { id: "distribucion", label: "Distribución", mark: "DI", icon: "📦", icono: "paquete" },
  { id: "pedidos", label: "Pedidos", mark: "PE", icon: "📄", icono: "pedidos" },
  { id: "clientes", label: "Clientes", mark: "CL", icon: "👥", icono: "clientes" },
  { id: "rutas", label: "Rutas", mark: "RU", icon: "🗺", icono: "rutas" },
  { id: "conductores", label: "Conductores", mark: "CO", icon: "👤", icono: "conductores" },
  { id: "vehiculos", label: "Vehículos", mark: "VE", icon: "🚚", icono: "vehiculos" },
  { id: "optimizacion", label: "Optimización", mark: "OP", icon: "📊", icono: "optimizacion" },
  { id: "mapa-vivo", label: "Mapa en vivo", mark: "MV", icon: "📍", icono: "mapa" },
  { id: "reportes", label: "Reportes", mark: "RE", icon: "📈", icono: "reportes" },
  { id: "ia", label: "IA Asistente", mark: "IA", icon: "🤖", icono: "ia" },
  { id: "configuracion", label: "Configuración", mark: "CF", icon: "⚙️", icono: "configuracion" },
  { id: "usuarios", label: "Usuarios", mark: "US", icon: "🛡️", icono: "usuarios" },
  { id: "conductor-movil", label: "Vista Conductor", mark: "MO", icon: "📱", icono: "conductor-movil" },
];

const pageTitles: Record<Screen, string> = {
  dashboard: "Centro de operaciones",
  distribucion: "Centro de distribución",
  pedidos: "Pedidos",
  "pedido-detalle": "Detalle de pedido",
  clientes: "Clientes",
  rutas: "Rutas",
  "ruta-detalle": "Detalle de ruta",
  vehiculos: "Vehículos",
  conductores: "Conductores",
  optimizacion: "Planificación multi-entrega",
  ia: "IA Asistente",
  "mapa-vivo": "Mapa en vivo",
  reportes: "Reportes operativos",
  configuracion: "Configuración",
  "conductor-movil": "Mi ruta — Conductor",
  usuarios: "Usuarios y permisos",
};

const number = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });
function formatNumber(v: number | null | undefined) { return v == null ? "—" : number.format(v); }
function StatusPill({ status }: { status: string }) {
  const n = status.toLowerCase().replaceAll("_", "-");
  return <span className={`status status--${n}`}>{status.replaceAll("_", " ")}</span>;
}
function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><span className="empty-state__mark">OR</span><strong>{title}</strong><p>{detail}</p></div>;
}
function MetricCard({ label, value, detail, variant = "blue" }: { label: string; value: string | number; detail: string; variant?: "blue"|"green"|"purple"|"orange"|"cyan"|"coral" }) {
  const icons: Record<string, string> = { blue: "▤", green: "✓", purple: "⬢", orange: "◷", cyan: "▭", coral: "◐" };
  const spark = variant==="blue" ? "M0 14 L8 10 L16 12 L24 8 L32 11 L40 6 L48 9 L56 4 L64 7" : variant==="green" ? "M0 10 L12 12 L24 8 L36 11 L48 6 L60 9 L64 7" : variant==="purple" ? "M0 8 L10 4 L20 10 L30 6 L40 12 L50 7 L64 3" : variant==="orange" ? "M0 12 L10 9 L20 11 L30 7 L40 10 L50 6 L64 8" : variant==="cyan" ? "M0 11 L14 9 L28 12 L42 7 L56 9 L64 6" : "M0 13 L12 10 L24 12 L36 8 L48 11 L60 7 L64 9";
  const gradId = `g-${variant}-${label.replace(/\s/g,'')}`;
  return <article className={`metric-card metric-card--${variant}`}>
    <div className="metric-card__head"><div className="metric-card__icon">{icons[variant]||"•"}</div><span className="metric-card__label">{label}</span></div>
    <strong className="metric-card__value">{value}</strong><small className="metric-card__detail">{detail}</small>
    <div className="metric-card__spark"><svg viewBox="0 0 64 16" preserveAspectRatio="none">
      <defs><linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="currentColor" stopOpacity="0.28"/><stop offset="100%" stopColor="currentColor" stopOpacity="0"/></linearGradient></defs>
      <path d={`${spark} L64 16 L0 16 Z`} fill={`url(#${gradId})`} stroke="none" />
      <path d={spark} fill="none" stroke="currentColor" strokeWidth="1.3" opacity="0.85" strokeLinecap="round" strokeLinejoin="round" />
    </svg></div>
  </article>;
}
function CapacityBar({ label, used, capacity, unit }: { label: string; used: number; capacity: number; unit: string }) {
  const pct = capacity > 0 ? (used / capacity) * 100 : 0;
  const w = Math.min(pct, 100);
  return <div className="capacity"><div className="capacity__header"><span>{label}</span><strong>{formatNumber(used)} / {formatNumber(capacity)} {unit}</strong></div><div className="capacity__track"><span className={pct >= 90 ? "capacity__fill capacity__fill--warning" : "capacity__fill"} style={{ width: `${w}%` }} /></div><small>{formatNumber(pct)}% utilizado</small></div>;
}

function AIResult({ analysis }: { analysis: AIAnalysis }) {
  const riskLabels: Record<RiskLevel, string> = { BAJO: "Operación estable", MEDIO: "Requiere seguimiento", ALTO: "Atención operativa", CRITICO: "Intervención necesaria" };
  return <div className="ai-result">
    <div className={`risk-card risk-card--${analysis.nivel_riesgo.toLowerCase()}`}><div><span>Nivel de riesgo</span><strong>{analysis.nivel_riesgo}</strong></div><p>{riskLabels[analysis.nivel_riesgo]}</p></div>
    <p className="ai-summary">{analysis.resumen}</p>
    <div className="indicator-grid">
      <MetricCard label="Peso" value={`${formatNumber(analysis.indicadores.utilizacion_peso_pct)}%`} detail="Utilización" />
      <MetricCard label="Volumen" value={`${formatNumber(analysis.indicadores.utilizacion_volumen_pct)}%`} detail="Utilización" />
      <MetricCard label="Destinos" value={analysis.indicadores.cantidad_destinos} detail={`${analysis.indicadores.cantidad_pedidos} pedidos`} />
      <MetricCard label="Urgentes" value={analysis.indicadores.pedidos_urgentes} detail="Pedidos prioritarios" />
    </div>
    <div className="split-grid"><section><h4>Alertas</h4>{analysis.alertas.length ? <ul className="insight-list">{analysis.alertas.map(a => <li key={a.codigo} className={`insight insight--${a.severidad.toLowerCase()}`}><span>{a.severidad}</span><p>{a.mensaje}</p></li>)}</ul> : <p className="muted-copy">No se detectaron alertas.</p>}</section>
      <section><h4>Recomendaciones</h4><ol className="recommendations">{analysis.recomendaciones.map(r => <li key={r}>{r}</li>)}</ol></section></div>
    <footer className="engine-note">Motor determinista: {analysis.motor.replaceAll("_", " ")}</footer>
  </div>;
}

function PlanResult({ plan, nodes, onSave, saving }: { plan: PlanningResponse; nodes: CatalogNode[]; onSave: () => void; saving: boolean }) {
  const priorities = useMemo(() => plan.pedidos.reduce<Record<string, number>>((t, o) => { t[o.prioridad] = (t[o.prioridad] || 0) + 1; return t; }, {}), [plan]);
  const nodeMap = new Map(nodes.map(n => [n.id_nodo, n]));
  const originNode = nodeMap.get(plan.origen.id_nodo) || plan.origen as any;
  const mapPoints = [
    { id: plan.origen.id_nodo, nombre: plan.origen.nombre, lat: originNode.latitud, lng: originNode.longitud, tipo: plan.origen.tipo_nodo, orden: 0 },
    ...plan.orden_optimo.map((id, idx) => {
      const n = nodeMap.get(id);
      return { id, nombre: n?.nombre || `Nodo ${id}`, lat: n?.latitud || originNode.latitud + idx * 0.005, lng: n?.longitud || originNode.longitud + idx * 0.005, tipo: n?.tipo_nodo || "CLIENTE", orden: idx + 1 };
    })
  ];
  const routePoly = [{ id: "opt", points: plan.recorrido.map(id => {
    const n = nodeMap.get(id);
    return { id, nombre: n?.nombre || `Nodo ${id}`, lat: n?.latitud || 0, lng: n?.longitud || 0, tipo: n?.tipo_nodo || "INTERSECCION" };
  }).filter(p=>p.lat!==0), color: "#2563eb", label: "Óptima" }];

  return <div className="plan-result">
    <div className="result-head"><div><span className="eyebrow">Resultado calculado</span><h3>{plan.vehiculo.placa} · {plan.vehiculo.tipo_vehiculo}</h3></div><StatusPill status={plan.factible ? "FACTIBLE" : "NO_FACTIBLE"} /></div>
    <div className="capacity-grid"><CapacityBar label="Peso" used={plan.peso_total} capacity={plan.capacidad_peso} unit="kg" /><CapacityBar label="Volumen" used={plan.volumen_total} capacity={plan.capacidad_volumen} unit="m³" /></div>
    <div className="result-metrics"><div><span>Distancia total</span><strong>{formatNumber(plan.distancia_total_km)} km</strong></div><div><span>Algoritmo</span><strong>{plan.algoritmo.replaceAll("_", " + ")}</strong></div><div><span>Evaluaciones</span><strong>{formatNumber(plan.permutaciones_evaluadas)}</strong></div></div>
    <section className="sequence-section"><div className="section-heading"><div><span className="eyebrow">Secuencia comercial</span><h4>Orden óptimo</h4></div><span>{plan.regresar_origen ? "Regresa al origen" : "Finaliza en destino"}</span></div>
      <div className="node-flow"><span className="node-chip node-chip--origin">{plan.origen.nombre}</span>{plan.orden_optimo.map((nid, i) => <span className="node-pair" key={`${nid}-${i}`}><span className="flow-arrow">→</span><span className="node-chip">Nodo {nid} {nodeMap.get(nid)?.nombre ? `· ${nodeMap.get(nid)?.nombre}` : ""}</span></span>)}</div></section>
    <section className="sequence-section"><span className="eyebrow">Camino sobre el grafo</span><h4>Recorrido físico</h4><div className="route-line">{plan.recorrido.map((nid, i) => <span key={`${nid}-${i}`}><i />{nid}</span>)}</div></section>
    <div style={{ marginTop: 18 }}><LeafletMap points={mapPoints} routes={routePoly} height={320} /></div>
    <div className="split-grid"><section><h4>Pedidos incluidos</h4><div className="order-list">{plan.pedidos.map(o => <div key={o.id_pedido}><div><strong>{o.codigo}</strong><span>{o.destino.nombre}</span></div><StatusPill status={o.prioridad} /></div>)}</div></section>
      <section><h4>Distribución prioridades</h4><div className="priority-summary">{Object.entries(priorities).map(([p, t]) => <div key={p}><StatusPill status={p} /><strong>{t}</strong></div>)}</div></section></div>
    <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
      <button className="primary-button" onClick={onSave} disabled={saving}>{saving ? "Guardando ruta completa…" : "Guardar y asignar ruta"}</button>
      <span className="muted-copy" style={{ alignSelf: "center" }}>Guarda recorrido, pedidos y recursos en una sola operacion.</span>
    </div>
  </div>;
}

export default function App() {
  const [isAuth, setIsAuth] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [bootstrapPendiente, setBootstrapPendiente] = useState(false);
  const [avisoArranque, setAvisoArranque] = useState("");
  const [loginEnviando, setLoginEnviando] = useState(false);
  const [permisos, setPermisos] = useState<string[]>([]);
  const [usuarioActual, setUsuarioActual] = useState<UsuarioInfo | null>(null);
  const [loginUser, setLoginUser] = useState("");
  const [loginPass, setLoginPass] = useState("");
  const [screen, setScreen] = useState<Screen>("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [headerVisible, setHeaderVisible] = useState(true);
  const lastScrollYRef = useRef(0);
  const tickingRef = useRef(false);
  const headerVisibleRef = useRef(true);
  const [routes, setRoutes] = useState<RouteSummary[]>([]);
  const [routesLoading, setRoutesLoading] = useState(true);
  const [routesError, setRoutesError] = useState("");
  const [orders, setOrders] = useState<OrderCatalogItem[]>([]);
  const [vehicles, setVehicles] = useState<VehicleCatalogItem[]>([]);
  const [drivers, setDrivers] = useState<DriverCatalogItem[]>([]);
  const [nodes, setNodes] = useState<CatalogNode[]>([]);
  const [clientes, setClientes] = useState<ClienteItem[]>([]);
  const [catalogsLoading, setCatalogsLoading] = useState(true);
  const [catalogsError, setCatalogsError] = useState("");
  // optimization
  const [origin, setOrigin] = useState("");
  const [selectedOrderIds, setSelectedOrderIds] = useState<string[]>([]);
  const [vehicleId, setVehicleId] = useState("");
  const [conductorId, setConductorId] = useState("");
  const [returnToOrigin, setReturnToOrigin] = useState(false);
  const [plan, setPlan] = useState<PlanningResponse | null>(null);
  const [lastRequest, setLastRequest] = useState<PlanningRequest | null>(null);
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null);
  const [planning, setPlanning] = useState(false);
  const [savingPlan, setSavingPlan] = useState(false);
  const [planIdempotencyKey, setPlanIdempotencyKey] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");
  // pedidos filters
  const [searchPedido, setSearchPedido] = useState("");
  const [filterEstadoPed, setFilterEstadoPed] = useState("TODOS");
  const [selectedPedido, setSelectedPedido] = useState<OrderCatalogItem | null>(null);
  const [pedidoDetail, setPedidoDetail] = useState<OrderCatalogItem | null>(null);
  const [pedidoDetailLoading, setPedidoDetailLoading] = useState(false);
  const [pedidoRuta, setPedidoRuta] = useState<any>(null);
const [showCreatePedido, setShowCreatePedido] = useState(false);
const [showEditPedido, setShowEditPedido] = useState(false);
const [cancelacion, setCancelacion] = useState<{ tipo: "pedido" | "ruta"; estado: string } | null>(null);
const [procesandoCancelacion, setProcesandoCancelacion] = useState(false);
  const [editPedidoData, setEditPedidoData] = useState({ descripcion: "", peso: "", volumen: "", prioridad: "NORMAL" });
  const [newPedido, setNewPedido] = useState({ id_cliente: "", id_direccion: "", descripcion: "", peso: "", volumen: "", prioridad: "NORMAL" });
  // clientes
  const [searchCliente, setSearchCliente] = useState("");
  const [selectedCliente, setSelectedCliente] = useState<ClienteItem | null>(null);
  const [clienteDirecciones, setClienteDirecciones] = useState<DireccionItem[]>([]);
  const [clientePedidos, setClientePedidos] = useState<OrderCatalogItem[]>([]);
  // rutas detalle
  const [routeDetail, setRouteDetail] = useState<RouteDetail | null>(null);
  const [routeDetailLoading, setRouteDetailLoading] = useState(false);
  const [selectedConductor, setSelectedConductor] = useState<DriverCatalogItem | null>(null);
  const [selectedVehiculo, setSelectedVehiculo] = useState<VehicleCatalogItem | null>(null);
  // mapa vivo geoloc
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number; accuracy?: number } | null>(null);
  const [geoError, setGeoError] = useState("");
  const [geoLoading, setGeoLoading] = useState(false);
  const [focusTrigger, setFocusTrigger] = useState(0);
  const [fitTrigger, setFitTrigger] = useState(0);
  const [liveRouteDetails, setLiveRouteDetails] = useState<Record<number, RouteDetail>>({});
  const [liveLoading, setLiveLoading] = useState(false);
  const [tmcFocusTrigger, setTmcFocusTrigger] = useState(0);
  const [tmcEditMode, setTmcEditMode] = useState(false);
  const [pendingTmc, setPendingTmc] = useState<{ lat: number; lng: number } | null>(null);
  const [savingTmc, setSavingTmc] = useState(false);
  // grafo academico
  const [grafoData, setGrafoData] = useState<{ nodos: CatalogNode[]; conexiones: Array<{ origen: number; destino: number; distancia_km: number; bidireccional: boolean }> } | null>(null);
  const [bfsInicio, setBfsInicio] = useState("");
  const [bfsResult, setBfsResult] = useState<any>(null);
  const [dfsResult, setDfsResult] = useState<any>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  // report filters
  const [reporteDesde, setReporteDesde] = useState("");
  const [reporteHasta, setReporteHasta] = useState("");
  // ia chat
  const [chatMessages, setChatMessages] = useState<Array<{ role: "user" | "assistant"; text: string; ts: string }>>([
    { role: "assistant", text: "Hola, soy tu asistente logístico basado en reglas y análisis de datos. Consulta rutas, pedidos, vehículos, conductores, grafos y planificación.", ts: new Date().toLocaleTimeString() }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [lastIntent, setLastIntent] = useState<string | null>(null);

  async function loadRoutes() {
    setRoutesLoading(true); setRoutesError("");
    try { setRoutes(await api.listRoutes()); } catch (e) { setRoutesError(e instanceof Error ? e.message : "Error rutas"); } finally { setRoutesLoading(false); }
  }
  async function loadCatalogs() {
    setCatalogsLoading(true); setCatalogsError("");
    try {
      if (usuarioActual?.rol === "CONDUCTOR") {
        setOrders(await api.listOrders());
        setVehicles([]); setDrivers([]); setNodes([]); setClientes([]);
        return;
      }
      const [o, v, d, n, c] = await Promise.all([api.listOrders(), api.listVehicles(), api.listDrivers(), api.listNodes(), api.listClientes().catch(() => [] as ClienteItem[])]);
      setOrders(o); setVehicles(v); setDrivers(d); setNodes(n); setClientes(c as ClienteItem[]);
      const wh = (n as CatalogNode[]).find(x => x.tipo_nodo === "BODEGA");
      if (wh) setOrigin(s => s || String(wh.id_nodo));
      if (!bfsInicio && wh) setBfsInicio(String(wh.id_nodo));
    } catch (e) { setCatalogsError(e instanceof Error ? e.message : "Error catálogos"); } finally { setCatalogsLoading(false); }
  }
  async function loadGrafo() {
    setGraphLoading(true);
    try { const g = await api.getGrafo(); setGrafoData({ nodos: g.nodos as any, conexiones: g.conexiones }); } catch { /* ignore */ } finally { setGraphLoading(false); }
  }
  useEffect(() => { if (isAuth) { void loadRoutes(); void loadCatalogs(); void loadGrafo(); } }, [isAuth]);
  // Header superior: ocultar al bajar, mostrar al subir (scroll con rAF, sin renders innecesarios)
  useEffect(() => {
    if (!isAuth) return;
    lastScrollYRef.current = window.scrollY;
    headerVisibleRef.current = true;
    setHeaderVisible(true);
    const onScroll = () => {
      if (tickingRef.current) return;
      tickingRef.current = true;
      requestAnimationFrame(() => {
        const curr = window.scrollY;
        const delta = curr - lastScrollYRef.current;
        const atTop = curr <= 8;
        if (atTop) {
          if (!headerVisibleRef.current) {
            headerVisibleRef.current = true;
            setHeaderVisible(true);
          }
        } else if (Math.abs(delta) > 5) {
          if (delta > 0 && headerVisibleRef.current) {
            headerVisibleRef.current = false;
            setHeaderVisible(false);
          } else if (delta < 0 && !headerVisibleRef.current) {
            headerVisibleRef.current = true;
            setHeaderVisible(true);
          }
        }
        lastScrollYRef.current = curr;
        tickingRef.current = false;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [isAuth]);
  const activeRoutes = routes.filter(r => !["COMPLETADA", "CANCELADA"].includes(r.estado)).length;
  const completedRoutes = routes.filter(r => r.estado === "COMPLETADA").length;
  const pedidosHoy = orders.filter(o => o.fecha_solicitada && o.fecha_solicitada === new Date().toISOString().slice(0, 10)).length || orders.filter(o => o.estado === "PENDIENTE").length;
  const distanciaTotal = routes.reduce((s, r) => s + (r.distancia_total_km || 0), 0);
  const tiempoTotalMin = Math.round(distanciaTotal * 2.2); // estimación
  const tmcNode = nodes.find(n => n.nombre.includes("TMC")) || nodes.find(n => n.tipo_nodo === "BODEGA");
  const tmcLocation = tmcNode ? { lat: tmcNode.latitud, lng: tmcNode.longitud } : null;
  function handleTmcDrag(lat: number, lng: number) { setPendingTmc({ lat, lng }); }
  function handleMapClickForTmc(lat: number, lng: number) { if (tmcEditMode) setPendingTmc({ lat, lng }); }
  async function saveTmcLocation() {
    if (!pendingTmc) { setActionError("Mueve el marcador o haz clic en el mapa primero"); return; }
    setSavingTmc(true); setActionError("");
    try {
      const res = await api.updateTmcLocation(pendingTmc.lat, pendingTmc.lng);
      setActionSuccess(`Ubicación TMC guardada: ${res.latitud.toFixed(6)}, ${res.longitud.toFixed(6)} — ${res.recalculadas} aristas recalculadas (haversine)`);
      setPendingTmc(null); setTmcEditMode(false);
      void loadCatalogs(); void loadGrafo(); void loadRoutes();
    } catch (e) { setActionError(e instanceof Error ? e.message : "Error guardando TMC"); } finally { setSavingTmc(false); }
  }

  async function verificarArranque() {
    try {
      const estado = await authApi.estado();
      setBootstrapPendiente(!estado.propietario_creado);
    } catch {
      setBootstrapPendiente(false);
    }
  }

  async function cargarSesion() {
    const token = localStorage.getItem("or_token");
    if (!token) {
      setIsAuth(false);
      setPermisos([]);
      setUsuarioActual(null);
      await verificarArranque();
      setAuthLoading(false);
      return;
    }
    setAuthLoading(true);
    setAuthToken(token);
    try {
      const sesion = await authApi.session();
      setIsAuth(true);
      setBootstrapPendiente(false);
      setPermisos(sesion.permisos || []);
      setUsuarioActual(sesion.usuario);
      setAuthToken(token);
      if (sesion.usuario.rol === "OPERADOR") setScreen("distribucion");
      localStorage.setItem("or_usuario", sesion.usuario.correo);
      localStorage.setItem("or_rol", sesion.usuario.rol);
    } catch {      setIsAuth(false);
      setPermisos([]);
      setUsuarioActual(null);
      setAuthToken(null);
      localStorage.removeItem("or_token");
      localStorage.removeItem("or_usuario");
      localStorage.removeItem("or_rol");
      await verificarArranque();
    } finally {
      setAuthLoading(false);
    }
  }

  function alCrearPropietario(correo: string) {
    setBootstrapPendiente(false);
    setLoginUser(correo);
    setLoginPass("");
    setAvisoArranque("Cuenta propietaria creada. Inicia sesión con tu correo y contraseña.");
  }

  useEffect(() => {
    void cargarSesion();
  }, []);

  function selectScreen(next: Screen) {
    if (!puedeVerPantalla(permisos, next)) {
      setActionError("No tienes permisos para acceder a esta pantalla.");
      return;
    }
    setScreen(next);
    setSidebarOpen(false);
    setActionError("");
    setActionSuccess("");
    if (next !== "ruta-detalle") setRouteDetail(null);
  }
  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    if (loginEnviando) return;
    setActionError("");
    setLoginEnviando(true);
    try {
      const sesion = await authApi.login({
        correo: loginUser.trim().toLowerCase(),
        password: loginPass,
      });
      if (sesion.token) {
        localStorage.setItem("or_token", sesion.token);
      } else {
        localStorage.setItem("or_token", "");
      }
      setAuthToken(sesion.token || localStorage.getItem("or_token") || "");
      setIsAuth(true);
      setBootstrapPendiente(false);
      setAvisoArranque("");
      setPermisos(sesion.permisos || []);
      setUsuarioActual(sesion.usuario);
      if (sesion.usuario.rol === "OPERADOR") setScreen("distribucion");
      localStorage.setItem("or_usuario", sesion.usuario.correo);
      localStorage.setItem("or_rol", sesion.usuario.rol);
      setLoginPass("");
    } catch (err) {
      if (err instanceof ApiError) {
        setActionError(err.message);
      } else {
        setActionError("Credenciales invalidas.");
      }
    } finally {
      setLoginEnviando(false);
    }
  }
  function logout() {
    try {
      void authApi.logout().catch(() => undefined);
    } finally {
      setAuthToken(null);
      localStorage.removeItem("or_token");
      localStorage.removeItem("or_usuario");
      localStorage.removeItem("or_rol");
      setIsAuth(false);
      setLoginUser("");
      setLoginPass("");
      setPermisos([]);
      setUsuarioActual(null);
    }
  }

  // pedidos create
  async function submitCreatePedido(e: FormEvent) {
    e.preventDefault();
    setActionError(""); setActionSuccess("");
    try {
      const payload = {
        id_cliente: Number(newPedido.id_cliente),
        id_direccion_entrega: Number(newPedido.id_direccion),
        descripcion: newPedido.descripcion || null,
        peso_kg: Number(newPedido.peso),
        volumen_m3: Number(newPedido.volumen),
        prioridad: newPedido.prioridad,
      };
      await api.createOrder(payload);
      setShowCreatePedido(false);
      setNewPedido({ id_cliente: "", id_direccion: "", descripcion: "", peso: "", volumen: "", prioridad: "NORMAL" });
      setActionSuccess("Pedido creado correctamente.");
      void loadCatalogs();
    } catch (err) { setActionError(err instanceof Error ? err.message : "Error al crear pedido"); }
  }

  // optimizacion
  function parseRequest(): PlanningRequest {
    const po = Number(origin); const pv = Number(vehicleId); const pids = selectedOrderIds.map(Number);
    if (!Number.isInteger(po) || po <= 0) throw new Error("Origen inválido");
    if (!Number.isInteger(pv) || pv <= 0) throw new Error("Vehículo requerido");
    if (!pids.length) throw new Error("Selecciona al menos un pedido");
    if (new Set(pids).size !== pids.length) throw new Error("Pedidos duplicados");
    return { origen: po, pedidos: pids, id_vehiculo: pv, regresar_origen: returnToOrigin };
  }
  async function submitPlanning(e: FormEvent) {
    e.preventDefault(); setActionError(""); setPlan(null); setAnalysis(null);
    let req: PlanningRequest; try { req = parseRequest(); } catch (err) { setActionError(err instanceof Error ? err.message : "Error"); return; }
    setPlanning(true);
    try { const res = await api.planDeliveries(req); setPlan(res); setLastRequest(req); setPlanIdempotencyKey(crypto.randomUUID().replaceAll("-", "")); setActionSuccess("Planificación calculada con Dijkstra + TSP exacto."); } catch (err) { setActionError(err instanceof Error ? err.message : "No se pudo calcular"); } finally { setPlanning(false); }
  }
  async function requestAnalysis() {
    if (!lastRequest || !plan) return;
    setAnalyzing(true); setActionError("");
    try { setAnalysis(await api.analyzePlanning(lastRequest)); } catch (e) { setActionError(e instanceof Error ? e.message : "Error análisis"); } finally { setAnalyzing(false); }
  }
  async function savePlanAsRoute() {
    if (!plan || !lastRequest) return;
    setActionError(""); setActionSuccess("");
    if (!conductorId) { setActionError("Selecciona un conductor disponible antes de guardar."); return; }
    setSavingPlan(true);
    try {
      const ruta = await api.savePlannedRoute({
        ...lastRequest,
        id_conductor: Number(conductorId),
        clave_idempotencia: planIdempotencyKey || crypto.randomUUID().replaceAll("-", ""),
      });
      setActionSuccess(ruta.duplicada ? `La ruta ${ruta.codigo} ya había sido guardada; no se duplicó.` : `Ruta ${ruta.codigo} guardada con ${ruta.recorrido.length} puntos y ${ruta.pedidos.length} pedidos.`);
      await Promise.all([loadRoutes(), loadCatalogs()]);
    } catch (err) { setActionError(err instanceof Error ? err.message : "Error al guardar ruta"); }
    finally { setSavingPlan(false); }
  }

  async function openRouteDetail(id: number) {
    setRouteDetailLoading(true); selectScreen("ruta-detalle" as Screen);
    try { const det = await api.getRoute(id); setRouteDetail(det); } catch (e) { setActionError(e instanceof Error ? e.message : "Error detalle"); }
    finally { setRouteDetailLoading(false); }
  }
  async function openClienteDetail(c: ClienteItem) {
    setSelectedCliente(c);
    try {
      const [dirs, peds] = await Promise.all([api.getClienteDirecciones(c.id_cliente), api.getClientePedidos(c.id_cliente)]);
      setClienteDirecciones(dirs); setClientePedidos(peds as any);
    } catch { setClienteDirecciones([]); setClientePedidos([]); }
  }

  async function openPedidoDetail(id: number) {
    setPedidoDetailLoading(true); setActionError(""); setPedidoRuta(null);
    selectScreen("pedido-detalle");
    try {
      const det = await api.getOrder(id);
      setPedidoDetail(det);
      setEditPedidoData({ descripcion: det.descripcion || "", peso: String(det.peso_kg || ""), volumen: String(det.volumen_m3 || ""), prioridad: det.prioridad });
      try { const r = await api.getOrderRoute(id); setPedidoRuta(r); } catch { setPedidoRuta(null); }
    } catch (e) { setActionError(e instanceof Error ? e.message : "Error cargando pedido"); }
    finally { setPedidoDetailLoading(false); }
  }
  async function handleUpdatePedido(e: FormEvent) {
    e.preventDefault();
    if (!pedidoDetail) return;
    setActionError(""); setActionSuccess("");
    try {
      const updated = await api.updateOrder(pedidoDetail.id_pedido, {
        descripcion: editPedidoData.descripcion || null,
        peso_kg: editPedidoData.peso ? Number(editPedidoData.peso) : undefined,
        volumen_m3: editPedidoData.volumen ? Number(editPedidoData.volumen) : undefined,
        prioridad: editPedidoData.prioridad,
      });
      setPedidoDetail(updated);
      setShowEditPedido(false);
      setActionSuccess("Pedido actualizado correctamente");
      void loadCatalogs();
    } catch (err) { setActionError(err instanceof Error ? err.message : "Error al actualizar"); }
  }
  async function handleChangePedidoEstado(nuevo: string) {
    if (!pedidoDetail) return;
    if (nuevo === "CANCELADO") {
      setCancelacion({ tipo: "pedido", estado: nuevo });
      return;
    }
    setActionError("");
    try {
      const updated = await api.changeOrderState(pedidoDetail.id_pedido, nuevo);
      setPedidoDetail(updated);
      setActionSuccess(`Estado cambiado a ${nuevo}`);
      void loadCatalogs();
    } catch (err) { setActionError(err instanceof Error ? err.message : "Error cambiando estado"); }
  }

  async function confirmarCancelacionPedido(motivo: string) {
    if (!pedidoDetail || !cancelacion) return;
    setProcesandoCancelacion(true);
    setActionError("");
    try {
      const updated = await api.changeOrderState(pedidoDetail.id_pedido, cancelacion.estado, motivo);
      setPedidoDetail(updated);
      setActionSuccess(`Pedido ${cancelacion.estado.toLowerCase()} con motivo registrado en auditoria.`);
      setCancelacion(null);
      void loadCatalogs();
    } catch (err) { setActionError(err instanceof Error ? err.message : "Error cancelando el pedido"); }
    finally { setProcesandoCancelacion(false); }
  }

  async function confirmarCancelacionRuta(motivo: string) {
    if (!routeDetail || !cancelacion) return;
    setProcesandoCancelacion(true);
    setActionError("");
    try {
      await api.changeRouteState(routeDetail.id_ruta, cancelacion.estado, motivo);
      setActionSuccess(`Ruta ${cancelacion.estado.toLowerCase()} con motivo registrado en auditoria.`);
      setCancelacion(null);
      void openRouteDetail(routeDetail.id_ruta);
    } catch (err) { setActionError(err instanceof Error ? err.message : "Error cancelando la ruta"); }
    finally { setProcesandoCancelacion(false); }
  }

  function requestGeolocation(watch = false) {
    setGeoError(""); setGeoLoading(true);
    if (!navigator.geolocation) {
      setGeoError("Tu navegador no soporta geolocalización.");
      setGeoLoading(false);
      return;
    }
    const opts: PositionOptions = { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 };
    const onSuccess = (pos: GeolocationPosition) => {
      const { latitude, longitude, accuracy } = pos.coords;
      setUserLocation({ lat: latitude, lng: longitude, accuracy });
      setFocusTrigger(v => v + 1);
      setGeoLoading(false);
      setActionSuccess(`Ubicación obtenida: ${latitude.toFixed(5)}, ${longitude.toFixed(5)} ±${Math.round(accuracy)}m`);
    };
    const onError = (err: GeolocationPositionError) => {
      let msg = "";
      if (err.code === 1) msg = "Permiso de ubicación rechazado. Actívalo en el navegador para centrar el mapa.";
      else if (err.code === 2) msg = "Ubicación no disponible. Verifica GPS / conexión.";
      else if (err.code === 3) msg = "Tiempo agotado al obtener ubicación.";
      else msg = err.message;
      setGeoError(msg); setGeoLoading(false);
    };
    if (watch) navigator.geolocation.watchPosition(onSuccess, onError, opts);
    else navigator.geolocation.getCurrentPosition(onSuccess, onError, opts);
  }

  async function loadLiveRouteDetails(active: RouteSummary[]) {
    if (!active.length) { setLiveRouteDetails({}); return; }
    setLiveLoading(true);
    const entries = await Promise.all(active.slice(0, 4).map(async r => {
      try { const d = await api.getRoute(r.id_ruta); return [r.id_ruta, d] as const; } catch { return null; }
    }));
    const map: Record<number, RouteDetail> = {};
    entries.forEach(e => { if (e) map[e[0]] = e[1]; });
    setLiveRouteDetails(map);
    setLiveLoading(false);
  }

  // auto geoloc al entrar a mapa-vivo
  useEffect(() => {
    if (screen === "mapa-vivo" && !userLocation && !geoLoading) {
      requestGeolocation(false);
      const active = routes.filter(r => !["COMPLETADA", "CANCELADA"].includes(r.estado));
      if (active.length) void loadLiveRouteDetails(active);
    }
  }, [screen, routes.length]);

  async function runBFS() {
    if (!bfsInicio) { setActionError("Selecciona nodo inicial"); return; }
    setGraphLoading(true); setActionError("");
    try { const r = await api.bfs(Number(bfsInicio)); setBfsResult(r); setDfsResult(null); } catch (e) { setActionError(e instanceof Error ? e.message : "Error BFS"); } finally { setGraphLoading(false); }
  }
  async function runDFS() {
    if (!bfsInicio) { setActionError("Selecciona nodo inicial"); return; }
    setGraphLoading(true); setActionError("");
    try { const r = await api.dfs(Number(bfsInicio)); setDfsResult(r); setBfsResult(null); } catch (e) { setActionError(e instanceof Error ? e.message : "Error DFS"); } finally { setGraphLoading(false); }
  }

  // IA chat logic - mejorada con sinónimos, contexto y fuzzy
  function normalizeIA(s: string) {
    return s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();
  }
  function extractCodesIA(q: string) {
    const up = q.toUpperCase();
    const ped = up.match(/PED-[A-Z0-9-]+/);
    const rut = up.match(/RUT-[A-Z0-9-]+/);
    return { ped: ped?.[0] || null, rut: rut?.[0] || null };
  }
  function answerIA(question: string) {
    const raw = question;
    const q = normalizeIA(question);
    const codes = extractCodesIA(raw);
    // contexto follow-up corto
    if (lastIntent && q.length < 35) {
      if ((q.includes("mas corta") || q.includes("menor") || q.includes("corta")) && lastIntent === "RUTA_MAS_LARGA") {
        const sorted = [...routes].sort((a, b) => (a.distancia_total_km || 0) - (b.distancia_total_km || 0));
        if (!sorted.length) return "No hay rutas registradas aún.";
        const r = sorted[0];
        setLastIntent("RUTA_MAS_CORTA");
        return `La ruta más corta actualmente es ${r.codigo}, con una distancia de ${formatNumber(r.distancia_total_km)} km. Va de ${r.origen.nombre} a ${r.destino.nombre} y está en estado ${r.estado}.`;
      }
      if ((q.includes("mas larga") || q.includes("mayor") || q.includes("larga")) && lastIntent === "RUTA_MAS_CORTA") {
        const sorted = [...routes].sort((a, b) => (b.distancia_total_km || 0) - (a.distancia_total_km || 0));
        const r = sorted[sorted.length-1] || sorted[0];
        // actually longest is first when desc
        const longest = [...routes].sort((a,b)=>(b.distancia_total_km||0)-(a.distancia_total_km||0))[0];
        if (!longest) return "No hay rutas.";
        setLastIntent("RUTA_MAS_LARGA");
        return `La ruta más larga es ${longest.codigo}, con ${formatNumber(longest.distancia_total_km)} km de ${longest.origen.nombre} a ${longest.destino.nombre}, estado ${longest.estado}.`;
      }
      if (q.includes("menor") && lastIntent === "VEHICULO_MAYOR_CAP") {
        const sorted = [...vehicles].sort((a,b)=>(a.capacidad_kg||0)-(b.capacidad_kg||0));
        if (!sorted.length) return "No hay vehículos.";
        setLastIntent("VEHICULO_MENOR_CAP");
        return `El vehículo con menor capacidad es ${sorted[0].placa} (${sorted[0].tipo_vehiculo}) con ${formatNumber(sorted[0].capacidad_kg)} kg.`;
      }
      if (q.includes("mayor") && lastIntent === "VEHICULO_MENOR_CAP") {
        const sorted = [...vehicles].sort((a,b)=>(b.capacidad_kg||0)-(a.capacidad_kg||0));
        const v = sorted[sorted.length-1] || sorted[0];
        if (!v) return "No hay vehículos.";
        setLastIntent("VEHICULO_MAYOR_CAP");
        return `El vehículo con mayor capacidad es ${v.placa} con ${formatNumber(v.capacidad_kg)} kg.`;
      }
    }
    // códigos directos
    if (codes.ped) {
      const ped = orders.find(o => o.codigo.toUpperCase() === codes.ped);
      if (q.includes("estado")) {
        if (!ped) return `No encontré el pedido ${codes.ped}. Verifica el código.`;
        setLastIntent("ESTADO_PEDIDO");
        return `El pedido ${ped.codigo} está en estado ${ped.estado}, prioridad ${ped.prioridad}, destino ${ped.destino?.nombre || "sin nodo"}, peso ${formatNumber(ped.peso_kg)} kg.`;
      }
      if (q.includes("ruta") || q.includes("quien") || q.includes("tiene")) {
        // buscar ruta de pedido vía liveRouteDetails o routes
        let found: any = null;
        for (const [id, det] of Object.entries(liveRouteDetails)) {
          // liveRouteDetails doesn't have pedido mapping, fallback to buscar en rutas pedidas
        }
        // intentar buscar en rutasPedidos no disponible sin fetch, usar mensaje
        if (ped) {
          setLastIntent("RUTA_PEDIDO");
          return `El pedido ${ped.codigo} está destinado a ${ped.destino?.nombre || "sin nodo"} (${ped.destino?.id_nodo || "?"}). Para ver su ruta asignada, ve a Rutas y filtra por el pedido. Si fue incluido en la última planificación, aparece en el mapa de Optimización.`;
        }
      }
      if (ped) {
        setLastIntent("ESTADO_PEDIDO");
        return `Pedido ${ped.codigo}: cliente ${ped.id_cliente}, destino ${ped.destino?.nombre || "—"}, ${formatNumber(ped.peso_kg)} kg, ${ped.prioridad}, estado ${ped.estado}, fecha ${ped.fecha_solicitada || "—"}.`;
      }
    }
    if (codes.rut) {
      const r = routes.find(x => x.codigo.toUpperCase() === codes.rut);
      if (!r) return `No encontré la ruta ${codes.rut}.`;
      if (q.includes("quien") || q.includes("conduce") || q.includes("conductor")) {
        setLastIntent("CONDUCTOR_RUTA");
        return `La ruta ${r.codigo} la conduce ${r.conductor ? `${r.conductor.nombres} ${r.conductor.apellidos}` : "sin conductor asignado"}, vehículo ${r.vehiculo?.placa || "sin vehículo"}, estado ${r.estado}.`;
      }
      if (q.includes("vehiculo") || q.includes("placa")) {
        setLastIntent("VEHICULO_RUTA");
        return `La ruta ${r.codigo} usa el vehículo ${r.vehiculo?.placa || "sin asignar"}, conductor ${r.conductor ? `${r.conductor.nombres} ${r.conductor.apellidos}` : "—"}.`;
      }
      if (q.includes("cuanto") || q.includes("mide") || q.includes("distancia") || q.includes("km")) {
        setLastIntent("ESTADO_RUTA");
        return `La ruta ${r.codigo} mide ${formatNumber(r.distancia_total_km)} km, de ${r.origen.nombre} a ${r.destino.nombre}, estado ${r.estado}.`;
      }
      setLastIntent("ESTADO_RUTA");
      return `Ruta ${r.codigo}: ${r.origen.nombre} → ${r.destino.nombre}, ${formatNumber(r.distancia_total_km)} km, estado ${r.estado}, conductor ${r.conductor ? `${r.conductor.nombres} ${r.conductor.apellidos}` : "—"}, vehículo ${r.vehiculo?.placa || "—"}.`;
    }
    // intenciones por palabras clave
    const has = (...words: string[]) => words.some(w => q.includes(normalizeIA(w)));
    // RUTAS
    if (has("ruta mas larga", "mayor distancia", "recorre mas", "mas extensa", "mayor recorrido", "mas kilometros")) {
      const sorted = [...routes].sort((a,b)=>(b.distancia_total_km||0)-(a.distancia_total_km||0));
      if (!sorted.length) return "Aún no hay rutas registradas.";
      const r = sorted[0];
      const empates = sorted.filter(x => x.distancia_total_km === r.distancia_total_km);
      setLastIntent("RUTA_MAS_LARGA");
      if (empates.length>1) return `Hay ${empates.length} rutas empatadas con la mayor distancia (${formatNumber(r.distancia_total_km)} km): ${empates.map(x=>x.codigo).join(", ")}. La primera es ${r.codigo} de ${r.origen.nombre} a ${r.destino.nombre}, estado ${r.estado}.`;
      return `La ruta más larga actualmente es ${r.codigo}, con una distancia de ${formatNumber(r.distancia_total_km)} km. Va de ${r.origen.nombre} a ${r.destino.nombre} y está en estado ${r.estado}.`;
    }
    if (has("ruta mas corta", "menor distancia", "recorre menos", "menor recorrido", "mas corta", "y la mas corta", "y la corta")) {
      const sorted = [...routes].sort((a,b)=>(a.distancia_total_km||0)-(b.distancia_total_km||0));
      if (!sorted.length) return "No hay rutas.";
      const r = sorted[0];
      setLastIntent("RUTA_MAS_CORTA");
      return `La ruta más corta es ${r.codigo}, con ${formatNumber(r.distancia_total_km)} km, de ${r.origen.nombre} a ${r.destino.nombre}, estado ${r.estado}.`;
    }
    if (has("cantidad de rutas", "cuantas rutas", "total rutas", "numero de rutas")) {
      setLastIntent("CANTIDAD_RUTAS");
      return `Hay ${routes.length} rutas registradas. Activas: ${activeRoutes}, completadas: ${completedRoutes}, planificadas: ${routes.filter(r=>r.estado==="PLANIFICADA").length}.`;
    }
    if (has("rutas activas", "rutas en curso", "rutas vigentes")) {
      setLastIntent("RUTAS_ACTIVAS");
      const act = routes.filter(r=>!["COMPLETADA","CANCELADA"].includes(r.estado));
      return `Hay ${act.length} rutas activas: ${act.map(r=>`${r.codigo}(${r.estado})`).join(", ") || "ninguna"}.`;
    }
    if (has("rutas completadas", "rutas terminadas", "completadas")) {
      setLastIntent("RUTAS_COMPLETADAS");
      return `Rutas completadas: ${completedRoutes} de ${routes.length}.`;
    }
    if (has("ruta con mas paradas", "mas paradas", "con mas puntos", "mas entregas")) {
      // usar liveRouteDetails para paradas
      let max = { codigo: "", paradas: 0 };
      for (const r of routes) {
        const det = liveRouteDetails[r.id_ruta];
        const p = det ? det.puntos.length : 2;
        if (p > max.paradas) max = { codigo: r.codigo, paradas: p };
      }
      setLastIntent("RUTA_MAS_PARADAS");
      return max.codigo ? `La ruta con más paradas es ${max.codigo} con ${max.paradas} puntos.` : "No hay datos de paradas; abre detalle de ruta para ver.";
    }
    if (has("ruta con menos paradas", "menos paradas")) {
      let min = { codigo: "", paradas: 99 };
      for (const r of routes) {
        const det = liveRouteDetails[r.id_ruta];
        const p = det ? det.puntos.length : 2;
        if (p < min.paradas) min = { codigo: r.codigo, paradas: p };
      }
      setLastIntent("RUTA_MENOS_PARADAS");
      return min.codigo ? `La ruta con menos paradas es ${min.codigo} con ${min.paradas} puntos.` : "Sin datos.";
    }
    if (has("distancia promedio", "promedio distancia", "media distancia")) {
      const avg = routes.length ? distanciaTotal/routes.length : 0;
      setLastIntent("DISTANCIA_PROMEDIO");
      return `La distancia promedio de las ${routes.length} rutas es ${formatNumber(avg)} km. Total ${formatNumber(distanciaTotal)} km.`;
    }
    if (has("distancia total", "total distancia", "total kilometros")) {
      setLastIntent("DISTANCIA_TOTAL");
      return `La distancia total planificada es ${formatNumber(distanciaTotal)} km en ${routes.length} rutas.`;
    }
    // PEDIDOS
    if (has("total de pedidos", "cuantos pedidos", "cantidad de pedidos", "numero de pedidos") && !q.includes("pendiente") && !q.includes("entregado")) {
      setLastIntent("PEDIDOS_TOTAL");
      return `Hay ${orders.length} pedidos en total. Pendientes: ${orders.filter(o=>o.estado==="PENDIENTE").length}, entregados: ${orders.filter(o=>o.estado==="ENTREGADO").length}, en ruta: ${orders.filter(o=>o.estado==="EN_RUTA").length}.`;
    }
    if (has("pedidos pendientes", "cuantos faltan", "faltan por entregar", "sin entregar", "pendientes", "faltan")) {
      const pend = orders.filter(o=>o.estado==="PENDIENTE").length;
      setLastIntent("PEDIDOS_PENDIENTES");
      return `Hay ${pend} pedidos pendientes de ${orders.length} totales. Estados: ${[...new Set(orders.map(o=>o.estado))].join(", ")}.`;
    }
    if (has("pedidos entregados", "cuantos se entregaron", "completados", "terminadas", "entregados")) {
      const ent = orders.filter(o=>o.estado==="ENTREGADO").length;
      setLastIntent("PEDIDOS_ENTREGADOS");
      return `Se han entregado ${ent} pedidos de ${orders.length}.`;
    }
    if (has("pedidos cancelados", "cancelados")) {
      const can = orders.filter(o=>o.estado==="CANCELADO").length;
      setLastIntent("PEDIDOS_CANCELADOS");
      return `Hay ${can} pedidos cancelados.`;
    }
    if (has("pedidos alta", "alta prioridad", "prioritarios", "urgentes") && !q.includes("riesgo")) {
      const alta = orders.filter(o=>["ALTA","URGENTE"].includes(o.prioridad)).length;
      const urg = orders.filter(o=>o.prioridad==="URGENTE").length;
      setLastIntent("PEDIDOS_ALTA");
      return `Hay ${alta} pedidos con prioridad alta/urgente, de los cuales ${urg} son urgentes.`;
    }
    if (has("pedido mas pesado", "mas pesado", "mayor peso", "mas pesada")) {
      const sorted = [...orders].sort((a,b)=>(b.peso_kg||0)-(a.peso_kg||0));
      if (!sorted.length) return "No hay pedidos.";
      setLastIntent("PEDIDO_MAS_PESADO");
      return `El pedido más pesado es ${sorted[0].codigo} con ${formatNumber(sorted[0].peso_kg)} kg, destino ${sorted[0].destino?.nombre || "—"}, prioridad ${sorted[0].prioridad}.`;
    }
    if (has("pedido mas liviano", "mas ligero", "menor peso", "mas liviano")) {
      const sorted = [...orders].sort((a,b)=>(a.peso_kg||0)-(b.peso_kg||0));
      if (!sorted.length) return "No hay pedidos.";
      setLastIntent("PEDIDO_LIVIANO");
      return `El pedido más liviano es ${sorted[0].codigo} con ${formatNumber(sorted[0].peso_kg)} kg.`;
    }
    if (has("peso total pendiente", "peso pendiente", "total peso")) {
      const peso = orders.filter(o=>o.estado==="PENDIENTE").reduce((s,o)=>s+(o.peso_kg||0),0);
      setLastIntent("PESO_TOTAL");
      return `El peso total pendiente es ${formatNumber(peso)} kg en ${orders.filter(o=>o.estado==="PENDIENTE").length} pedidos.`;
    }
    if (has("pedidos de cliente") || (q.includes("cliente") && (q.includes("cuantos")||q.includes("tiene")))) {
      // buscar cliente por nombre aproximado
      const nombres = ["cliente a","cliente b","cliente c","cliente d","cliente e","cliente f","cliente g","cliente h"];
      const found = nombres.find(n=>q.includes(normalizeIA(n)));
      if (found) {
        const nodeName = found.split(" ")[1].toUpperCase();
        const count = orders.filter(o=>o.destino?.nombre.toLowerCase().includes("cliente "+nodeName.toLowerCase())).length;
        setLastIntent("PEDIDOS_CLIENTE");
        return `El ${found} tiene ${count} pedidos asociados.`;
      }
    }
    // CLIENTES
    if (has("cuantos clientes", "total clientes", "cantidad clientes")) {
      setLastIntent("CLIENTES_TOTAL");
      return `Hay ${clientes.length} clientes registrados.`;
    }
    if (has("cliente con mas pedidos", "cliente mas pedidos", "mayor cliente")) {
      const map: Record<number, number> = {};
      orders.forEach(o=> map[o.id_cliente]=(map[o.id_cliente]||0)+1);
      const maxId = Object.entries(map).sort((a,b)=>b[1]-a[1])[0];
      if (!maxId) return "No hay pedidos para determinar cliente.";
      const cli = clientes.find(c=>c.id_cliente===Number(maxId[0]));
      setLastIntent("CLIENTE_MAS_PEDIDOS");
      return `El cliente con más pedidos es ${cli ? (cli.razon_social || `${cli.nombres} ${cli.apellidos}`) : "ID "+maxId[0]} con ${maxId[1]} pedidos.`;
    }
    // CONDUCTORES
    if (has("total conductores", "cuantos conductores")) {
      setLastIntent("CONDUCTORES_TOTAL");
      return `Hay ${drivers.length} conductores. Disponibles: ${drivers.filter(d=>d.disponible).length}, ocupados: ${drivers.filter(d=>!d.disponible).length}.`;
    }
    if (has("conductores disponibles", "disponibles")) {
      const disp = drivers.filter(d=>d.disponible).length;
      setLastIntent("CONDUCTORES_DISP");
      return `Hay ${disp} conductores disponibles de ${drivers.length}.`;
    }
    if (has("conductor con mas entregas", "quien tiene mas entregas", "conductor con mas rutas", "quien tiene mas trabajo", "mas entregas")) {
      // contar rutas por conductor
      const cnt: Record<number, number> = {};
      routes.forEach(r=> { if(r.conductor) cnt[r.conductor.id_conductor]=(cnt[r.conductor.id_conductor]||0)+1; });
      const top = Object.entries(cnt).sort((a,b)=>b[1]-a[1])[0];
      if (!top) return "No hay rutas asignadas a conductores.";
      const drv = drivers.find(d=>d.id_conductor===Number(top[0]));
      setLastIntent("CONDUCTOR_MAS");
      return `El conductor con más entregas es ${drv ? `${drv.nombres} ${drv.apellidos}` : "ID "+top[0]} con ${top[1]} rutas.`;
    }
    // VEHICULOS
    if (has("total vehiculos", "cuantos vehiculos")) {
      setLastIntent("VEHICULOS_TOTAL");
      return `Hay ${vehicles.length} vehículos. Disponibles: ${vehicles.filter(v=>v.disponible).length}, en ruta: ${vehicles.filter(v=>v.estado==="EN_RUTA").length}.`;
    }
    if (has("vehiculo con mayor capacidad", "cual carga mas", "camion con mayor capacidad", "vehiculo mas grande", "mayor capacidad")) {
      const sorted = [...vehicles].sort((a,b)=>(b.capacidad_kg||0)-(a.capacidad_kg||0));
      if (!sorted.length) return "No hay vehículos.";
      setLastIntent("VEHICULO_MAYOR_CAP");
      return `El vehículo con mayor capacidad es ${sorted[0].placa} (${sorted[0].tipo_vehiculo}) con ${formatNumber(sorted[0].capacidad_kg)} kg / ${formatNumber(sorted[0].capacidad_volumen_m3)} m³.`;
    }
    if (has("vehiculo con menor capacidad", "menor capacidad", "mas pequeño")) {
      const sorted = [...vehicles].sort((a,b)=>(a.capacidad_kg||0)-(b.capacidad_kg||0));
      if (!sorted.length) return "No hay vehículos.";
      setLastIntent("VEHICULO_MENOR_CAP");
      return `El vehículo con menor capacidad es ${sorted[0].placa} con ${formatNumber(sorted[0].capacidad_kg)} kg.`;
    }
    if (has("vehiculo mas cargado", "mayor carga", "mas cargado", "lleva mas carga")) {
      setLastIntent("VEHICULO_CARGADO");
      return "La carga asignada se ve en la planificación: después de optimizar, el panel muestra peso/volumen utilizados por vehículo. Sin planificación activa no puedo calcular carga actual.";
    }
    if (has("disponibles") && q.includes("vehiculo")) {
      setLastIntent("VEHICULOS_DISP");
      return `Vehículos disponibles: ${vehicles.filter(v=>v.disponible).length} de ${vehicles.length}.`;
    }
    if (has("cual es la bodega", "donde esta la bodega", "bodega principal", "desde donde salen las rutas", "cual es el nodo origen", "donde inicia la planificacion", "nodo origen", "matriz central", "tmc tramaco")) {
      setLastIntent("BODEGA");
      return `La bodega principal configurada es TMC Grupo Tramaco - Matriz Quito, ubicada en Manuel Najas OE1-346 y Joaquín Mancheno, sector Carcelén Industrial, Quito. ${tmcLocation ? `Coordenadas ${tmcLocation.lat.toFixed(5)}, ${tmcLocation.lng.toFixed(5)}.` : ""} Desde allí salen todas las rutas de distribución.`;
    }
    // GRAFOS
    if (has("que es un nodo", "qué es un nodo", "nodo en optiroute", "que representa un nodo")) {
      setLastIntent("GRAFO_NODO");
      return "Un nodo es un vértice del grafo: Bodega, Cliente o Intersección, con lat/lng. Hay "+ (grafoData?.nodos.length || nodes.length) +" nodos activos en Quito.";
    }
    if (has("que es una arista", "qué es una arista", "que representa una arista", "que es arista")) {
      setLastIntent("GRAFO_ARISTA");
      return "Una arista es la conexión entre dos nodos, con peso distancia_km. El grafo tiene "+ (grafoData?.conexiones.length || 17) +" aristas bidireccionales.";
    }
    if (has("que representa el peso", "que es el peso", "peso de la arista")) {
      setLastIntent("GRAFO_PESO");
      return "El peso es la distancia en km entre nodos. Dijkstra y TSP minimizan la suma de pesos.";
    }
    if (has("cuantos nodos", "cantidad de nodos", "nodos tiene el grafo")) {
      const n = grafoData?.nodos.length || nodes.length;
      setLastIntent("G_NODOS");
      return `El grafo tiene ${n} nodos activos.`;
    }
    if (has("cuantas conexiones", "cuantas aristas", "conexiones hay", "aristas hay")) {
      const c = grafoData?.conexiones.length || 17;
      setLastIntent("G_CONEX");
      return `El grafo tiene ${c} conexiones/aristas activas.`;
    }
    if (has("que algoritmo", "que hace dijkstra", "explica dijkstra", "que es dijkstra")) {
      setLastIntent("DIJKSTRA");
      return "Dijkstra calcula el camino mínimo entre dos nodos usando cola de prioridad, complejidad O((V+E)logV). En OptiRoute se usa para cada segmento de la ruta.";
    }
    if (has("que hace bfs", "explica bfs", "que es bfs")) {
      setLastIntent("BFS");
      return "BFS (Breadth First) recorre el grafo por niveles usando cola. Demo: BFS desde Bodega → [1,2,3,17,21,22,4,18,5,19,20]. Útil para conectividad.";
    }
    if (has("que hace dfs", "explica dfs", "que es dfs")) {
      setLastIntent("DFS");
      return "DFS (Depth First) explora en profundidad recursivamente. Demo: DFS desde Bodega → [1,2,3,4,5,19,22,20,18,21,17].";
    }
    if (has("que hace tsp", "explica tsp", "que es tsp", "tsp multi", "multi entrega")) {
      setLastIntent("TSP");
      return "TSP (Viajante) busca el orden óptimo de visita probando todas las permutaciones (exacto, O(n!) ≤8 destinos). En OptiRoute, TSP + Dijkstra = distancia mínima total.";
    }
    if (has("diferencia entre dijkstra y tsp", "diferencia dijkstra")) {
      setLastIntent("DIF");
      return "Dijkstra: origen→destino, un camino mínimo. TSP: origen→varios destinos, orden óptimo minimizando suma de Dijkstras. Dijkstra es subrutina de TSP.";
    }
    // RESUMEN
    if (has("resumen del dia", "resumen del dia", "resumen", "hoy")) {
      const pend = orders.filter(o=>o.estado==="PENDIENTE").length;
      const ent = orders.filter(o=>o.estado==="ENTREGADO").length;
      setLastIntent("RESUMEN");
      return `Hoy existen ${orders.length} pedidos: ${pend} pendientes, ${ent} entregados, ${activeRoutes} rutas activas, ${vehicles.filter(v=>v.disponible).length} vehículos disponibles y ${drivers.filter(d=>d.disponible).length} conductores disponibles. Distancia total planificada ${formatNumber(distanciaTotal)} km.`;
    }
    // RIESGO
    if (has("rutas con riesgo", "hay riesgo", "riesgo", "vehiculos sobrecargados", "pedidos urgentes", "que debo atender")) {
      if (analysis) { setLastIntent("RIESGO"); return `${analysis.resumen} Recomendaciones: ${analysis.recomendaciones.slice(0,2).join(" · ")}`; }
      const urg = orders.filter(o=>o.prioridad==="URGENTE").length;
      setLastIntent("RIESGO");
      return `Según reglas logísticas, hay ${urg} pedidos urgentes. ${urg? "Atiende urgentes primero." : "Sin urgentes."} Verifica capacidad antes de planificar.`;
    }
    // FUZZY fallback para errores ortográficos leves (ej: larrga, pendietes, mayro)
    function lev(a: string, b: string) {
      const m = a.length, n = b.length;
      const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
      for (let i = 0; i <= m; i++) dp[i][0] = i;
      for (let j = 0; j <= n; j++) dp[0][j] = j;
      for (let i = 1; i <= m; i++) for (let j = 1; j <= n; j++) dp[i][j] = Math.min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+(a[i-1]===b[j-1]?0:1));
      return dp[m][n];
    }
    function fuzzyHas(q: string, keyword: string) {
      const qw = q.split(" "); const kw = keyword.split(" ");
      for (const k of kw) if (k.length>3) {
        for (const w of qw) if (Math.abs(w.length-k.length)<=2 && lev(w,k)<=2) return true;
      }
      return false;
    }
    const fuzzyIntents: Array<{k: string, fn: ()=>string}> = [
      {k:"ruta mas larga", fn:()=>{ const s=[...routes].sort((a,b)=>(b.distancia_total_km||0)-(a.distancia_total_km||0))[0]; return s?`La ruta más larga es ${s.codigo} con ${formatNumber(s.distancia_total_km)} km.`:"No hay rutas."; }},
      {k:"ruta mas corta", fn:()=>{ const s=[...routes].sort((a,b)=>(a.distancia_total_km||0)-(b.distancia_total_km||0))[0]; return s?`La ruta más corta es ${s.codigo} con ${formatNumber(s.distancia_total_km)} km.`:"No hay rutas."; }},
      {k:"pedidos pendientes", fn:()=>`Hay ${orders.filter(o=>o.estado==="PENDIENTE").length} pedidos pendientes.`},
      {k:"vehiculo mayor capacidad", fn:()=>{ const s=[...vehicles].sort((a,b)=>(b.capacidad_kg||0)-(a.capacidad_kg||0))[0]; return s?`Vehículo mayor capacidad: ${s.placa} ${formatNumber(s.capacidad_kg)} kg`:"No hay vehículos."; }},
    ];
    for (const {k, fn} of fuzzyIntents) if (fuzzyHas(q,k)) { setLastIntent(k.toUpperCase().replace(/ /g,"_")); return fn(); }
    // si no entendió, ofrecer ayuda contextual según lastIntent
    if (lastIntent) {
      return `No pude identificar exactamente la consulta. Como venías preguntando por ${lastIntent.toLowerCase().replace("_"," ")}, puedes preguntar por ejemplo: "¿cuál es la ruta más corta?", "¿cuántos pedidos pendientes hay?", "¿qué vehículo tiene mayor capacidad?"`;
    }
    return "No pude identificar exactamente la consulta. Puedes preguntarme, por ejemplo: ¿Cuál es la ruta más corta?, ¿Cuántos pedidos pendientes hay?, ¿Qué conductor tiene más entregas?, ¿Qué vehículo tiene mayor capacidad?, ¿Cuántos nodos tiene el grafo?";
  }
  async function sendChat(e: FormEvent) {
    e.preventDefault();
    if (!chatInput.trim()) return;
    const q = chatInput.trim();
    const ts = new Date().toLocaleTimeString();
    setChatMessages(m => [...m, { role: "user", text: q, ts }]);
    setChatInput(""); setChatLoading(true);
    setTimeout(() => {
      const ans = answerIA(q);
      setChatMessages(m => [...m, { role: "assistant", text: ans, ts: new Date().toLocaleTimeString() }]);
      setChatLoading(false);
    }, 500);
  }

  if (authLoading) {
    return <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "linear-gradient(135deg,#0a1931 0%,#123a7a 55%,#2563eb 100%)" }}>
      <div className="loading-panel" style={{ background: "#fff", padding: 24 }}>
        <span /><strong>Cargando sesion</strong>
      </div>
    </div>;
  }

  if (!isAuth) {
    if (bootstrapPendiente) {
      return <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "linear-gradient(135deg,#0a1931 0%,#123a7a 55%,#2563eb 100%)", padding: 20 }}>
        <BootstrapPanel onCreado={alCrearPropietario} />
      </div>;
    }
    return <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "linear-gradient(135deg,#0a1931 0%,#123a7a 55%,#2563eb 100%)", padding: 20 }}>
      <form onSubmit={handleLogin} className="panel" style={{ width: "100%", maxWidth: 420, borderRadius: 16 }}>
        <div style={{ textAlign: "center", marginBottom: 18 }}><span style={{ display: "inline-grid", placeItems: "center", width: 52, height: 52, borderRadius: 14, background: "linear-gradient(135deg,#2563eb,#38bdf8)", color: "#fff", fontWeight: 800, boxShadow: "0 4px 16px rgba(37,99,235,0.3)" }}>OR</span><h2 style={{ margin: "12px 0 4px" }}>OptiRoute</h2><p className="muted-copy">Optimización de Rutas</p></div>
        <label><span>Usuario (correo)</span><input value={loginUser} onChange={e => setLoginUser(e.target.value)} placeholder="correo@optiroute.test" required /></label>
        <label><span>Contraseña</span><input type="password" value={loginPass} onChange={e => setLoginPass(e.target.value)} placeholder="Contraseña" required /></label>
        {avisoArranque && <div className="inline-success"><span>{avisoArranque}</span></div>}
        {actionError && <div className="inline-error"><span>{actionError}</span></div>}
        <button className="primary-button primary-button--full" type="submit" disabled={loginEnviando}>{loginEnviando ? "Ingresando…" : "Ingresar"}</button>
      </form>
    </div>;
  }

  // filtered orders
  const filteredOrders = orders.filter(o => {
    const mSearch = searchPedido ? (o.codigo.toLowerCase().includes(searchPedido.toLowerCase()) || o.descripcion?.toLowerCase().includes(searchPedido.toLowerCase()) || o.destino?.nombre.toLowerCase().includes(searchPedido.toLowerCase())) : true;
    const mEst = filterEstadoPed === "TODOS" ? true : o.estado === filterEstadoPed;
    return mSearch && mEst;
  });
  const filteredClientes = clientes.filter(c => {
    if (!searchCliente) return true;
    const t = searchCliente.toLowerCase();
    return (c.nombres?.toLowerCase().includes(t) || c.apellidos?.toLowerCase().includes(t) || c.razon_social?.toLowerCase().includes(t) || c.identificacion?.toLowerCase().includes(t) || c.correo?.toLowerCase().includes(t));
  });

  // dashboard maps
  const dashboardPoints = nodes.map(n => ({ id: n.id_nodo, nombre: n.nombre, lat: n.latitud, lng: n.longitud, tipo: n.tipo_nodo }));
  const dashboardRoutes = routes.filter(r => !["COMPLETADA", "CANCELADA"].includes(r.estado)).slice(0, 3).map((r, idx) => {
    const colors = ["#2563eb", "#f59e0b", "#8b5cf6"];
    // we don't have puntos, approximate with origen/destino
    const oNode = nodes.find(n => n.id_nodo === r.origen.id_nodo);
    const dNode = nodes.find(n => n.id_nodo === r.destino.id_nodo);
    const pts = [];
    if (oNode) pts.push({ id: oNode.id_nodo, nombre: oNode.nombre, lat: oNode.latitud, lng: oNode.longitud, tipo: oNode.tipo_nodo });
    if (dNode) pts.push({ id: dNode.id_nodo, nombre: dNode.nombre, lat: dNode.latitud, lng: dNode.longitud, tipo: dNode.tipo_nodo });
    return { id: r.codigo, points: pts, color: colors[idx % colors.length], label: r.codigo };
  });

  let content: React.ReactNode = null;

  if (screen === "dashboard" && usuarioActual) {
    content = <ProfileDashboard
      usuario={usuarioActual}
      rutas={routes}
      pedidos={orders}
      vehiculos={vehicles}
      conductores={drivers}
      permisos={permisos}
      cargando={routesLoading || catalogsLoading}
      onNavigate={selectScreen}
    />;
  } else if (false) {
    const recentRoutes = [...routes].sort((a,b)=> new Date(b.creado_en).getTime() - new Date(a.creado_en).getTime()).slice(0,5);
    function hace(dateStr: string){
      const diff = Date.now() - new Date(dateStr).getTime();
      const h = Math.floor(diff/3600000);
      if(h<1) return "Hace minutos";
      if(h===1) return "Hace 1 h";
      if(h<24) return `Hace ${h} h`;
      const d = Math.floor(h/24);
      if(d===1) return "Hace 1 día";
      return `Hace ${d} días`;
    }
    function dotColor(estado: string){
      if(["ASIGNADA","PLANIFICADA"].includes(estado)) return "activity-dot--blue";
      if(estado==="COMPLETADA") return "activity-dot--green";
      if(estado==="EN_RUTA") return "activity-dot--orange";
      if(estado==="CANCELADA") return "activity-dot--coral";
      return "activity-dot--blue";
    }
    content = <>
      <section className="hero-panel">
        <div className="hero-left">
          <span className="eyebrow">OPTIMIZACIÓN DE RUTAS</span>
          <h2>Planifica entregas con el<br/><span>grafo logístico real.</span></h2>
          <p className="hero-sub">Dijkstra + TSP exacto + análisis determinista. Datos reales de PostgreSQL.</p>
          <div className="hero-concepts">
            <span><i>⚡</i> Rutas más eficientes</span>
            <span><i>⬡</i> Menor costo operativo</span>
            <span><i>↗</i> Decisiones basadas en datos</span>
          </div>
        </div>
        <div className="hero-right">
          <div className="hero-image" aria-hidden />
          <div className="hero-geometric" aria-hidden />
          <button className="hero-cta" onClick={() => selectScreen("optimizacion")}>Crear planificación <span>→</span></button>
          <div className="hero-location">
            <span className="pin">📍</span>
            <div><strong>Quito</strong><br/><small>Conectando destinos<br/>de forma inteligente</small></div>
          </div>
        </div>
      </section>

      <section className="metrics-grid">
        <MetricCard label="Pedidos hoy" value={catalogsLoading ? "…" : pedidosHoy} detail="Pendientes / solicitados" variant="blue" />
        <MetricCard label="Entregas completadas" value={completedRoutes} detail="Rutas completadas" variant="green" />
        <MetricCard label="Distancia total" value={`${formatNumber(distanciaTotal)} km`} detail="Suma de rutas" variant="purple" />
        <MetricCard label="Tiempo total" value={`${tiempoTotalMin} min`} detail="Estimado 2.2 min/km" variant="orange" />
        <MetricCard label="Vehículos" value={catalogsLoading ? "…" : vehicles.length} detail="Flota activa" variant="cyan" />
        <MetricCard label="Conductores" value={catalogsLoading ? "…" : drivers.length} detail="Disponibles" variant="coral" />
      </section>

      <section className="dashboard-grid">
        <div className="panel" style={{ padding: 14 }}>
          <div className="panel__heading" style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <i style={{ width: 32, height: 32, borderRadius: 8, background: "#eff6ff", color: "#2563eb", display: "grid", placeItems: "center", fontSize: 14, border: "1px solid #dbeafe" }}>🗺</i>
              <div><small className="eyebrow" style={{ color: "#64748b", textTransform: "none", letterSpacing: 0, fontWeight: 600, fontSize: 11 }}>Mapa principal</small><h3 style={{ margin: 0, fontSize: 16 }}>Rutas activas</h3></div>
            </div>
            <button className="link-view" onClick={() => selectScreen("mapa-vivo")}>Ver todas →</button>
          </div>
          <div style={{ position: "relative", borderRadius: 12, overflow: "hidden", border: "1px solid #e2e8f0" }}>
            {nodes.length ? <LeafletMap points={dashboardPoints} routes={dashboardRoutes} height={360} /> : <EmptyState title="Sin nodos" detail="Carga el grafo" />}
            <div className="map-legend">
              <div className="map-legend__row"><span className="map-legend__line" /> Rutas activas</div>
              <div className="map-legend__row"><span className="map-legend__dot map-legend__dot--tmc" /> TMC Matriz</div>
              <div className="map-legend__row"><span className="map-legend__dot map-legend__dot--client" /> Clientes</div>
            </div>
          </div>
        </div>

        <div className="panel" style={{ padding: 14 }}>
          <div className="panel__heading" style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <i style={{ width: 32, height: 32, borderRadius: 8, background: "#eff6ff", color: "#2563eb", display: "grid", placeItems: "center", fontSize: 15, border: "1px solid #dbeafe" }}>◷</i>
              <div><h3 style={{ margin: 0, fontSize: 14 }}>Actividad reciente</h3><small className="muted-copy" style={{ fontSize: 11 }}>Últimas rutas y pedidos</small></div>
            </div>
            <button className="link-view" onClick={() => selectScreen("rutas")}>Ver todas →</button>
          </div>
          {routesLoading ? <div className="loading-panel" style={{ minHeight: 120 }}><span /><strong>Cargando</strong></div> : routesError ? <div className="inline-error"><span>{routesError}</span></div> : recentRoutes.length===0 ? <EmptyState title="Sin actividad" detail="Crea una planificación y guárdala." /> :
            <div className="activity-list">
              {recentRoutes.map(r => (
                <div key={r.id_ruta} className="activity-item">
                  <span className={`activity-dot ${dotColor(r.estado)}`} />
                  <div className="activity-meta">
                    <strong>{r.codigo}</strong>
                    <small>{r.origen.nombre} → {r.destino.nombre.includes("Cliente") ? r.destino.nombre.replace("Cliente","Cliente ") : r.destino.nombre}</small>
                  </div>
                  <div className="activity-km">
                    <strong>{formatNumber(r.distancia_total_km)} km</strong>
                    <small>{hace(r.creado_en)}</small>
                  </div>
                  <span className={`status activity-badge status--${r.estado.toLowerCase().replaceAll("_","-")}`}>{r.estado}</span>
                </div>
              ))}
            </div>
          }
          <button className="quiet-button" style={{ width: "100%", marginTop: 10, background: "#f8fafc", borderColor: "#e2e8f0", color: "#475569", fontSize: 12 }} onClick={() => selectScreen("rutas")}>Ver historial completo</button>
        </div>
      </section>
    </>;
  } else if (screen === "pedidos") {
    content = <div className="panel">
      <div className="panel__heading"><div><span className="eyebrow">Catálogo operativo</span><h3>Pedidos</h3></div>{tienePermiso(permisos, "pedidos:crear") ? <button className="primary-button" onClick={() => setShowCreatePedido(true)}>+ Nuevo pedido</button> : <small className="muted-copy">Solo lectura: tu perfil no crea pedidos.</small>}</div>
      <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
        <input placeholder="Buscar código, destino, descripción" value={searchPedido} onChange={e => setSearchPedido(e.target.value)} style={{ flex: 1, minWidth: 220 }} />
        <select value={filterEstadoPed} onChange={e => setFilterEstadoPed(e.target.value)}><option value="TODOS">Todos los estados</option><option>PENDIENTE</option><option>PLANIFICADO</option><option>EN_RUTA</option><option>ENTREGADO</option><option>CANCELADO</option></select>
        <button className="quiet-button" onClick={() => void loadCatalogs()}>Actualizar</button>
      </div>
      {actionSuccess && <div style={{ padding: 10, background: "#e5f4e9", borderRadius: 8, marginBottom: 10 }}>{actionSuccess}</div>}
      {actionError && <div className="inline-error"><span>{actionError}</span></div>}
      {catalogsLoading ? <div className="loading-panel"><span /><strong>Cargando pedidos</strong></div> : filteredOrders.length === 0 ? <EmptyState title="No hay pedidos" detail="Crea un pedido o ajusta filtros." /> :
        <div className="table-scroll"><table><thead><tr><th>Código</th><th>Cliente</th><th>Destino</th><th>Carga</th><th>Prioridad</th><th>Estado</th><th>Acción</th></tr></thead><tbody>
          {filteredOrders.map(o => <tr key={o.id_pedido}><td><strong>{o.codigo}</strong><br /><small>{o.descripcion || "—"}</small></td><td>{o.id_cliente}</td><td>{o.destino?.nombre || "Sin nodo"}</td><td>{formatNumber(o.peso_kg)} kg · {formatNumber(o.volumen_m3)} m³</td><td><StatusPill status={o.prioridad} /></td><td><StatusPill status={o.estado} /></td><td><button className="quiet-button" onClick={() => void openPedidoDetail(o.id_pedido)}>Ver</button></td></tr>)}
        </tbody></table></div>}
      {showCreatePedido && <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "grid", placeItems: "center", zIndex: 50, padding: 16 }}><form onSubmit={submitCreatePedido} className="panel" style={{ width: "100%", maxWidth: 520 }}>
        <h3>Nuevo pedido</h3>
        <label><span>Cliente ID</span><select value={newPedido.id_cliente} onChange={e => setNewPedido({ ...newPedido, id_cliente: e.target.value })} required>{['', ...clientes.map(c => String(c.id_cliente))].map(v => v === "" ? <option key="" value="">Selecciona cliente</option> : <option key={v} value={v}>{v} · {clientes.find(c => String(c.id_cliente) === v)?.nombres} {clientes.find(c => String(c.id_cliente) === v)?.apellidos || clientes.find(c => String(c.id_cliente) === v)?.razon_social}</option>)}</select></label>
        <label><span>Dirección ID</span><input value={newPedido.id_direccion} onChange={e => setNewPedido({ ...newPedido, id_direccion: e.target.value })} placeholder="ID dirección (ver Clientes)" required /></label>
        <label><span>Descripción</span><input value={newPedido.descripcion} onChange={e => setNewPedido({ ...newPedido, descripcion: e.target.value })} placeholder="Insumos, referencia..." /></label>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}><label><span>Peso kg</span><input type="number" step="0.01" value={newPedido.peso} onChange={e => setNewPedido({ ...newPedido, peso: e.target.value })} required /></label><label><span>Volumen m³</span><input type="number" step="0.001" value={newPedido.volumen} onChange={e => setNewPedido({ ...newPedido, volumen: e.target.value })} required /></label></div>
        <label><span>Prioridad</span><select value={newPedido.prioridad} onChange={e => setNewPedido({ ...newPedido, prioridad: e.target.value })}><option>BAJA</option><option>NORMAL</option><option>ALTA</option><option>URGENTE</option></select></label>
        <div style={{ display: "flex", gap: 10, marginTop: 12 }}><button className="primary-button" type="submit">Crear</button><button type="button" className="quiet-button" onClick={() => setShowCreatePedido(false)}>Cancelar</button></div>
      </form></div>}
    </div>;
  } else if (screen === "pedido-detalle") {
    content = pedidoDetailLoading ? <div className="loading-panel"><span /><strong>Cargando pedido...</strong></div> : !pedidoDetail ? <EmptyState title="Pedido no encontrado" detail="Vuelve a Pedidos." /> :
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
          <div><span className="eyebrow">Pedido {pedidoDetail.codigo}</span><h2 style={{ margin: "4px 0" }}><StatusPill status={pedidoDetail.estado} /> <StatusPill status={pedidoDetail.prioridad} /></h2></div>
          <button className="quiet-button" onClick={() => selectScreen("pedidos")}>← Volver a Pedidos</button>
        </div>
        <div className="split-grid" style={{ marginTop: 16 }}>
          <div><h4>Datos del pedido</h4>
            <p><strong>Código:</strong> {pedidoDetail.codigo}</p>
            <p><strong>Cliente ID:</strong> {pedidoDetail.id_cliente} {clientes.find(c=>c.id_cliente===pedidoDetail.id_cliente)?.nombres ? `· ${clientes.find(c=>c.id_cliente===pedidoDetail.id_cliente)?.nombres} ${clientes.find(c=>c.id_cliente===pedidoDetail.id_cliente)?.apellidos}` : clientes.find(c=>c.id_cliente===pedidoDetail.id_cliente)?.razon_social || ""}</p>
            <p><strong>Dirección ID:</strong> {pedidoDetail.id_direccion_entrega}</p>
            <p><strong>Descripción:</strong> {pedidoDetail.descripcion || "—"}</p>
            <p><strong>Peso:</strong> {formatNumber(pedidoDetail.peso_kg)} kg</p>
            <p><strong>Volumen:</strong> {formatNumber(pedidoDetail.volumen_m3)} m³</p>
            <p><strong>Prioridad:</strong> <StatusPill status={pedidoDetail.prioridad} /></p>
            <p><strong>Estado:</strong> <StatusPill status={pedidoDetail.estado} /></p>
            <p><strong>Fecha solicitada:</strong> {pedidoDetail.fecha_solicitada || "—"}</p>
            <p><strong>Creado:</strong> {new Date(pedidoDetail.creado_en).toLocaleString()}</p>
          </div>
          <div><h4>Destino y logística</h4>
            <p><strong>Destino:</strong> {pedidoDetail.destino?.nombre || "Sin nodo"} {pedidoDetail.destino ? `· ${pedidoDetail.destino.tipo_nodo}` : ""}</p>
            <p><strong>Coordenadas:</strong> {pedidoDetail.destino ? `${pedidoDetail.destino.latitud}, ${pedidoDetail.destino.longitud}` : "—"}</p>
            <p><strong>Referencia dirección:</strong> {pedidoDetail.destino?.nombre || "—"}</p>
            <p><strong>Entrega estado:</strong> {pedidoDetail.estado_entrega ? <StatusPill status={pedidoDetail.estado_entrega} /> : "—"}</p>
            {pedidoDetail.destino && <div style={{ marginTop: 10 }}><LeafletMap points={[{ id: pedidoDetail.destino.id_nodo, nombre: pedidoDetail.destino.nombre, lat: pedidoDetail.destino.latitud, lng: pedidoDetail.destino.longitud, tipo: pedidoDetail.destino.tipo_nodo, orden: 1 }]} routes={[]} height={220} /></div>}
            {pedidoRuta ? <div style={{ marginTop: 10, padding: 10, background: "#f8faf8", borderRadius: 8 }}><strong>Ruta asignada:</strong> {pedidoRuta.codigo} · <StatusPill status={pedidoRuta.estado} /><br/><small>Vehículo {pedidoRuta.vehiculo?.placa || "—"} · Conductor {pedidoRuta.conductor ? `${pedidoRuta.conductor.nombres} ${pedidoRuta.conductor.apellidos}` : "—"} · {formatNumber(pedidoRuta.distancia_km)} km</small><br/><button className="quiet-button" style={{ marginTop: 6 }} onClick={() => void openRouteDetail(pedidoRuta.id_ruta)}>Ver ruta</button></div> : <p className="muted-copy">Sin ruta asignada aún.</p>}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
          {tienePermiso(permisos, "pedidos:editar") && <button className="secondary-button" onClick={() => setShowEditPedido(true)}>Editar pedido</button>}
          {estadosPedidoEditables(permisos).length > 0 && <select value={pedidoDetail.estado} onChange={e => void handleChangePedidoEstado(e.target.value)} style={{ maxWidth: 180 }}>
            {estadosPedidoEditables(permisos).map(estado => <option key={estado} value={estado}>{estado}</option>)}
          </select>}
          <button className="quiet-button" onClick={() => { selectScreen("mapa-vivo"); setTimeout(()=> { if(pedidoDetail.destino) { setUserLocation({ lat: pedidoDetail.destino!.latitud, lng: pedidoDetail.destino!.longitud }); setFocusTrigger(v=>v+1); } }, 300); }}>Ver en mapa</button>
          {pedidoRuta && <button className="primary-button" onClick={() => void openRouteDetail(pedidoRuta.id_ruta)}>Ver ruta</button>}
          <button className="quiet-button" onClick={() => selectScreen("pedidos")}>Volver</button>
        </div>
        {actionSuccess && <div style={{ marginTop: 10, padding: 8, background: "#e5f4e9", borderRadius: 8 }}>{actionSuccess}</div>}
        {actionError && <div className="inline-error" style={{ marginTop: 10 }}><span>{actionError}</span></div>}
        {showEditPedido && <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "grid", placeItems: "center", zIndex: 60, padding: 16 }}><form onSubmit={handleUpdatePedido} className="panel" style={{ width: "100%", maxWidth: 500 }}>
          <h3>Editar {pedidoDetail.codigo}</h3>
          <label><span>Descripción</span><input value={editPedidoData.descripcion} onChange={e=>setEditPedidoData({...editPedidoData, descripcion: e.target.value})} /></label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}><label><span>Peso kg</span><input type="number" step="0.01" value={editPedidoData.peso} onChange={e=>setEditPedidoData({...editPedidoData, peso: e.target.value})} /></label><label><span>Volumen m³</span><input type="number" step="0.001" value={editPedidoData.volumen} onChange={e=>setEditPedidoData({...editPedidoData, volumen: e.target.value})} /></label></div>
          <label><span>Prioridad</span><select value={editPedidoData.prioridad} onChange={e=>setEditPedidoData({...editPedidoData, prioridad: e.target.value})}><option>BAJA</option><option>NORMAL</option><option>ALTA</option><option>URGENTE</option></select></label>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}><button className="primary-button" type="submit">Guardar</button><button type="button" className="quiet-button" onClick={()=>setShowEditPedido(false)}>Cancelar</button></div>
        </form></div>}
      </div>;
  } else if (screen === "clientes") {
    content = <div className="panel"><div className="panel__heading"><div><span className="eyebrow">Catálogo</span><h3>Clientes</h3></div><button className="quiet-button" onClick={() => void loadCatalogs()}>Actualizar</button></div>
      <input placeholder="Buscar cliente, identificación, correo..." value={searchCliente} onChange={e => setSearchCliente(e.target.value)} style={{ width: "100%", marginBottom: 12 }} />
      {catalogsLoading ? <div className="loading-panel"><span /><strong>Cargando clientes</strong></div> : filteredClientes.length === 0 ? <EmptyState title="No hay clientes" detail="Clientes en operaciones.clientes" /> :
        <div className="table-scroll"><table><thead><tr><th>Cliente</th><th>Identificación</th><th>Contacto</th><th>Tipo</th><th>Acción</th></tr></thead><tbody>{filteredClientes.map(c => <tr key={c.id_cliente}><td><strong>{c.razon_social || `${c.nombres} ${c.apellidos}`}</strong><br /><small>ID {c.id_cliente}</small></td><td>{c.identificacion || "—"}</td><td>{c.correo || "—"}<br /><small>{c.telefono || ""}</small></td><td><StatusPill status={c.tipo_cliente} /></td><td><button className="quiet-button" onClick={() => void openClienteDetail(c)}>Ver</button></td></tr>)}</tbody></table></div>}
      {selectedCliente && <div className="panel" style={{ marginTop: 14, background: "#f8faf8" }}><h4>{selectedCliente.razon_social || `${selectedCliente.nombres} ${selectedCliente.apellidos}`} <StatusPill status={selectedCliente.activo ? "ACTIVO" : "INACTIVO"} /></h4>
        <div className="split-grid"><section><h4>Direcciones</h4>{clienteDirecciones.length === 0 ? <p className="muted-copy">Sin direcciones</p> : clienteDirecciones.map(d => <div key={d.id_direccion} style={{ padding: 10, border: "1px solid #e5eae7", borderRadius: 8, marginBottom: 6 }}><strong>{d.etiqueta}</strong> · {d.direccion_texto}<br /><small>{d.ciudad} · {d.latitud},{d.longitud} {d.nodo ? `· Nodo ${d.nodo.nombre}` : ""}</small></div>)}</section><section><h4>Pedidos relacionados</h4>{clientePedidos.length === 0 ? <p className="muted-copy">Sin pedidos</p> : clientePedidos.slice(0, 5).map(p => <div key={p.id_pedido} style={{ padding: 8, border: "1px solid #e5eae7", borderRadius: 8, marginBottom: 6, display: "flex", justifyContent: "space-between" }}><span><strong>{p.codigo}</strong><br /><small>{p.descripcion || ""}</small></span><StatusPill status={p.estado} /></div>)}</section></div><button className="quiet-button" onClick={() => setSelectedCliente(null)}>Cerrar</button></div>}
    </div>;
  } else if (screen === "rutas") {
    content = <section className="panel"><div className="panel__heading"><div><span className="eyebrow">Consulta operativa</span><h3>Rutas registradas</h3></div><div style={{ display: "flex", gap: 8 }}><button className="quiet-button" onClick={() => void loadRoutes()}>Actualizar</button>{tienePermiso(permisos, "rutas:planificar") && <button className="primary-button" onClick={() => selectScreen("optimizacion")}>Optimizar nueva</button>}</div></div>
      {routesLoading ? <div className="loading-panel"><span /><strong>Cargando rutas</strong></div> : routesError ? <div className="inline-error"><span>{routesError}</span></div> : routes.length === 0 ? <EmptyState title="Sin rutas" detail="Crea una planificación y guárdala como ruta." /> :
        <div className="table-scroll"><table><thead><tr><th>Código</th><th>Trayecto</th><th>Estado</th><th>Paradas / Distancia</th><th>Conductor / Vehículo</th><th>Acción</th></tr></thead><tbody>{routes.map(r => <tr key={r.id_ruta}><td><strong>{r.codigo}</strong><br /><small>{new Date(r.creado_en).toLocaleDateString()}</small></td><td>{r.origen.nombre} <span className="arrow">→</span> {r.destino.nombre}</td><td><StatusPill status={r.estado} /></td><td>{formatNumber(r.distancia_total_km)} km</td><td>{r.conductor ? `${r.conductor.nombres} ${r.conductor.apellidos}` : "Sin conductor"}<br /><small>{r.vehiculo?.placa || "Sin vehículo"}</small></td><td><button className="quiet-button" onClick={() => void openRouteDetail(r.id_ruta)}>Ver detalle</button></td></tr>)}</tbody></table></div>}
    </section>;
  } else if (screen === "ruta-detalle") {
    content = routeDetailLoading ? <div className="loading-panel"><span /><strong>Cargando ruta</strong></div> : !routeDetail ? <EmptyState title="No se encontró la ruta" detail="Selecciona una ruta de la lista." /> :
      <div>
        <div className="panel"><div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}><div><span className="eyebrow">Ruta {routeDetail.codigo}</span><h2 style={{ margin: "4px 0" }}>Estado: <StatusPill status={routeDetail.estado} /></h2><p className="muted-copy">{routeDetail.origen.nombre} → {routeDetail.destino.nombre} · {formatNumber(routeDetail.distancia_total_km)} km · {routeDetail.vehiculo?.placa || "Sin vehículo"} · {routeDetail.conductor ? `${routeDetail.conductor.nombres} ${routeDetail.conductor.apellidos}` : "Sin conductor"}</p></div><button className="quiet-button" onClick={() => selectScreen("rutas")}>← Volver</button></div>
          <div className="split-grid" style={{ marginTop: 16 }}><div>
            <LeafletMap points={routeDetail.puntos.map((p, idx) => ({ id: p.id_nodo, nombre: p.nombre, lat: p.latitud, lng: p.longitud, tipo: p.tipo_nodo, orden: p.orden }))} routes={[{ id: routeDetail.codigo, points: routeDetail.puntos.map(p => ({ id: p.id_nodo, nombre: p.nombre, lat: p.latitud, lng: p.longitud, tipo: p.tipo_nodo })), color: "#2563eb", label: routeDetail.codigo }]} height={420} />
            <div className="split-grid" style={{ marginTop: 12 }}><MetricCard label="Paradas" value={routeDetail.puntos.length} detail="Puntos de la ruta" /><MetricCard label="Distancia" value={`${formatNumber(routeDetail.distancia_total_km)} km`} detail="Total" /><MetricCard label="Progreso" value={routeDetail.estado === "COMPLETADA" ? "100%" : routeDetail.estado === "EN_RUTA" ? "60%" : routeDetail.estado === "ASIGNADA" ? "30%" : "10%"} detail={routeDetail.estado} /></div>
          </div>
            <div>
              <div className="panel" style={{ padding: 14 }}><h4>Paradas de la ruta</h4><div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 10 }}>{routeDetail.puntos.map(p => <div key={p.orden} style={{ padding: 10, border: "1px solid #e5eae7", borderRadius: 9, display: "flex", gap: 10 }}><span style={{ width: 28, height: 28, borderRadius: "50%", background: p.orden === 1 ? "#0a1931" : "#2563eb", color: "white", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 11 }}>{p.orden}</span><div><strong>{p.nombre}</strong><br /><small>{p.tipo_nodo} · {p.latitud},{p.longitud} · acum {formatNumber(p.distancia_acumulada_km)} km</small></div></div>)}</div></div>
              <div className="panel" style={{ padding: 14, marginTop: 12 }}><h4>Resumen</h4><p><strong>Conductor:</strong> {routeDetail.conductor ? `${routeDetail.conductor.nombres} ${routeDetail.conductor.apellidos} (${routeDetail.conductor.numero_licencia})` : "—"}</p><p><strong>Vehículo:</strong> {routeDetail.vehiculo ? `${routeDetail.vehiculo.placa} ${routeDetail.vehiculo.marca || ""} ${routeDetail.vehiculo.modelo || ""}` : "—"}</p><p><strong>Fecha planificada:</strong> {routeDetail.fecha_planificada ? new Date(routeDetail.fecha_planificada).toLocaleString() : "—"}</p><p><strong>Creada:</strong> {new Date(routeDetail.creado_en).toLocaleString()}</p><div style={{ display: "flex", gap: 8, marginTop: 10 }}>{puedeCambiarEstadoRuta(permisos) && estadosRutaEditables(permisos).map(estado => estado === "CANCELADA" ? <button key={estado} className="secondary-button" onClick={() => setCancelacion({ tipo: "ruta", estado })}>Cancelar ruta</button> : <button key={estado} className={estado === "COMPLETADA" ? "primary-button" : "secondary-button"} onClick={async () => { try { await api.changeRouteState(routeDetail.id_ruta, estado); setActionSuccess(`Ruta ${estado.toLowerCase()}`); void openRouteDetail(routeDetail.id_ruta); } catch (e) { setActionError(e instanceof Error ? e.message : "Error"); } }}>{estado === "EN_RUTA" ? "Iniciar" : estado === "COMPLETADA" ? "Completar" : `Marcar ${estado}`}</button>)}</div>{actionError && <div className="inline-error" style={{ marginTop: 8 }}><span>{actionError}</span></div>}{actionSuccess && <div style={{ marginTop: 8, padding: 8, background: "#e5f4e9", borderRadius: 8 }}>{actionSuccess}</div>}</div>
            </div></div>
          <RouteIncidentForm idRuta={routeDetail.id_ruta} />
        </div>
      </div>;
  } else if (screen === "conductores") {
    content = <section className="panel"><div className="panel__heading"><div><span className="eyebrow">Catálogo</span><h3>Conductores</h3></div><button className="quiet-button" onClick={() => void loadCatalogs()}>Actualizar</button></div>
      {catalogsLoading ? <div className="loading-panel"><span /><strong>Cargando</strong></div> : <div className="table-scroll"><table><thead><tr><th>Conductor</th><th>Licencia</th><th>Teléfono</th><th>Activo</th><th>Disponibilidad</th><th>Ruta asignada</th><th>Acción</th></tr></thead><tbody>{drivers.map(d => {
        const ruta = routes.find(r => r.conductor?.id_conductor === d.id_conductor && !["COMPLETADA", "CANCELADA"].includes(r.estado));
        return <tr key={d.id_conductor}><td><strong>{d.nombres} {d.apellidos}</strong></td><td>{d.numero_licencia}{d.tipo_licencia ? ` · ${d.tipo_licencia}` : ""}</td><td>{d.telefono || "—"}</td><td><StatusPill status={d.activo ? "ACTIVO" : "INACTIVO"} /></td><td><StatusPill status={d.disponible ? "DISPONIBLE" : "NO DISPONIBLE"} /></td><td>{ruta ? <span style={{ color: "#2563eb", fontWeight: 700 }}>{ruta.codigo}</span> : "—"}</td><td><button className="quiet-button" onClick={() => setSelectedConductor(d)}>Ver</button></td></tr>;
      })}</tbody></table></div>}
      {selectedConductor && <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "grid", placeItems: "center", zIndex: 50, padding: 16 }}><div className="panel" style={{ width: "100%", maxWidth: 520 }}>
        <h3>{selectedConductor.nombres} {selectedConductor.apellidos}</h3>
        <p><strong>Licencia:</strong> {selectedConductor.numero_licencia} {selectedConductor.tipo_licencia ? `· ${selectedConductor.tipo_licencia}` : ""}</p>
        <p><strong>Teléfono:</strong> {selectedConductor.telefono || "—"}</p>
        <p><strong>Activo:</strong> <StatusPill status={selectedConductor.activo ? "ACTIVO" : "INACTIVO"} /> <strong>Disponible:</strong> <StatusPill status={selectedConductor.disponible ? "DISPONIBLE" : "NO DISPONIBLE"} /></p>
        {(() => { const ruta = routes.find(r => r.conductor?.id_conductor === selectedConductor.id_conductor && !["COMPLETADA","CANCELADA"].includes(r.estado)); return ruta ? <div style={{ padding: 10, background: "#f8faf8", borderRadius: 8, marginTop: 8 }}><strong>Ruta asignada:</strong> {ruta.codigo} · {ruta.origen.nombre} → {ruta.destino.nombre} · <StatusPill status={ruta.estado} /><br/><button className="quiet-button" style={{ marginTop: 6 }} onClick={() => { setSelectedConductor(null); void openRouteDetail(ruta.id_ruta); }}>Ver ruta</button></div> : <p className="muted-copy">Sin ruta asignada</p>; })()}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}><button className="quiet-button" onClick={() => setSelectedConductor(null)}>Cerrar</button></div>
      </div></div>}
    </section>;
  } else if (screen === "vehiculos") {
    content = <section className="panel"><div className="panel__heading"><div><span className="eyebrow">Catálogo</span><h3>Vehículos</h3></div><button className="quiet-button" onClick={() => void loadCatalogs()}>Actualizar</button></div>
      {catalogsLoading ? <div className="loading-panel"><span /><strong>Cargando</strong></div> : <div className="table-scroll"><table><thead><tr><th>Placa</th><th>Tipo</th><th>Capacidad</th><th>Estado</th><th>Disponibilidad</th><th>Ruta</th><th>Acción</th></tr></thead><tbody>{vehicles.map(v => {
        const ruta = routes.find(r => r.vehiculo?.id_vehiculo === v.id_vehiculo && !["COMPLETADA", "CANCELADA"].includes(r.estado));
        return <tr key={v.id_vehiculo}><td><strong>{v.placa}</strong><br /><small>{[v.marca, v.modelo].filter(Boolean).join(" ")}</small></td><td>{v.tipo_vehiculo}</td><td>{formatNumber(v.capacidad_kg)} kg · {formatNumber(v.capacidad_volumen_m3)} m³</td><td><StatusPill status={v.estado} /></td><td><StatusPill status={v.activo && v.disponible ? "DISPONIBLE" : "NO DISPONIBLE"} /></td><td>{ruta ? ruta.codigo : "—"}</td><td><button className="quiet-button" onClick={() => setSelectedVehiculo(v)}>Ver</button></td></tr>;
      })}</tbody></table></div>}
      {selectedVehiculo && <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "grid", placeItems: "center", zIndex: 50, padding: 16 }}><div className="panel" style={{ width: "100%", maxWidth: 520 }}>
        <h3>{selectedVehiculo.placa} · {selectedVehiculo.tipo_vehiculo}</h3>
        <p><strong>Marca/Modelo:</strong> {[selectedVehiculo.marca, selectedVehiculo.modelo].filter(Boolean).join(" ") || "—"} {selectedVehiculo.anio ? `· ${selectedVehiculo.anio}` : ""}</p>
        <p><strong>Capacidad:</strong> {formatNumber(selectedVehiculo.capacidad_kg)} kg · {formatNumber(selectedVehiculo.capacidad_volumen_m3)} m³</p>
        <p><strong>Estado:</strong> <StatusPill status={selectedVehiculo.estado} /> <strong>Disponible:</strong> <StatusPill status={selectedVehiculo.activo && selectedVehiculo.disponible ? "DISPONIBLE" : "NO DISPONIBLE"} /></p>
        {(() => { const ruta = routes.find(r => r.vehiculo?.id_vehiculo === selectedVehiculo.id_vehiculo && !["COMPLETADA","CANCELADA"].includes(r.estado)); return ruta ? <div style={{ padding: 10, background: "#f8faf8", borderRadius: 8, marginTop: 8 }}><strong>Ruta:</strong> {ruta.codigo} · {ruta.origen.nombre} → {ruta.destino.nombre} <StatusPill status={ruta.estado} /><br/><button className="quiet-button" style={{ marginTop: 6 }} onClick={() => { setSelectedVehiculo(null); void openRouteDetail(ruta.id_ruta); }}>Ver ruta</button></div> : <p className="muted-copy">Sin ruta asignada</p>; })()}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}><button className="quiet-button" onClick={() => setSelectedVehiculo(null)}>Cerrar</button></div>
      </div></div>}
    </section>;
  } else if (screen === "optimizacion") {
    const selectedPedidosLive = orders.filter(o => selectedOrderIds.includes(String(o.id_pedido)));
    const pesoLive = selectedPedidosLive.reduce((s, o) => s + (o.peso_kg || 0), 0);
    const volLive = selectedPedidosLive.reduce((s, o) => s + (o.volumen_m3 || 0), 0);
    const vehLive = vehicles.find(v => String(v.id_vehiculo) === vehicleId);
    const capPeso = vehLive?.capacidad_kg || 0;
    const capVol = vehLive?.capacidad_volumen_m3 || 0;
    const excedePeso = capPeso > 0 && pesoLive > capPeso;
    const excedeVol = capVol > 0 && volLive > capVol;
    const graphEdges: Array<{ origen: number; destino: number; distancia_km: number }> = grafoData?.conexiones || [];
    const graphPoints = (grafoData?.nodos || nodes).map(n => ({ id: n.id_nodo, nombre: n.nombre, lat: n.latitud, lng: n.longitud, tipo: n.tipo_nodo }));
    const graphRouteEdges = graphEdges.slice(0, 30).map(c => {
      const o = (grafoData?.nodos || nodes).find(n => n.id_nodo === c.origen);
      const d = (grafoData?.nodos || nodes).find(n => n.id_nodo === c.destino);
      if (!o || !d) return null;
      return { id: `e-${c.origen}-${c.destino}`, points: [{ id: o.id_nodo, nombre: o.nombre, lat: o.latitud, lng: o.longitud, tipo: o.tipo_nodo }, { id: d.id_nodo, nombre: d.nombre, lat: d.latitud, lng: d.longitud, tipo: d.tipo_nodo }], color: "#d1d5db", label: `${c.distancia_km}km` };
    }).filter(Boolean) as any[];
    content = <div className="optimization-layout">
      <section className="panel form-panel"><div className="panel__heading"><div><span className="eyebrow">Nueva operación</span><h3>Datos de planificación</h3></div><span className="step-badge">01</span></div>
        <form onSubmit={submitPlanning}>
          <label><span>Nodo origen (Bodega)</span><select value={origin} onChange={e => setOrigin(e.target.value)} required>{nodes.filter(n => n.tipo_nodo === "BODEGA").map(n => <option key={n.id_nodo} value={n.id_nodo}>{n.nombre}</option>)}</select><small>Bodega = origen del grafo, nodo 1 en demo</small></label>
          <label><span>Pedidos pendientes ({orders.filter(o=>o.estado==="PENDIENTE").length})</span><select multiple value={selectedOrderIds} onChange={e => setSelectedOrderIds(Array.from(e.target.selectedOptions, o => o.value))} style={{ minHeight: 140 }}>{orders.filter(o => o.estado === "PENDIENTE" && o.destino?.activo).map(o => <option key={o.id_pedido} value={o.id_pedido}>{o.codigo} · {o.destino?.nombre} · {formatNumber(o.peso_kg)}kg · {formatNumber(o.volumen_m3)}m³ · {o.prioridad}</option>)}</select><small>Ctrl+click hasta 8 destinos únicos (TSP exacto)</small></label>
          <label><span>Vehículo</span><select value={vehicleId} onChange={e => setVehicleId(e.target.value)} required><option value="">Selecciona vehículo</option>{vehicles.map(v => <option key={v.id_vehiculo} value={v.id_vehiculo} disabled={!v.disponible}>{v.placa} · {v.tipo_vehiculo} · {formatNumber(v.capacidad_kg)}kg / {formatNumber(v.capacidad_volumen_m3)}m³ · {v.estado}</option>)}</select></label>
          <label><span>Conductor (requerido para guardar)</span><select value={conductorId} onChange={e => setConductorId(e.target.value)} required><option value="">Selecciona conductor</option>{drivers.map(d => <option key={d.id_conductor} value={d.id_conductor} disabled={!d.disponible}>{d.nombres} {d.apellidos} · {d.numero_licencia} {d.disponible?"· DISP":""}</option>)}</select></label>
          <label className="checkbox-field"><input type="checkbox" checked={returnToOrigin} onChange={e => setReturnToOrigin(e.target.checked)} /><span><strong>Regresar al origen</strong><small>Incluye retorno en distancia/tiempo</small></span></label>
          {/* restricciones live */}
          <div style={{ padding: 12, border: excedePeso||excedeVol ? "2px solid #ef4444" : "1px solid #dfe5df", borderRadius: 10, background: excedePeso||excedeVol ? "#fff3f3" : "#f8faf8" }}>
            <strong>Restricción vehículo</strong>
            <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
              <CapacityBar label="Peso" used={pesoLive} capacity={capPeso || 1} unit="kg" />
              <CapacityBar label="Volumen" used={volLive} capacity={capVol || 1} unit="m³" />
            </div>
            {(excedePeso||excedeVol) && <p style={{ color: "#ef4444", fontWeight: 700, margin: "8px 0 0" }}>⚠ El vehículo no posee capacidad suficiente.</p>}
            <small className="muted-copy">Selecciona {selectedPedidosLive.length} pedidos · validar backend también bloquea si excede.</small>
          </div>
          <button className="primary-button primary-button--full" type="submit" disabled={planning || (excedePeso||excedeVol)}>{planning ? "Calculando Dijkstra+TSP..." : "Optimizar ruta"}</button>
        </form>
        <div className="method-note"><strong>Grafo real</strong><p>Nodos={grafoData?.nodos.length || nodes.length} · Aristas={graphEdges.length} · Peso=distancia_km · Conectado ✅</p></div>
        <div style={{ marginTop: 12 }}>
          <h4 style={{ margin: "0 0 8px" }}>Vista previa del grafo</h4>
          <LeafletMap points={graphPoints} routes={graphRouteEdges} height={260} />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8, fontSize: 10 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 12, height: 12, background: "#0a1931", borderRadius: "50%" }} /> Bodega</span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 12, height: 12, background: "#2563eb", borderRadius: "50%" }} /> Destino</span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 12, height: 12, background: "#5a6b66", borderRadius: "50%" }} /> Intermedio</span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 20, height: 2, background: "#d1d5db" }} /> Conexión</span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 20, height: 3, background: "#2563eb" }} /> Ruta óptima</span>
          </div>
          <button className="quiet-button" style={{ marginTop: 8 }} onClick={() => void loadGrafo()}>⟳ Recargar grafo</button>
        </div>
        {actionError && <div className="inline-error" style={{ marginTop: 12 }}><span>{actionError}</span></div>}
        {actionSuccess && <div style={{ marginTop: 12, padding: 10, background: "#e5f4e9", borderRadius: 8 }}>{actionSuccess}</div>}
      </section>
      <div className="results-column">
        {!plan && !planning && <EmptyState title="La planificación aparecerá aquí" detail="Selecciona origen, 2-4 pedidos, vehículo y conductor. El motor Dijkstra+TSP calculará orden, distancia y tiempo." />}
        {planning && <div className="loading-panel"><span /><strong>Ejecutando Dijkstra + TSP exacto</strong><p>Validando capacidad, calculando caminos mínimos y permutaciones</p></div>}
        {plan && <section className="panel"><PlanResult plan={plan} nodes={nodes} onSave={savePlanAsRoute} saving={savingPlan} />
          <div style={{ marginTop: 16, padding: 12, background: "#f0f9ff", borderLeft: "3px solid #2563eb", borderRadius: 8 }}>
            <h4>Algoritmo de camino mínimo: Dijkstra</h4>
            <p className="muted-copy">Cada segmento origen→destino usa Dijkstra (cola prioridad O((V+E)logV)). Ejemplo real:</p>
            <div style={{ fontSize: 12, lineHeight: 1.6 }}>{plan.recorrido.map((nid, i) => i===0 ? `Inicio: ${plan.origen.nombre} (${plan.origen.id_nodo})` : `→ Nodo ${nid} ${nodes.find(n=>n.id_nodo===nid)?.nombre ? `(${nodes.find(n=>n.id_nodo===nid)?.nombre})` : ""}` ).join(" ")}<br/><strong>Distancia total: {formatNumber(plan.distancia_total_km)} km</strong> · Tiempo estimado: {Math.round(plan.distancia_total_km*2.2)} min · Algoritmo: {plan.algoritmo}</div>
            <h4 style={{ marginTop: 10 }}>TSP / Multi-entrega</h4>
            <p className="muted-copy">Orden óptimo encontrado evaluando {plan.permutaciones_evaluadas} permutaciones (TSP exacto):</p>
            <ol style={{ fontSize: 12 }}>{[{ id: plan.origen.id_nodo, nombre: plan.origen.nombre } as any, ...plan.orden_optimo.map(id=>({id, nombre: nodes.find(n=>n.id_nodo===id)?.nombre || `Nodo ${id}`}))].map((n, i)=><li key={i}>{i+1}. {n.nombre} (Nodo {n.id}) {i===0?"— Bodega origen": ""}</li>)} {plan.regresar_origen && <li>{plan.orden_optimo.length+2}. {plan.origen.nombre} — Regreso</li>}</ol>
            <small className="muted-copy">Paradas: {plan.orden_optimo.length} · Peso {formatNumber(plan.peso_total)}/{formatNumber(plan.capacidad_peso)} kg · Conductores con prioridad {Object.entries(plan.pedidos.reduce((a:any,o:any)=>{a[o.prioridad]=(a[o.prioridad]||0)+1;return a},{})).map(([k,v])=>`${k}:${v}`).join(" ")}</small>
          </div>
        </section>}
        {plan && <section className="panel ai-panel"><div className="panel__heading"><div><span className="eyebrow">IA</span><h3>Análisis</h3></div><button className="secondary-button" onClick={() => void requestAnalysis()} disabled={analyzing}>{analyzing ? "Analizando..." : analysis ? "Actualizar" : "Analizar planificación"}</button></div>{analysis ? <AIResult analysis={analysis} /> : <p className="muted-copy">Evalúa utilización, prioridades y riesgo determinista.</p>}</section>}
        <section className="panel" style={{ marginTop: 16 }}>
          <h3>Exploración del grafo — BFS / DFS</h3>
          <p className="muted-copy">Demuestra recorridos académicos sobre el grafo real. Selecciona nodo inicial y ejecuta.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
            <select value={bfsInicio} onChange={e=>setBfsInicio(e.target.value)} style={{ flex: 1, minWidth: 140 }}>{(grafoData?.nodos || nodes).map(n=><option key={n.id_nodo} value={n.id_nodo}>{n.nombre} ({n.id_nodo})</option>)}</select>
            <button className="quiet-button" onClick={()=>void runBFS()} disabled={graphLoading}>BFS</button>
            <button className="quiet-button" onClick={()=>void runDFS()} disabled={graphLoading}>DFS</button>
          </div>
          {graphLoading && <div className="loading-panel" style={{ minHeight: 80 }}><span /><small>Recorriendo grafo...</small></div>}
          {bfsResult && !dfsResult && <div style={{ marginTop: 10, padding: 10, background: "#eff6ff", borderRadius: 8 }}><strong>BFS desde {bfsResult.inicio.nombre}:</strong><br/><small>{bfsResult.recorrido.join(" → ")}</small><br/><small>Visitados: {bfsResult.visitados} nodos · Orden anchura</small></div>}
          {dfsResult && <div style={{ marginTop: 10, padding: 10, background: "#fff0d7", borderRadius: 8 }}><strong>DFS desde {dfsResult.inicio.nombre}:</strong><br/><small>{dfsResult.recorrido.join(" → ")}</small><br/><small>Visitados: {dfsResult.visitados} nodos · Profundidad</small></div>}
          <p className="muted-copy" style={{ marginTop: 8 }}>BFS usa cola, DFS recursión. Útil para explicar conectividad antes de Dijkstra/TSP.</p>
        </section>
      </div>
    </div>;
  } else if (screen === "mapa-vivo") {
    const active = routes.filter(r => !["COMPLETADA", "CANCELADA"].includes(r.estado));
    // construir puntos y rutas reales desde liveRouteDetails si disponible
    const liveColors = ["#2563eb", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"];
    const detailedRoutes = active.slice(0, 5).map((r, idx) => {
      const det = liveRouteDetails[r.id_ruta];
      if (det && det.puntos.length) {
        return { id: r.codigo, points: det.puntos.map(p => ({ id: p.id_nodo, nombre: p.nombre, lat: p.latitud, lng: p.longitud, tipo: p.tipo_nodo, orden: p.orden })), color: liveColors[idx % liveColors.length], label: r.codigo, detalle: det };
      }
      const o = nodes.find(n => n.id_nodo === r.origen.id_nodo);
      const d = nodes.find(n => n.id_nodo === r.destino.id_nodo);
      const pts = [o, d].filter(Boolean).map(n => ({ id: n!.id_nodo, nombre: n!.nombre, lat: n!.latitud, lng: n!.longitud, tipo: n!.tipo_nodo }));
      return { id: r.codigo, points: pts as any, color: liveColors[idx % liveColors.length], label: r.codigo, detalle: null as any };
    });
    // todos los puntos: si hay rutas detalladas, usar esos puntos, sino todos los nodos
    const allPointsDetailed = detailedRoutes.flatMap(r => r.points);
    const displayPoints = allPointsDetailed.length ? allPointsDetailed : nodes.map(n => ({ id: n.id_nodo, nombre: n.nombre, lat: n.latitud, lng: n.longitud, tipo: n.tipo_nodo }));
    // si no hay ubicación ni rutas, no dejar mundo completo: usar Quito -0.20,-78.50 con zoom manejado por disableAutoFit logic handled in LeafletMap via center fallback
    content = <div className="panel">
      <div className="panel__heading"><div><span className="eyebrow">Tiempo real</span><h3>Mapa en vivo</h3></div><span className="muted-copy">Geolocalización navegador + rutas reales</span></div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <button className="primary-button" onClick={() => requestGeolocation(false)} disabled={geoLoading}>{geoLoading ? "Obteniendo..." : "📍 Mi ubicación"}</button>
        <button className="quiet-button" onClick={() => { if (tmcLocation) { setTmcFocusTrigger(v=>v+1); setActionSuccess("Centrado en TMC Matriz Quito"); } else setGeoError("Bodega TMC no cargada"); }}>{`🏢 Ir a TMC Matriz`}</button>
        <button className="quiet-button" onClick={() => setFitTrigger(v => v + 1)}>{`🗺 Ver ruta completa`}</button>
        <button className="quiet-button" onClick={async () => { void loadRoutes(); const a = routes.filter(r => !["COMPLETADA", "CANCELADA"].includes(r.estado)); void loadLiveRouteDetails(a); if (!userLocation) requestGeolocation(false); setFitTrigger(v=>v+1); }}>{`⟳ Actualizar`}</button>
        {userLocation && <span className="muted-copy" style={{ alignSelf: "center" }}>±{userLocation.accuracy ? Math.round(userLocation.accuracy) + "m" : ""} · {userLocation.lat.toFixed(5)}, {userLocation.lng.toFixed(5)}</span>}
        {tmcLocation && <span className="muted-copy" style={{ alignSelf: "center" }}>🏢 TMC {tmcLocation.lat.toFixed(5)}, {tmcLocation.lng.toFixed(5)}</span>}
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12, padding: 10, background: tmcEditMode ? "#fef3c7" : "#f8faf8", borderRadius: 8, border: "1px solid #e5e7eb" }}>
        <button className={tmcEditMode ? "primary-button" : "quiet-button"} onClick={() => setTmcEditMode(v=>!v)}>{tmcEditMode ? "✏️ Modo edición activo (arrastra o clic)" : "✏️ Editar ubicación TMC"}</button>
        <span className="muted-copy" style={{ alignSelf: "center" }}>Modo desarrollo/admin: marcador TMC arrastrable</span>
        {tmcEditMode && <button className="quiet-button" onClick={() => { setTmcEditMode(false); setPendingTmc(null); }}>Cancelar edición</button>}
      </div>
      {tmcEditMode && (
        <div style={{ padding: 10, background: "#fffbeb", border: "1px solid #fcd34d", borderRadius: 8, marginBottom: 12 }}>
          <p style={{ margin: "0 0 8px", fontSize: 12 }}><strong>Modo edición TMC activo:</strong> arrastra el marcador 🏢 o haz clic en el mapa sobre el predio "Tramaco Express" (Manuel Najas).</p>
          {pendingTmc ? (
            <div>
              <p style={{ margin: "0 0 6px", fontSize: 12 }}>Nueva ubicación TMC pendiente:<br/>Latitud: <strong>{pendingTmc.lat.toFixed(6)}</strong> Longitud: <strong>{pendingTmc.lng.toFixed(6)}</strong></p>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="primary-button" onClick={() => void saveTmcLocation()} disabled={savingTmc}>{savingTmc ? "Guardando..." : "Guardar ubicación TMC"}</button>
                <button className="quiet-button" onClick={() => setPendingTmc(null)}>Descartar</button>
              </div>
            </div>
          ) : (
            <p className="muted-copy" style={{ margin: 0 }}>Mueve el marcador o haz clic en el mapa para seleccionar nueva ubicación.</p>
          )}
          <p className="muted-copy" style={{ margin: "8px 0 0", fontSize: 10 }}>Al guardar se actualizará PostgreSQL (id 1), se recalcularán todas las aristas TMC con haversine y se actualizará el seed.</p>
        </div>
      )}
      {geoError && <div className="inline-error" style={{ marginBottom: 10 }}><strong>Ubicación:</strong><span>{geoError}</span></div>}
      {actionSuccess && <div style={{ padding: 8, background: "#e5f4e9", borderRadius: 8, marginBottom: 8 }}>{actionSuccess}</div>}
      <LeafletMap points={displayPoints} routes={detailedRoutes.map(r=>({id:r.id, points:r.points, color:r.color, label:r.label}))} height={500} userLocation={userLocation} focusTrigger={focusTrigger} fitTrigger={fitTrigger} focusPoint={tmcLocation} focusPointTrigger={tmcFocusTrigger} editableTmc={tmcEditMode} pendingTmcLocation={pendingTmc} onTmcDragEnd={handleTmcDrag} onMapClick={handleMapClickForTmc} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 12, marginTop: 14 }}>
        {liveLoading ? <div className="loading-panel" style={{ minHeight: 80 }}><span /><small>Cargando rutas reales...</small></div> : active.length === 0 ? <EmptyState title="Sin rutas activas" detail="Crea una planificación y guárdala como ruta para verla aquí con marcadores y polyline." /> : detailedRoutes.map(r => (
          <div key={r.id} style={{ padding: 12, border: `2px solid ${r.color}`, borderRadius: 12, background: "#fff" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}><strong>{r.id}</strong><StatusPill status={active.find(a=>a.codigo===r.id)?.estado || ""} /></div>
            <small>{r.detalle ? `${r.detalle.puntos.length} paradas · ${r.detalle.puntos.map((p: any)=>p.nombre).join(" → ")}` : `${r.points.length} puntos`}</small><br />
            <small>Vehículo: {active.find(a=>a.codigo===r.id)?.vehiculo?.placa || "—"} · Conductor: {(() => { const c = active.find(a=>a.codigo===r.id)?.conductor; return c ? `${c.nombres} ${c.apellidos}` : "—"; })()}</small><br />
            <small>Distancia: {formatNumber(active.find(a=>a.codigo===r.id)?.distancia_total_km)} km · Progreso: {(() => { const st = active.find(a=>a.codigo===r.id)?.estado; return st==="EN_RUTA"?"60%":st==="ASIGNADA"?"30%":"10%"; })()}</small>
            <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>{r.points.slice(0,5).map((p: any) => <span key={p.id} style={{ fontSize: 9, padding: "2px 6px", background: "#eff6ff", borderRadius: 99 }}>{p.orden ? `#${p.orden}` : ""} {p.nombre}</span>)}</div>
          </div>
        ))}
      </div>
      <p className="muted-copy" style={{ marginTop: 10 }}>Al entrar se intenta obtener tu GPS automáticamente. Si bloqueas permiso, el mapa hace fitBounds a las rutas activas. El marcador azul 📍 es tu posición real (no inventada).</p>
    </div>;
  } else if (screen === "reportes") {
    const filteredRoutesReport = routes.filter(r => {
      const d = new Date(r.creado_en);
      if (reporteDesde && d < new Date(reporteDesde)) return false;
      if (reporteHasta && d > new Date(reporteHasta + "T23:59:59")) return false;
      return true;
    });
    const filteredOrdersReport = orders.filter(o => {
      const d = new Date(o.creado_en);
      if (reporteDesde && d < new Date(reporteDesde)) return false;
      if (reporteHasta && d > new Date(reporteHasta + "T23:59:59")) return false;
      return true;
    });
    const totalPed = filteredOrdersReport.length;
    const completados = filteredOrdersReport.filter(o => o.estado === "ENTREGADO").length || filteredRoutesReport.filter(r=>r.estado==="COMPLETADA").length;
    const pct = totalPed ? Math.round((completados / totalPed) * 100) : 0;
    const distTotalFiltered = filteredRoutesReport.reduce((s,r)=>s+(r.distancia_total_km||0),0);
    const tiempoFiltered = Math.round(distTotalFiltered*2.2);
    const distByDay = filteredRoutesReport.slice(0, 7).map(r => ({ label: new Date(r.creado_en).toLocaleDateString(), km: r.distancia_total_km || 0 }));
    const maxKm = Math.max(...distByDay.map(d => d.km), 1);
    content = <div><div className="panel"><div className="panel__heading"><div><span className="eyebrow">Filtros</span><h3>Reportes</h3></div><div style={{ display: "flex", gap: 8 }}><button className="primary-button" onClick={() => setActionSuccess(`Reporte generado: ${totalPed} pedidos, ${filteredRoutesReport.length} rutas, ${distTotalFiltered.toFixed(1)} km`)}>Generar reporte</button><button className="quiet-button" onClick={() => { const csv = `metrica,valor\nTotal pedidos,${totalPed}\nCompletados,${completados}\nDistancia total,${distTotalFiltered}\nRutas,${filteredRoutesReport.length}\n`; const blob = new Blob([csv], { type: "text/csv" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "reporte_optiroute.csv"; a.click(); }}>Descargar CSV</button></div></div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}><label><span>Desde</span><input type="date" value={reporteDesde} onChange={e => setReporteDesde(e.target.value)} /></label><label><span>Hasta</span><input type="date" value={reporteHasta} onChange={e => setReporteHasta(e.target.value)} /></label><button className="quiet-button" onClick={() => { setReporteDesde(""); setReporteHasta(""); setActionSuccess("Filtros limpiados"); }}>Limpiar</button><span className="muted-copy" style={{ alignSelf: "end" }}>{filteredRoutesReport.length} rutas · {totalPed} pedidos (filtrados)</span></div>{actionSuccess && <div style={{ marginTop: 10, padding: 8, background: "#e5f4e9", borderRadius: 8 }}>{actionSuccess}</div>}</div>
      <div className="metrics-grid" style={{ marginTop: 14 }}><MetricCard label="Total pedidos" value={totalPed} detail="Filtrado" variant="blue" /><MetricCard label="Entregas completadas" value={completados} detail={`${pct}% completado`} variant="green" /><MetricCard label="Distancia total" value={`${formatNumber(distTotalFiltered)} km`} detail="Filtrada" variant="purple" /><MetricCard label="Tiempo estimado" value={`${tiempoFiltered} min`} detail="Acumulado" variant="orange" /></div>
      <div className="split-grid"><div className="panel"><h4>Distancia por día (rutas filtradas)</h4>{distByDay.length===0 ? <p className="muted-copy">Sin rutas en rango</p> : <div style={{ display: "flex", alignItems: "end", gap: 8, height: 140, marginTop: 12 }}>{distByDay.map((d, i) => <div key={i} style={{ flex: 1, textAlign: "center" }}><div style={{ height: `${(d.km / maxKm) * 100}%`, minHeight: 12, background: "#2563eb", borderRadius: 6 }} /><small>{d.label.slice(0, 5)}</small><br /><small>{formatNumber(d.km)}</small></div>)}</div>}</div><div className="panel"><h4>Entregas por estado (filtrado)</h4>{Object.entries(filteredOrdersReport.reduce<Record<string, number>>((a, o) => { a[o.estado] = (a[o.estado] || 0) + 1; return a; }, {})).map(([k, v]) => <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #eef2ee" }}><StatusPill status={k} /><strong>{v}</strong></div>)}</div></div>
    </div>;
  } else if (screen === "ia") {
    content = <div className="panel" style={{ maxWidth: 900, margin: "0 auto" }}><div className="panel__heading"><div><span className="eyebrow">Asistente</span><h3>IA Asistente logístico</h3><p className="muted-copy" style={{ margin: "4px 0 0" }}>Consulta información de rutas, pedidos, vehículos, conductores, grafos y planificación.</p></div><span className="muted-copy">Asistente logístico basado en reglas y análisis de datos</span></div>
      {analysis && <div style={{ marginBottom: 14 }}><AIResult analysis={analysis} /></div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 380, overflowY: "auto", padding: 10, background: "#f8faf8", borderRadius: 12, border: "1px solid #dfe5df" }}>
        {chatMessages.map((m, i) => <div key={i} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "82%", padding: "10px 12px", borderRadius: 12, background: m.role === "user" ? "#2563eb" : "white", color: m.role === "user" ? "white" : "#172521", border: "1px solid #dfe5df" }}><small style={{ opacity: .7 }}>{m.ts} · {m.role}</small><p style={{ margin: "4px 0 0", fontSize: 13, whiteSpace: "pre-wrap" }}>{m.text}</p></div>)}
        {chatLoading && <div style={{ display: "flex", alignItems: "center", gap: 8, padding: 10, background: "#eff6ff", borderRadius: 8 }}><span style={{ width: 16, height: 16, border: "2px solid #2563eb", borderTopColor: "transparent", borderRadius: "50%", display: "inline-block", animation: "spin 800ms linear infinite" }} /><small>Analizando datos logísticos...</small></div>}
      </div>
      <form onSubmit={sendChat} style={{ display: "flex", gap: 8, marginTop: 12 }}><input value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e=> { if(e.key==="Enter" && !e.shiftKey){ /* Enter envía, Shift+Enter nueva línea si fuera textarea */}}} placeholder="Pregunta: ¿cuál es la ruta más larga? ¿pedidos pendientes?" style={{ flex: 1 }} /><button className="primary-button" type="submit">Enviar</button></form>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>{["¿cuál es la ruta más larga?","¿cuál es la ruta más corta?","pedidos pendientes","resumen del día","vehículo con mayor capacidad","conductor con más entregas","rutas activas","pedidos urgentes","explicar Dijkstra","explicar TSP"].map(s => <button key={s} className="quiet-button" onClick={() => setChatInput(s)}>{s}</button>)}</div>
      {!analysis && <p className="muted-copy" style={{ marginTop: 12 }}>Genera una planificación en Optimización para obtener análisis de riesgo real; el chat también usa datos en vivo para responder.</p>}
      {actionError && <div className="inline-error" style={{ marginTop: 8 }}><span>No se pudo consultar el asistente. Verifica la conexión con la API. {actionError}</span></div>}
    </div>;
  } else if (screen === "configuracion") {
    content = <div className="panel" style={{ maxWidth: 700 }}><h3>Configuración</h3><div style={{ display: "grid", gap: 12, marginTop: 12 }}><label><span>Nombre del sistema</span><input defaultValue="OptiRoute AI" /></label><label><span>Empresa</span><input defaultValue="OptiRoute Logistics S.A." /></label><label><span>Ciudad base</span><input defaultValue="Quito, Ecuador" /></label><label><span>Bodega principal</span><input defaultValue={nodes.find(n => n.tipo_nodo === "BODEGA")?.nombre || "Bodega Principal"} /></label><label><span>API URL</span><input defaultValue={(import.meta as any).env.VITE_API_URL || "http://127.0.0.1:8000"} readOnly /></label><div style={{ padding: 12, background: "#f0f9ff", borderLeft: "3px solid #38bdf8", borderRadius: 8 }}><strong>Información</strong><p className="muted-copy">Configuración visual y operativa. No se requieren cambios de BD para la demo. Variables en .env: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, FRONTEND_ORIGINS, VITE_API_URL.</p></div><button className="primary-button" onClick={() => setActionSuccess("Configuración guardada (demo).")}>Guardar</button>{actionSuccess && <div style={{ padding: 8, background: "#e5f4e9", borderRadius: 8 }}>{actionSuccess}</div>}</div></div>;
  } else if (screen === "usuarios" && usuarioActual) {
    content = usuarioActual.rol === "DESARROLLADOR"
      ? <DeveloperConsole
          usuario={usuarioActual}
          rutas={routes}
          pedidos={orders}
          conductores={drivers}
          vehiculos={vehicles}
          cargando={routesLoading || catalogsLoading}
          onNavigate={selectScreen}
        />
      : <AccessPanel usuario={usuarioActual} />;
  } else if (screen === "conductor-movil") {
    content = <DriverPanel rutas={routes} onRefresh={loadRoutes} />;
  } else if (screen === "distribucion" && usuarioActual) {
    content = <DistribucionPanel usuario={usuarioActual} permisos={permisos} />;
  } else if (false) {
    const myRoute = routes.find(r => !["COMPLETADA", "CANCELADA"].includes(r.estado)) || routes[0];
    const puntos = myRoute && routeDetail?.id_ruta === myRoute.id_ruta ? (routeDetail?.puntos || []) : (myRoute ? [{ orden: 1, id_nodo: myRoute.origen.id_nodo, nombre: myRoute.origen.nombre, tipo_nodo: "BODEGA", latitud: nodes.find(n => n.id_nodo === myRoute.origen.id_nodo)?.latitud || -0.2, longitud: nodes.find(n => n.id_nodo === myRoute.origen.id_nodo)?.longitud || -78.5, distancia_acumulada_km: 0 }, { orden: 2, id_nodo: myRoute.destino.id_nodo, nombre: myRoute.destino.nombre, tipo_nodo: "CLIENTE", latitud: nodes.find(n => n.id_nodo === myRoute.destino.id_nodo)?.latitud || -0.205, longitud: nodes.find(n => n.id_nodo === myRoute.destino.id_nodo)?.longitud || -78.495, distancia_acumulada_km: myRoute.distancia_total_km }] : []);
    content = <div style={{ maxWidth: 480, margin: "0 auto" }}><div className="panel"><div style={{ display: "flex", justifyContent: "space-between" }}><div><span className="eyebrow">MI RUTA</span><h3>{myRoute ? myRoute.codigo : "Sin ruta asignada"}</h3><p className="muted-copy">{myRoute ? `${myRoute.origen.nombre} → ${myRoute.destino.nombre} · ${myRoute.estado}` : "No hay ruta"}</p></div><StatusPill status={myRoute?.estado || "SIN_RUTA"} /></div>
      {myRoute && <LeafletMap points={puntos.map(p => ({ id: p.id_nodo, nombre: p.nombre, lat: p.latitud, lng: p.longitud, tipo: p.tipo_nodo, orden: p.orden }))} routes={[{ id: myRoute.codigo, points: puntos.map(p => ({ id: p.id_nodo, nombre: p.nombre, lat: p.latitud, lng: p.longitud, tipo: p.tipo_nodo })), color: "#2563eb", label: myRoute.codigo }]} height={300} />}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12 }}>{puntos.map(p => <div key={p.orden} style={{ padding: 12, border: "1px solid #e5eae7", borderRadius: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}><div><strong>{p.orden}. {p.nombre}</strong><br /><small>{p.tipo_nodo} · {formatNumber(p.distancia_acumulada_km)} km</small></div><button className="quiet-button" onClick={() => window.open(`https://www.google.com/maps/dir/?api=1&destination=${p.latitud},${p.longitud}`, "_blank")}>Navegar</button></div>)}</div>
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}><button className="primary-button" style={{ flex: 1 }} onClick={async () => { if (myRoute) { try { await api.changeRouteState(myRoute.id_ruta, "EN_RUTA"); setActionSuccess("Ruta iniciada"); void loadRoutes(); } catch (e) { setActionError(e instanceof Error ? e.message : "Error"); } } }}>Iniciar navegación</button><button className="secondary-button" onClick={async () => { if (myRoute) { try { await api.changeRouteState(myRoute.id_ruta, "COMPLETADA"); setActionSuccess("Entrega marcada completada"); void loadRoutes(); } catch (e) { setActionError(e instanceof Error ? e.message : "Error"); } } }}>Marcar entrega</button></div>
      {actionSuccess && <div style={{ marginTop: 8, padding: 8, background: "#e5f4e9", borderRadius: 8 }}>{actionSuccess}</div>}{actionError && <div className="inline-error"><span>{actionError}</span></div>}
      <p className="muted-copy" style={{ marginTop: 8, textAlign: "center" }}>Vista responsive — probar en DevTools móvil</p></div></div>;
  }

  return <div className={`app-shell app-shell--${usuarioActual?.rol?.toLowerCase() || "operador"}`}>
    <aside className={`sidebar${sidebarOpen ? " sidebar--open" : ""}`}>
      <div className="brand"><span>OR</span><div><strong>OptiRoute<span className="brand__accent">-AI</span></strong><small>Plataforma logística</small></div></div>
      <nav aria-label="Navegación principal">
        {navigation
          .filter((item) => puedeVerPantalla(permisos, item.id))
          .map((item) => (
            <button
              key={item.id}
              className={screen === item.id ? "nav-item nav-item--active" : "nav-item"}
              onClick={() => selectScreen(item.id)}
            >
              <span><Icono nombre={item.icono} size={17} /></span>
              {item.label}
            </button>
          ))}
      </nav>
      <button className="nav-item" onClick={logout} style={{ marginTop: 8, border: "1px solid rgba(255,255,255,.12)" }}><span>↪</span>Cerrar sesión ({usuarioActual?.correo || localStorage.getItem("or_usuario") || localStorage.getItem("or_user")})</button>
      <div className="sidebar-graph">
        <svg viewBox="0 0 120 70" preserveAspectRatio="none"><circle cx="14" cy="18" r="3.5" fill="#60a5fa"/><circle cx="46" cy="10" r="2.8" fill="#38bdf8"/><circle cx="84" cy="20" r="3.5" fill="#60a5fa"/><circle cx="66" cy="38" r="2.8" fill="#38bdf8"/><circle cx="104" cy="46" r="2.8" fill="#60a5fa"/><circle cx="20" cy="52" r="2.5" fill="#38bdf8"/><path d="M14 18 L46 10 L84 20 M46 10 L66 38 L104 46 M84 20 L66 38 M14 18 L20 52 L66 38" stroke="#38bdf8" strokeWidth="1.1" fill="none" opacity="0.55"/><path d="M14 18 L66 38" stroke="#60a5fa" strokeWidth="0.7" strokeDasharray="3 3" opacity="0.45"/></svg>
        <div className="graph-label"><strong>Grafos<br/>que mueven<br/>resultados</strong></div>
      </div>
      <div className="sidebar-status" style={{ display: "none" }}><span /><div><strong>API local</strong><small>{(import.meta as any).env.VITE_API_URL || "http://127.0.0.1:8000"}</small></div></div>
    </aside>
    {sidebarOpen && <button className="sidebar-backdrop" aria-label="Cerrar menú" onClick={() => setSidebarOpen(false)} />}
    <main>
      <header className={`topbar ${headerVisible ? "" : "topbar--hidden"}`}>
        <button className="menu-button" aria-label="Abrir menú" onClick={() => setSidebarOpen(true)}>☰</button>
        <div className="topbar-left"><div className="welcome-icon">👋</div><div><strong>Bienvenido, {usuarioActual?.nombres || usuarioActual?.correo || localStorage.getItem("or_usuario") || "Usuario"}</strong><small>{pageTitles[screen]} · Sistema de Optimización de Rutas</small></div></div>
        <div className="topbar-right"><div className="environment-badge"><span />Entorno local</div><button className="icon-btn" aria-label="Notificaciones">🔔</button><div className="admin-chip"><span>{usuarioActual?.rol?.charAt(0) || "A"}</span>{usuarioActual?.rol || localStorage.getItem("or_rol") || "Admin"}</div></div>
      </header>
      <div className="page-content"><div className="demo-banner"><strong>DEMO LOCAL</strong><span>Datos de demostracion · autenticacion en repositorio provisional · sin Supabase</span></div>{content}</div>
      {cancelacion?.tipo === "pedido" && <CancelReasonModal
        titulo="Cancelar pedido"
        descripcion="El motivo queda registrado en la auditoria junto a tu usuario. Esta accion cierra el pedido para la operacion."
        procesando={procesandoCancelacion}
        onCerrar={() => setCancelacion(null)}
        onConfirmar={confirmarCancelacionPedido}
      />}
      {cancelacion?.tipo === "ruta" && <CancelReasonModal
        titulo="Cancelar ruta"
        descripcion="El motivo queda registrado en la auditoria junto a tu usuario. Los recursos asignados se liberan al cancelar."
        procesando={procesandoCancelacion}
        onCerrar={() => setCancelacion(null)}
        onConfirmar={confirmarCancelacionRuta}
      />}
    </main>
  </div>;
}
