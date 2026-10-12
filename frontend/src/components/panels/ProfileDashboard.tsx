import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { authApi } from "../../api/client";
import type { OrderCatalogItem, RouteSummary, Screen, UsuarioInfo, VehicleCatalogItem, DriverCatalogItem } from "../../api/types";
import { puedeVerPantalla } from "../../auth/permissions";
import administratorHero from "../../assets/dashboards/administrator-quito.webp";
import developerHero from "../../assets/dashboards/developer-quito.webp";
import driverHero from "../../assets/dashboards/driver-sierra.webp";
import operatorHero from "../../assets/dashboards/operator-quito.webp";

type Props = {
  usuario: UsuarioInfo;
  rutas: RouteSummary[];
  pedidos: OrderCatalogItem[];
  vehiculos: VehicleCatalogItem[];
  conductores: DriverCatalogItem[];
  permisos: string[];
  cargando: boolean;
  onNavigate: (screen: Screen) => void;
};

type QuickAction = { titulo: string; detalle: string; screen: Screen; mark: string };

const perfil: Record<string, { titulo: string; subtitulo: string; hero: string; acciones: QuickAction[] }> = {
  OPERADOR: {
    titulo: "Centro operativo",
    subtitulo: "Planifica pedidos y coordina la operación logística desde un solo lugar.",
    hero: operatorHero,
    acciones: [
      { titulo: "Distribución", detalle: "Mis rutas y entregas", screen: "distribucion", mark: "01" },
      { titulo: "Pedidos", detalle: "Crear y dar seguimiento", screen: "pedidos", mark: "02" },
      { titulo: "Clientes", detalle: "Consultar destinatarios", screen: "clientes", mark: "03" },
      { titulo: "Rutas", detalle: "Control y novedades", screen: "rutas", mark: "04" },
    ],
  },
  ADMINISTRADOR: {
    titulo: "Centro de administración",
    subtitulo: "Supervisa la operación, la flota y las cuentas operativas autorizadas.",
    hero: administratorHero,
    acciones: [
      { titulo: "Cuentas operativas", detalle: "Operadores y conductores", screen: "usuarios", mark: "01" },
      { titulo: "Conductores", detalle: "Disponibilidad y asignación", screen: "conductores", mark: "02" },
      { titulo: "Vehículos", detalle: "Capacidad y estado", screen: "vehiculos", mark: "03" },
      { titulo: "Reportes", detalle: "Rendimiento de la operación", screen: "reportes", mark: "04" },
    ],
  },
  DESARROLLADOR: {
    titulo: "Administración del sistema",
    subtitulo: "Consulta permisos, auditoría y diagnóstico técnico sin exponer secretos.",
    hero: developerHero,
    acciones: [
      { titulo: "Usuarios", detalle: "Administradores y cuentas", screen: "usuarios", mark: "01" },
      { titulo: "Roles y permisos", detalle: "Matriz efectiva de acceso", screen: "usuarios", mark: "02" },
      { titulo: "Auditoría", detalle: "Eventos recientes", screen: "usuarios", mark: "03" },
      { titulo: "Configuración", detalle: "Parámetros existentes", screen: "configuracion", mark: "04" },
    ],
  },
  CONDUCTOR: {
    titulo: "Mis rutas de entrega",
    subtitulo: "Gestiona únicamente tus asignaciones, entregas y novedades autorizadas.",
    hero: driverHero,
    acciones: [
      { titulo: "Mi ruta", detalle: "Recorrido y navegación", screen: "conductor-movil", mark: "01" },
      { titulo: "Mis pedidos", detalle: "Entregas asignadas", screen: "pedidos", mark: "02" },
      { titulo: "Mapa", detalle: "Trayecto autorizado", screen: "conductor-movil", mark: "03" },
      { titulo: "Novedades", detalle: "Registrar un incidente", screen: "conductor-movil", mark: "04" },
    ],
  },
};

function Metric({ label, value, detail, tone }: { label: string; value: string | number; detail: string; tone: string }) {
  return <article className={`role-metric role-metric--${tone}`}><div className="role-metric__top"><span>{label}</span><i /></div><strong>{value}</strong><small>{detail}</small></article>;
}

