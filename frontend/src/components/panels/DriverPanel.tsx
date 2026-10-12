import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { RouteDetail, RouteOrder, RouteSummary } from "../../api/types";
import LeafletMap from "../LeafletMap";

type Props = { rutas: RouteSummary[]; onRefresh: () => Promise<void> | void };

export default function DriverPanel({ rutas, onRefresh }: Props) {
  const ruta = rutas.find((item) => !["COMPLETADA", "CANCELADA"].includes(item.estado)) || rutas[0];
  const [detalle, setDetalle] = useState<RouteDetail | null>(null);
  const [pedidos, setPedidos] = useState<RouteOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [novedad, setNovedad] = useState("");

  async function recargar() {
    if (!ruta) return;
    setLoading(true); setError("");
    try {
      const [route, orders] = await Promise.all([api.getRoute(ruta.id_ruta), api.listRouteOrders(ruta.id_ruta)]);
      setDetalle(route); setPedidos(orders);
    } catch (e) { setError(e instanceof Error ? e.message : "No fue posible cargar la ruta."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void recargar(); }, [ruta?.id_ruta]);

  async function ejecutar(clave: string, accion: () => Promise<unknown>, mensaje: string) {
    setProcessing(clave); setError(""); setSuccess("");
    try { await accion(); setSuccess(mensaje); await onRefresh(); await recargar(); }
    catch (e) { setError(e instanceof Error ? e.message : "La operacion no pudo completarse."); }
    finally { setProcessing(""); }
  }

  if (!ruta) return <div className="panel empty-state"><strong>Sin rutas asignadas</strong><p>Cuando exista una asignacion propia aparecera aqui.</p></div>;
  const pendientes = pedidos.filter((pedido) => pedido.estado !== "ENTREGADO");
  const puntos = (detalle?.puntos ?? []).map((punto) => ({
    id: punto.id_nodo,
    nombre: punto.nombre,
    lat: punto.latitud,
    lng: punto.longitud,
    tipo: punto.tipo_nodo,
    orden: punto.orden,
  }));

  return <div className="driver-panel">
    <section className="panel driver-summary">
      <div><span className="eyebrow">MI RUTA · {ruta.estado}</span><h2>{ruta.codigo}</h2><p>{ruta.origen.nombre} → {ruta.destino.nombre}</p></div>
      <button className="primary-button" disabled={!!processing || ruta.estado !== "ASIGNADA"} onClick={() => void ejecutar("iniciar", () => api.changeRouteState(ruta.id_ruta, "EN_RUTA"), "Ruta iniciada.")}>{processing === "iniciar" ? "Iniciando…" : "Iniciar ruta"}</button>
    </section>
    {loading ? <div className="loading-panel"><span /><strong>Cargando asignacion…</strong></div> : <>
      {detalle && puntos.length > 0 && <section className="panel driver-map">
        <div className="panel__heading"><div><span className="eyebrow">RECORRIDO AUTORIZADO</span><h3>Mapa de la ruta</h3></div><small>{puntos.length} puntos · {detalle.distancia_total_km ?? 0} km</small></div>
        <LeafletMap
          points={puntos}
          routes={[{ id: ruta.codigo, points: puntos, color: "#0f766e", label: ruta.codigo }]}
          height={320}
        />
        <div className="driver-stops" aria-label="Secuencia del recorrido">
          {detalle.puntos.map((punto) => <div key={`${punto.orden}-${punto.id_nodo}`}>
            <span>{punto.orden}</span>
            <div><strong>{punto.nombre}</strong><small>{punto.tipo_nodo} · {punto.distancia_acumulada_km ?? 0} km acumulados</small></div>
            <a className="quiet-button" href={`https://www.google.com/maps/dir/?api=1&destination=${punto.latitud},${punto.longitud}`} target="_blank" rel="noreferrer">Navegar</a>
          </div>)}
        </div>
      </section>}
      <section className="panel"><div className="panel__heading"><div><span className="eyebrow">ENTREGAS</span><h3>{pedidos.length - pendientes.length} de {pedidos.length} confirmadas</h3></div></div>
        <div className="driver-orders">{pedidos.map((pedido) => <article key={pedido.id_pedido} className="driver-order">
          <div><span>Parada {pedido.orden_entrega}</span><strong>{pedido.codigo}</strong><small>{pedido.descripcion || "Pedido asignado"} · {pedido.estado}</small></div>
          <button className="secondary-button" disabled={!!processing || ruta.estado !== "EN_RUTA" || pedido.estado === "ENTREGADO"} onClick={() => void ejecutar(`pedido-${pedido.id_pedido}`, () => api.confirmDelivery(ruta.id_ruta, pedido.id_pedido), `Entrega ${pedido.codigo} confirmada.`)}>{processing === `pedido-${pedido.id_pedido}` ? "Confirmando…" : pedido.estado === "ENTREGADO" ? "Entregado" : "Confirmar entrega"}</button>
        </article>)}</div>
        <button className="primary-button" disabled={!!processing || ruta.estado !== "EN_RUTA" || pendientes.length > 0} onClick={() => void ejecutar("completar", () => api.changeRouteState(ruta.id_ruta, "COMPLETADA"), "Ruta completada y recursos liberados.")}>{processing === "completar" ? "Completando…" : "Completar ruta"}</button>
        {pendientes.length > 0 && ruta.estado === "EN_RUTA" && <p className="muted-copy">Confirma cada entrega antes de completar la ruta.</p>}
      </section>
      <section className="panel"><span className="eyebrow">NOVEDAD OPERATIVA</span><h3>Registrar incidente</h3><textarea value={novedad} onChange={(e) => setNovedad(e.target.value)} placeholder="Describe la novedad sin incluir datos sensibles" rows={3} />
        <button className="quiet-button" disabled={!!processing || novedad.trim().length < 3 || ["COMPLETADA", "CANCELADA"].includes(ruta.estado)} onClick={() => void ejecutar("novedad", () => api.addRouteIncident(ruta.id_ruta, { tipo: "OPERATIVA", descripcion: novedad.trim() }), "Novedad registrada.").then(() => setNovedad(""))}>{processing === "novedad" ? "Guardando…" : "Guardar novedad"}</button>
      </section>
      {detalle && <small className="muted-copy">Recorrido completo: {detalle.puntos.length} puntos · {detalle.distancia_total_km ?? 0} km.</small>}
    </>}
    {error && <div className="inline-error"><span>{error}</span></div>}{success && <div className="inline-success">{success}</div>}
  </div>;
}
