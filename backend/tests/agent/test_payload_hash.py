from app.agent.policies.approval_policy import compute_payload_hash


def _hash(**overrides) -> str:
    base = {
        "tool_name": "workspace.write_file",
        "args": {"path": "a.txt", "content": "hi"},
        "target": None,
        "run_id": "run-1",
        "task_id": "task-1",
        "workspace_root": "/workspace",
    }
    base.update(overrides)
    return compute_payload_hash(**base)


def test_identical_inputs_produce_identical_hash():
    assert _hash() == _hash()


def test_hash_is_independent_of_dict_key_order():
    h1 = compute_payload_hash(
        tool_name="t",
        args={"a": 1, "b": 2},
        target=None,
        run_id="r",
        task_id="k",
        workspace_root="/w",
    )
    h2 = compute_payload_hash(
        tool_name="t",
        args={"b": 2, "a": 1},
        target=None,
        run_id="r",
        task_id="k",
        workspace_root="/w",
    )
    assert h1 == h2


def test_hash_changes_with_args():
    assert _hash() != _hash(args={"path": "a.txt", "content": "different"})


def test_hash_changes_with_tool_name():
    assert _hash() != _hash(tool_name="workspace.delete_file")


def test_hash_changes_with_target():
    assert _hash() != _hash(target="https://example.com")


def test_hash_changes_with_run_id():
    # No cross-run collisions even with otherwise-identical args.
    assert _hash() != _hash(run_id="run-2")


def test_hash_changes_with_task_id():
    # No cross-task collisions within the same run.
    assert _hash() != _hash(task_id="task-2")


def test_hash_changes_with_workspace_root():
    assert _hash() != _hash(workspace_root="/other-workspace")


def test_hash_changes_with_retry_count():
    # Load-bearing for task.retry: without this, retrying a task whose tool requires
    # approval would recompute the exact same hash as its first (already-resolved)
    # attempt, collide with the ApprovalRequest unique (run_id, task_id, payload_hash)
    # constraint, and deadlock the run waiting on an approval nothing can resolve again.
    assert _hash(retry_count=0) != _hash(retry_count=1)


def test_hash_defaults_retry_count_to_zero():
    assert _hash() == _hash(retry_count=0)


def test_hash_is_a_deterministic_sha256_hex_digest():
    h = _hash()
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
