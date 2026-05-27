from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


client = TestClient(app)


def test_healthcheck_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_use_repo_root_paths() -> None:
    assert settings.upload_dir.endswith("uploads")
    assert ":/" in settings.upload_dir or ":\\" in settings.upload_dir
    assert "sqlite:///" in settings.database_url
    assert "data/app.db" in settings.database_url.replace("\\", "/")
