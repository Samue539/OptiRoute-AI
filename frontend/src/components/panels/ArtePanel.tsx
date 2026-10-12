/**
 * Ilustraciones vectoriales locales para los paneles por rol.
 *
 * Son recursos propios (SVG incrustado, sin peticiones de red ni dominios
 * externos) pensados como capa decorativa: siempre van acompanadas de un
 * degradado oscuro que garantiza el contraste del texto.
 */

import type { ReactNode } from "react";

type EscenaProps = { className?: string };

const CIELO_ATOARDECER = (
  <>
    <stop offset="0%" stopColor="#1e1b4b" />
    <stop offset="38%" stopColor="#4c1d95" />
    <stop offset="62%" stopColor="#b45309" />
    <stop offset="82%" stopColor="#f59e0b" />
    <stop offset="100%" stopColor="#fcd34d" />
  </>
);

function Edificios({
  x,
  ancho,
  yBase,
  color,
  ventanas,
  altoMax,
  semilla,
}: {
  x: number;
  ancho: number;
  yBase: number;
  color: string;
  ventanas: string;
  altoMax: number;
  semilla: number;
}) {
  const edificios: ReactNode[] = [];
  let cursor = x;
  let indice = 0;
  while (cursor < x + ancho) {
    const anchoEdificio = 18 + ((semilla * (indice + 3)) % 26);
    const alto = 40 + ((semilla * (indice + 5) * 7) % altoMax);
    const y = yBase - alto;
    edificios.push(
      <rect
        key={`e${indice}`}
        x={cursor}
        y={y}
        width={anchoEdificio - 4}
        height={alto}
        rx={2}
        fill={color}
      />,
    );
    const filas = Math.floor(alto / 16);
    for (let fila = 0; fila < filas; fila += 1) {
      for (let columna = 0; columna < 3; columna += 1) {
        const encendida = (semilla * (fila + 2) * (columna + 3) * 13) % 5 > 1;
        if (!encendida) continue;
        edificios.push(
          <rect
            key={`v${indice}-${fila}-${columna}`}
            x={cursor + 5 + columna * 6}
            y={y + 8 + fila * 14}
            width={3}
            height={5}
            fill={ventanas}
            opacity={0.85}
          />,
        );
      }
    }
    cursor += anchoEdificio;
    indice += 1;
  }
  return <>{edificios}</>;
}

/** Quito al atardecer: cielo calido, volcan andino y ciudad iluminada. */
export function QuitoAtardecer({ className }: EscenaProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 900 500"
      preserveAspectRatio="xMidYMid slice"
      role="img"
      aria-label="Panorámica de Quito al atardecer con un volcán andino al fondo"
    >
      <defs>
        <linearGradient id="qaCielo" x1="0" y1="0" x2="0" y2="1">
          {CIELO_ATOARDECER}
        </linearGradient>
        <linearGradient id="qaSol" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fffbeb" />
          <stop offset="100%" stopColor="#fbbf24" />
        </linearGradient>
      </defs>
      <rect width="900" height="500" fill="url(#qaCielo)" />
      <circle cx="660" cy="336" r="58" fill="url(#qaSol)" opacity="0.95" />
      <circle cx="660" cy="336" r="96" fill="#fbbf24" opacity="0.16" />
      {/* Volcan andino */}
      <path d="M40 404 L318 176 L596 404 Z" fill="#3b0764" opacity="0.82" />
      <path d="M282 226 L318 176 L354 226 Z" fill="#f8fafc" opacity="0.9" />
      <path d="M520 404 L700 250 L900 404 Z" fill="#1e1b4b" opacity="0.78" />
      {/* Ciudad iluminada */}
      <Edificios
        x={0}
        ancho={900}
        yBase={470}
        color="#0f172a"
        ventanas="#fcd34d"
        altoMax={150}
        semilla={7}
      />
      <rect x="0" y="430" width="900" height="70" fill="#020617" opacity="0.55" />
      <path
        d="M0 470 H900"
        stroke="#f59e0b"
        strokeWidth="2"
        opacity="0.35"
      />
    </svg>
  );
}

