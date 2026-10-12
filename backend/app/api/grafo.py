import math
import pathlib
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.algorithms.bfs import bfs
from backend.app.algorithms.dfs import dfs
from backend.app.core.database import obtener_conexion
from backend.app.core.deps import Principal, requiere_permiso
from backend.app.core.permisos import Permiso
from backend.app.services.grafo_service import cargar_grafo_desde_bd, obtener_nodo


class TmcUbicacionUpdate(BaseModel):
    latitud: float
    longitud: float


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

router = APIRouter(prefix="/api/grafo", tags=["Grafo"])


@router.get("", summary="Grafo completo con nodos y aristas")
def get_grafo(
    principal: Principal = Depends(requiere_permiso(Permiso.RECURSOS_VER)),
):
    grafo = cargar_grafo_desde_bd()
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT id_nodo, nombre, tipo_nodo, latitud, longitud, activo FROM logistica.nodos WHERE activo=TRUE ORDER BY id_nodo;")
            nodos = [{"id_nodo": r[0], "nombre": r[1], "tipo_nodo": r[2], "latitud": float(r[3]), "longitud": float(r[4]), "activo": r[5]} for r in cur.fetchall()]
            cur.execute("SELECT id_conexion, id_nodo_origen, id_nodo_destino, distancia_km, tiempo_minutos, costo, bidireccional, activo FROM logistica.conexiones WHERE activo=TRUE ORDER BY id_conexion;")
            conexiones = [{"id_conexion": r[0], "origen": r[1], "destino": r[2], "distancia_km": float(r[3]), "tiempo_minutos": float(r[4]) if r[4] else None, "costo": float(r[5]), "bidireccional": r[6], "activo": r[7]} for r in cur.fetchall()]
    finally:
        conexion.close()
    return {"nodos": nodos, "conexiones": conexiones, "vertices": grafo.obtener_vertices()}


@router.get("/bfs")
def run_bfs(
    inicio: int,
    principal: Principal = Depends(requiere_permiso(Permiso.RECURSOS_VER)),
):
    nodo = obtener_nodo(inicio)
    if nodo is None:
        raise HTTPException(status_code=404, detail="Nodo inicio no existe")
    grafo = cargar_grafo_desde_bd()
    recorrido = bfs(grafo, inicio)
    detalles = [obtener_nodo(n) for n in recorrido]
    return {"algoritmo": "BFS", "inicio": nodo, "recorrido": recorrido, "detalles": detalles, "visitados": len(recorrido)}


@router.get("/dfs")
def run_dfs(
    inicio: int,
    principal: Principal = Depends(requiere_permiso(Permiso.RECURSOS_VER)),
):
    nodo = obtener_nodo(inicio)
    if nodo is None:
        raise HTTPException(status_code=404, detail="Nodo inicio no existe")
    grafo = cargar_grafo_desde_bd()
    recorrido = dfs(grafo, inicio)
    detalles = [obtener_nodo(n) for n in recorrido]
    return {"algoritmo": "DFS", "inicio": nodo, "recorrido": recorrido, "detalles": detalles, "visitados": len(recorrido)}


@router.patch("/nodos/{id_nodo}/ubicacion", summary="Actualizar ubicación de nodo (TMC draggable)")
def actualizar_ubicacion_nodo(
    id_nodo: int,
    datos: TmcUbicacionUpdate,
    principal: Principal = Depends(requiere_permiso(Permiso.CONFIGURACION_TECNICA)),
):
    if not (-90 <= datos.latitud <= 90 and -180 <= datos.longitud <= 180):
        raise HTTPException(status_code=400, detail="Coordenadas fuera de rango")
    # Solo permitir TMC (id 1) en modo demo, pero genérico para cualquier nodo BODEGA
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT id_nodo, nombre, tipo_nodo FROM logistica.nodos WHERE id_nodo=%s", (id_nodo,))
            fila = cur.fetchone()
            if fila is None:
                raise HTTPException(status_code=404, detail="Nodo no existe")
            # Actualizar nodo
            cur.execute("UPDATE logistica.nodos SET latitud=%s, longitud=%s, actualizado_en=CURRENT_TIMESTAMP WHERE id_nodo=%s", (datos.latitud, datos.longitud, id_nodo))
            # Sincronizar dirección si existe
            cur.execute("UPDATE operaciones.direcciones SET latitud=%s, longitud=%s WHERE id_nodo=%s", (datos.latitud, datos.longitud, id_nodo))
            # Recalcular aristas donde participa este nodo (solo una vez por arista, no duplicar bidireccional)
            cur.execute("SELECT id_conexion, id_nodo_origen, id_nodo_destino FROM logistica.conexiones WHERE id_nodo_origen=%s OR id_nodo_destino=%s", (id_nodo, id_nodo))
            conns = cur.fetchall()
            for cid, orig, dest in conns:
                cur.execute("SELECT latitud, longitud FROM logistica.nodos WHERE id_nodo=%s", (orig,))
                lat1, lon1 = cur.fetchone()
                cur.execute("SELECT latitud, longitud FROM logistica.nodos WHERE id_nodo=%s", (dest,))
                lat2, lon2 = cur.fetchone()
                dist = round(_haversine(float(lat1), float(lon1), float(lat2), float(lon2)), 3)
                tiempo = round(dist * 2.2, 2)
                cur.execute("UPDATE logistica.conexiones SET distancia_km=%s, tiempo_minutos=%s WHERE id_conexion=%s", (dist, tiempo, cid))
        conexion.commit()
        # Actualizar seed 004 si es TMC (id 1)
        if id_nodo == 1:
            try:
                seed_path = pathlib.Path(__file__).resolve().parents[3] / "database" / "seeds" / "004_tmc_matriz.sql"
                if seed_path.exists():
                    content = seed_path.read_text(encoding="utf-8")
                    # reemplazar latitud/longitud del UPDATE TMC (dos ocurrencias: comentario y UPDATE)
                    content = re.sub(r"lat -0\.0966838, lon -78\.4753787", f"lat {datos.latitud}, lon {datos.longitud}", content)
                    content = re.sub(r"latitud = -0\.0966838", f"latitud = {datos.latitud}", content)
                    content = re.sub(r"longitud = -78\.4753787", f"longitud = {datos.longitud}", content)
                    # actualizar distancias harcodeadas en seed a valores recalculados (se mantendrán 6 valores, pero se recalculan en BD ya)
                    # agregar nota de ajuste visual
                    if "Coordenada ajustada visualmente" not in content:
                        content = content.replace(
                            "Coordenada referencial verificada para la intersección",
                            "Coordenada ajustada visualmente sobre el predio TMC/Tramaco Express mostrado por OpenStreetMap. Referencial intersección",
                        )
                    seed_path.write_text(content, encoding="utf-8")
            except Exception:
                pass  # no bloquear actualización BD por error de seed
        nodo = obtener_nodo(id_nodo)
        return {"id_nodo": id_nodo, "nombre": nodo["nombre"] if nodo else "", "latitud": datos.latitud, "longitud": datos.longitud, "recalculadas": len(conns)}
    except HTTPException:
        conexion.rollback()
        raise
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()
