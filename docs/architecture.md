# Architecture

TaskPilot is a local-first personal work agent: a FastAPI backend runs a LangGraph
execution graph that plans and executes multi-step work using a fixed set of tools,
pausing for human approval before anything consequential. A React frontend gives a
human visibility into and control over that execution. A separate, minimal service
owns the one piece of infrastructure (the Docker socket) that needs isolating from the
rest of the system.

## Components

```
┌─────────────┐      HTTP       ┌──────────────┐     HTTP (internal only)   ┌───────────────┐
│  frontend    │ ─────────────▶ │   backend    │ ─────────────────────────▶ │ python-runner  │
│ React/Vite   │ ◀───────────── │  FastAPI +   │ ◀───────────────────────── │  FastAPI +     │
│              │                │  LangGraph   │                            │  docker socket │
└─────────────┘                 └──────┬───────┘                            └───────┬────────┘
                                        │                                            │
                                        ▼                                            ▼
                                 SQLite (app DB +                           ephemeral, network-
                                 LangGraph checkpoints)                     isolated containers
                                        │                                   (one per script run)
                                        ▼
                                 Ollama (host, local model)
```

- **backend** (`backend/`) — FastAPI app, SQLAlchemy 2.x models, Alembic migrations, the
  LangGraph agent execution graph, the tool implementations, and the REST API the
  frontend consumes. Binds to `127.0.0.1` only.
- **frontend** (`frontend/`) — React 19 + TypeScript + Vite + Tailwind v4 + shadcn-style
  components + TanStack Query. Eight screens, all backed by real API calls — no
  hardcoded or fake data anywhere.
- **python-runner** (`python-runner/`) — a small, separate FastAPI service that is the
  *only* component with access to the host's Docker socket. It spawns one ephemeral,
  network-isolated container per Python script the agent wants to run, and is
  reachable only from `backend` over an internal Docker network — never from the
  frontend or the host. See [security.md](security.md) for why this boundary exists
  and its honestly-documented limits.
- **Ollama** — runs on the host (not in Compose), reached via
  `host.docker.internal`. No paid LLM API is used anywhere.

## Data model

Two separate SQLite databases, both under `data/` (a single Docker volume in Compose):

- **`taskpilot.db`** — the application database, managed by Alembic. Nine tables:
  `AgentRun`, `AgentTask`, `TaskDependency`, `ToolExecution`, `ApprovalRequest`,
  `UserPreference`, `BrowserSession`, `WorkspaceArtifact`, `AgentEvent`. This is what
  the REST API and the frontend query — it's the source of truth for "what happened
  and what state is everything in," across every run, past and present.
- **`checkpoints.db`** — owned entirely by LangGraph's `AsyncSqliteSaver`. This is the
  source of truth for a run's exact resumable execution position: which node it's
  paused at, and the full in-flight graph state. It's opaque outside LangGraph and
  deliberately kept in its own file so Alembic's autogenerate never has to reason
  about LangGraph-owned tables.

These two stores can't drift out of sync by construction: every node writes its DB
projection (state update + row writes + an `AgentEvent`) as the *last* thing it does
before returning, via a shared `NodeContext` helper
(`backend/app/agent/nodes/_context.py`). API routes never write `AgentTask`/`AgentRun`
status directly — the only way state moves is through the graph itself (including
resolving an approval, which resumes the graph rather than patching a row).

`TaskStatus` transitions the graph itself ever performs: `PENDING → IN_PROGRESS`
(`tool_execution`), `→ BLOCKED_ON_APPROVAL` (`permission_evaluation`, reversible back to
`IN_PROGRESS` on resume), `→ COMPLETED` (`result_verification`), `→ FAILED`
(`retry_recovery`, after retries are exhausted). `SKIPPED` and `CANCELLED` are the two
transitions a task can only reach through an explicit agent-invoked
`task.update_status`/`task.cancel` call, never automatically.

## The agent execution graph

Twelve LangGraph nodes (`backend/app/agent/nodes/`), wired in `graph/builder.py`, with
all conditional routing logic kept in pure, independently unit-tested functions
(`graph/routers.py`) separate from the node bodies themselves:

