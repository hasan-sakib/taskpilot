from pathlib import Path


class WorkspacePathError(ValueError):
    """Raised when a path would resolve outside the configured workspace root."""


def resolve_workspace_path(workspace_root: Path, relative_path: str | None) -> Path:
    """Resolve `relative_path` against `workspace_root`, rejecting any escape.

    Rejects absolute-path injection (`Path(root) / "/etc/passwd"` would otherwise
    silently discard `root`), `..` traversal, and symlinks that resolve outside the
    root -- all via a single real `.resolve()` call compared against the resolved root.
    """
    if not relative_path:
        relative_path = "."

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise WorkspacePathError(f"Path must be relative to the workspace: {relative_path}")

    resolved_root = workspace_root.resolve()
    resolved = (resolved_root / candidate).resolve()

    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise WorkspacePathError(f"Path escapes workspace root: {relative_path}")

    return resolved
