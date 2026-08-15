from datetime import datetime
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db


def simular_refresh(obj):
    if getattr(obj, "id", None) is None:
        obj.id = 1
    if hasattr(obj, "fecha_registro") and obj.fecha_registro is None:
        obj.fecha_registro = datetime.utcnow()
    if hasattr(obj, "fecha") and obj.fecha is None:
        obj.fecha = datetime.utcnow()


@pytest.fixture
def db_mock():
    mock = MagicMock()
    mock.refresh.side_effect = simular_refresh
    return mock


@pytest.fixture
def client(db_mock):
    app.dependency_overrides[get_db] = lambda: db_mock
    yield TestClient(app)
    app.dependency_overrides.clear()