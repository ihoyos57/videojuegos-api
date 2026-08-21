import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no está configurada")

if not DB_SCHEMA.replace("_", "").isalnum():
    raise ValueError("DB_SCHEMA contiene caracteres no permitidos")

engine = create_engine(
    DATABASE_URL,
    connect_args={"options": f"-csearch_path={DB_SCHEMA}"},
)

with engine.connect() as connection:
    connection.execute(
        text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}")
    )
    connection.commit()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()