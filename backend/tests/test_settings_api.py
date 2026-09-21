import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_settings_returns_current_config(api_client: AsyncClient, api_settings):
    resp = await api_client.get("/api/v1/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ollama_model"] == api_settings.ollama_model
    assert body["workspace_root"] == str(api_settings.resolved_workspace_root())
    assert body["max_retries_per_task"] == api_settings.max_retries_per_task
    assert body["browser_allowed_domains"] == []
    assert "python_runner_timeout_seconds" in body
