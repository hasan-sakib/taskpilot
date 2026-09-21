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
    retry_count: int = 0,
) -> str:
    """Bind an approval to the exact action + arguments + execution context.

    Deliberately excludes timestamps/nonces so a replay of the SAME permission_evaluation
    node call (e.g. after an interrupt/resume) reuses the same hash -- that's what makes
    the idempotent upsert on resume safe. `retry_count` is included specifically so it
    is NOT constant across separate attempt sequences at the same task: without it, a
    task manually reset to PENDING via task.retry (same tool_name/args/task_id/run_id)
    would collide with its own already-resolved ApprovalRequest row -- permission_evaluation
    would find that row via the unique (run_id, task_id, payload_hash) constraint and
    pause again, but resolve_approval refuses to re-resolve a non-pending request,
    deadlocking the run. AgentTask.retry_count is bumped by retry_task specifically to
    force a fresh hash (and thus a fresh, resolvable ApprovalRequest) for each attempt
    sequence, while staying constant within one sequence's own retry_recovery loop
    (which never re-invokes permission_evaluation) and across a single interrupt/resume
    replay (same call, same retry_count either side of the pause).
    """
    canonical = {
        "tool_name": tool_name,
        "args": args,
        "target": target,
        "run_id": run_id,
        "task_id": task_id,
        "workspace_root": workspace_root,
        "retry_count": retry_count,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
