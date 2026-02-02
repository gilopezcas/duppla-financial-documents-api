from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from models     import *
from database   import *

from pydantic   import BaseModel

from time       import sleep
from datetime   import datetime
from threading  import Thread

class Documento(BaseModel):
    tipo: int
    monto: float
    fecha_creacion: str=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata:dict=None

class DocumentoActualizar(BaseModel):
    monto:  float   = None
    metadata:dict   = None


class BatchRequest(BaseModel):
    ids: list[int]

app = FastAPI()
init_db()

# db_dependency = Annotated[Session, Depends(get_db)]

@app.post("/documentos/")
def crear_documento(documento:Documento, db:Session=Depends(get_db)):
    """Crear un documento.

    Body: `Documento` (tipo, monto, fecha_creacion, metadata opcional).
    Crea la entrada en la tabla `documentos` con `estado=1` (borrador) y
    devuelve el objeto creado.
    """
    documento_dict = documento.model_dump()
    documento_dict["_metadata"] = documento_dict["metadata"]
    documento_dict.pop("metadata")
    db_obj = Documentos(**documento_dict, estado=1)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@app.get("/documentos/{id_documento}")
def consultar_documento(id_documento:int, db:Session=Depends(get_db)):
    """Obtener un documento por su ID.

    Path param: `id_documento` (int).
    Retorna el registro `Documentos` si existe, o 404 si no se encuentra.
    """
    _documento:Documento = db.query(Documentos).filter(Documentos.id == id_documento).first()
    if not _documento:
        raise HTTPException(status_code=404, detail=f"Documento {id_documento} no encontrado")
    return _documento

@app.put("/documentos/{id_documento}")
def actualizar_documento(id_documento:int, documento:DocumentoActualizar, db:Session=Depends(get_db)):
    """Actualizar campos permitidos de un documento.

    Path param: `id_documento` (int).
    Body: `DocumentoActualizar` (solo `monto` y/o `metadata`).
    Realiza cambios parciales y devuelve el objeto actualizado.
    """
    _documento:Documento = db.query(Documentos).filter(Documentos.id == id_documento).first()
    if not _documento:
        raise HTTPException(status_code=404, detail=f"Documento {id_documento} no encontrado")
    
    if documento.monto is not None: _documento.monto = documento.monto
    if documento.metadata is not None: _documento._metadata = documento.metadata

    db.commit()
    db.refresh(_documento)

    return _documento

