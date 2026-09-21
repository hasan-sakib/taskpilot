import hashlib
import json


def compute_payload_hash(
    *,
    tool_name: str,
    args: dict,
    target: str | None,
    run_id: str,
    task_id: str,
    workspace_root: str,
) -> str:
    """Bind an approval to the exact action + arguments + execution context.

    Deliberately excludes timestamps/nonces so an identical retry reuses the same
    hash (idempotent upsert on resume); includes run_id/task_id so identical args
    in a different run or task never collide.
    """
    canonical = {
        "tool_name": tool_name,
        "args": args,
        "target": target,
        "run_id": run_id,
        "task_id": task_id,
        "workspace_root": workspace_root,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
