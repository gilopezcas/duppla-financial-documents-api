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

- **API:** Los endpoints están definidos en `app/main.py`.
- **Validación de Datos:** Pydantic se encarga de la validación y serialización de los datos de entrada y salida.
- **Base de Datos:** Se utiliza SQLAlchemy como ORM, lo que permite interactuar con diferentes motores de bases de datos como PostgreSQL o SQLite con solo cambiar la URL de conexión, sin necesidad de modificar el código. Los modelos de datos se encuentran en `app/models.py`.
- **Procesamiento Asíncrono:** Una tarea en segundo plano simple, implementada con el módulo `threading` de Python, gestiona el procesamiento de lotes de documentos.
- **Inicialización:** Al iniciar, la aplicación puede crear las tablas de la base de datos y poblarlas con datos iniciales.

Trade-offs y Limitaciones
-------------------------
- **Worker Asíncrono:** Se utilizó `threading` para el procesamiento en background por su simplicidad. La principal limitación es que no es robusto para un entorno de producción: no hay reintentos automáticos, persistencia de colas (si la API se reinicia, los jobs en memoria se pierden).
- **Seguridad:** Se implementó un esquema básico de autenticación con `OAuth2PasswordBearer` y tokens (Bearer Token) para proteger los endpoints. Sin embargo, la implementación es simple y no es segura para producción: los usuarios se gestionan en un diccionario en memoria en lugar de una base de datos, y el hashing de contraseñas es simulado. No se implementó un sistema de roles o permisos (autorización).
- **Manejo de Errores:** El manejo de errores es básico. Una versión de producción debería tener un sistema de logging más estructurado y un manejo de excepciones especifico para diferentes casos (ej. problemas de conexión a la BD, datos inválidos, etc.).

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
```
2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Ejecutar la aplicación:
Desde la carpeta `app`, utiliza `uvicorn` para iniciar el servidor:
```bash
cd app
uvicorn main:app --reload
```
La API estará disponible en `http://127.0.0.1:8000`.

Ejecución de Pruebas
--------------------
Para ejecutar el conjunto de pruebas, asegúrate de tener las dependencias instaladas y luego ejecuta `pytest` desde la carpeta `app`:
```bash
cd app
pytest -q
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
