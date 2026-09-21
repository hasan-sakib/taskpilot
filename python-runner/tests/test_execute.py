import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_execute_captures_stdout_and_exit_code(client: AsyncClient) -> None:
    resp = await client.post(
        "/execute",
        json={"execution_id": "e1", "script": "print('hi')"},
        timeout=30,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stdout"] == "hi\n"
    assert body["exit_code"] == 0
    assert body["timed_out"] is False


@pytest.mark.asyncio
async def test_execute_captures_nonzero_exit_code(client: AsyncClient) -> None:
    resp = await client.post(
        "/execute",
        json={"execution_id": "e2", "script": "import sys; sys.exit(7)"},
        timeout=30,
    )
    assert resp.status_code == 200
    assert resp.json()["exit_code"] == 7


@pytest.mark.asyncio
async def test_execute_enforces_timeout(client: AsyncClient) -> None:
    resp = await client.post(
        "/execute",
        json={
            "execution_id": "e3",
            "script": "import time; time.sleep(30)",
            "timeout_seconds": 2,
        },
        timeout=30,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["timed_out"] is True
    assert body["exit_code"] is None


@pytest.mark.asyncio
async def test_execute_blocks_network_access(client: AsyncClient) -> None:
    script = (
        "import urllib.request\n"
        "try:\n"
        "    urllib.request.urlopen('http://example.com', timeout=3)\n"
        "    print('REACHED_NETWORK')\n"
        "except Exception:\n"
        "    print('BLOCKED')\n"
    )
    resp = await client.post(
        "/execute", json={"execution_id": "e4", "script": script}, timeout=30
    )
    assert resp.status_code == 200
    assert resp.json()["stdout"].strip() == "BLOCKED"


@pytest.mark.asyncio
async def test_execute_enforces_memory_limit(client: AsyncClient) -> None:
    # Allocates well beyond the requested cgroup memory limit -- the container's OOM
    # killer should terminate the process (SIGKILL, exit code 137), not silently let
    # it succeed. Confirms mem_limit/memswap_limit in sandbox.py are real, enforced
    # Docker constraints, not just parameters that get threaded through and ignored.
    script = (
        "data = bytearray(200 * 1024 * 1024)\n"
        "for i in range(0, len(data), 4096):\n"
        "    data[i] = 1\n"
        "print('SHOULD_NOT_REACH_HERE')\n"
    )
    resp = await client.post(
        "/execute",
        json={"execution_id": "e6", "script": script, "memory_limit_mb": 32},
        timeout=30,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["timed_out"] is False
    assert body["exit_code"] not in (0, None)
    assert "SHOULD_NOT_REACH_HERE" not in body["stdout"]


@pytest.mark.asyncio
async def test_execute_rejects_invalid_request(client: AsyncClient) -> None:
    resp = await client.post(
        "/execute",
        json={"execution_id": "e5", "script": "print(1)", "timeout_seconds": 99999},
        timeout=30,
    )
    assert resp.status_code == 422
