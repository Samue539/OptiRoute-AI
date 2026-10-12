import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

type MapPoint = { id: number; nombre: string; lat: number; lng: number; tipo: string; orden?: number };
type MapRoute = { id: string; points: MapPoint[]; color: string; label: string };

function FitBounds({ points, trigger }: { points: MapPoint[]; trigger?: number }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) return;
    const bounds = L.latLngBounds(points.map(p => [p.lat, p.lng] as [number, number]));
    map.fitBounds(bounds, { padding: [24, 24] });
  }, [points, map, trigger]);
  return null;
}

function FocusUser({ location, zoom = 16 }: { location: { lat: number; lng: number } | null; zoom?: number }) {
  const map = useMap();
  useEffect(() => {
    if (!location) return;
    map.setView([location.lat, location.lng], zoom, { animate: true });
  }, [location, zoom, map]);
  return null;
}
function FocusPoint({ point, trigger, zoom = 15 }: { point: { lat: number; lng: number } | null; trigger?: number; zoom?: number }) {
  const map = useMap();
  useEffect(() => {
    if (!point || trigger === undefined) return;
    if (trigger === 0) return;
    map.setView([point.lat, point.lng], zoom, { animate: true });
  }, [point, trigger, zoom, map]);
  return null;
}
function MapClickHandler({ onClick, enabled }: { onClick?: (lat: number, lng: number) => void; enabled?: boolean }) {
  const map = useMap();
  useEffect(() => {
    if (!enabled || !onClick) return;
    const handler = (e: L.LeafletMouseEvent) => onClick(e.latlng.lat, e.latlng.lng);
    map.on("click", handler);
    return () => { map.off("click", handler); };
  }, [map, onClick, enabled]);
  return null;
}

