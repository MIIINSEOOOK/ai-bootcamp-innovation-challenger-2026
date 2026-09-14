from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import PROJECT_ROOT, create_app


@pytest.fixture()
def data_path(tmp_path: Path) -> Path:
    return tmp_path / "app_data.json"


@pytest.fixture()
def app(data_path: Path):
    return create_app(data_path=data_path, personas_path=PROJECT_ROOT / "data" / "personas" / "personas.json")


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client

