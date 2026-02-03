import os
import pytest
import sys
import time

from datetime   import datetime

# Usar una base de datos SQLite local para pruebas antes de importar la app
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "test_db.sqlite")
DB_FILE = os.path.abspath(DB_FILE)
os.environ["DATEBASE_URL"] = f"sqlite:///{DB_FILE}"

# Configuración del nivel de los LOGs a monstrar
os.environ["LOG_LEVEL"] = "DEBUG"

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

# Creación de cliente, conexión a la api
@pytest.fixture
def client():
    return TestClient(app)

# Autenticación de la api con el enpoint /token
@pytest.fixture
def auth_headers(client):
    response = client.post(
        "/token", data={"username": "duppla", "password": "secret"}
    )
    assert response.status_code == 200, "No se pudo obtener el token de autenticación. Verifica las credenciales y el endpoint."
    token_data = response.json()
    access_token = token_data["access_token"]
    return {"Authorization": f"Bearer {access_token}"}

# Pruebas de aunteticación con usaurio no existente
def test_auth_non_existent_user(client):
    response = client.post("/token", data={"username": "nonexistent", "password": "user"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect username or password"

# Pruebas con usaurio existente pero que no se encuentra habilitado
def test_auth_disabled_user(client):
    # Primero, obtenemos un token para el usuario deshabilitado 'admin'
    response = client.post("/token", data={"username": "admin", "password": "secret2"})
    assert response.status_code == 200
    token_data = response.json()
    access_token = token_data["access_token"]
    disabled_auth_headers = {"Authorization": f"Bearer {access_token}"}

    # Ahora, intentamos acceder a un endpoint protegido con ese token
    r = client.get("/documentos/", headers=disabled_auth_headers)
    assert r.status_code == 400
    assert r.json()["detail"] == "Inactive user"

# Creación de documento
def crear_documento(client, auth_headers, tipo=1, monto=100.0, metadata=None):
    payload = {"tipo": tipo, "monto": monto, "metadata": metadata or {"k": "v"}}
    r = client.post("/documentos/", json=payload, headers=auth_headers)
    assert r.status_code == 200
    return r.json()

# Prueba de un ciclo completo (crear, consultar, actualizar, cambiar estado)
def test_crud_ciclo_completo(client, auth_headers):
    # Crear documento
    documento = crear_documento(client, auth_headers, tipo=2, monto=150.5, metadata={"x": 1})
    id_doc = documento.get("id")
    assert documento.get("estado") == 1
    assert documento.get("tipo") == 2
    assert documento.get("monto") == 150.5

    # Consultar que el documetno si existe
    r = client.get(f"/documentos/{id_doc}", headers=auth_headers)
    assert r.status_code == 200
    obtenido = r.json()
    assert obtenido["id"] == id_doc
    assert obtenido["monto"] == 150.5

    payload_actualizacion = {"monto": 250.75, "metadata": {"updated": True}}
    # Actualizar documento
    r = client.put(
        f"/documentos/{id_doc}", json=payload_actualizacion, headers=auth_headers
    )
    assert r.status_code == 200
    actualizado = r.json()
    assert actualizado["monto"] == 250.75

    # Cambio de estado de documento a pendiente
    r = client.patch(f"/documentos/{id_doc}/estado", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == 2

    # Cambio de estado de documetno a aprobado
    r = client.patch(
        f"/documentos/{id_doc}/estado", params={"aprobado": "true"}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["estado"] == 3

# Pruebas de cambio de estado a documetnos
def test_transiciones_estado_invalidas(client, auth_headers):
    # Creacion de documento
    documento = crear_documento(client, auth_headers, tipo=1, monto=10.0)
    id_doc = documento["id"]

    # El documento pasa de borrador a pendiente
    r = client.patch(f"/documentos/{id_doc}/estado", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == 2

    # Falta el parámetro 'aprobado' cuando el estado es 2 -> debe devolver 400
    r = client.patch(f"/documentos/{id_doc}/estado", headers=auth_headers)
    assert r.status_code == 400

    # Aprobar documento
    r = client.patch(f"/documentos/{id_doc}/estado", params={"aprobado": "true"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == 3

    # Intento de transición inválida sobre documento ya aprobado -> 409
    r = client.patch(f"/documentos/{id_doc}/estado", headers=auth_headers)
    assert r.status_code == 409

    # Consulta de recurso inexistente -> 404
    r = client.get("/documentos/9999999", headers=auth_headers)
    assert r.status_code == 404

# Prueba de /documentos/batch/procesar
def test_batch_processing_and_job_status(client, auth_headers):
    # Crear algunos documentos para procesar en lote
    doc1 = crear_documento(client, auth_headers, tipo=5, monto=10.0)
    doc2 = crear_documento(client, auth_headers, tipo=5, monto=20.0)
    doc3 = crear_documento(client, auth_headers, tipo=5, monto=30.0)
    ids_a_procesar = [doc1["id"], doc2["id"], doc3["id"]]

    assert doc1["estado"] == 1
    assert doc2["estado"] == 1
    assert doc3["estado"] == 1

    # Enviar la solicitud de procesamiento por lotes
    r_batch = client.post(
        "/documentos/batch/procesar",
        json={"ids": ids_a_procesar},
        headers=auth_headers,
    )
    assert r_batch.status_code == 200
    job_id = r_batch.json().get("job_id")
    assert job_id is not None

    # Consultar el estado del job hasta que se complete
    job_finalizado = False
    for i in range(15):  # Intentar por un máximo de 10 segundos
        r_job = client.get(f"/jobs/{job_id}", headers=auth_headers)
        assert r_job.status_code == 200
        job_data = r_job.json()

        # Verificar si todos los documentos del job están finalizados o con error
        estados = [job_doc["estado"] for job_doc in job_data["jobs"].values()]
        if all(estado in ["finalizado", "error"] for estado in estados):
            job_finalizado = True
            break
        time.sleep(1)

    assert job_finalizado, "El job no finalizó en el tiempo esperado."

    # Verificar que el estado de los documentos originales haya cambiado.
    r_doc1 = client.get(f"/documentos/{doc1['id']}", headers=auth_headers)
    assert r_doc1.status_code == 200
    assert r_doc1.json()["estado"] == 2

    r_doc2 = client.get(f"/documentos/{doc2['id']}", headers=auth_headers)
    assert r_doc2.status_code == 200
    assert r_doc2.json()["estado"] == 2

# Prueba de búsqueda de documentos con filtros
def test_buscar_documentos_con_filtros(client, auth_headers):
    # Crear documentos de prueba
    crear_documento(client, auth_headers, tipo=1, monto=50.0)
    crear_documento(client, auth_headers, tipo=1, monto=150.0)
    crear_documento(client, auth_headers, tipo=2, monto=250.0)
    doc_pendiente = crear_documento(client, auth_headers, tipo=2, monto=350.0)

    # Cambiar estado de un documento a pendiente para probar filtro de estado
    client.patch(f"/documentos/{doc_pendiente['id']}/estado", headers=auth_headers)

    # 1. Búsqueda por tipo
    r = client.get("/documentos/", params={"tipo": 1}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 2

    # 2. Búsqueda por monto mínimo
    r = client.get("/documentos/", params={"monto_min": 200.0}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 2

    # 3. Búsqueda por monto máximo
    r = client.get("/documentos/", params={"monto_max": 200.0}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 2

    # 4. Búsqueda por estado
    r = client.get("/documentos/", params={"estado": 2}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # 5. Búsqueda combinada (tipo y monto)
    r = client.get("/documentos/", params={"tipo": 1, "monto_min": 100.0}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # 6. Búsqueda por rango de fecha (fecha_desde y fecha_hasta)
    now = datetime.now()
    fecha_desde = now.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
    fecha_hasta = now.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%d %H:%M:%S")
    r = client.get("/documentos/", params={"fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 4
