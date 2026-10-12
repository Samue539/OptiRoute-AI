import { useEffect, useMemo, useState } from "react";
import { ApiError, authApi, distribucionApi, empresasApi } from "../../api/client";
import type {
  EmpresaItem,
  GuiaEvento,
  GuiaItem,
  ResumenGuias,
  RutaAsignada,
  UsuarioInfo,
  ZonaItem,
} from "../../api/types";
import { tienePermiso } from "../../auth/permissions";

type Props = { usuario: UsuarioInfo; permisos: string[] };

type Tab = "rutas" | "buscar" | "resumen" | "asignar";

const RELACIONES = ["DESTINATARIO", "FAMILIAR", "VECINO", "PORTERIA", "EMPLEADO", "OTRO"];
const MOTIVOS_FALLA = [
  "AUSENTE",
  "DIRECCION_INCOMPLETA",
  "RECHAZADO",
  "ZONA_INSEGURA",
  "REPROGRAMADO",
  "OTRO",
];
const ESTADOS_GUIA = ["TODOS", "PENDIENTE", "EN_RUTA", "ENTREGADA", "FALLIDA", "CANCELADA", "DEVUELTA"];
const MAX_FOTO_BYTES = 15 * 1024 * 1024;

function nuevaClave() {
  try {
    return crypto.randomUUID().replaceAll("-", "");
  } catch {
    return `${Date.now().toString(36)}${Math.floor(Math.random() * 1e9).toString(36)}`;
  }
}

function estadoClase(estado: string) {
  return `status status--${estado.toLowerCase().replaceAll("_", "-")}`;
}

function validarFoto(foto: File | null | undefined): string {
  if (!foto) return "Falta la fotografía.";
  if (!["image/jpeg", "image/png", "image/webp"].includes(foto.type)) {
    return "Solo JPEG, PNG o WebP.";
  }
  if (foto.size <= 0 || foto.size > MAX_FOTO_BYTES) return "Máximo 15 MB por foto.";
  return "";
}