/** Quito de noche con composicion tecnica de sistemas. */
export function QuitoNocheTech({ className }: EscenaProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 900 500"
      preserveAspectRatio="xMidYMid slice"
      role="img"
      aria-label="Quito de noche con una composición tecnológica de programación"
    >
      <defs>
        <linearGradient id="qnCielo" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#020617" />
          <stop offset="55%" stopColor="#0a1931" />
          <stop offset="100%" stopColor="#132a5c" />
        </linearGradient>
        <linearGradient id="qnBrillo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.75" />
        </linearGradient>
        <pattern id="qnGrid" width="46" height="46" patternUnits="userSpaceOnUse">
          <path d="M46 0H0V46" fill="none" stroke="#1d4ed8" strokeWidth="0.6" opacity="0.35" />
        </pattern>
      </defs>
      <rect width="900" height="500" fill="url(#qnCielo)" />
      <rect width="900" height="500" fill="url(#qnGrid)" />
      {[
        [90, 70],
        [180, 130],
        [280, 60],
        [420, 110],
        [520, 54],
        [640, 140],
        [760, 80],
        [840, 150],
      ].map(([cx, cy], indice) => (
        <circle key={indice} cx={cx} cy={cy} r={indice % 2 ? 1.4 : 2.1} fill="#e0f2fe" opacity={0.8} />
      ))}
      {/* Horizonte de ciudad */}
      <Edificios
        x={0}
        ancho={900}
        yBase={470}
        color="#04070f"
        ventanas="#38bdf8"
        altoMax={120}
        semilla={11}
      />
      {/* Panel de codigo flotante */}
      <g opacity="0.92">
        <rect x="560" y="150" width="290" height="150" rx="12" fill="#020617" opacity="0.86" />
        <rect x="560" y="150" width="290" height="26" rx="12" fill="#0f172a" />
        <circle cx="576" cy="163" r="4" fill="#f87171" />
        <circle cx="592" cy="163" r="4" fill="#fbbf24" />
        <circle cx="608" cy="163" r="4" fill="#34d399" />
        {[0, 1, 2, 3, 4].map((linea) => (
          <rect
            key={linea}
            x="578"
            y={192 + linea * 18}
            width={linea % 2 ? 168 : 236}
            height="6"
            rx="3"
            fill="url(#qnBrillo)"
            opacity={0.55}
          />
        ))}
      </g>
      {/* Trazos de circuito */}
      <g fill="none" stroke="#38bdf8" strokeWidth="1.6" opacity="0.5">
        <path d="M60 420 H240 L300 360 H430" />
        <path d="M120 470 H300 L360 410 H520" />
        <path d="M700 470 H820" />
      </g>
      {[
        [240, 420],
        [430, 360],
        [300, 470],
      ].map(([cx, cy], indice) => (
        <circle key={indice} cx={cx} cy={cy} r="5" fill="#38bdf8" />
      ))}
    </svg>
  );
}