```
START ──▶ goal_validation ──valid──▶ planning ──▶ plan_validation
              │invalid                                  │
              ▼                              valid ◀────┴────▶ invalid, attempts left
      final_report_generation                  │                      │
              │                                 ▼                      ▼
              ▼                          task_selection            planning (retry)
             END                         │    │    │
                    ┌────runnable────────┘    │    └──all done──▶ completion_evaluation
                    ▼                         │                          │
          permission_evaluation          blocked                   more work? ──yes──▶ replanning
              │           │                   │                          │no
        auto-approved  needs approval         ▼                          ▼
              │        (interrupt, pause) replanning ◀───────── final_report_generation
              ▼              │                                          │
        tool_execution   rejected                                       ▼
              │              │                                         END
              ▼              ▼
      result_observation  retry_recovery
              │
              ▼
      result_verification ──success──▶ task_selection
              │
           failure
              ▼
        retry_recovery ──retries left──▶ tool_execution
              │
        exhausted
              ▼
          replanning ──▶ plan_validation
```

Two edges are left out of the diagram above to keep it readable, but are just as real:
`plan_validation` doesn't only loop back to `planning` on an invalid plan — once
`max_plan_validation_attempts` is exhausted, it routes straight to
`final_report_generation` instead (run `FAILED`), same as the replanning-exhausted
path already shown. And `task_selection` can end the run directly, bypassing
everything else, straight to `final_report_generation` — if
`max_run_duration_seconds`/`max_tasks_per_run`/`max_tool_calls_per_run` is hit, or a
cooperative cancellation (`AgentRun.cancel_requested`) was requested. Both are checked
in `route_plan_validation`/`route_task_selection` (`backend/app/agent/graph/routers.py`)
alongside the paths drawn above.

Two things worth calling out explicitly:

- **The interrupt boundary sits strictly between "decide" and "execute."**
  `permission_evaluation` computes a deterministic `payload_hash` (see
  [security.md](security.md)), does an idempotent upsert of an `ApprovalRequest`, then
  calls LangGraph's `interrupt()` — `tool_execution` has not run yet at this point.
  Resolving the approval resumes the *same* checkpointed graph via
  `Command(resume=...)`, so it advances to `tool_execution` exactly once, not as a new
  run. A second, independent idempotency layer guards against the crash-mid-execution
  case: `tool_execution` writes a `ToolExecution` row keyed by unique
  `(task_id, attempt_number)` *before* invoking the tool, and checks for an existing
  completed/failed row for that key on replay before ever calling the tool again.
- **Deterministic test mode.** An `LLMProvider` is an interface
  (`backend/app/agent/llm/base.py`) with two implementations: `OllamaProvider` (real
  local inference) and `ScriptedTestProvider` (a fixed, pre-scripted sequence of plan
  responses — no network, no model, fully deterministic). Almost the entire backend
  test suite drives the real graph through `ScriptedTestProvider`, which is what makes
  it possible to test retries, replanning, interrupt/resume, and duplicate-execution
  prevention deterministically and fast, without needing Ollama installed at all.

See [agent-workflow.md](agent-workflow.md) for a walk-through of what actually happens,
end to end, when a goal is submitted.

## Tool interface

A single abstract `Tool` base class (`backend/app/agent/tools/base.py`) that every one
of the 30 tools (across five categories — web research, workspace, task management,
Python execution, browser automation; see
[tool-development.md](tool-development.md)) implements: Pydantic `input_schema`/
`output_schema`, a `default_permission` (`AUTO` or `REQUIRES_APPROVAL`), a
deterministic `evaluate_permission()`, and `redact_for_audit()` for audit-log secret
masking. The planner LLM only ever emits a `tool_name` and a JSON `tool_args` object —
permission is never decided by the model; see [security.md](security.md) for exactly
how and why.

## Frontend

Eight screens (Overview, Agent, Tasks, Approvals, Browser, Workspace, Memory,
Settings), each backed by a `features/<name>/` module (`api.ts` for the typed
axios calls, `use-*.ts` for the TanStack Query hooks). Because
`POST /agent/runs` and `POST /approvals/{id}/approve|reject` are synchronous, blocking
calls on the backend (they run the graph in-process until the next pause or terminal
state), the frontend derives its client-side timeout for those specific calls from the
backend's own real `max_run_duration_seconds` setting (fetched once from
`GET /settings` and cached) rather than guessing at a fixed value — a real integration
bug this session hit and fixed (see [agent-workflow.md](agent-workflow.md)'s notes on
real-model latency).

"Live" progress on the Agent page works via polling, not a websocket: because a node
commits its DB projection as its last step before returning, a concurrent
`GET /agent/runs/{id}/events` poll genuinely observes partial progress while the
triggering `POST` is still in flight server-side.