export default function DistribucionPanel({ usuario, permisos }: Props) {
  const puedeAsignar = tienePermiso(permisos, "rutas:asignar");
  const [tab, setTab] = useState<Tab>("rutas");
  const [rutas, setRutas] = useState<RutaAsignada[]>([]);
  const [zonas, setZonas] = useState<ZonaItem[]>([]);
  const [resumen, setResumen] = useState<ResumenGuias | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [exito, setExito] = useState("");
  const [sinModulo, setSinModulo] = useState(false);

  const [rutaSel, setRutaSel] = useState<RutaAsignada | null>(null);
  const [guias, setGuias] = useState<GuiaItem[]>([]);
  const [guiasCargando, setGuiasCargando] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("TODOS");

  const [numeroGuia, setNumeroGuia] = useState("");
  const [guiaEncontrada, setGuiaEncontrada] = useState<GuiaItem | null>(null);
  const [buscando, setBuscando] = useState(false);

  const [guiaEntrega, setGuiaEntrega] = useState<GuiaItem | null>(null);
  const [modoFalla, setModoFalla] = useState(false);
  const [receptor, setReceptor] = useState("");
  const [relacion, setRelacion] = useState("DESTINATARIO");
  const [motivo, setMotivo] = useState("AUSENTE");
  const [motivoOtro, setMotivoOtro] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [fotoGuia, setFotoGuia] = useState<File | null>(null);
  const [fotoPaquete, setFotoPaquete] = useState<File | null>(null);
  const [gps, setGps] = useState<{ lat: number; lng: number; precision: number; origen: string } | null>(null);
  const [gpsError, setGpsError] = useState("");
  const [gpsCargando, setGpsCargando] = useState(false);
  const [clave, setClave] = useState(nuevaClave());
  const [enviando, setEnviando] = useState(false);

  const [guiaHist, setGuiaHist] = useState<GuiaItem | null>(null);
  const [eventos, setEventos] = useState<GuiaEvento[]>([]);
  const [histCargando, setHistCargando] = useState(false);

  const [empresas, setEmpresas] = useState<EmpresaItem[]>([]);
  const [usuarios, setUsuarios] = useState<UsuarioInfo[]>([]);
  const [asgEmpresa, setAsgEmpresa] = useState("");
  const [asgCuenta, setAsgCuenta] = useState("");
  const [asgTipo, setAsgTipo] = useState("RUTA");
  const [asgRecurso, setAsgRecurso] = useState("");

  async function cargarTodo() {
    setCargando(true);
    setError("");
    setSinModulo(false);
    try {
      const [r, z, s] = await Promise.all([
        distribucionApi.misRutas(),
        distribucionApi.zonas(),
        distribucionApi.resumen(),
      ]);
      setRutas(r);
      setZonas(z);
      setResumen(s);
      setRutaSel((prev) => {
        if (!r.length) return null;
        if (prev) return r.find((x) => x.id_ruta === prev.id_ruta) || r[0];
        return r[0];
      });
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        setSinModulo(true);
      } else {
        setError(e instanceof Error ? e.message : "No fue posible cargar la distribución.");
      }
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    void cargarTodo();
    if (puedeAsignar) {
      empresasApi.listar().then(setEmpresas).catch(() => undefined);
      authApi.listarUsuarios().then(setUsuarios).catch(() => undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function cargarGuias(ruta: RutaAsignada, search = busqueda, estado = filtroEstado) {
    setGuiasCargando(true);
    setError("");
    try {
      const lista = await distribucionApi.guiasDeRuta(
        ruta.id_ruta,
        search,
        estado === "TODOS" ? "" : estado,
      );
      setGuias(lista);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No fue posible cargar las guías.");
      setGuias([]);
    } finally {
      setGuiasCargando(false);
    }
  }

  useEffect(() => {
    if (rutaSel && tab === "rutas") void cargarGuias(rutaSel);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rutaSel?.id_ruta]);

  async function buscarPorNumero() {
    if (!numeroGuia.trim()) return;
    setBuscando(true);
    setError("");
    setGuiaEncontrada(null);
    try {
      const guia = await distribucionApi.buscarGuia(numeroGuia);
      setGuiaEncontrada(guia);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Guía no encontrada o sin acceso.");
    } finally {
      setBuscando(false);
    }
  }

  function abrirEntrega(guia: GuiaItem, falla: boolean) {
    setGuiaEntrega(guia);
    setModoFalla(falla);
    setReceptor("");
    setRelacion("DESTINATARIO");
    setMotivo("AUSENTE");
    setMotivoOtro("");
    setObservaciones("");
    setFotoGuia(null);
    setFotoPaquete(null);
    setGps(null);
    setGpsError("");
    setClave(nuevaClave());
    setError("");
    setExito("");
  }

  function capturarGps() {
    setGpsError("");
    if (!navigator.geolocation) {
      setGpsError("Este dispositivo no ofrece geolocalización. Registra el origen como MANUAL.");
      return;
    }
    setGpsCargando(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGps({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          precision: Math.round((pos.coords.accuracy || 0) * 10) / 10,
          origen: "GPS",
        });
        setGpsCargando(false);
      },
      (err) => {
        setGpsError(
          err.code === 1
            ? "Permiso de ubicación denegado. Actívalo para registrar el GPS."
            : "No fue posible obtener la ubicación.",
        );
        setGpsCargando(false);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 },
    );
  }

  async function enviarEntrega() {
    if (!guiaEntrega || enviando) return;
    setError("");
    setExito("");
    if (modoFalla) {
      const motivoFinal = motivo === "OTRO" ? motivoOtro.trim() : motivo;
      if (motivoFinal.length < 5) {
        setError("La entrega fallida exige un motivo de al menos 5 caracteres.");
        return;
      }
    } else {
      if (receptor.trim().length < 2) {
        setError("Indica el nombre de quien recibe.");
        return;
      }
      const errG = validarFoto(fotoGuia);
      const errP = validarFoto(fotoPaquete);
      if (errG || errP) {
        setError(`Fotografías: guía (${errG || "ok"}) · paquete (${errP || "ok"}).`);
        return;
      }
    }
    setEnviando(true);
    try {
      const base = {
        gps_latitud: gps?.lat ?? null,
        gps_longitud: gps?.lng ?? null,
        gps_precision_m: gps?.precision ?? null,
        gps_origen: gps?.origen ?? null,
        observaciones: observaciones.trim() || undefined,
        clave_idempotencia: clave,
      };
      let resultado;
      if (modoFalla) {
        const fotos: File[] = [];
        if (fotoGuia) fotos.push(fotoGuia);
        if (fotoPaquete) fotos.push(fotoPaquete);
        resultado = await distribucionApi.registrarNovedad(guiaEntrega.id_guia, {
          tipo: "FALLIDA",
          motivo_falla: motivo === "OTRO" ? motivoOtro.trim() : motivo,
          ...base,
          fotos,
        });
        setExito(
          resultado.duplicada
            ? `Novedad ya registrada (reintento idempotente) para ${guiaEntrega.numero_guia}.`
            : `Entrega fallida registrada para ${guiaEntrega.numero_guia} con motivo.`,
        );
      } else {
        resultado = await distribucionApi.registrarEntrega(guiaEntrega.id_guia, {
          receptor_nombre: receptor.trim(),
          relacion_destinatario: relacion,
          ...base,
          foto_guia: fotoGuia as File,
          foto_paquete: fotoPaquete as File,
        });
        setExito(
          resultado.duplicada
            ? `Entrega ya registrada (reintento idempotente) para ${guiaEntrega.numero_guia}.`
            : `Entrega ${guiaEntrega.numero_guia} registrada a las ${resultado.creado_en || "hora del servidor"}.`,
        );
      }
      setGuiaEntrega(null);
      await cargarTodo();
      if (rutaSel) await cargarGuias(rutaSel);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No fue posible registrar.");
    } finally {
      setEnviando(false);
    }
  }

  async function abrirHistorial(guia: GuiaItem) {
    setGuiaHist(guia);
    setEventos([]);
    setHistCargando(true);
    setError("");
    try {
      const datos = await distribucionApi.historial(guia.id_guia);
      setEventos(datos.eventos);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No fue posible cargar el historial.");
    } finally {
      setHistCargando(false);
    }
  }

  async function verEvidencia(idEvidencia: number) {
    try {
      const { url } = await distribucionApi.urlEvidencia(idEvidencia);
      const baseApi =
        (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_URL ||
        "http://127.0.0.1:8000";
      const final = url.startsWith("http") ? url : `${baseApi.replace(/\/$/, "")}${url}`;
      const token = localStorage.getItem("or_token") || "";
      const resp = await fetch(final, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      if (!resp.ok) throw new Error(`La API respondió ${resp.status}.`);
      const blob = await resp.blob();
      window.open(URL.createObjectURL(blob), "_blank", "noopener");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No fue posible abrir la evidencia.");
    }
  }

  async function asignarRecurso() {
    setError("");
    setExito("");
    if (!asgEmpresa || !asgCuenta || !asgRecurso) {
      setError("Selecciona empresa, cuenta y recurso para asignar.");
      return;
    }
    try {
      const r = await distribucionApi.asignar({
        id_empresa: asgEmpresa,
        id_cuenta: Number(asgCuenta),
        tipo_recurso: asgTipo,
        id_recurso: Number(asgRecurso),
      });
      setExito(`Asignación creada: ${r.tipo_recurso} ${r.id_recurso}.`);
      setAsgRecurso("");
      await cargarTodo();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No fue posible asignar.");
    }
  }

  const guiasFiltradas = useMemo(() => guias, [guias]);

  if (cargando) {
    return (
      <div className="loading-panel">
        <span />
        <strong>Cargando centro de distribución…</strong>
      </div>
    );
  }

  if (sinModulo) {
    return (
      <div className="panel">
        <span className="eyebrow">CENTRO DE DISTRIBUCIÓN</span>
        <h2>Módulo no instalado en este entorno</h2>
        <p className="muted-copy">
          Aplica <code>007_multiempresa_base.sql</code>, <code>008_guias_evidencias_zonas.sql</code> y el seed{" "}
          <code>005_distribucion_demo.sql</code> en la base de desarrollo. No se muestran datos simulados.
        </p>
      </div>
    );
  }

  return (
    <div className="dist-panel">
      <section className="panel dist-head">
        <div>
          <span className="eyebrow">CENTRO DE DISTRIBUCIÓN Y ENTREGAS · {usuario.rol}</span>
          <h2>Mis rutas asignadas</h2>
          <p className="muted-copy">
            {usuario.nombres} {usuario.apellidos} · Datos reales de la base de desarrollo.
          </p>
        </div>
        <div className="dist-tabs" role="tablist">
          {(
            [
              ["rutas", "Mis rutas"],
              ["buscar", "Buscar guía"],
              ["resumen", "Resumen"],
              ...(puedeAsignar ? [["asignar", "Asignar"] as [Tab, string]] : []),
            ] as Array<[Tab, string]>
          ).map(([id, label]) => (
            <button
              key={id}
              role="tab"
              aria-selected={tab === id}
              className={tab === id ? "dist-tab dist-tab--active" : "dist-tab"}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      {error && (
        <div className="inline-error">
          <span>{error}</span>
        </div>
      )}
      {exito && <div className="inline-success">{exito}</div>}

      {tab === "rutas" && (
        <>
          {!rutas.length ? (
            <div className="panel empty-state">
              <strong>No tienes rutas asignadas</strong>
              <p>Solicita al administrador que te asigne una ruta o zona para comenzar a entregar.</p>
            </div>
          ) : (
            <div className="dist-rutas">
              {rutas.map((ruta) => (
                <button
                  key={ruta.id_ruta}
                  className={rutaSel?.id_ruta === ruta.id_ruta ? "dist-ruta dist-ruta--active" : "dist-ruta"}
                  onClick={() => {
                    setRutaSel(ruta);
                    setBusqueda("");
                    setFiltroEstado("TODOS");
                    void cargarGuias(ruta, "", "TODOS");
                  }}
                >
                  <div className="dist-ruta__top">
                    <strong>{ruta.nombre_ruta || ruta.codigo}</strong>
                    <span className={estadoClase(ruta.estado)}>{ruta.estado}</span>
                  </div>
                  <small>
                    {ruta.zona ? `Zona ${ruta.zona.nombre}` : "Sin zona"} ·{" "}
                    {ruta.conductor ? `${ruta.conductor.nombres} ${ruta.conductor.apellidos}` : "Sin conductor"} ·{" "}
                    {ruta.vehiculo?.placa || "Sin vehículo"}
                  </small>
                  <div className="dist-progress">
                    <div className="dist-progress__track">
                      <span
                        style={{
                          width: `${ruta.progreso.total ? Math.round((ruta.progreso.entregadas / ruta.progreso.total) * 100) : 0}%`,
                        }}
                      />
                    </div>
                    <small>
                      {ruta.progreso.entregadas} de {ruta.progreso.total} entregadas
                      {ruta.progreso.fallidas > 0 && ` · ${ruta.progreso.fallidas} fallidas`}
                    </small>
                  </div>
                </button>
              ))}
            </div>
          )}

          {rutaSel && (
            <section className="panel">
              <div className="panel__heading">
                <div>
                  <span className="eyebrow">
                    GUÍAS DE LA RUTA · {rutaSel.nombre_ruta || rutaSel.codigo}
                    {rutaSel.zona ? ` · ZONA ${rutaSel.zona.nombre.toUpperCase()}` : ""}
                  </span>
                  <h3>
                    {guiasFiltradas.length} guías{rutaSel.estado !== "EN_RUTA" && " · inicia la ruta para entregar"}
                  </h3>
                </div>
              </div>
              <div className="dist-filtros">
                <input
                  placeholder="Buscar por número de guía"
                  value={busqueda}
                  onChange={(e) => {
                    setBusqueda(e.target.value);
                    void cargarGuias(rutaSel, e.target.value, filtroEstado);
                  }}
                />
                <select
                  value={filtroEstado}
                  onChange={(e) => {
                    setFiltroEstado(e.target.value);
                    void cargarGuias(rutaSel, busqueda, e.target.value);
                  }}
                >
                  {ESTADOS_GUIA.map((e) => (
                    <option key={e} value={e}>
                      {e === "TODOS" ? "Todos los estados" : e}
                    </option>
                  ))}
                </select>
              </div>
              {guiasCargando ? (
                <div className="loading-panel">
                  <span />
                  <strong>Cargando guías…</strong>
                </div>
              ) : !guiasFiltradas.length ? (
                <div className="empty-state">
                  <strong>Sin guías</strong>
                  <p>Esta ruta aún no tiene guías o ninguna coincide con el filtro.</p>
                </div>
              ) : (
                <div className="dist-guias">
                  {guiasFiltradas.map((guia) => (
                    <article key={guia.id_guia} className="dist-guia">
                      <div className="dist-guia__main">
                        <div className="dist-guia__top">
                          <strong>{guia.numero_guia}</strong>
                          <span className={estadoClase(guia.estado)}>{guia.estado}</span>
                        </div>
                        <div>
                          <strong>{guia.destinatario_nombre}</strong>
                        </div>
                        <small>{guia.direccion_texto}</small>
                        <small>Tel. autorizado: {guia.telefono_autorizado || "—"}</small>
                        {guia.intentos_entrega > 0 && <small>Intentos: {guia.intentos_entrega}</small>}
                      </div>
                      <div className="dist-guia__actions">
                        <button
                          className="secondary-button"
                          disabled={["ENTREGADA", "CANCELADA", "DEVUELTA"].includes(guia.estado)}
                          onClick={() => abrirEntrega(guia, false)}
                        >
                          Registrar entrega
                        </button>
                        <button className="quiet-button" onClick={() => abrirHistorial(guia)}>
                          Historial
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}

      {tab === "buscar" && (
        <section className="panel">
          <span className="eyebrow">BÚSQUEDA POR NÚMERO DE GUÍA</span>
          <h3>Localizar guía asignada</h3>
          <div className="dist-filtros">
            <input
              placeholder="Ej. GUI-PED-DEMO-004"
              value={numeroGuia}
              onChange={(e) => setNumeroGuia(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void buscarPorNumero();
              }}
            />
            <button className="primary-button" disabled={buscando || !numeroGuia.trim()} onClick={() => void buscarPorNumero()}>
              {buscando ? "Buscando…" : "Buscar"}
            </button>
          </div>
          {guiaEncontrada && (
            <article className="dist-guia">
              <div className="dist-guia__main">
                <div className="dist-guia__top">
                  <strong>{guiaEncontrada.numero_guia}</strong>
                  <span className={estadoClase(guiaEncontrada.estado)}>{guiaEncontrada.estado}</span>
                </div>
                <div>
                  <strong>{guiaEncontrada.destinatario_nombre}</strong>
                </div>
                <small>{guiaEncontrada.direccion_texto}</small>
                <small>Tel. autorizado: {guiaEncontrada.telefono_autorizado || "—"}</small>
                <small>
                  Ruta: {guiaEncontrada.ruta_codigo || "—"}
                  {guiaEncontrada.zona ? ` · Zona ${guiaEncontrada.zona.nombre}` : ""}
                </small>
              </div>
              <div className="dist-guia__actions">
                <button
                  className="secondary-button"
                  disabled={["ENTREGADA", "CANCELADA", "DEVUELTA"].includes(guiaEncontrada.estado)}
                  onClick={() => abrirEntrega(guiaEncontrada, false)}
                >
                  Registrar entrega
                </button>
                <button className="quiet-button" onClick={() => abrirHistorial(guiaEncontrada)}>
                  Historial
                </button>
              </div>
            </article>
          )}
        </section>
      )}

      {tab === "resumen" && resumen && (
        <section className="panel">
          <span className="eyebrow">CANTIDADES REALES</span>
          <h3>Resumen de mis guías</h3>
          <div className="dist-resumen">
            <div className="dist-kpi dist-kpi--orange">
              <span>Pendientes</span>
              <strong>{resumen.pendientes}</strong>
            </div>
            <div className="dist-kpi dist-kpi--blue">
              <span>En ruta</span>
              <strong>{resumen.en_ruta}</strong>
            </div>
            <div className="dist-kpi dist-kpi--green">
              <span>Entregadas</span>
              <strong>{resumen.entregadas}</strong>
            </div>
            <div className="dist-kpi dist-kpi--coral">
              <span>Fallidas</span>
              <strong>{resumen.fallidas}</strong>
            </div>
            <div className="dist-kpi">
              <span>Total</span>
              <strong>{resumen.total}</strong>
            </div>
          </div>
          <p className="muted-copy">Conteos calculados en el servidor sobre tus guías asignadas.</p>
        </section>
      )}

      {tab === "asignar" && puedeAsignar && (
        <section className="panel">
          <span className="eyebrow">ADMINISTRACIÓN</span>
          <h3>Asignar ruta, zona o guía</h3>
          <p className="muted-copy">
            Vincula el recurso a la empresa y lo asigna a la membresía de la cuenta. El acceso se restringe a lo
            asignado.
          </p>
          <div className="dist-form">
            <label>
              Empresa
              <select value={asgEmpresa} onChange={(e) => setAsgEmpresa(e.target.value)}>
                <option value="">Seleccionar…</option>
                {empresas.map((e) => (
                  <option key={e.id_empresa} value={e.id_empresa}>
                    {e.nombre} ({e.codigo})
                  </option>
                ))}
              </select>
            </label>
            <label>
              Cuenta (operador o conductor)
              <select value={asgCuenta} onChange={(e) => setAsgCuenta(e.target.value)}>
                <option value="">Seleccionar…</option>
                {usuarios
                  .filter((u) => ["OPERADOR", "CONDUCTOR"].includes(u.rol))
                  .map((u) => (
                    <option key={u.id_usuario} value={u.id_usuario}>
                      {u.nombres} {u.apellidos} · {u.rol} · {u.correo}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Tipo de recurso
              <select value={asgTipo} onChange={(e) => setAsgTipo(e.target.value)}>
                <option value="RUTA">RUTA</option>
                <option value="ZONA">ZONA</option>
                <option value="GUIA">GUIA</option>
              </select>
            </label>
            <label>
              ID del recurso
              <input
                inputMode="numeric"
                placeholder={asgTipo === "RUTA" ? "Ej. 3 (id_ruta)" : asgTipo === "ZONA" ? "Ej. 1 (id_zona)" : "Ej. 12 (id_guia)"}
                value={asgRecurso}
                onChange={(e) => setAsgRecurso(e.target.value.replace(/[^0-9]/g, ""))}
              />
            </label>
            <button className="primary-button" onClick={() => void asignarRecurso()}>
              Asignar
            </button>
          </div>
          {zonas.length > 0 && (
            <small className="muted-copy">
              Zonas disponibles: {zonas.map((z) => `${z.id_zona}·${z.nombre}`).join(" · ")}
            </small>
          )}
        </section>
      )}

      {guiaEntrega && (
        <div className="dist-modal" role="dialog" aria-modal="true" aria-label="Registrar entrega">
          <div className="dist-modal__card">
            <div className="panel__heading">
              <div>
                <span className="eyebrow">{modoFalla ? "ENTREGA FALLIDA" : "REGISTRAR ENTREGA"}</span>
                <h3>{guiaEntrega.numero_guia}</h3>
              </div>
              <button className="quiet-button" onClick={() => setGuiaEntrega(null)}>
                Cerrar
              </button>
            </div>
            <div className="dist-form">
              <div className="dist-switch">
                <button
                  className={modoFalla ? "quiet-button" : "secondary-button"}
                  onClick={() => setModoFalla(false)}
                >
                  Exitosa
                </button>
                <button
                  className={modoFalla ? "secondary-button" : "quiet-button"}
                  onClick={() => setModoFalla(true)}
                >
                  Fallida
                </button>
              </div>
              {!modoFalla ? (
                <>
                  <label>
                    Nombre de quien recibe
                    <input value={receptor} onChange={(e) => setReceptor(e.target.value)} placeholder="Ej. María Pérez" maxLength={150} />
                  </label>
                  <label>
                    Relación con el destinatario
                    <select value={relacion} onChange={(e) => setRelacion(e.target.value)}>
                      {RELACIONES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Fotografía de la guía entregada
                    <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(e) => setFotoGuia(e.target.files?.[0] || null)} />
                    {fotoGuia && <small>{fotoGuia.name} · {Math.round(fotoGuia.size / 1024)} KB</small>}
                  </label>
                  <label>
                    Fotografía del paquete entregado
                    <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(e) => setFotoPaquete(e.target.files?.[0] || null)} />
                    {fotoPaquete && <small>{fotoPaquete.name} · {Math.round(fotoPaquete.size / 1024)} KB</small>}
                  </label>
                </>
              ) : (
                <>
                  <label>
                    Motivo de la falla
                    <select value={motivo} onChange={(e) => setMotivo(e.target.value)}>
                      {MOTIVOS_FALLA.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </label>
                  {motivo === "OTRO" && (
                    <label>
                      Detalle del motivo
                      <input value={motivoOtro} onChange={(e) => setMotivoOtro(e.target.value)} placeholder="Describe el motivo" maxLength={300} />
                    </label>
                  )}
                  <label>
                    Foto opcional (evidencia)
                    <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(e) => setFotoGuia(e.target.files?.[0] || null)} />
                  </label>
                </>
              )}
              <label>
                Observaciones
                <input value={observaciones} onChange={(e) => setObservaciones(e.target.value)} placeholder="Opcional" maxLength={500} />
              </label>
              <div className="dist-gps">
                <button className="quiet-button" disabled={gpsCargando} onClick={capturarGps}>
                  {gpsCargando ? "Capturando…" : "📍 Capturar ubicación GPS"}
                </button>
                {gps ? (
                  <small>
                    {gps.lat.toFixed(6)}, {gps.lng.toFixed(6)} · ±{gps.precision} m · origen {gps.origen}
                  </small>
                ) : (
                  <small className="muted-copy">Se solicita permiso del dispositivo. La fecha y hora las pone el servidor.</small>
                )}
                {gpsError && <small className="dist-gps__error">{gpsError}</small>}
              </div>
              <button className="primary-button" disabled={enviando} onClick={() => void enviarEntrega()}>
                {enviando ? "Guardando…" : modoFalla ? "Registrar falla" : "Confirmar entrega"}
              </button>
            </div>
          </div>
        </div>
      )}

      {guiaHist && (
        <div className="dist-modal" role="dialog" aria-modal="true" aria-label="Historial de la guía">
          <div className="dist-modal__card">
            <div className="panel__heading">
              <div>
                <span className="eyebrow">HISTORIAL DE MOVIMIENTOS</span>
                <h3>{guiaHist.numero_guia}</h3>
              </div>
              <button className="quiet-button" onClick={() => setGuiaHist(null)}>
                Cerrar
              </button>
            </div>
            {histCargando ? (
              <div className="loading-panel">
                <span />
                <strong>Cargando historial…</strong>
              </div>
            ) : !eventos.length ? (
              <p className="muted-copy">Esta guía aún no tiene movimientos registrados.</p>
            ) : (
              <ol className="dist-timeline">
                {eventos.map((ev) => (
                  <li key={ev.id_evento}>
                    <div className="dist-timeline__head">
                      <strong>{ev.tipo}</strong>
                      <small>{ev.creado_en ? new Date(ev.creado_en).toLocaleString() : "—"}</small>
                    </div>
                    {ev.receptor_nombre && (
                      <small>
                        Recibió {ev.receptor_nombre} ({ev.relacion_destinatario})
                      </small>
                    )}
                    {ev.motivo_falla && <small>Motivo: {ev.motivo_falla}</small>}
                    {(ev.gps_latitud != null || ev.gps_origen) && (
                      <small>
                        GPS: {ev.gps_latitud ?? "—"}, {ev.gps_longitud ?? "—"}
                        {ev.gps_precision_m != null && ` · ±${ev.gps_precision_m} m`}
                        {ev.gps_origen && ` · ${ev.gps_origen}`}
                      </small>
                    )}
                    {ev.observaciones && <small>{ev.observaciones}</small>}
                    {ev.evidencias.length > 0 && (
                      <div className="dist-evidencias">
                        {ev.evidencias.map((v) => (
                          <button key={v.id_evidencia} className="quiet-button" onClick={() => void verEvidencia(v.id_evidencia)}>
                            🖼 {v.tipo} · {Math.round(v.tamano_bytes / 1024)} KB
                          </button>
                        ))}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
