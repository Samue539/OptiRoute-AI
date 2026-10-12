import { useCallback, useEffect, useMemo, useState } from "react";
import { authApi } from "../../api/client";
import type { CatalogoPermisos, PermisoCatalogo } from "../../api/types";

/**
 * Matriz de permisos efectiva (solo lectura).
 *
 * Los datos provienen de `GET /api/auth/permisos`, es decir, del mismo
 * catalogo que usa el backend para autorizar: la pantalla no puede divergir
 * de la seguridad real. No permite editar permisos ni crear roles
 * personalizados.
 */

type EstadoPermiso = "permitido" | "limitado" | "denegado";

const ORDEN_ROLES = ["DESARROLLADOR", "ADMINISTRADOR", "OPERADOR", "CONDUCTOR"];

const LEYENDA: Array<{ estado: EstadoPermiso; texto: string; detalle: string }> = [
  { estado: "permitido", texto: "Permitido", detalle: "El perfil tiene el permiso completo." },
  { estado: "limitado", texto: "Limitado", detalle: "Permitido solo en el alcance indicado." },
  { estado: "denegado", texto: "Denegado", detalle: "El permiso no existe para el perfil." },
];

function estadoDe(permiso: PermisoCatalogo, permisos: readonly string[]): EstadoPermiso {
  if (!permisos.includes(permiso.codigo)) return "denegado";
  return permiso.ambito === "general" ? "permitido" : "limitado";
}

function ResumenRol({
  rol,
  total,
  descripcion,
  actual,
}: {
  rol: string;
  total: number;
  descripcion: string;
  actual: boolean;
}) {
  return (
    <article className={`role-card${actual ? " role-card--actual" : ""}`}>
      <header>
        <span className={`user-badge user-badge--${rol}`}>{rol}</span>
        {actual && <span className="role-card__flag">Tu perfil</span>}
      </header>
      <p className="role-card__descripcion">{descripcion}</p>
      <strong className="role-card__total">{total} permisos</strong>
    </article>
  );
}

