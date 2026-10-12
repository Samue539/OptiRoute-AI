from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_cors_permite_preflight_desde_frontend_local():
    response = client.options(
        "/api/optimizacion/planificar",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_no_autorizado_no_recibe_cabecera_de_origen():
    response = client.get(
        "/",
        headers={"Origin": "https://sitio-no-autorizado.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
