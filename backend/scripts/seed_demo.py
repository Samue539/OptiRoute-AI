"""
Seed demo seguro para OptiRoute AI.
Ejecutar: python -m backend.scripts.seed_demo
o: .venv\Scripts\python backend\scripts\seed_demo.py
Idempotente: no duplica datos DEMO.
"""

import os
import pathlib

from dotenv import load_dotenv

load_dotenv()

from backend.app.core.database import obtener_conexion

ROOT = pathlib.Path(__file__).resolve().parents[2]
SQL_FILES = [
    ROOT / "database" / "seeds" / "001_grafo_prueba.sql",
    ROOT / "database" / "seeds" / "002_datos_demo.sql",
    ROOT / "database" / "seeds" / "003_demo_completo.sql",
    ROOT / "database" / "seeds" / "004_tmc_matriz.sql",
]

def run_seed():
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            for sql_path in SQL_FILES:
                if not sql_path.exists():
                    print(f"[WARN] No existe {sql_path}")
                    continue
                print(f"[INFO] Ejecutando {sql_path.name} ...")
                sql = sql_path.read_text(encoding="utf-8")
                # psycopg can execute multiple statements; pg8000 also supports.
                # For pg8000 we need split? We'll try execute whole.
                try:
                    cur.execute(sql)
                except Exception as e:
                    # fallback: split by semicolon for pg8000
                    statements = [s.strip() for s in sql.split(";") if s.strip()]
                    for stmt in statements:
                        cur.execute(stmt + ";")
                print(f"[OK] {sql_path.name}")
        conn.commit()
        print("[OK] Seed DEMO completado.")
        # mostrar resumen
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM logistica.nodos;")
            print("nodos:", cur.fetchone()[0])
            cur.execute("SELECT count(*) FROM operaciones.pedidos;")
            print("pedidos:", cur.fetchone()[0])
            cur.execute("SELECT count(*) FROM operaciones.clientes;")
            print("clientes:", cur.fetchone()[0])
            cur.execute("SELECT count(*) FROM logistica.vehiculos;")
            print("vehiculos:", cur.fetchone()[0])
            cur.execute("SELECT count(*) FROM logistica.conductores;")
            print("conductores:", cur.fetchone()[0])
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] {exc}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_seed()
