import { useState, type FormEvent } from "react";
import { ApiError, authApi } from "../../api/client";

const PRIMERA_CUENTA = {
  nombres: "Samuel Patricio",
  apellidos: "Simbaña Gualacata",
  correo: "patosimba2000@gmail.com",
};

export function validezPassword(password: string): string {
  if (password.length < 10) {
    return "La contraseña debe tener al menos 10 caracteres.";
  }
  const tieneLetras = /[a-zA-ZÀ-ÿ]/.test(password);
  const tieneDigitos = /[0-9]/.test(password);
  if (!tieneLetras || !tieneDigitos) {
    return "La contraseña debe combinar letras y números.";
  }
  return "";
}

export default function BootstrapPanel({
  onCreado,
}: {
  onCreado: (correo: string) => void;
}) {
  const [nombres, setNombres] = useState(PRIMERA_CUENTA.nombres);
  const [apellidos, setApellidos] = useState(PRIMERA_CUENTA.apellidos);
  const [correo, setCorreo] = useState(PRIMERA_CUENTA.correo);
  const [password, setPassword] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  async function crearCuenta(e: FormEvent) {
    e.preventDefault();
    if (enviando) return;
    setError("");
    const problema = validezPassword(password);
    if (problema) {
      setError(problema);
      return;
    }
    if (password !== confirmacion) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setEnviando(true);
    try {
      await authApi.bootstrap({
        nombres: nombres.trim(),
        apellidos: apellidos.trim(),
        correo: correo.trim().toLowerCase(),
        password,
      });
      onCreado(correo.trim().toLowerCase());
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        if (err.status === 409) {
          window.setTimeout(() => onCreado(correo.trim().toLowerCase()), 2500);
        }
      } else {
        setError("No se pudo crear la cuenta propietaria.");
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form
      onSubmit={crearCuenta}
      className="panel bootstrap-panel"
      style={{ width: "100%", maxWidth: 460, borderRadius: 16 }}
    >
      <div style={{ textAlign: "center", marginBottom: 18 }}>
        <span
          style={{
            display: "inline-grid",
            placeItems: "center",
            width: 52,
            height: 52,
            borderRadius: 14,
            background: "linear-gradient(135deg,#2563eb,#38bdf8)",
            color: "#fff",
            fontWeight: 800,
            boxShadow: "0 4px 16px rgba(37,99,235,0.3)",
          }}
        >
          OR
        </span>
        <h2 style={{ margin: "12px 0 4px" }}>Crear cuenta propietaria</h2>
        <p className="muted-copy">
          OptiRoute AI no tiene cuentas. Registra el primer usuario DESARROLLADOR.
        </p>
      </div>

      <label>
        <span>Nombres</span>
        <input
          value={nombres}
          onChange={(e) => setNombres(e.target.value)}
          minLength={2}
          required
        />
      </label>
      <label>
        <span>Apellidos</span>
        <input
          value={apellidos}
          onChange={(e) => setApellidos(e.target.value)}
          minLength={2}
          required
        />
      </label>
      <label>
        <span>Correo</span>
        <input
          type="email"
          value={correo}
          onChange={(e) => setCorreo(e.target.value)}
          placeholder="correo@empresa.com"
          required
        />
      </label>
      <label>
        <span>Contraseña</span>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Elige tu contraseña"
          minLength={10}
          required
        />
      </label>
      <label>
        <span>Confirmar contraseña</span>
        <input
          type="password"
          value={confirmacion}
          onChange={(e) => setConfirmacion(e.target.value)}
          placeholder="Repite la contraseña"
          minLength={10}
          required
        />
      </label>
      <p className="bootstrap-hint">
        Mínimo 10 caracteres, debe combinar letras y números. No se guarda en
        texto plano (PBKDF2-SHA256) y solo se permite una cuenta propietaria.
      </p>
      {error && (
        <div className="inline-error">
          <span>{error}</span>
        </div>
      )}
      <button
        className="primary-button primary-button--full"
        type="submit"
        disabled={enviando}
      >
        {enviando ? "Creando cuenta…" : "Crear cuenta e iniciar sesión"}
      </button>
    </form>
  );
}
