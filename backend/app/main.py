import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.ia import router as ia_router
from backend.app.api.auth import router as auth_router
from backend.app.api.clientes import router as clientes_router
from backend.app.api.conductores import router as conductores_router
from backend.app.api.grafo import router as grafo_router
from backend.app.api.nodos import router as nodos_router
from backend.app.api.rutas import router as rutas_router
from backend.app.api.optimizacion import router as optimizacion_router
from backend.app.api.pedidos import router as pedidos_router
from backend.app.api.vehiculos import router as vehiculos_router
from backend.app.api.empresas import router as empresas_router
from backend.app.api.distribucion import router as distribucion_router


app = FastAPI(
    title="OptiRoute AI API",
    description=(
        "Sistema inteligente de optimizacion de rutas "
        "mediante grafos e inteligencia artificial."
    ),
    version="0.1.0",
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


app.include_router(auth_router)
app.include_router(rutas_router)
app.include_router(optimizacion_router)
app.include_router(ia_router)
app.include_router(pedidos_router)
app.include_router(vehiculos_router)
app.include_router(conductores_router)
app.include_router(nodos_router)
app.include_router(clientes_router)
app.include_router(grafo_router)
app.include_router(empresas_router)
app.include_router(distribucion_router)


@app.get("/")
def inicio():
    return {
        "sistema": "OptiRoute AI",
        "estado": "funcionando",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }
