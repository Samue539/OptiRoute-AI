from fastapi import FastAPI

from backend.app.api.rutas import router as rutas_router
from backend.app.api.optimizacion import router as optimizacion_router


app = FastAPI(
    title="OptiRoute AI API",
    description=(
        "Sistema inteligente de optimizacion de rutas "
        "mediante grafos e inteligencia artificial."
    ),
    version="0.1.0",
)


app.include_router(rutas_router)
app.include_router(optimizacion_router)


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