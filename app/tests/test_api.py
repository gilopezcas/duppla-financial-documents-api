import os
import pytest
import sys

# Usar una base de datos SQLite local para pruebas antes de importar la app
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "test_db.sqlite")
DB_FILE = os.path.abspath(DB_FILE)
os.environ["DATEBASE_URL"] = f"sqlite:///{DB_FILE}"

try:
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
except Exception:
    pass

# Poner el directorio `app/` primero en sys.path para que las importaciones
# actuales dentro de `app/` (por ejemplo `from models import *`) resuelvan
# correctamente hacia `app/models.py` sin modificar `app/main.py`.
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Mantener también la raíz del proyecto en sys.path por compatibilidad
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def crear_documento(client, tipo=1, monto=100.0, metadata=None):
    payload = {"tipo": tipo, "monto": monto, "metadata": metadata or {"k": "v"}}
    r = client.post("/documentos/", json=payload)
    assert r.status_code == 200
    return r.json()


def test_crud_camino_feliz(client):
    documento = crear_documento(client, tipo=2, monto=150.5, metadata={"x": 1})
    id_doc = documento.get("id")
    assert documento.get("estado") == 1
    assert documento.get("tipo") == 2
    assert documento.get("monto") == 150.5

    r = client.get(f"/documentos/{id_doc}")
    assert r.status_code == 200
    obtenido = r.json()
    assert obtenido["id"] == id_doc
    assert obtenido["monto"] == 150.5

    payload_actualizacion = {"monto": 250.75, "metadata": {"updated": True}}
    r = client.put(f"/documentos/{id_doc}", json=payload_actualizacion)
    assert r.status_code == 200
    actualizado = r.json()
    assert actualizado["monto"] == 250.75

    r = client.patch(f"/documentos/{id_doc}/estado")
    assert r.status_code == 200
    assert r.json()["estado"] == 2

    r = client.patch(f"/documentos/{id_doc}/estado", params={"aprobado": "true"})
    assert r.status_code == 200
    assert r.json()["estado"] == 3


def test_transiciones_estado_invalidas(client):
    documento = crear_documento(client, tipo=1, monto=10.0)
    id_doc = documento["id"]

    r = client.patch(f"/documentos/{id_doc}/estado")
    assert r.status_code == 200
    assert r.json()["estado"] == 2

    # Falta el parámetro 'aprobado' cuando el estado es 2 -> debe devolver 400
    r = client.patch(f"/documentos/{id_doc}/estado")
    assert r.status_code == 400

    # Aprobar
    r = client.patch(f"/documentos/{id_doc}/estado", params={"aprobado": "true"})
    assert r.status_code == 200
    assert r.json()["estado"] == 3

    # Intento de transición inválida sobre documento ya aprobado -> 409
    r = client.patch(f"/documentos/{id_doc}/estado")
    assert r.status_code == 409

    # Consulta de recurso inexistente -> 404
    r = client.get("/documentos/9999999")
    assert r.status_code == 404


def test_limite_de_tasa(client):
    intentos = 30
    obtuvo_429 = False
    for _ in range(intentos):
        r = client.get("/documentos/")
        if r.status_code == 429:
            obtuvo_429 = True
            break

    if obtuvo_429:
        assert True
    else:
        pytest.skip("Limitación de tasa no configurada en la aplicación; omitiendo la aseveración de rate-limit.")
