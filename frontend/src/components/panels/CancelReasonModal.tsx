import { useEffect, useState, type FormEvent } from "react";

type Props = {
  titulo: string;
  descripcion: string;
  etiquetaConfirmar?: string;
  procesando?: boolean;
  onCerrar: () => void;
  onConfirmar: (motivo: string) => void | Promise<void>;
};

const MINIMO = 5;
const MAXIMO = 300;

/**
 * Modal minimo para exigir el motivo de una cancelacion.
 *
 * El backend rechaza (422) cualquier cancelacion sin motivo valido y guarda
 * el motivo en la bitacora de auditoria junto al usuario que la realizo.
 */
export default function CancelReasonModal({
  titulo,
  descripcion,
  etiquetaConfirmar = "Confirmar cancelacion",
  procesando = false,
  onCerrar,
  onConfirmar,
}: Props) {
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    function alPulsarTecla(evento: KeyboardEvent) {
      if (evento.key === "Escape" && !procesando) onCerrar();
    }
    window.addEventListener("keydown", alPulsarTecla);
    return () => window.removeEventListener("keydown", alPulsarTecla);
  }, [onCerrar, procesando]);

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    const texto = motivo.trim();
    if (texto.length < MINIMO) {
      setError(`Indica un motivo de al menos ${MINIMO} caracteres.`);
      return;
    }
    setError("");
    void onConfirmar(texto);
  }

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,.5)", display: "grid", placeItems: "center", zIndex: 70, padding: 16 }}
      role="dialog"
      aria-modal="true"
      aria-label={titulo}
    >
      <form className="panel" style={{ width: "100%", maxWidth: 460 }} onSubmit={enviar}>
        <span className="eyebrow">Confirmacion requerida</span>
        <h3 style={{ margin: "4px 0 6px" }}>{titulo}</h3>
        <p className="muted-copy" style={{ marginBottom: 12 }}>
          {descripcion}
        </p>
        <label>
          <span>Motivo</span>
          <textarea
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Ej. El cliente anulo la compra por telefonomail."
            rows={3}
            maxLength={MAXIMO}
            autoFocus
          />
        </label>
        <small className="muted-copy">
          {motivo.trim().length}/{MAXIMO} caracteres · queda registrado en la auditoria
        </small>
        {error && (
          <div className="inline-error" style={{ marginTop: 8 }}>
            <span>{error}</span>
          </div>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
          <button className="primary-button" type="submit" disabled={procesando}>
            {procesando ? "Cancelando…" : etiquetaConfirmar}
          </button>
          <button type="button" className="quiet-button" onClick={onCerrar} disabled={procesando}>
            Volver
          </button>
        </div>
      </form>
    </div>
  );
}
