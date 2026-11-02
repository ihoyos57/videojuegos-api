
import os
from dotenv import load_dotenv

load_dotenv()

# Las pruebas solo pueden ejecutarse en el esquema de testing.
os.environ["DB_SCHEMA"] = "schema_testing"

if not os.getenv("DATABASE_URL", "").startswith(
    ("postgresql://", "postgresql+psycopg2://", "postgresql+psycopg://")
):
    raise RuntimeError(
        "Configura DATABASE_URL con una conexión real a PostgreSQL "
        "antes de ejecutar las pruebas."
    )

from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

import pytest

from app.database import Base, engine
from app import models


@pytest.fixture
def db():
    if os.getenv("DB_SCHEMA") != "schema_testing":
        pytest.fail("Las pruebas solo pueden usar schema_testing.")

    # Crea las tablas faltantes exclusivamente en schema_testing.
    Base.metadata.create_all(bind=engine)

    connection = engine.connect()
    transaction = connection.begin()

    TestingSession = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        join_transaction_mode="create_savepoint",
    )
    session = TestingSession()

    try:
        yield session
    finally:
        session.close()

        # Revierte las inserciones, actualizaciones y eliminaciones
        # realizadas durante la prueba, incluso si el CRUD hizo commit.
        if transaction.is_active:
            transaction.rollback()

        connection.close()