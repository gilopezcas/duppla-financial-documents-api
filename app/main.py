from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
# from . import database, models
from database  import *
from models import *

from datetime   import datetime
from pydantic   import BaseModel

class Documento(BaseModel):
    tipo: int
    monto: float
    fecha_creacion: str=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata:dict=None

class DocumentoActualizar(BaseModel):
    monto:  float   = None
    metadata:dict   = None

app = FastAPI()
init_db()

# db_dependency = Annotated[Session, Depends(get_db)]

@app.post("/documentos/")
def crear_documento(documento:Documento, db:Session=Depends(get_db)):
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
    _documento:Documento = db.query(Documentos).filter(Documentos.id == id_documento).first()
    if not _documento:
        raise HTTPException(status_code=404, detail=f"Documento {id_documento} no encontrado")
    return _documento

@app.put("/documentos/{id_documento}")
def actualizar_documento(id_documento:int, documento:DocumentoActualizar, db:Session=Depends(get_db)):
    _documento:Documento = db.query(Documentos).filter(Documentos.id == id_documento).first()
    if not _documento:
        raise HTTPException(status_code=404, detail=f"Documento {id_documento} no encontrado")
    
    if documento.monto is not None: _documento.monto = documento.monto
    if documento.metadata is not None: _documento._metadata = documento.metadata

    db.commit()
    db.refresh(_documento)

    return _documento

@app.get("/documentos")
def buscar_documentos():
    return {}

@app.patch("/documentos/{id_documento}/estado")
def cambiar_estado(id_documento:int, aprobado:bool=None, db:Session=Depends(get_db)):
    _documento:Documentos = db.query(Documentos).filter(Documentos.id == id_documento).first()
    if not _documento:
        raise HTTPException(status_code=404, detail=f"Documento {id_documento} no encontrado")
    
    match _documento.estado:
        case 1:
            print("Actualizar de borrador a pendiente")
            _documento.estado = 2
        case 2:
            if aprovado is None:
                raise HTTPException(status_code=400, detail="Falta el parámetro 'aprobado' (true|false) para decidir aprobación/rechazo")
            if not isinstance(aprobado, bool):
                raise HTTPException(status_code=400, detail="Parámetro 'aprobado' inválido; se espera booleano")
            _documento.estado = 3 if aprobado else 4
        case __:
            raise HTTPException(status_code=409, detail=f"Transición inválida: el documento {id_documento} ya está {'aprobado (estado=3)' if _documento.estado == 3 else 'rechazado (estado=4)'}")

    db.commit()
    db.refresh(_documento)

    return _documento

@app.post("/documentos/batch/procesar")
def procesar_batch():
    return {}

@app.get("/jobs/{job_id}")
def job_status():
    return {}

@app.get("/health")
def health():
    return {}
