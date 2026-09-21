from datetime import datetime

from pydantic import BaseModel


class WorkspaceEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    size_bytes: int
    modified_at: datetime


class WorkspaceListing(BaseModel):
    path: str
    parent_path: str | None
    entries: list[WorkspaceEntry]