@app.get("/documentos")
def buscar_documentos(tipo: int = None, estado: int = None, monto_min: float = None, monto_max: float = None, fecha_desde: str = None, fecha_hasta: str = None, limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """Buscar documentos con filtros simples y paginación.

    Parámetros aceptados (todos opcionales):
    - `tipo`, `estado`: filtros por id
    - `monto_min`, `monto_max`: rango de monto
    - `fecha_desde`, `fecha_hasta`: rango de `fecha_creacion` (formato YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
    - `limit`, `offset`: paginación
    """
    query = db.query(Documentos)
    if tipo is not None:
        query = query.filter(Documentos.tipo == tipo)
    if estado is not None:
        query = query.filter(Documentos.estado == estado)
    if monto_min is not None:
        query = query.filter(Documentos.monto >= monto_min)
    if monto_max is not None:
        query = query.filter(Documentos.monto <= monto_max)
    if fecha_desde is not None:
        query = query.filter(Documentos.fecha_creacion >= fecha_desde)
    if fecha_hasta is not None:
        query = query.filter(Documentos.fecha_creacion <= fecha_hasta)

    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return {"total": total, "items": items}

@app.patch("/documentos/{id_documento}/estado")
def cambiar_estado(id_documento:int, aprobado:bool=None, db:Session=Depends(get_db)):
        """Cambiar el estado del documento según la máquina de estados.

        Transiciones permitidas:
        - Si `estado==1` (borrador) -> se pasa a `2` (pendiente).
        - Si `estado==2` (pendiente) -> requiere query param `aprobado` (bool):
            `true` => `3` (aprobado), `false` => `4` (rechazado).
        Cualquier otra transición devuelve 409 Conflict.
        """
        _documento:Documentos = db.query(Documentos).filter(Documentos.id == id_documento).first()
    if not _documento:
        raise HTTPException(status_code=404, detail=f"Documento {id_documento} no encontrado")
    
    match _documento.estado:
        case 1:
            print("Actualizar de borrador a pendiente")
            _documento.estado = 2
        case 2:
            if aprobado is None:
                raise HTTPException(status_code=400, detail="Falta el parámetro 'aprobado' (true|false) para decidir aprobación/rechazo")
            if not isinstance(aprobado, bool):
                raise HTTPException(status_code=400, detail="Parámetro 'aprobado' inválido; se espera booleano")
            _documento.estado = 3 if aprobado else 4
        case __:
            raise HTTPException(status_code=409, detail=f"Transición inválida: el documento {id_documento} ya está {'aprobado (estado=3)' if _documento.estado == 3 else 'rechazado (estado=4)'}")

    db.commit()
    db.refresh(_documento)

    return _documento

def iniciar_batch(id_job:str):
    """Worker local que procesa los jobs de un `Batch`.

    Este helper se ejecuta en un `Thread` y actualiza la fila `Batch.jobs`
    conforme procesa cada documento (marca `finalizado` o `error`).
    """
    try:
        for db in get_db():
            _batch:Batch = db.query(Batch).filter(Batch.id_job == id_job).first()
            if _batch:
                sleep_time = 10 / len(_batch.jobs)
                sleep(sleep_time)
                _jobs = _batch.jobs.copy()
                for id_doc in _jobs:
                    print(f"{type(_jobs)=}")
                    if _doc:= db.query(Documentos).filter(Documentos.id == _jobs[id_doc]["id_documento"]).first():
                        print(f"{_doc=}")
                        _jobs[id_doc]["estado"] = "finalizado"
                        match _doc.estado:
                            case 1: _doc.estado = 2
                            case 2: _doc.estado = 3
                            case __:
                                _jobs[id_doc]["error"] = f"El documento {_jobs[id_doc]['id_documento']} ya está {'aprobado (estado=3)' if _doc.estado == 3 else 'rechazado (estado=4)'}"
                                _jobs[id_doc]["estado"] = "error"
                    else:
                        _jobs[id_doc]["error"] = f"Documento {_jobs[id_doc]['id_documento']} no encontrado"
                        _jobs[id_doc]["estado"] = "error"
                    _batch.jobs = _jobs
                    db.commit()
                    sleep(sleep_time)
                db.refresh(_batch)
                print(f"{_batch.jobs=}")

    except Exception as e:
        print(f"Error: {e}")

@app.post("/documentos/batch/procesar")
def procesar_batch(payload: BatchRequest, db:Session=Depends(get_db)):
    """Crear un batch de procesamiento y lanzarlo en background.

    Body: { "ids": [<id_documento>, ...] }
    Crea una fila en la tabla `Batch` con una estructura `jobs` y arranca
    un `Thread` que ejecuta `iniciar_batch` para procesarlos.
    Devuelve: `{ "job_id": <id_job> }`.
    """
    documentos = {}
    for id_doc in payload.ids:
        documentos[f"{id_doc}"] = {"id_documento":id_doc, "estado":"pendiente", "error":None}

    batch = Batch(jobs=documentos)
    db.add(batch)
    db.commit()
    db.refresh(batch)

    Thread(target=iniciar_batch, args=(batch.id_job,)).start()
    return {"job_id": batch.id_job}

@app.get("/jobs/{job_id}")
def job_status(job_id: str, db:Session=Depends(get_db)):
    """Consultar el estado de un `Batch` por `job_id`.

    Path param: `job_id` (UUID string).
    Retorna la fila `Batch` completa con el campo `jobs` que contiene el
    progreso y errores por documento.
    """
    job = db.query(Batch).filter(Batch.id_job == job_id).first()
    if not job:
        raise HTTPException(404, detail=f"Job {job_id} no existe")
    return job
