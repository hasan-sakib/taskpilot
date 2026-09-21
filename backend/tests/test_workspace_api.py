import pytest
from httpx import AsyncClient

from app.core.config import Settings


@pytest.mark.asyncio
async def test_list_entries_at_root(api_client: AsyncClient, api_settings: Settings):
    (api_settings.resolved_workspace_root() / "notes.txt").write_text("hello")
    (api_settings.resolved_workspace_root() / "reports").mkdir()

    resp = await api_client.get("/api/v1/workspace/entries")
    assert resp.status_code == 200
    body = resp.json()
    assert body["path"] == "."
    assert body["parent_path"] is None
    names = {e["name"]: e for e in body["entries"]}
    assert names["notes.txt"]["is_dir"] is False
    assert names["notes.txt"]["size_bytes"] == 5
    assert names["reports"]["is_dir"] is True


@pytest.mark.asyncio
async def test_list_entries_directories_sort_before_files(
    api_client: AsyncClient, api_settings: Settings
):
    root = api_settings.resolved_workspace_root()
    (root / "z_file.txt").write_text("x")
    (root / "a_dir").mkdir()

    resp = await api_client.get("/api/v1/workspace/entries")
    entries = resp.json()["entries"]
    assert entries[0]["name"] == "a_dir"
    assert entries[0]["is_dir"] is True


@pytest.mark.asyncio
async def test_list_entries_rejects_path_traversal(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/workspace/entries", params={"path": "../../etc"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_entries_404_for_missing_path(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/workspace/entries", params={"path": "does-not-exist"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_entries_400_when_path_is_a_file(
    api_client: AsyncClient, api_settings: Settings
):
    (api_settings.resolved_workspace_root() / "a.txt").write_text("x")
    resp = await api_client.get("/api/v1/workspace/entries", params={"path": "a.txt"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_file_returns_content(api_client: AsyncClient, api_settings: Settings):
    (api_settings.resolved_workspace_root() / "note.txt").write_text("hello world")

    resp = await api_client.get("/api/v1/workspace/file", params={"path": "note.txt"})
    assert resp.status_code == 200
    assert resp.text == "hello world"
    assert resp.headers["content-type"].startswith("text/plain")


@pytest.mark.asyncio
async def test_get_file_404_for_missing_file(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/workspace/file", params={"path": "missing.txt"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_file_rejects_path_traversal(api_client: AsyncClient):
    resp = await api_client.get(
        "/api/v1/workspace/file", params={"path": "../../etc/passwd"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_file_404_when_path_is_a_directory(
    api_client: AsyncClient, api_settings: Settings
):
    (api_settings.resolved_workspace_root() / "a_dir").mkdir()
    resp = await api_client.get("/api/v1/workspace/file", params={"path": "a_dir"})
    assert resp.status_code == 404