export default function PermissionMatrix() {
  const [catalogo, setCatalogo] = useState<CatalogoPermisos | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [filtroRol, setFiltroRol] = useState("todos");
  const [filtroModulo, setFiltroModulo] = useState("todos");
  const [filtroTexto, setFiltroTexto] = useState("");
  const [detalle, setDetalle] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      setCatalogo(await authApi.permisos());
    } catch (e) {
      setError(e instanceof Error ? e.message : "No fue posible cargar la matriz de permisos.");
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const roles = useMemo(() => {
    if (!catalogo) return [];
    const ordenados = [...catalogo.roles].sort(
      (a, b) => ORDEN_ROLES.indexOf(a.rol) - ORDEN_ROLES.indexOf(b.rol),
    );
    return filtroRol === "todos" ? ordenados : ordenados.filter((rol) => rol.rol === filtroRol);
  }, [catalogo, filtroRol]);

  const permisos = useMemo(() => {
    if (!catalogo) return [];
    const termino = filtroTexto.trim().toLowerCase();
    return catalogo.permisos.filter((permiso) => {
      if (filtroModulo !== "todos" && permiso.modulo !== filtroModulo) return false;
      if (!termino) return true;
      return [permiso.nombre, permiso.descripcion, permiso.codigo]
        .join(" ")
        .toLowerCase()
        .includes(termino);
    });
  }, [catalogo, filtroModulo, filtroTexto]);

  const modulosDisponibles = useMemo(() => {
    if (!catalogo) return [];
    const usados = new Set(catalogo.permisos.map((permiso) => permiso.modulo));
    return catalogo.modulos.filter((modulo) => usados.has(modulo.id));
  }, [catalogo]);

  if (cargando) {
    return (
      <div className="loading-panel">
        <span />
        <strong>Cargando matriz de permisos…</strong>
      </div>
    );
  }

  if (error || !catalogo) {
    return (
      <div className="inline-error">
        <span>{error || "La matriz de permisos no está disponible."}</span>
        <button className="quiet-button" onClick={() => void cargar()}>
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="rbac">
      <header className="rbac__head">
        <div>
          <span className="eyebrow">Control de acceso</span>
          <h2>Gestión de roles y permisos</h2>
          <p className="muted-copy">
            Matriz efectiva generada desde el backend. Cada endpoint valida estos permisos
            en el servidor: ocultar un botón nunca reemplaza esa validación.
          </p>
        </div>
        <button className="quiet-button" onClick={() => void cargar()}>
          Actualizar
        </button>
      </header>

      <section className="rbac__roles" aria-label="Resumen de perfiles">
        {catalogo.roles
          .slice()
          .sort((a, b) => ORDEN_ROLES.indexOf(a.rol) - ORDEN_ROLES.indexOf(b.rol))
          .map((rol) => (
            <ResumenRol
              key={rol.rol}
              rol={rol.rol}
              total={rol.total_permisos}
              descripcion={rol.descripcion}
              actual={rol.rol === catalogo.rol_actual}
            />
          ))}
      </section>

      <section className="panel rbac__leyenda" aria-label="Significado de los estados">
        {LEYENDA.map((item) => (
          <span key={item.estado} className="rbac__leyenda-item">
            <i className={`rbac-dot rbac-dot--${item.estado}`} aria-hidden />
            <strong>{item.texto}</strong>
            <small>{item.detalle}</small>
          </span>
        ))}
      </section>

      <section className="panel rbac__filtros">
        <label>
          <span>Filtrar por rol</span>
          <select value={filtroRol} onChange={(e) => setFiltroRol(e.target.value)}>
            <option value="todos">Todos los roles</option>
            {catalogo.roles.map((rol) => (
              <option key={rol.rol} value={rol.rol}>
                {rol.rol}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Filtrar por módulo</span>
          <select value={filtroModulo} onChange={(e) => setFiltroModulo(e.target.value)}>
            <option value="todos">Todos los módulos</option>
            {modulosDisponibles.map((modulo) => (
              <option key={modulo.id} value={modulo.id}>
                {modulo.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="rbac__filtros-buscador">
          <span>Buscar permiso</span>
          <input
            type="search"
            value={filtroTexto}
            onChange={(e) => setFiltroTexto(e.target.value)}
            placeholder="Nombre, código o descripción"
          />
        </label>
        <small className="muted-copy">
          {permisos.length} permisos · {roles.length} perfiles
        </small>
      </section>

      <section className="panel rbac__matriz">
        <div className="table-scroll">
          <table className="data-table data-table--permisos">
            <thead>
              <tr>
                <th scope="col">Permiso</th>
                {roles.map((rol) => (
                  <th key={rol.rol} scope="col">
                    {rol.rol}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {permisos.map((permiso) => (
                <tr key={permiso.codigo}>
                  <th scope="row">
                    <button
                      type="button"
                      className="rbac__permiso"
                      onClick={() => setDetalle(permiso.codigo === detalle ? null : permiso.codigo)}
                      aria-expanded={permiso.codigo === detalle}
                    >
                      <strong>{permiso.nombre}</strong>
                      <code>{permiso.codigo}</code>
                    </button>
                    {permiso.codigo === detalle && (
                      <div className="rbac__detalle">
                        <p>{permiso.descripcion}</p>
                        {permiso.limite && <p className="rbac__limite">{permiso.limite}</p>}
                        <small>
                          Módulo:{" "}
                          {catalogo.modulos.find((modulo) => modulo.id === permiso.modulo)?.nombre ??
                            permiso.modulo}{" "}
                          · Alcance: {permiso.ambito}
                        </small>
                      </div>
                    )}
                  </th>
                  {roles.map((rol) => {
                    const estado = estadoDe(permiso, rol.permisos);
                    const simbolo = estado === "denegado" ? "—" : estado === "limitado" ? "~" : "✓";
                    return (
                      <td key={rol.rol} className="rbac__celda">
                        <span
                          className={`rbac-chip rbac-chip--${estado}`}
                          title={`${rol.rol}: ${estado}`}
                        >
                          <span aria-hidden>{simbolo}</span>
                          <small>{estado === "limitado" ? "Limitado" : estado === "permitido" ? "Sí" : "No"}</small>
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
              {permisos.length === 0 && (
                <tr>
                  <td colSpan={roles.length + 1}>
                    <small className="muted-copy">Ningún permiso coincide con el filtro.</small>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel rbac__reglas">
        <div className="panel__heading">
          <div>
            <span className="eyebrow">Reglas verificadas</span>
            <h3>Restricciones que aplica el servidor</h3>
          </div>
        </div>
        <ul className="rule-list">
          {catalogo.reglas.map((regla) => (
            <li key={regla.titulo}>
              <strong>{regla.titulo}:</strong> {regla.detalle}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
