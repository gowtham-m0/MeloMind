"""Tests for GET /api/v1/health."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.settings import Settings, get_settings
from app.main import create_app


@pytest.mark.parametrize(
    ("qloo_api_key", "expected_mode"),
    [("", "demo_fixtures"), ("test-key", "live")],
)
def test_health_reports_status_and_qloo_mode(qloo_api_key: str, expected_mode: str) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, app_env="test", qloo_api_key=SecretStr(qloo_api_key)
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": "MeloMind",
        "env": "test",
        "qloo_mode": expected_mode,
    }
