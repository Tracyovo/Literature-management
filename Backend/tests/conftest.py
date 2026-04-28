import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    os.environ["DB_PATH"] = str(db_path)
    os.environ["STORAGE_ROOT"] = str(upload_dir)
    os.environ["AUTH_ENABLED"] = "false"
    os.environ["ALLOWED_EXTENSIONS"] = "txt"
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
