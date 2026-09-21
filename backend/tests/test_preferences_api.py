import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_preference(api_client: AsyncClient):
    create_resp = await api_client.post(
        "/api/v1/memory/preferences",
        json={"key": "tool.workspace.move_file.require_approval", "value": True},
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["key"] == "tool.workspace.move_file.require_approval"
    assert body["value"] is True
    assert body["confirmed_by_user"] is True  # explicit human creation via the API

    list_resp = await api_client.get("/api/v1/memory/preferences")
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_create_duplicate_key_returns_409(api_client: AsyncClient):
    body = {"key": "dup.key", "value": 1}
    first = await api_client.post("/api/v1/memory/preferences", json=body)
    assert first.status_code == 201

    second = await api_client.post("/api/v1/memory/preferences", json=body)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_create_can_propose_unconfirmed_preference(api_client: AsyncClient):
    resp = await api_client.post(
        "/api/v1/memory/preferences",
        json={"key": "proposed.key", "value": "x", "confirmed_by_user": False},
    )
    assert resp.status_code == 201
    assert resp.json()["confirmed_by_user"] is False


@pytest.mark.asyncio
async def test_update_preference(api_client: AsyncClient):
    create_resp = await api_client.post(
        "/api/v1/memory/preferences", json={"key": "k", "value": "old", "confirmed_by_user": False}
    )
    preference_id = create_resp.json()["id"]

    update_resp = await api_client.patch(
        f"/api/v1/memory/preferences/{preference_id}",
        json={"value": "new", "confirmed_by_user": True},
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["value"] == "new"
    assert body["confirmed_by_user"] is True
    # updated_at is server-computed (onupdate) -- this response must not 500 trying to
    # read it outside an awaited context (regression test for that exact bug).
    assert body["updated_at"] is not None


@pytest.mark.asyncio
async def test_update_404(api_client: AsyncClient):
    resp = await api_client.patch(
        "/api/v1/memory/preferences/missing", json={"value": "x"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_preference(api_client: AsyncClient):
    create_resp = await api_client.post(
        "/api/v1/memory/preferences", json={"key": "k", "value": "v"}
    )
    preference_id = create_resp.json()["id"]

    delete_resp = await api_client.delete(f"/api/v1/memory/preferences/{preference_id}")
    assert delete_resp.status_code == 204

    list_resp = await api_client.get("/api/v1/memory/preferences")
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_404(api_client: AsyncClient):
    resp = await api_client.delete("/api/v1/memory/preferences/missing")
    assert resp.status_code == 404
