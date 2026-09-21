# Security model

TaskPilot has real access to your local files, can execute arbitrary Python, and can
drive a real browser. This document states the actual boundaries enforced, how they're
enforced, and — just as importantly — where those boundaries are honestly incomplete,
rather than claiming a perfect sandbox that doesn't exist.

## The core principle: the LLM never decides permission

The planner emits a `tool_name` and a JSON `tool_args` object. That's the entire
surface it controls. Every tool call then passes through
`Tool.evaluate_permission()` (`backend/app/agent/tools/base.py`) — pure, deterministic
Python, run by the backend, with no model involved:

```python
def evaluate_permission(self, args: dict, preferences: dict) -> PermissionDecision:
    if self.default_permission == PermissionLevel.REQUIRES_APPROVAL:
        return PermissionDecision(requires_approval=True)          # floor, not negotiable
    key = f"tool.{self.name}.require_approval"
    if preferences.get(key) is True:
        return PermissionDecision(requires_approval=True)          # a preference can RAISE...
    return PermissionDecision(requires_approval=False)              # ...never lower
```

A confirmed user preference (see below) can *raise* an `AUTO` tool to require
approval; there is no mechanism — none — by which anything, including a preference,
can lower a `REQUIRES_APPROVAL` tool's floor. `python.execute`, `workspace.write_file`,
`workspace.delete_file`, and `browser.click` (the one browser action that actually
submits something) default to `REQUIRES_APPROVAL`; everything else defaults to `AUTO`.
This is tested exhaustively in `backend/tests/agent/test_permission_policy.py`,
including the adversarial cases (wrong-type preference values, missing keys, unrelated
keys) — none of them can lower the floor, because there is no code path that does.

## Approval binding: the exact action, not a category

