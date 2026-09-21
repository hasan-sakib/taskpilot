import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_runs_empty(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/agent/runs")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_runs_returns_created_runs_newest_first(api_client: AsyncClient):
    first = await api_client.post(
        "/api/v1/agent/runs", json={"goal": "first goal", "llm_provider": "test"}
    )
    second = await api_client.post(
        "/api/v1/agent/runs", json={"goal": "second goal", "llm_provider": "test"}
    )
    assert first.status_code == 201
    assert second.status_code == 201

    resp = await api_client.get("/api/v1/agent/runs")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["id"] == second.json()["id"]
    assert body[1]["id"] == first.json()["id"]


@pytest.mark.asyncio
async def test_list_run_events_404_for_unknown_run(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/agent/runs/missing/events")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_run_events_returns_events_in_order(api_client: AsyncClient):
    create_resp = await api_client.post(
        "/api/v1/agent/runs", json={"goal": "do something", "llm_provider": "test"}
    )
    run_id = create_resp.json()["id"]

    resp = await api_client.get(f"/api/v1/agent/runs/{run_id}/events")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) > 0
    assert all(event["run_id"] == run_id for event in body)
    timestamps = [event["created_at"] for event in body]
    assert timestamps == sorted(timestamps)
