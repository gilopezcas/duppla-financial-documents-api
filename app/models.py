from uuid   import uuid4

from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey
from database   import Base

class TiposDocumentos(Base):
    __tablename__ = "tipos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)

class EstadosDocumentos(Base):
    __tablename__ = "estados"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)

class Batch(Base):
    __tablename__ = "batch"

    id_job = Column(String, primary_key=True, index=True, default=str(uuid4()))
    jobs = Column(JSON)

class Documentos(Base):
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(Integer, ForeignKey("tipos.id"))
    monto = Column(Float)
    estado = Column(Integer, ForeignKey("estados.id"))
    fecha_creacion = Column(String)
    _metadata = Column(JSON)