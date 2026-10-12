import { useEffect, useState, type FormEvent } from "react";
import { api, authApi, ApiError } from "../../api/client";
import type { DriverCatalogItem, UsuarioInfo } from "../../api/types";
import { validezPassword } from "./BootstrapPanel";

/**
 * Gestión de cuentas compartida por el Centro de Control del Desarrollador y
 * por el panel del Administrador. Toda acción se valida además en el backend;
 * este componente solo decide qué mostrar según los permisos del usuario.
 */

export function rolBadge(rol: string) {
  return <span className={`user-badge user-badge--${rol}`}>{rol}</span>;
}

export function estadoPill(activo: boolean) {
  return (
    <span className={`user-state ${activo ? "user-state--on" : "user-state--off"}`}>
      {activo ? "ACTIVA" : "INACTIVA"}
    </span>
  );
}

type Props = {
  usuario: UsuarioInfo;
  /** Notificaciones tipo toast para el módulo que lo aloja. */
  onAviso?: (tipo: "ok" | "error", mensaje: string) => void;
};

export default function UsersManager({ usuario, onAviso }: Props) {
  const esDev = usuario.rol === "DESARROLLADOR";
  const rolesCreables = esDev
    ? ["ADMINISTRADOR", "OPERADOR", "CONDUCTOR"]
    : ["OPERADOR", "CONDUCTOR"];

  const [usuarios, setUsuarios] = useState<UsuarioInfo[]>([]);
  const [conductores, setConductores] = useState<DriverCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [resetAbierto, setResetAbierto] = useState<number | null>(null);
  const [resetPass, setResetPass] = useState({ password: "", confirmacion: "" });
  const [miCuenta, setMiCuenta] = useState({ actual: "", password: "", confirmacion: "" });
  const [nuevo, setNuevo] = useState({
    nombres: "",
    apellidos: "",
    correo: "",
    password: "",
    rol: rolesCreables[0],
    id_conductor: "",
  });

  async function cargar() {
    setLoading(true);
    setError("");
    try {
      setUsuarios(await authApi.listarUsuarios());
    } catch (e) {
      setError(e instanceof Error ? e.message : "No fue posible cargar las cuentas.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void cargar();
    api
      .listDrivers()
      .then((lista) => setConductores(lista.filter((c) => c.activo)))
      .catch(() => setConductores([]));
  }, [usuario.rol]);

  function avisar(tipo: "ok" | "error", mensaje: string) {
    onAviso?.(tipo, mensaje);
  }

  const desarrolladoresActivos = usuarios.filter(
    (c) => c.rol === "DESARROLLADOR" && c.activo,
  ).length;
  function esUltimoDevActivo(cuenta: UsuarioInfo) {
    return cuenta.rol === "DESARROLLADOR" && cuenta.activo && desarrolladoresActivos <= 1;
  }
  function puedeGestionarRol(cuenta: UsuarioInfo) {
    // Cambiar de perfil exige permiso perfiles:administrar: solo DESARROLLADOR.
    if (!esDev) return false;
    if (cuenta.id_usuario === usuario.id_usuario || cuenta.es_propietario) return false;
    return true;
  }
  function rolesAsignables(cuenta: UsuarioInfo) {
    if (!puedeGestionarRol(cuenta)) return [cuenta.rol];
    return ["ADMINISTRADOR", "OPERADOR", "CONDUCTOR"];
  }
  function puedeCambiarEstado(cuenta: UsuarioInfo) {
    if (cuenta.id_usuario === usuario.id_usuario || cuenta.es_propietario) return false;
    if (esUltimoDevActivo(cuenta)) return false;
    // Un administrador solo actua sobre cuentas operativas.
    if (!esDev) return cuenta.rol === "OPERADOR" || cuenta.rol === "CONDUCTOR";
    return true;
  }
  function puedeRestablecer(cuenta: UsuarioInfo) {
    if (cuenta.id_usuario === usuario.id_usuario) return false;
    if (!esDev) return cuenta.rol === "OPERADOR" || cuenta.rol === "CONDUCTOR";
    return true;
  }

  async function crear(e: FormEvent) {
    e.preventDefault();
    if (processing) return;
    setProcessing("crear");
    setError("");
    setSuccess("");
    try {
      const problema = validezPassword(nuevo.password);
      if (problema) throw new ApiError(problema, 0);
      const creada = await authApi.crearUsuario({
        nombres: nuevo.nombres.trim(),
        apellidos: nuevo.apellidos.trim(),
        correo: nuevo.correo.trim().toLowerCase(),
        password: nuevo.password,
        rol: nuevo.rol,
        id_conductor: nuevo.rol === "CONDUCTOR" ? Number(nuevo.id_conductor) : null,
      });
      setNuevo({ nombres: "", apellidos: "", correo: "", password: "", rol: rolesCreables[0], id_conductor: "" });
      const mensaje = `Cuenta ${creada.correo} creada con perfil ${creada.rol}.`;
      setSuccess(mensaje);
      avisar("ok", mensaje);
      await cargar();
    } catch (err) {
      const mensaje = err instanceof Error ? err.message : "No se pudo crear la cuenta.";
      setError(mensaje);
      avisar("error", mensaje);
    } finally {
      setProcessing("");
    }
  }

  async function cambiarEstado(cuenta: UsuarioInfo) {
    setProcessing(`estado-${cuenta.id_usuario}`);
    setError("");
    setSuccess("");
    try {
      await authApi.cambiarEstado(cuenta.id_usuario, !cuenta.activo);
      const mensaje = `Cuenta ${cuenta.correo} ${cuenta.activo ? "desactivada" : "activada"}.`;
      setSuccess(mensaje);
      avisar("ok", mensaje);
      await cargar();
    } catch (e) {
      const mensaje = e instanceof Error ? e.message : "No se pudo actualizar.";
      setError(mensaje);
      avisar("error", mensaje);
    } finally {
      setProcessing("");
    }
  }

  async function cambiarRol(cuenta: UsuarioInfo, rol: string) {
    if (rol === cuenta.rol) return;
    setProcessing(`rol-${cuenta.id_usuario}`);
    setError("");
    setSuccess("");
    try {
      const actualizada = await authApi.cambiarRol(cuenta.id_usuario, rol);
      const mensaje = `Perfil de ${actualizada.correo} actualizado a ${actualizada.rol}. Sesiones cerradas.`;
      setSuccess(mensaje);
      avisar("ok", mensaje);
      await cargar();
    } catch (e) {
      const mensaje = e instanceof Error ? e.message : "No se pudo cambiar el perfil.";
      setError(mensaje);
      avisar("error", mensaje);
    } finally {
      setProcessing("");
    }
  }

  async function restablecer(cuenta: UsuarioInfo) {
    setProcessing(`reset-${cuenta.id_usuario}`);
    setError("");
    setSuccess("");
    try {
      const problema = validezPassword(resetPass.password);
      if (problema) throw new ApiError(problema, 0);
      if (resetPass.password !== resetPass.confirmacion) {
        throw new ApiError("Las contraseñas no coinciden.", 0);
      }
      const r = await authApi.restablecerPassword(cuenta.id_usuario, resetPass.password);
      const mensaje = `${r.mensaje} (${r.sesiones_revocadas} sesión/es cerradas)`;
      setSuccess(mensaje);
      avisar("ok", mensaje);
      setResetAbierto(null);
      setResetPass({ password: "", confirmacion: "" });
    } catch (e) {
      const mensaje = e instanceof Error ? e.message : "No se pudo restablecer la contraseña.";
      setError(mensaje);
      avisar("error", mensaje);
    } finally {
      setProcessing("");
    }
  }

  async function cambiarMiPassword(e: FormEvent) {
    e.preventDefault();
    if (processing) return;
    setProcessing("mi-cuenta");
    setError("");
    setSuccess("");
    try {
      const problema = validezPassword(miCuenta.password);
      if (problema) throw new ApiError(problema, 0);
      if (miCuenta.password !== miCuenta.confirmacion) {
        throw new ApiError("Las contraseñas no coinciden.", 0);
      }
      const r = await authApi.cambiarPassword({
        password_actual: miCuenta.actual,
        password_nueva: miCuenta.password,
      });
      const mensaje = `${r.mensaje} (${r.sesiones_revocadas} sesión/es cerradas)`;
      setSuccess(mensaje);
      avisar("ok", mensaje);
      setMiCuenta({ actual: "", password: "", confirmacion: "" });
    } catch (e) {
      const mensaje = e instanceof Error ? e.message : "No se pudo cambiar la contraseña.";
      setError(mensaje);
      avisar("error", mensaje);
    } finally {
      setProcessing("");
    }
  }

  const conductoresLibres = conductores.filter(
    (c) => !usuarios.some((u) => u.id_conductor === c.id_conductor),
  );

  return (
    <div className="users-manager">
      <section className="panel">
        <div className="panel__heading">
          <div>
            <span className="eyebrow">Alta de cuentas</span>
            <h2>{esDev ? "Crear administradores y cuentas operativas" : "Crear operadores y conductores"}</h2>
          </div>
          <span className="provisional-badge">Almacenamiento local provisional</span>
        </div>
        <form className="access-form" onSubmit={crear}>
          <input
            required
            placeholder="Nombres"
            value={nuevo.nombres}
            onChange={(e) => setNuevo({ ...nuevo, nombres: e.target.value })}
          />
          <input
            required
            placeholder="Apellidos"
            value={nuevo.apellidos}
            onChange={(e) => setNuevo({ ...nuevo, apellidos: e.target.value })}
          />
          <input
            required
            type="email"
            placeholder="correo@empresa.com"
            value={nuevo.correo}
            onChange={(e) => setNuevo({ ...nuevo, correo: e.target.value })}
          />
          <input
            required
            type="password"
            minLength={10}
            placeholder="Contraseña (mín. 10, letras y números)"
            value={nuevo.password}
            onChange={(e) => setNuevo({ ...nuevo, password: e.target.value })}
          />
          <select
            value={nuevo.rol}
            onChange={(e) => setNuevo({ ...nuevo, rol: e.target.value, id_conductor: "" })}
            aria-label="Perfil de la nueva cuenta"
          >
            {rolesCreables.map((rol) => (
              <option key={rol} value={rol}>
                {rol}
              </option>
            ))}
          </select>
          {nuevo.rol === "CONDUCTOR" && (
            <select
              required
              value={nuevo.id_conductor}
              onChange={(e) => setNuevo({ ...nuevo, id_conductor: e.target.value })}
              aria-label="Conductor vinculado"
            >
              <option value="">Selecciona conductor…</option>
              {conductoresLibres.map((c) => (
                <option key={c.id_conductor} value={String(c.id_conductor)}>
                  {c.nombres} {c.apellidos} · Lic. {c.numero_licencia}
                </option>
              ))}
            </select>
          )}
          <button className="primary-button" type="submit" disabled={!!processing}>
            {processing === "crear" ? "Creando…" : "Crear cuenta"}
          </button>
        </form>
        <p className="access-hint">
          {esDev
            ? "Como DESARROLLADOR puedes crear ADMINISTRADOR, OPERADOR y CONDUCTOR."
            : "Como ADMINISTRADOR solo puedes crear cuentas OPERADOR y CONDUCTOR."}{" "}
          El perfil CONDUCTOR debe vincularse a un conductor existente. El backend
          valida siempre los permisos, incluso si se ocultan los botones.
        </p>
      </section>

      <section className="panel">
        <div className="panel__heading">
          <div>
            <span className="eyebrow">Mi cuenta</span>
            <h2>Cambiar mi contraseña</h2>
          </div>
        </div>
        <form className="access-form" onSubmit={cambiarMiPassword}>
          <input
            required
            type="password"
            placeholder="Contraseña actual"
            value={miCuenta.actual}
            onChange={(e) => setMiCuenta({ ...miCuenta, actual: e.target.value })}
          />
          <input
            required
            type="password"
            minLength={10}
            placeholder="Nueva contraseña (mín. 10)"
            value={miCuenta.password}
            onChange={(e) => setMiCuenta({ ...miCuenta, password: e.target.value })}
          />
          <input
            required
            type="password"
            minLength={10}
            placeholder="Confirmar nueva contraseña"
            value={miCuenta.confirmacion}
            onChange={(e) => setMiCuenta({ ...miCuenta, confirmacion: e.target.value })}
          />
          <button className="primary-button" type="submit" disabled={!!processing}>
            {processing === "mi-cuenta" ? "Guardando…" : "Actualizar contraseña"}
          </button>
        </form>
        <p className="access-hint">
          Al cambiar tu contraseña se cierran todas tus sesiones y deberás iniciar
          sesión de nuevo.
        </p>
      </section>

      <section className="panel">
        <div className="panel__heading">
          <div>
            <span className="eyebrow">Directorio</span>
            <h2>Cuentas registradas ({usuarios.length})</h2>
          </div>
        </div>
        {loading ? (
          <div className="loading-panel">
            <span />
            <strong>Cargando cuentas…</strong>
          </div>
        ) : usuarios.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state__mark">US</span>
            <strong>Sin cuentas registradas</strong>
            <p>Crea la primera cuenta con el formulario superior.</p>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Cuenta</th>
                  <th>Perfil</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((cuenta) => {
                  const conductor = conductores.find((c) => c.id_conductor === cuenta.id_conductor);
                  const gestionaEstado = puedeCambiarEstado(cuenta);
                  return (
                    <tr key={cuenta.id_usuario}>
                      <td>
                        <strong>
                          {cuenta.nombres} {cuenta.apellidos}
                        </strong>
                        <br />
                        <small>{cuenta.correo}</small>
                        {cuenta.es_propietario && (
                          <>
                            <br />
                            <small className="access-hint">Cuenta propietaria</small>
                          </>
                        )}
                        {cuenta.id_conductor !== null && (
                          <>
                            <br />
                            <small className="access-hint">
                              Conductor: {conductor ? `${conductor.nombres} ${conductor.apellidos}` : `#${cuenta.id_conductor}`}
                            </small>
                          </>
                        )}
                      </td>
                      <td>
                        {puedeGestionarRol(cuenta) ? (
                          <select
                            className="role-select"
                            value={cuenta.rol}
                            disabled={!!processing}
                            onChange={(e) => void cambiarRol(cuenta, e.target.value)}
                            aria-label={`Cambiar perfil de ${cuenta.correo}`}
                          >
                            {rolesAsignables(cuenta).map((rol) => (
                              <option key={rol} value={rol}>
                                {rol}
                              </option>
                            ))}
                          </select>
                        ) : (
                          rolBadge(cuenta.rol)
                        )}
                      </td>
                      <td>{estadoPill(cuenta.activo)}</td>
                      <td>
                        <div className="access-actions">
                          <button
                            className="quiet-button"
                            disabled={!puedeRestablecer(cuenta) || !!processing}
                            title={cuenta.id_usuario === usuario.id_usuario ? "Usa el cambio personal de contraseña" : undefined}
                            onClick={() => {
                              setResetAbierto(resetAbierto === cuenta.id_usuario ? null : cuenta.id_usuario);
                              setResetPass({ password: "", confirmacion: "" });
                              setError("");
                            }}
                          >
                            Restablecer contraseña
                          </button>
                          <button
                            className="quiet-button"
                            disabled={!gestionaEstado || !!processing}
                            title={esUltimoDevActivo(cuenta) ? "Es el último desarrollador activo" : undefined}
                            onClick={() => void cambiarEstado(cuenta)}
                          >
                            {processing === `estado-${cuenta.id_usuario}`
                              ? "Procesando…"
                              : cuenta.activo
                                ? "Desactivar"
                                : "Activar"}
                          </button>
                        </div>
                        {resetAbierto === cuenta.id_usuario && (
                          <form
                            className="reset-form"
                            onSubmit={(e) => {
                              e.preventDefault();
                              void restablecer(cuenta);
                            }}
                          >
                            <label>
                              <span>Nueva contraseña</span>
                              <input
                                type="password"
                                minLength={10}
                                required
                                value={resetPass.password}
                                onChange={(e) => setResetPass({ ...resetPass, password: e.target.value })}
                              />
                            </label>
                            <label>
                              <span>Confirmar</span>
                              <input
                                type="password"
                                minLength={10}
                                required
                                value={resetPass.confirmacion}
                                onChange={(e) => setResetPass({ ...resetPass, confirmacion: e.target.value })}
                              />
                            </label>
                            <button
                              className="primary-button"
                              type="submit"
                              disabled={processing === `reset-${cuenta.id_usuario}`}
                            >
                              {processing === `reset-${cuenta.id_usuario}` ? "Guardando…" : "Guardar"}
                            </button>
                          </form>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="access-hint">
          Nunca se muestran contraseñas ni hashes. No se puede desactivar al último
          desarrollador activo ni modificar la cuenta propietaria; el cambio de
          perfil es exclusivo del DESARROLLADOR. El backend valida siempre los
          permisos aunque los botones estén visibles.
        </p>
      </section>

      {error && (
        <div className="inline-error">
          <span>{error}</span>
        </div>
      )}
      {success && <div className="inline-success">{success}</div>}
    </div>
  );
}