export default function ProfileDashboard({ usuario, rutas, pedidos, vehiculos, conductores, permisos, cargando, onNavigate }: Props) {
  const config = perfil[usuario.rol] || perfil.OPERADOR;
  const [diagnostico, setDiagnostico] = useState<any>(null);
  const [diagnosticoError, setDiagnosticoError] = useState("");
  useEffect(() => {
    setDiagnosticoError("");
    if (usuario.rol !== "DESARROLLADOR") { setDiagnostico(null); return; }
    authApi.diagnostico().then(setDiagnostico).catch((error) => setDiagnosticoError(error instanceof Error ? error.message : "Diagnóstico no disponible"));
  }, [usuario.rol]);

  const metricas = useMemo(() => {
    const rutasActivas = rutas.filter((ruta) => !["COMPLETADA", "CANCELADA"].includes(ruta.estado));
    const pendientes = pedidos.filter((pedido) => pedido.estado !== "ENTREGADO" && pedido.estado !== "CANCELADO").length;
    const entregados = pedidos.filter((pedido) => pedido.estado === "ENTREGADO").length;
    const vehiculosDisponibles = vehiculos.filter((vehiculo) => vehiculo.disponible).length;
    const conductoresDisponibles = conductores.filter((conductor) => conductor.disponible && conductor.activo).length;
    if (usuario.rol === "CONDUCTOR") return [
      { label: "Rutas asignadas", value: cargando ? "…" : rutasActivas.length, detail: "Solo rutas propias", tone: "blue" },
      { label: "Entregas pendientes", value: cargando ? "…" : pendientes, detail: "Requieren confirmación", tone: "orange" },
      { label: "Entregas completadas", value: cargando ? "…" : entregados, detail: "Pedidos entregados", tone: "green" },
      { label: "Vehículo asignado", value: cargando ? "…" : (rutasActivas[0]?.vehiculo?.placa || "—"), detail: "Según la ruta activa", tone: "teal" },
    ];
    if (usuario.rol === "DESARROLLADOR") return [
      { label: "Cuentas activas", value: diagnostico?.cuentas?.activas ?? (cargando ? "…" : "—"), detail: "Dato del backend", tone: "violet" },
      { label: "Sesiones activas", value: diagnostico?.sesiones?.activas ?? (cargando ? "…" : "—"), detail: "Sin exponer tokens", tone: "blue" },
      { label: "Rutas activas", value: rutasActivas.length, detail: "Estado operativo", tone: "cyan" },
      { label: "Almacenamiento", value: String(diagnostico?.almacenamiento?.backend || "local").toUpperCase(), detail: "Repositorio provisional", tone: "slate" },
    ];
    return [
      { label: "Rutas activas", value: cargando ? "…" : rutasActivas.length, detail: "Planificadas o en curso", tone: "blue" },
      { label: "Pedidos pendientes", value: cargando ? "…" : pendientes, detail: "Por entregar", tone: "orange" },
      { label: "Vehículos disponibles", value: cargando ? "…" : vehiculosDisponibles, detail: `De ${vehiculos.length} registrados`, tone: "green" },
      { label: "Conductores", value: cargando ? "…" : conductoresDisponibles, detail: "Disponibles y activos", tone: "violet" },
    ];
  }, [cargando, conductores, diagnostico, pedidos, rutas, usuario.rol, vehiculos]);

  const style = { "--role-hero": `url(${config.hero})` } as CSSProperties;
  return <div className={`profile-dashboard profile-dashboard--${usuario.rol.toLowerCase()}`} aria-busy={cargando}>
    <section className="role-hero" style={style}>
      <div className="role-hero__content"><span className="role-kicker"><i /> PANEL {usuario.rol}</span><h1>{config.titulo}</h1><p>{config.subtitulo}</p><button onClick={() => onNavigate(config.acciones[0].screen)}>Abrir módulo principal <span>→</span></button></div>
      <div className="role-hero__live"><i /> Datos operativos en vivo</div>
    </section>
    <section className="role-metrics" aria-label="Indicadores reales">{metricas.map((metrica) => <Metric key={metrica.label} {...metrica} />)}</section>
    <section className="role-section"><div className="role-section__heading"><div><span>ACCESOS DEL PERFIL</span><h2>Acciones rápidas</h2></div><small>La interfaz respeta la matriz y el backend valida cada acción.</small></div><div className="role-actions">{config.acciones.map((accion) => {
      const autorizada = puedeVerPantalla(permisos, accion.screen);
      return <button key={accion.titulo} className="role-action" disabled={!autorizada} title={autorizada ? accion.detalle : "No habilitado para este perfil"} onClick={() => onNavigate(accion.screen)}><span className="role-action__mark">{accion.mark}</span><div><strong>{accion.titulo}</strong><small>{autorizada ? accion.detalle : "No habilitado para este perfil"}</small></div><i>{autorizada ? "→" : "×"}</i></button>;
    })}</div></section>
    {diagnosticoError && <div className="inline-error"><span>{diagnosticoError}</span></div>}
    <div className="provisional-note"><strong>Entorno local identificado.</strong> Los datos de acceso usan un repositorio provisional; Supabase no está conectado y ningún secreto se muestra en pantalla.</div>
  </div>;
}
