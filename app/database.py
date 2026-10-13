import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

if not DB_SCHEMA.replace("_", "").isalnum():
    raise ValueError("DB_SCHEMA contiene caracteres no permitidos")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_USER = os.getenv("DB_USER")
    DB_NAME = os.getenv("DB_NAME")
    INSTANCE_CONNECTION_NAME = os.getenv(
        "INSTANCE_CONNECTION_NAME"
    )

    if not all(
        [
            DB_PASSWORD,
            DB_USER,
            DB_NAME,
            INSTANCE_CONNECTION_NAME,
        ]
    ):
        raise ValueError(
            "Configura DATABASE_URL o las variables "
            "DB_PASSWORD, DB_USER, DB_NAME e "
            "INSTANCE_CONNECTION_NAME"
        )

    DATABASE_URL = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        query={
            "host": f"/cloudsql/{INSTANCE_CONNECTION_NAME}"
        },
    )

if isinstance(DATABASE_URL, str) and DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"options": f"-csearch_path={DB_SCHEMA}"},
        pool_size=3,
        max_overflow=2,
    )

    with engine.connect() as connection:
        connection.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}")
        )
        connection.commit()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
