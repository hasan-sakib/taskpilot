import mimetypes
from datetime import UTC, datetime
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.agent.policies.workspace_policy import WorkspacePathError, resolve_workspace_path
from app.core.config import Settings, get_settings
from app.schemas.workspace import WorkspaceEntry, WorkspaceListing

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _relative_path(workspace_root, target) -> str:
    relative = target.relative_to(workspace_root)
    return "." if str(relative) == "." else relative.as_posix()


@router.get("/entries", response_model=WorkspaceListing)
async def list_entries(
    path: str = "", settings: Settings = Depends(get_settings)
) -> WorkspaceListing:
    workspace_root = settings.resolved_workspace_root()
    try:
        target = resolve_workspace_path(workspace_root, path)
    except WorkspacePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"No such path in workspace: {path}")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {path}")

    entries = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        stat = child.stat()
        entries.append(
            WorkspaceEntry(
                name=child.name,
                path=_relative_path(workspace_root, child),
                is_dir=child.is_dir(),
                size_bytes=0 if child.is_dir() else stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC).replace(tzinfo=None),
            )
        )

    relative = _relative_path(workspace_root, target)
    parent_path = None if relative == "." else str(PurePosixPath(relative).parent)
    if parent_path == ".":
        parent_path = ""

    return WorkspaceListing(path=relative, parent_path=parent_path, entries=entries)


@router.get("/file")
async def get_file(path: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    workspace_root = settings.resolved_workspace_root()
    try:
        target = resolve_workspace_path(workspace_root, path)
    except WorkspacePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"No such file in workspace: {path}")

    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type, filename=target.name)
