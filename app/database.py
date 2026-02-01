from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATEBASE_URL = "postgresql://postgres:vSeJugvcj2@localhost:5432/dupla_db"

engine = create_engine(DATEBASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Inicialización y seed de datos por defecto
def init_db():
    """Crea las tablas y agrega datos por defecto si no existen."""
    # importar modelos aquí para evitar problemas de importación circular al cargar módulos
    from models import TiposDocumentos, EstadosDocumentos

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Insertar tipos por defecto si la tabla está vacía
        if not db.query(TiposDocumentos).first():
            tipos = [
                TiposDocumentos(nombre="facturas"),
                TiposDocumentos(nombre="recibos"),
                TiposDocumentos(nombre="comprobantes"),
            ]
            db.add_all(tipos)

        # Insertar estados por defecto si la tabla está vacía
        if not db.query(EstadosDocumentos).first():
            estados = [
                EstadosDocumentos(nombre="borrador"),
                EstadosDocumentos(nombre="pendiente"),
                EstadosDocumentos(nombre="aprobado"),
                EstadosDocumentos(nombre="rechazado"),
            ]
            db.add_all(estados)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
