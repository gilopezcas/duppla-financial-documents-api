# duppla-financial-documents-api
API REST de gestion de documentos financieros (facturas, recibos, comprobantes).

Descripción
-----------
API mínima para crear, buscar y procesar documentos financieros. Incluye:
- Endpoints REST para CRUD básico y búsqueda con filtros.
- Procesamiento asíncrono de batches usando `threading` (worker local).
- Soporte para ejecución local y en Docker (imagen y `docker-compose`).

Arquitectura y patrones
-----------------------
Patrones y decisiones de diseño aplicados en esta prueba técnica:

- **Controladores:** Los endpoints en `app/main.py` actúan como controladores que reciben y validan requests (usando `pydantic`), gestionan la sesión y retornan respuestas.
- **ORM directo:** Se usa SQLAlchemy con modelos en `app/models.py` y el código accede al `Session` directamente desde los controladores. No se implementó una capa `Repository` explícita para mantener el proyecto pequeño y directo.
- **Unidad de Trabajo:** Las transacciones se gestionan mediante `Session` de SQLAlchemy; cada operación crea/usa la sesión (dependencia `get_db`) y realiza commit/rollback apropiados.
- **Worker background:** El procesamiento de batches se implementó con `threading.Thread`.
- **Validación:** `pydantic` se usa para definir los esquemas de entrada (`Documento`, `BatchRequest`) y validar payloads.
- **Inicialización/Seed:** La función `init_db()` realiza creación de tablas y seed de datos por defecto al iniciar la app.

Requisitos
---------
- Python 3.11 (recomendado)
- pip
- PostgreSQL 12+ (o usar el servicio `db` en `docker-compose`)
- Docker & Docker Compose (opcional, para levantar el entorno local)

Instalación (entorno local)
---------------------------
1. Crear y activar un virtualenv:
```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Windows cmd
.venv\Scripts\activate.bat
# Unix / macOS
source .venv/bin/activate
```
2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

Instalación (Docker)
---------------------------
Levantar el entorno con Docker Compose:
```bash
docker-compose up -d --build
```

Endpoints principales
--------------------
- `POST /documentos/` — Crear documento. Body: `{ "tipo": int, "monto": float, "metadata": {...} }`.
- `GET /documentos/{id}` — Obtener documento por id.
- `PUT /documentos/{id}` — Actualizar `monto` y/o `metadata`.
- `GET /documentos` — Buscar documentos; soporta query params: `tipo`, `estado`, `monto_min`, `monto_max`, `fecha_desde`, `fecha_hasta`, `limit`, `offset`.
- `PATCH /documentos/{id}/estado` — Cambiar estado (transiciones controladas; si está en `pendiente` requiere `aprobado=true|false`).
- `POST /documentos/batch/procesar` — Encolar batch: Body `{ "ids": [1,2,3] }`. Devuelve `job_id`.
- `GET /jobs/{job_id}` — Consultar estado y progreso del batch.

Significados
-----------
Variables y códigos utilizados por la API:

- `DATEBASE_URL`: variable de entorno que contiene la URL de conexión a PostgreSQL. Ejemplo: `postgresql://postgres:postgres@db:5432/dupla_db`.

- `Documentos.estado` (valores enteros):
	- `1` = borrador
	- `2` = pendiente
	- `3` = aprobado
	- `4` = rechazado

- `Documentos.tipo` (valores enteros):
	- `1` = facturas
	- `2` = recibos
	- `3` = comprobantes

- `Batch.jobs` (estructura interna del batch): para cada entrada se mantiene un objeto con campos:
	- `id_documento`: id del documento a procesar
	- `estado`: `pendiente` | `finalizado` | `error`
	- `error`: texto opcional con la causa del fallo
