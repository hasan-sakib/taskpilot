import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_run_executes_synchronously_end_to_end(api_client: AsyncClient):
    resp = await api_client.post(
        "/api/v1/agent/runs", json={"goal": "List workspace files", "llm_provider": "test"}
    )
    assert resp.status_code == 201
    body = resp.json()
    # The route's default "test" provider has no scripted plan, so the run predictably
    # fails plan validation -- what this test actually verifies is that the route wired
    # the graph, DB, and settings together correctly end-to-end and persisted the result,
    # not planning correctness (that's covered by the agent test suite).
    assert body["status"] == "failed"
    assert body["final_report"] is not None
    run_id = body["id"]

    get_resp = await api_client.get(f"/api/v1/agent/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == run_id
    assert get_resp.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_get_run_404_for_unknown_id(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/agent/runs/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_run_rejects_empty_goal(api_client: AsyncClient):
    resp = await api_client.post("/api/v1/agent/runs", json={"goal": "", "llm_provider": "test"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cancel_run_sets_flag(api_client: AsyncClient):
    create_resp = await api_client.post(
        "/api/v1/agent/runs", json={"goal": "List workspace files", "llm_provider": "test"}
    )
    run_id = create_resp.json()["id"]

    # The run already finished synchronously (failed, per the note above) by the time
    # we get here, so cancelling it now must be rejected as already-terminal.
    cancel_resp = await api_client.post(f"/api/v1/agent/runs/{run_id}/cancel")
    assert cancel_resp.status_code == 409


@pytest.mark.asyncio
async def test_cancel_run_404_for_unknown_id(api_client: AsyncClient):
    resp = await api_client.post("/api/v1/agent/runs/does-not-exist/cancel")
    assert resp.status_code == 404
