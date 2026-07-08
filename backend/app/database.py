from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

SQL_DATABASE_URL=f"postgresql://{settings.database_role}:{settings.database_password}@{settings.database_hostname}-pooler.{settings.database_region}.aws.neon.tech/{settings.database_name}?sslmode=require&channel_binding=require"

engine = create_engine(
    SQL_DATABASE_URL,
    pool_size=10,       
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800, 
    pool_pre_ping=True   
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base=declarative_base()

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()
