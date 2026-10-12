import { useState } from "react";
import type { UsuarioInfo } from "../../api/types";
import PermissionMatrix from "./PermissionMatrix";
import UsersManager from "./UsersManager";

/**
 * Panel de acceso del ADMINISTRADOR.
 *
 * Comparte con el Centro de Control del Desarrollador los componentes de
 * gestion de cuentas y de matriz de permisos (misma validacion en backend)
 * para evitar duplicidad. La matriz es de solo lectura y no muestra datos
 * tecnicos: sesiones, almacenamiento, credenciales ni diagnosticos siguen
 * siendo exclusivos del DESARROLLADOR.
 */

type Pestana = "cuentas" | "permisos";

const PESTANAS: Array<{ id: Pestana; label: string; detalle: string }> = [
  { id: "cuentas", label: "Cuentas operativas", detalle: "Altas, perfiles y accesos" },
  { id: "permisos", label: "Roles y permisos", detalle: "Matriz efectiva (solo lectura)" },
];

export default function AccessPanel({ usuario }: { usuario: UsuarioInfo }) {
  const [pestana, setPestana] = useState<Pestana>("cuentas");

  return (
    <div className="admin-panel">
      <header className="admin-panel__head">
        <div>
          <span className="eyebrow">Panel de acceso · {usuario.rol}</span>
          <h2>Gestión de cuentas y permisos</h2>
          <p className="muted-copy">
            Administración operativa. La configuración técnica, el diagnóstico, la
            auditoría y las sesiones son exclusivas del perfil DESARROLLADOR.
          </p>
        </div>
      </header>

      <nav className="admin-panel__tabs" aria-label="Secciones del panel de acceso">
        {PESTANAS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={pestana === item.id}
            className={`admin-tab${pestana === item.id ? " admin-tab--active" : ""}`}
            onClick={() => setPestana(item.id)}
          >
            <strong>{item.label}</strong>
            <small>{item.detalle}</small>
          </button>
        ))}
      </nav>

      <div className="admin-panel__contenido">
        {pestana === "cuentas" && <UsersManager usuario={usuario} />}
        {pestana === "permisos" && <PermissionMatrix />}
      </div>
    </div>
  );
}