function iconFor(tipo: string, nombre: string, orden?: number) {
  const isTMC = nombre.includes("TMC") || nombre.includes("Tramaco");
  if (isTMC) {
    return L.divIcon({
      className: "custom-div-icon",
      html: `<div style="background:#0a1931;color:white;width:36px;height:36px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-size:14px;border:3px solid white;box-shadow:0 4px 12px rgba(10,25,49,.35)">🏢</div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    });
  }
  const bg = tipo === "BODEGA" ? "#0a1931" : tipo === "CLIENTE" ? "#10b981" : "#94a3b8";
  const label = orden != null ? String(orden) : tipo === "BODEGA" ? "B" : "•";
  return L.divIcon({
    className: "custom-div-icon",
    html: `<div style="background:${bg};color:white;width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-size:11px;border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,.25)">${label}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

export default function LeafletMap({
  points,
  routes,
  height = 420,
  userLocation,
  focusTrigger,
  fitTrigger,
  focusPoint,
  focusPointTrigger,
  disableAutoFit = false,
  editableTmc = false,
  pendingTmcLocation = null as { lat: number; lng: number } | null,
  onTmcDragEnd,
  onMapClick,
}: {
  points: MapPoint[];
  routes: MapRoute[];
  height?: number;
  userLocation?: { lat: number; lng: number; accuracy?: number } | null;
  focusTrigger?: number;
  fitTrigger?: number;
  focusPoint?: { lat: number; lng: number } | null;
  focusPointTrigger?: number;
  disableAutoFit?: boolean;
  editableTmc?: boolean;
  pendingTmcLocation?: { lat: number; lng: number } | null;
  onTmcDragEnd?: (lat: number, lng: number) => void;
  onMapClick?: (lat: number, lng: number) => void;
}) {
  const center: [number, number] = userLocation ? [userLocation.lat, userLocation.lng] : points.length ? [points[0].lat, points[0].lng] : [-0.0966838, -78.4753787];
  const zoom = userLocation ? 16 : 13;
  const colors = ["#2563eb", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"];

  const userIcon = L.divIcon({
    className: "user-div-icon",
    html: `<div style="background:#2563eb;color:white;width:36px;height:36px;border-radius:50%;display:grid;place-items:center;font-size:16px;border:3px solid white;box-shadow:0 4px 14px rgba(37,99,235,.4)">📍</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });

  return (
    <div style={{ height, borderRadius: 14, overflow: "hidden", border: "1px solid #dfe5df" }}>
      <MapContainer center={center} zoom={zoom} style={{ height: "100%", width: "100%" }} scrollWheelZoom={true}>
        <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {routes.map((r, idx) => (
          <Polyline
            key={r.id}
            positions={r.points.map(p => [p.lat, p.lng] as [number, number])}
            pathOptions={{ color: r.color || colors[idx % colors.length], weight: 4, opacity: 0.85 }}
          />
        ))}
        {points.map(p => {
          const isTMC = p.nombre.includes("TMC");
          const isDraggable = isTMC && !!editableTmc;
          return (
            <Marker
              key={`${p.id}-${p.orden ?? ""}`}
              position={[p.lat, p.lng]}
              icon={iconFor(p.tipo, p.nombre, p.orden)}
              draggable={isDraggable}
              eventHandlers={
                isDraggable && onTmcDragEnd
                  ? {
                      dragend: (e: any) => {
                        const ll = e.target.getLatLng();
                        onTmcDragEnd(ll.lat, ll.lng);
                      },
                    }
                  : undefined
              }
            >
              <Popup>
                {isTMC ? (
                  <>
                    <strong>🏢 TMC Grupo Tramaco</strong><br />Matriz Central Quito<br /><small>Manuel Najas OE1-346 y Joaquín Mancheno<br />Carcelén Industrial</small><br /><small>{p.lat.toFixed(5)}, {p.lng.toFixed(5)}</small>
                    {isDraggable && <><br /><small style={{ color: "#7c3aed", fontWeight: 700 }}>Arrastrable — suelta sobre Tramaco Express</small></>}
                  </>
                ) : (
                  <>
                    <strong>{p.nombre}</strong><br />{p.tipo} {p.orden ? `#${p.orden}` : ""}<br /><small>{p.lat.toFixed(5)}, {p.lng.toFixed(5)}</small>
                  </>
                )}
              </Popup>
            </Marker>
          );
        })}
        {pendingTmcLocation && (
          <Marker
            position={[pendingTmcLocation.lat, pendingTmcLocation.lng]}
            icon={L.divIcon({
              className: "pending-tmc",
              html: `<div style="background:#f59e0b;color:white;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;font-size:14px;border:3px solid white;box-shadow:0 3px 10px rgba(245,158,11,.5)">◎</div>`,
              iconSize: [32, 32],
              iconAnchor: [16, 16],
            })}
          >
            <Popup>
              <strong>◎ Nueva ubicación TMC (pendiente)</strong><br />
              {pendingTmcLocation.lat.toFixed(6)}, {pendingTmcLocation.lng.toFixed(6)}<br />
              <small>Pulsa Guardar para confirmar</small>
            </Popup>
          </Marker>
        )}
        {userLocation && (
          <>
            <Marker position={[userLocation.lat, userLocation.lng]} icon={userIcon}>
              <Popup>
                <strong>📍 Mi ubicación</strong><br />
                {userLocation.lat.toFixed(6)}, {userLocation.lng.toFixed(6)}<br />
                {userLocation.accuracy ? <small>Precisión ±{Math.round(userLocation.accuracy)} m</small> : null}
              </Popup>
            </Marker>
          </>
        )}
        {!disableAutoFit && points.length > 1 && <FitBounds points={userLocation ? [...points, { id: -1, nombre: "Mi ubicación", lat: userLocation.lat, lng: userLocation.lng, tipo: "USER" }] : points} trigger={fitTrigger} />}
        {focusTrigger !== undefined && userLocation && <FocusUser location={userLocation} zoom={16} />}
        {focusPoint && focusPointTrigger !== undefined && <FocusPoint point={focusPoint} trigger={focusPointTrigger} zoom={15} />}
        <MapClickHandler enabled={!!editableTmc && !!onMapClick} onClick={onMapClick} />
      </MapContainer>
    </div>
  );
}
