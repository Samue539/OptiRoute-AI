import { useState } from "react";
import { api } from "../../api/client";

export default function RouteIncidentForm({ idRuta }: { idRuta: number }) {
  const [tipo, setTipo] = useState("OPERATIVA");
  const [descripcion, setDescripcion] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function guardar() {
    setSaving(true); setMessage(""); setError("");
    try { await api.addRouteIncident(idRuta, { tipo, descripcion: descripcion.trim() }); setDescripcion(""); setMessage("Novedad registrada en el historial de la ruta."); }
    catch (e) { setError(e instanceof Error ? e.message : "No se pudo registrar la novedad."); }
    finally { setSaving(false); }
  }
  return <section className="panel" style={{ marginTop: 12 }}><span className="eyebrow">NOVEDADES OPERATIVAS</span><h4>Registrar seguimiento</h4><div className="incident-form"><select value={tipo} onChange={(e) => setTipo(e.target.value)}><option>OPERATIVA</option><option>TRAFICO</option><option>VEHICULO</option><option>CLIENTE</option></select><input value={descripcion} onChange={(e) => setDescripcion(e.target.value)} placeholder="Describe la novedad" /><button className="secondary-button" disabled={saving || descripcion.trim().length < 3} onClick={() => void guardar()}>{saving ? "Guardando…" : "Registrar"}</button></div>{message && <div className="inline-success">{message}</div>}{error && <div className="inline-error"><span>{error}</span></div>}</section>;
}