When a tool requires approval, the backend computes a `payload_hash` — a SHA-256 of
`{tool_name, sorted(tool_args), target, run_id, task_id, workspace_root}` in canonical
JSON — and creates an `ApprovalRequest` carrying the **unredacted** action payload
(the human approving needs to see the real value, not a masked one; see "Audit-log
redaction" below for where masking *does* apply, and why it's a different case). When
you approve or reject, the backend **recomputes the hash from the live task state and
compares it** before resuming the graph — a stale or tampered approval can't be
replayed against a task whose arguments have since changed. `retry_count` is part of
the hash specifically so an automatic retry and a manual retry of the same task can
never collide into approving one when you meant the other (a real deadlock this
project hit and fixed during development — see the retry-recovery tests). Approvals
expire after `TASKPILOT_APPROVAL_TTL_SECONDS` (default 900s); a periodic sweep marks
expired ones so the UI reflects reality even if nobody happens to poll.

Resolving an approval is a single atomic conditional `UPDATE ... WHERE status =
'pending'` (not a read-then-write), specifically because a read-then-write here is a
real, exploitable race: two concurrent approve/reject calls for the same request could
otherwise both pass a Python-side status check before either commits, and both resume
the same graph checkpoint. `backend/tests/test_approval_concurrency.py` forces this
exact race deterministically (not just a flaky timing test) and confirms the fix
closes it.

## Workspace path containment

Every workspace-touching tool routes through one shared resolver,
`resolve_workspace_path()` (`backend/app/agent/policies/workspace_policy.py`): it
rejects absolute-path injection, resolves `..` via a single real `.resolve()` call,
and compares against the resolved root using real path-hierarchy containment (not a
string prefix check, so a sibling directory that merely starts with the same name
isn't confused for being inside it) — and because `.resolve()` follows symlinks fully
before that comparison, a symlink planted inside the workspace pointing outside it is
caught too. The same resolver backs both the agent's tools and the
`GET /workspace/entries` / `GET /workspace/file` API endpoints the frontend's
Workspace explorer uses, so there's exactly one place this logic lives, not two
copies that could drift apart.

## Prompt-injection mitigation (structural, not a guarantee)

Externally-sourced text that could reach an LLM prompt — a summarized web page, prior
task errors/results fed into a replanning prompt — is wrapped with explicit delimiters
and an instruction boundary (`wrap_untrusted_content()`,
`backend/app/agent/llm/prompt_safety.py`) before being included. This is deliberately
framed as defense in depth, not a promise: no delimiter scheme can guarantee a model
is never confused by cleverly crafted injected text. What *is* architecturally
guaranteed is the other half of the risk — permission decisions are made from the
plan's static `tool_args`, authored at planning time and schema-validated, never from
a tool's output data, so even a model that *was* fooled by injected content into
"deciding" to do something can't skip an approval gate that way. The gate is
deterministic backend policy evaluated on the plan, not something the model re-decides
per call.

## Audit-log redaction

`Tool.redact_for_audit()` recursively masks string values under keys that look
secret-like (substring match against `password`, `passwd`, `secret`, `api_key`,
`apikey`, `access_key`, `private_key`, `token`, `credential`, `auth`) before a tool
call's input args or output are written to `ToolExecution`/`AgentTask` rows. No
current tool actually takes a credential as an argument, so this is real defense in
depth for whenever one does, not a response to an active leak. **This is deliberately
not applied to the `ApprovalRequest` payload shown to a human approver** — the
approver is the trust boundary at that point and needs the real value to make an
informed decision; redacting it there would defeat the purpose of asking.

## The Python sandbox — a real, honestly-documented limitation

`python-runner` is a separate service, reachable only from `backend` over an internal
Docker network never exposed to the frontend or the host. It is the *only* component
with access to `/var/run/docker.sock`; the main backend never touches Docker directly.
Each script execution gets its own ephemeral container: `network_mode=none`,
`cap_drop=ALL`, `no-new-privileges`, a real enforced memory limit
(`mem_limit`/`memswap_limit`, no swap beyond the cap), a real CPU limit (`nano_cpus`),
a `pids_limit` of 64 (fork-bomb protection), and a `noexec` tmpfs for `/tmp`. The
script itself is injected via `put_archive` rather than a bind mount, and the
container has **no access to the real workspace filesystem in either direction** — a
script's only output is stdout/stderr/exit code; a workspace file has to come from a
separately-permissioned `workspace.write_file` call. The container is force-removed
after every run regardless of outcome. All of this is genuinely enforced and tested
(`python-runner/tests/test_execute.py` exercises the timeout, the network block, and
the memory limit against real Docker, not mocks).

The limitation, stated plainly: **the supervisor's access to the host's Docker socket
is root-equivalent access to the host.** This is a real, accepted trade-off for a
local, single-user tool — not a claim of a perfect security boundary. A second, known
gap: the container's writable root filesystem has no size cap (Docker's
`storage_opt size=` quota isn't reliably supported on the default overlay2 setup this
project targets — including Docker Desktop on macOS — so it isn't set); a script could
fill disk until `timeout_seconds` cuts it off. Both are documented here rather than
silently accepted.

## Browser automation

Navigation (`browser.navigate`) is `AUTO` — visiting pages isn't itself the
consequential action the approval model targets, and gating every navigation would
make a research agent unusable. `browser.click` — the action that actually submits
something — defaults to `REQUIRES_APPROVAL`. An allowed-domains list
(`TASKPILOT_BROWSER_ALLOWED_DOMAINS_RAW`, comma-separated) is enforced as a hard block
on navigation when configured, not an approval prompt; left empty (the default), any
domain is reachable subject to the per-action approval gate above.

## Network exposure

`backend` and `frontend` bind to `127.0.0.1` only, both in local dev and in the
Compose stack. `python-runner` has no published port and isn't on the same Docker
network as `frontend` at all — only `backend` can reach it. CORS on the backend is
restricted to the local Vite dev server origins.

## What's deliberately out of scope for a local-first personal tool

There is no multi-tenant user model, no auth layer beyond binding to localhost, and no
attempt to defend against a host that's already compromised. This is the right trade-
off for a tool that runs entirely on your own machine with your own data — adding
auth/multi-tenancy would be solving a problem this deployment model doesn't have,
while adding real complexity and its own attack surface.