/** Carretera de la Sierra ecuatoriana con camion de reparto. */
export function SierraCarretera({ className }: EscenaProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 900 500"
      preserveAspectRatio="xMidYMid slice"
      role="img"
      aria-label="Carretera de la sierra ecuatoriana con un camión de reparto y montañas"
    >
      <defs>
        <linearGradient id="scCielo" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0ea5e9" />
          <stop offset="45%" stopColor="#7dd3fc" />
          <stop offset="100%" stopColor="#e0f2fe" />
        </linearGradient>
        <linearGradient id="scMonteLejos" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e3a5f" />
          <stop offset="100%" stopColor="#334155" />
        </linearGradient>
        <linearGradient id="scMonteCerca" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#064e3b" />
          <stop offset="100%" stopColor="#065f46" />
        </linearGradient>
      </defs>
      <rect width="900" height="500" fill="url(#scCielo)" />
      <circle cx="760" cy="96" r="44" fill="#fef9c3" opacity="0.9" />
      <path d="M0 300 L150 176 L280 268 L400 150 L560 300 Z" fill="url(#scMonteLejos)" opacity="0.85" />
      <path d="M420 300 L560 190 L700 268 L820 200 L900 300 Z" fill="#1e3a5f" opacity="0.7" />
      <path d="M0 330 L200 236 L360 322 L520 240 L720 330 L900 250 V500 H0 Z" fill="url(#scMonteCerca)" />
      {/* Carretera en perspectiva */}
      <path d="M330 500 L430 316 L520 316 L640 500 Z" fill="#1f2937" />
      <path d="M474 500 H476 L482 318 H472 Z" fill="#f8fafc" opacity="0.85" />
      {[0, 1, 2, 3, 4, 5].map((indice) => (
        <rect
          key={indice}
          x={474 - indice * 0.4}
          y={330 + indice * 30}
          width={4 + indice * 0.8}
          height={16 + indice * 2}
          fill="#fbbf24"
          opacity={0.9}
        />
      ))}
      {/* Camion de reparto */}
      <g transform="translate(300 402) scale(1.12)">
        <rect x="0" y="18" width="118" height="52" rx="7" fill="#0f172a" />
        <rect x="8" y="26" width="102" height="36" rx="4" fill="#1d4ed8" opacity="0.85" />
        <path d="M118 32h30l16 20v18h-46z" fill="#0a1931" />
        <rect x="124" y="36" width="22" height="16" rx="3" fill="#bae6fd" />
        <circle cx="32" cy="76" r="11" fill="#020617" />
        <circle cx="32" cy="76" r="4.6" fill="#94a3b8" />
        <circle cx="132" cy="76" r="11" fill="#020617" />
        <circle cx="132" cy="76" r="4.6" fill="#94a3b8" />
      </g>
      <path d="M0 470 H900" stroke="#022c22" strokeWidth="2" opacity="0.4" />
    </svg>
  );
}

/** Supervision logistica: mapa esquematico con nodos y rutas. */
export function SupervisionLogistica({ className }: EscenaProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 900 500"
      preserveAspectRatio="xMidYMid slice"
      role="img"
      aria-label="Mapa logístico esquemático con rutas y nodos de entrega"
    >
      <defs>
        <linearGradient id="slFondo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0a1931" />
          <stop offset="55%" stopColor="#132a5c" />
          <stop offset="100%" stopColor="#1e3a8a" />
        </linearGradient>
        <radialGradient id="slRadar" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.45" />
          <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="900" height="500" fill="url(#slFondo)" />
      <g stroke="#1d4ed8" strokeWidth="0.7" opacity="0.28">
        {[0, 1, 2, 3, 4, 5].map((fila) => (
          <path key={`h${fila}`} d={`M0 ${fila * 90 + 30} H900`} />
        ))}
        {[0, 1, 2, 3, 4, 5, 6, 7].map((columna) => (
          <path key={`v${columna}`} d={`M${columna * 112 + 26} 0 V500`} />
        ))}
      </g>
      <circle cx="470" cy="250" r="220" fill="url(#slRadar)" />
      <g fill="none" stroke="#38bdf8" strokeWidth="2.4" opacity="0.85">
        <path d="M180 350 C300 300 340 220 470 210 C600 200 660 260 760 190" />
        <path d="M180 350 C280 250 380 300 470 210" />
        <path d="M470 210 L560 330 L700 350" />
      </g>
      {([
        [180, 350, 9, "#f59e0b"],
        [470, 210, 11, "#38bdf8"],
        [760, 190, 8, "#34d399"],
        [560, 330, 8, "#a78bfa"],
        [700, 350, 8, "#34d399"],
      ] as Array<[number, number, number, string]>).map(([cx, cy, r, color], indice) => (
        <g key={indice}>
          <circle cx={cx} cy={cy} r={r} fill={color} opacity="0.95" />
          <circle cx={cx} cy={cy} r={r + 9} fill="none" stroke={color} strokeWidth="1.4" opacity="0.45" />
        </g>
      ))}
    </svg>
  );
}

export type ArteRol = "operador" | "administrador" | "desarrollador" | "conductor";

export function ArtePanel({ rol }: { rol: ArteRol }) {
  const escenas: Record<ArteRol, ReactNode> = {
    operador: <QuitoAtardecer className="arte-panel__svg" />,
    administrador: <SupervisionLogistica className="arte-panel__svg" />,
    desarrollador: <QuitoNocheTech className="arte-panel__svg" />,
    conductor: <SierraCarretera className="arte-panel__svg" />,
  };
  return <div className="arte-panel">{escenas[rol]}</div>;
}
