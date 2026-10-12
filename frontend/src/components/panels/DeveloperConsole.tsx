import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { authApi } from "../../api/client";
import type {
  DriverCatalogItem,
  OrderCatalogItem,
  RouteSummary,
  Screen,
  UsuarioInfo,
  VehicleCatalogItem,
} from "../../api/types";
import PermissionMatrix from "./PermissionMatrix";
import UsersManager from "./UsersManager";

/**
 * Centro de Control del DESARROLLADOR.
 *
 * Organiza en módulos las capacidades reales expuestas por los endpoints
 * seguros del backend (usuarios, roles, auditoría, diagnóstico). No muestra
 * datos simulados: cada cifra proviene de la API o de los catálogos cargados.
 */

type Modulo = "resumen" | "usuarios" | "roles" | "auditoria" | "diagnostico" | "configuracion";

const MODULOS: Array<{ id: Modulo; label: string; icon: string; detalle: string }> = [
  { id: "resumen", label: "Resumen", icon: "📊", detalle: "Métricas operativas" },
  { id: "usuarios", label: "Usuarios", icon: "🛡️", detalle: "Altas, perfiles y accesos" },
  { id: "roles", label: "Roles y permisos", icon: "🔐", detalle: "Matriz y restricciones" },
  { id: "auditoria", label: "Auditoría", icon: "🧾", detalle: "Eventos registrados" },
  { id: "diagnostico", label: "Diagnóstico", icon: "🩺", detalle: "Estado de servicios" },
  { id: "configuracion", label: "Configuración", icon: "⚙️", detalle: "Parámetros técnicos" },
];

type Toast = { id: number; tipo: "ok" | "error"; mensaje: string };

type Props = {
  usuario: UsuarioInfo;
  rutas: RouteSummary[];
  pedidos: OrderCatalogItem[];
  conductores: DriverCatalogItem[];
  vehiculos: VehicleCatalogItem[];
  cargando: boolean;
  onNavigate: (pantalla: Screen) => void;
};

function Kpi({
  etiqueta,
  valor,
  detalle,
  variante,
}: {
  etiqueta: string;
  valor: string | number;
  detalle: string;
  variante: "azul" | "verde" | "violeta" | "ambar" | "cyan";
}) {
  return (
    <article className={`kpi-card kpi-card--${variante}`}>
      <span className="kpi-card__label">{etiqueta}</span>
      <strong className="kpi-card__value">{valor}</strong>
      <small className="kpi-card__detalle">{detalle}</small>
    </article>
  );
}

