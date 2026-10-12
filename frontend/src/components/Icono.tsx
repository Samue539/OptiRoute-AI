/**
 * Iconos SVG locales (24x24, trazo, `currentColor`).
 *
 * Sustituyen a los emojis del menú y de las tarjetas para tener una
 * apariencia consistente en cualquier sistema operativo y sin depender de
 * recursos externos.
 */

import type { ReactNode } from "react";

const ICONOS: Record<string, ReactNode> = {
  dashboard: (
    <>
      <path d="M3.5 10.5 12 3.5l8.5 7" />
      <path d="M5.5 9.5V20.5h13V9.5" />
      <path d="M9.5 20.5v-5.5h5v5.5" />
    </>
  ),
  pedidos: (
    <>
      <path d="M4 8.5 12 4l8 4.5v7L12 20l-8-4.5z" />
      <path d="M4 8.5 12 13l8-4.5" />
      <path d="M12 13v7" />
    </>
  ),
  clientes: (
    <>
      <circle cx="9" cy="8.5" r="3.2" />
      <path d="M3.5 19.5c0-3 2.5-5 5.5-5s5.5 2 5.5 5" />
      <path d="M16 5.6a3.2 3.2 0 0 1 0 5.9" />
      <path d="M17.5 14.9c2 .7 3.3 2.4 3.3 4.6" />
    </>
  ),
  rutas: (
    <>
      <circle cx="6" cy="6" r="2.4" />
      <circle cx="18" cy="18" r="2.4" />
      <path d="M8.4 6h4.6a3 3 0 0 1 0 6h-3a3 3 0 0 0 0 6h5.6" />
    </>
  ),
  conductores: (
    <>
      <circle cx="12" cy="7.5" r="3.2" />
      <path d="M5.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" />
      <path d="M15.5 4.5h4v3" />
    </>
  ),
  vehiculos: (
    <>
      <path d="M2.5 15.5V12h11l3 3.5h3.5v3" />
      <path d="M2.5 12h11" />
      <circle cx="7" cy="17.5" r="2" />
      <circle cx="17" cy="17.5" r="2" />
    </>
  ),
  optimizacion: (
    <>
      <path d="M4 19V5" />
      <path d="M4 19h16" />
      <path d="M7.5 15.5 12 10l3 2.5 4-6" />
    </>
  ),
  mapa: (
    <>
      <path d="M12 21s6.5-6.1 6.5-10.4A6.5 6.5 0 0 0 5.5 10.6C5.5 14.9 12 21 12 21z" />
      <circle cx="12" cy="10.4" r="2.4" />
    </>
  ),
  reportes: (
    <>
      <path d="M4.5 20h15" />
      <path d="M7 20v-6" />
      <path d="M12 20V7" />
      <path d="M17 20v-9" />
    </>
  ),
  ia: (
    <>
      <rect x="5" y="5" width="14" height="14" rx="3.4" />
      <path d="M9.2 10.4h.01M14.8 10.4h.01M9.5 14.2c1.6 1.1 3.4 1.1 5 0" />
      <path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4" />
    </>
  ),
  configuracion: (
    <>
      <circle cx="12" cy="12" r="3.1" />
      <path d="M12 2.8v2.2M12 19v2.2M4.6 7.2l1.9 1.1M17.5 15.7l1.9 1.1M4.6 16.8l1.9-1.1M17.5 8.3l1.9-1.1" />
    </>
  ),
  usuarios: (
    <>
      <path d="M12 3.2 5 6v5.6c0 4.3 3 7.6 7 9.2 4-1.6 7-4.9 7-9.2V6z" />
      <path d="M9.4 12.2l1.9 1.9 3.4-3.6" />
    </>
  ),
  "conductor-movil": (
    <>
      <rect x="6.5" y="2.8" width="11" height="18.4" rx="2.6" />
      <path d="M10.4 5.4h3.2" />
      <circle cx="12" cy="17.6" r="1" />
    </>
  ),
  asignada: (
    <>
      <circle cx="12" cy="12" r="8.2" />
      <path d="M12 7.6V12l3 1.9" />
    </>
  ),
  paquete: (
    <>
      <path d="M20 7.4 12 3.2 4 7.4v9.2L12 20.8l8-4.2z" />
      <path d="M4 7.4 12 11.6l8-4.2M12 11.6v9.2" />
    </>
  ),
  volante: (
    <>
      <circle cx="12" cy="12" r="8.4" />
      <circle cx="12" cy="12" r="2.6" />
      <path d="M12 9.4V4.2M12 14.6v5.2M4.6 12h5M14.4 12h5" />
    </>
  ),
};

export type IconoNombre = keyof typeof ICONOS | string;

export function Icono({
  nombre,
  size = 18,
  className,
}: {
  nombre: IconoNombre;
  size?: number;
  className?: string;
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {ICONOS[nombre] ?? ICONOS.dashboard}
    </svg>
  );
}