export default function DeveloperConsole({
  usuario,
  rutas,
  pedidos,
  conductores,
  vehiculos,
  cargando,
  onNavigate,
}: Props) {
  const [modulo, setModulo] = useState<Modulo>("resumen");
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [diagnostico, setDiagnostico] = useState<any>(null);
  const [diagCargando, setDiagCargando] = useState(true);
  const [diagError, setDiagError] = useState("");
  const [auditoria, setAuditoria] = useState<any[]>([]);
  const [auditCargando, setAuditCargando] = useState(true);
  const [auditError, setAuditError] = useState("");
  const [auditFiltro, setAuditFiltro] = useState("");

  const avisar = useCallback((tipo: "ok" | "error", mensaje: string) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, tipo, mensaje }]);
    window.setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5200);
  }, []);

  const cargarDiagnostico = useCallback(async () => {
    setDiagCargando(true);
    setDiagError("");
    try {
      setDiagnostico(await authApi.diagnostico());
    } catch (e) {
      setDiagError(e instanceof Error ? e.message : "No fue posible cargar el diagnóstico.");
    } finally {
      setDiagCargando(false);
    }
  }, []);

  const cargarAuditoria = useCallback(async () => {
    setAuditCargando(true);
    setAuditError("");
    try {
      setAuditoria(await authApi.auditoria(60));
    } catch (e) {
      setAuditError(e instanceof Error ? e.message : "No fue posible cargar la auditoría.");
    } finally {
      setAuditCargando(false);
    }
  }, []);

  useEffect(() => {
    void cargarDiagnostico();
  }, [cargarDiagnostico]);

  useEffect(() => {
    if (modulo === "auditoria" && auditoria.length === 0 && !auditError) {
      void cargarAuditoria();
    }
  }, [modulo, auditoria.length, auditError, cargarAuditoria]);

  const rutasActivas = useMemo(
    () => rutas.filter((r) => !["COMPLETADA", "CANCELADA"].includes(r.estado)),
    [rutas],
  );
  const pedidosPendientes = useMemo(
    () => pedidos.filter((p) => p.estado === "PENDIENTE"),
    [pedidos],
  );
  const conductoresDisponibles = useMemo(
    () => conductores.filter((c) => c.disponible),
    [conductores],
  );

  const eventos = useMemo(() => {
    const termino = auditFiltro.trim().toLowerCase();
    if (!termino) return auditoria;
    return auditoria.filter((evento) =>
      [evento.accion, evento.actor, evento.objetivo, evento.rol]
        .filter(Boolean)
        .some((campo: string) => campo.toLowerCase().includes(termino)),
    );
  }, [auditoria, auditFiltro]);

  const cuentasPorRol = diagnostico?.cuentas?.por_rol ?? {};

  return (
    <div className="dev-console">
      <header className="dev-hero">
        <div>
          <span className="eyebrow">Centro de control · {usuario.rol}</span>
          <h1>OptiRoute-AI · Panel del desarrollador</h1>
          <p>
            Administración técnica de la plataforma: cuentas, perfiles, auditoría y
            diagnóstico. Todas las acciones se validan en el servidor.
          </p>
        </div>
        <div className="dev-hero__meta">
          <span className={`dev-hero__chip${diagError ? " dev-hero__chip--alerta" : ""}`}>
            <i /> {diagError ? "API con errores" : diagCargando ? "Verificando API…" : "API en línea"}
          </span>
          <span className="dev-hero__chip dev-hero__chip--neutral">{usuario.correo}</span>
        </div>
      </header>

      <nav className="dev-tabs" aria-label="Módulos del centro de control">
        {MODULOS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={modulo === item.id}
            className={`dev-tab${modulo === item.id ? " dev-tab--active" : ""}`}
            onClick={() => setModulo(item.id)}
          >
            <span aria-hidden>{item.icon}</span>
            <strong>{item.label}</strong>
            <small>{item.detalle}</small>
          </button>
        ))}
      </nav>

      <div className="toast-stack" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast--${toast.tipo}`}>
            <span aria-hidden>{toast.tipo === "ok" ? "✓" : "!"}</span>
            <p>{toast.mensaje}</p>
          </div>
        ))}
      </div>

      {modulo === "resumen" && (
        <section className="dev-module">
          <div className="kpi-grid">
            <Kpi
              etiqueta="Rutas activas"
              valor={cargando ? "…" : rutasActivas.length}
              detalle={`${cargando ? "…" : rutas.length} rutas en total`}
              variante="azul"
            />
            <Kpi
              etiqueta="Pedidos pendientes"
              valor={cargando ? "…" : pedidosPendientes.length}
              detalle={`${cargando ? "…" : pedidos.length} pedidos registrados`}
              variante="ambar"
            />
            <Kpi
              etiqueta="Conductores disponibles"
              valor={cargando ? "…" : conductoresDisponibles.length}
              detalle={`${cargando ? "…" : conductores.length} en el catálogo`}
              variante="verde"
            />
            <Kpi
              etiqueta="Vehículos"
              valor={cargando ? "…" : vehiculos.length}
              detalle="Flota registrada"
              variante="cyan"
            />
            <Kpi
              etiqueta="Cuentas activas"
              valor={diagCargando ? "…" : (diagnostico?.cuentas?.activas ?? "—")}
              detalle={
                diagnostico?.cuentas
                  ? `${diagnostico.cuentas.total} cuentas en total`
                  : "Desde /api/auth/diagnostico"
              }
              variante="violeta"
            />
            <Kpi
              etiqueta="Sesiones activas"
              valor={diagCargando ? "…" : (diagnostico?.sesiones?.activas ?? "—")}
              detalle={
                diagnostico?.sesiones
                  ? `Expiran a las ${diagnostico.sesiones.duracion_horas} h`
                  : "Desde /api/auth/diagnostico"
              }
              variante="azul"
            />
          </div>

          <div className="dev-quick">
            <h3>Accesos rápidos</h3>
            <div className="dev-quick__grid">
              <button className="dev-quick__item" onClick={() => setModulo("usuarios")}>
                <strong>Gestionar usuarios</strong>
                <small>Crear cuentas, cambiar perfiles y restablecer accesos</small>
              </button>
              <button className="dev-quick__item" onClick={() => setModulo("auditoria")}>
                <strong>Revisar auditoría</strong>
                <small>Eventos de acceso y administración de cuentas</small>
              </button>
              <button className="dev-quick__item" onClick={() => onNavigate("pedidos")}>
                <strong>Ir a Pedidos</strong>
                <small>Operación diaria del negocio</small>
              </button>
              <button className="dev-quick__item" onClick={() => onNavigate("rutas")}>
                <strong>Ir a Rutas</strong>
                <small>Planificación y seguimiento</small>
              </button>
            </div>
          </div>

          {diagError && (
            <div className="inline-error">
              <span>{diagError}</span>
            </div>
          )}
        </section>
      )}

      {modulo === "usuarios" && (
        <section className="dev-module">
          <UsersManager usuario={usuario} onAviso={avisar} />
        </section>
      )}

      {modulo === "roles" && (
        <section className="dev-module">
          <PermissionMatrix />
        </section>
      )}

      {modulo === "auditoria" && (
        <section className="dev-module">
          <div className="panel">
            <div className="panel__heading">
              <div>
                <span className="eyebrow">Bitácora</span>
                <h2>Auditoría de accesos y cuentas</h2>
              </div>
              <button className="quiet-button" onClick={() => void cargarAuditoria()} disabled={auditCargando}>
                {auditCargando ? "Actualizando…" : "Actualizar"}
              </button>
            </div>
            <form
              className="dev-filter"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
              }}
            >
              <input
                type="search"
                placeholder="Filtrar por acción, actor u objetivo…"
                value={auditFiltro}
                onChange={(e) => setAuditFiltro(e.target.value)}
                aria-label="Filtrar eventos de auditoría"
              />
              <small>{eventos.length} eventos</small>
            </form>
            {auditError ? (
              <div className="inline-error">
                <span>{auditError}</span>
              </div>
            ) : auditCargando ? (
              <div className="loading-panel">
                <span />
                <strong>Cargando auditoría…</strong>
              </div>
            ) : eventos.length === 0 ? (
              <div className="empty-state">
                <span className="empty-state__mark">AU</span>
                <strong>Sin eventos registrados</strong>
                <p>
                  {auditoria.length === 0
                    ? "Todavía no hay actividad: inicios de sesión y cambios de cuentas se registrarán aquí."
                    : "Ningún evento coincide con el filtro aplicado."}
                </p>
              </div>
            ) : (
              <div className="table-scroll">
                <table className="data-table data-table--audit">
                  <thead>
                    <tr>
                      <th>Evento</th>
                      <th>Actor</th>
                      <th>Detalle</th>
                      <th>Fecha</th>
                    </tr>
                  </thead>
                  <tbody>
                    {eventos.map((evento, indice) => (
                      <tr key={`${evento.creado_en ?? indice}-${indice}`}>
                        <td>
                          <span className={`audit-tag audit-tag--${evento.accion?.includes("fallido") || evento.accion?.includes("inactiva") ? "alerta" : "normal"}`}>
                            {evento.accion || "evento"}
                          </span>
                        </td>
                        <td>{evento.actor || "sistema"}</td>
                        <td>
                          {[
                            evento.objetivo ? `objetivo: ${evento.objetivo}` : null,
                            evento.rol ? `rol: ${evento.rol}` : null,
                            evento.detalle || null,
                            typeof evento.sesiones_revocadas === "number"
                              ? `sesiones revocadas: ${evento.sesiones_revocadas}`
                              : null,
                          ]
                            .filter(Boolean)
                            .join(" · ") || "—"}
                        </td>
                        <td>
                          <small>{evento.creado_en ? new Date(evento.creado_en).toLocaleString("es-CO") : "—"}</small>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="access-hint">
              La bitácora no incluye contraseñas, hashes, tokens ni valores de variables de
              entorno.
            </p>
          </div>
        </section>
      )}

      {modulo === "diagnostico" && (
        <section className="dev-module">
          <div className="panel">
            <div className="panel__heading">
              <div>
                <span className="eyebrow">Estado técnico</span>
                <h2>Diagnóstico de servicios</h2>
              </div>
              <button className="quiet-button" onClick={() => void cargarDiagnostico()} disabled={diagCargando}>
                {diagCargando ? "Actualizando…" : "Actualizar"}
              </button>
            </div>
            {diagError ? (
              <div className="inline-error">
                <span>{diagError}</span>
              </div>
            ) : diagCargando || !diagnostico ? (
              <div className="loading-panel">
                <span />
                <strong>Cargando diagnóstico…</strong>
              </div>
            ) : (
              <div className="diag-grid">
                <article className="diag-card">
                  <h3>Almacenamiento de acceso</h3>
                  <dl>
                    <div>
                      <dt>Backend</dt>
                      <dd>{diagnostico.almacenamiento?.backend}</dd>
                    </div>
                    <div>
                      <dt>Modo</dt>
                      <dd>{diagnostico.almacenamiento?.provisional ? "Provisional (JSON local)" : "Persistente"}</dd>
                    </div>
                    <div>
                      <dt>Supabase</dt>
                      <dd>{diagnostico.almacenamiento?.supabase_conectado ? "Conectado" : "No conectado (pendiente de migración)"}</dd>
                    </div>
                  </dl>
                </article>
                <article className="diag-card">
                  <h3>Cuentas</h3>
                  <dl>
                    <div>
                      <dt>Totales</dt>
                      <dd>{diagnostico.cuentas?.total}</dd>
                    </div>
                    <div>
                      <dt>Activas</dt>
                      <dd>{diagnostico.cuentas?.activas}</dd>
                    </div>
                    <div>
                      <dt>Propietario</dt>
                      <dd>{diagnostico.cuentas?.propietario ? diagnostico.cuentas.propietario.correo : "Sin definir"}</dd>
                    </div>
                    <div>
                      <dt>Por perfil</dt>
                      <dd>
                        {Object.keys(cuentasPorRol).length
                          ? Object.entries(cuentasPorRol)
                              .map(([rol, total]) => `${rol}: ${total}`)
                              .join(" · ")
                          : "—"}
                      </dd>
                    </div>
                  </dl>
                </article>
                <article className="diag-card">
                  <h3>Sesiones</h3>
                  <dl>
                    <div>
                      <dt>Activas</dt>
                      <dd>{diagnostico.sesiones?.activas}</dd>
                    </div>
                    <div>
                      <dt>Duración</dt>
                      <dd>{diagnostico.sesiones?.duracion_horas} horas</dd>
                    </div>
                    <div>
                      <dt>Modo demo</dt>
                      <dd>{diagnostico.modo_demo ? "Activado" : "Desactivado"}</dd>
                    </div>
                  </dl>
                </article>
              </div>
            )}
            <p className="access-hint">
              Fuente: <code>GET /api/auth/diagnostico</code> (permiso{" "}
              <code>diagnostico:ver</code>). Nunca expone contraseñas, hashes, tokens ni
              valores de <code>.env</code>.
            </p>
          </div>
        </section>
      )}

      {modulo === "configuracion" && (
        <section className="dev-module">
          <div className="panel">
            <div className="panel__heading">
              <div>
                <span className="eyebrow">Parámetros técnicos</span>
                <h2>Configuración del desarrollador</h2>
              </div>
            </div>
            <p className="muted-copy">
              Estos parámetros se configuran por variables de entorno en el backend. Se
              muestran sus valores actuales solo cuando no son sensibles.
            </p>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Variable</th>
                    <th>Propósito</th>
                    <th>Valor actual</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>
                      <code>OPTIROUTE_AUTH_STORAGE</code>
                    </td>
                    <td>Backend de almacenamiento de cuentas y sesiones</td>
                    <td>{diagnostico?.almacenamiento?.backend ?? "local (por defecto)"}</td>
                  </tr>
                  <tr>
                    <td>
                      <code>AUTH_SESSION_HORAS</code>
                    </td>
                    <td>Duración de las sesiones emitidas</td>
                    <td>{diagnostico?.sesiones?.duracion_horas ?? "8"} horas</td>
                  </tr>
                  <tr>
                    <td>
                      <code>AUTH_PBKDF2_ITERACIONES</code>
                    </td>
                    <td>Iteraciones del hash de contraseñas</td>
                    <td>210000 (valor por defecto, no sensible)</td>
                  </tr>
                  <tr>
                    <td>
                      <code>OPTIROUTE_DEMO</code>
                    </td>
                    <td>Modo demostración del diagnóstico</td>
                    <td>{diagnostico?.modo_demo ? "activado" : "desactivado"}</td>
                  </tr>
                  <tr>
                    <td>
                      <code>FRONTEND_ORIGINS</code>
                    </td>
                    <td>Orígenes permitidos por CORS</td>
                    <td>Definido en .env del backend (valor no mostrado)</td>
                  </tr>
                  <tr>
                    <td>
                      <code>DB_*</code>
                    </td>
                    <td>Conexión a PostgreSQL (datos logísticos)</td>
                    <td>Definido en .env del backend (valor no mostrado)</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="access-hint">
              La configuración operativa y de interfaz continúa disponible en la pantalla
              <strong> Configuración</strong> del menú principal. No se almacenan secretos
              en el frontend.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}
