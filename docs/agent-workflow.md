# Agent workflow

This walks through what actually happens, node by node, when you submit a goal —
and what to realistically expect from the local model.

## 1. Submitting a goal

`POST /api/v1/agent/runs` with a goal creates an `AgentRun` row (`status: pending`)
and then calls `run_graph()` **synchronously, in the same request** — the call blocks
until the graph reaches its first pause (needs your approval) or a terminal state
(completed / failed / cancelled). This is a deliberate simplicity trade-off for a
local-first, single-user tool: no job queue, no websocket, no polling infrastructure
to keep in sync — the HTTP response *is* the next meaningful state. The frontend
derives its client timeout for this call from the backend's own
`max_run_duration_seconds` setting (default 1800s / 30 minutes) rather than a fixed
guess, specifically because this call can legitimately take a long time with a real
local model.

## 2. Goal validation → planning → plan validation

`goal_validation` checks the goal is non-empty and within length limits; a genuinely
invalid goal short-circuits straight to a final report explaining why, without ever
calling the model.

`planning` sends the goal, the full list of available tools (name, description, JSON
schema), and any confirmed user preferences to the LLM provider, asking for a JSON plan:
a list of tasks, each with a `tool_name`, `tool_args`, and `depends_on` (indices into
the same plan, for tasks that must run first).

**Every value in `tool_args` must be something the model can specify right now** — a
real URL, a real path, real text. There is no mechanism for one task's arguments to
reference another task's *future* result; tools don't understand placeholders like
`"result_from_task0"`, and a plan that tries this will simply fail at execution time.
If part of a goal genuinely depends on information only an earlier task's result will
reveal, the model is expected to plan only what it can specify now — a task that
subsequently *fails* (not one that silently under-delivers) is what triggers the
replanning loop below with the real error fed back. The planning system prompt
(`backend/app/agent/llm/ollama_provider.py`) says this explicitly, including a
concrete example: `web_research.search` already returns titles, URLs, *and snippets*
for every result, which is usually enough to write a useful summary directly, without
ever needing to open one specific result's URL.

`plan_validation` (`backend/app/agent/nodes/plan_validation.py`) is pure, deterministic
Python — not another LLM call — checking: at least one task, every `tool_name` is a
real registered tool, every `tool_args` actually validates against that tool's Pydantic
input schema, every `depends_on` index is in range, and the dependency graph has no
cycles. A rejected plan loops back to `planning`, and — unlike a naive retry — the
*specific* validation errors from the previous attempt are fed back into the next
prompt, so the model has a real chance to correct a schema mistake rather than
regenerating the identical invalid plan (the planner runs at `temperature=0`, so
without that feedback it very likely would). This repeats up to
`max_plan_validation_attempts` (default 3) before giving up and going straight to a
final report.

## 3. Task selection, permission, execution

`task_selection` picks the next runnable task (`PENDING`, all dependencies
`COMPLETED`), respecting `max_tasks_per_run`, `max_tool_calls_per_run`, and
`max_run_duration_seconds` — any of these being exceeded fails the run outright rather
than looping forever. A cooperative-cancellation flag is also checked here (see
"Cancelling a run" below).

`permission_evaluation` is where the deterministic, backend-only permission gate lives
— see [security.md](security.md) for the full model. If the tool's evaluated
permission is `AUTO`, straight to `tool_execution`. If `REQUIRES_APPROVAL`, the graph
creates an `ApprovalRequest` (with the exact, **unredacted** action payload — the human
approving needs to see the real value) and calls LangGraph's `interrupt()`. The HTTP
call that triggered all this now returns, with the run at `paused_for_approval`.

`tool_execution` validates the args against the tool's schema (again — never trust
that a previously-validated plan's args are still exactly right by the time they're
about to run), calls the tool, and records a `ToolExecution` row. `result_observation`
and `result_verification` translate the tool's outcome into `task.status` (`COMPLETED`
or, on failure, into the retry path) and log an `AgentEvent`.

## 4. Approving or rejecting

`POST /approvals/{id}/approve` (or `/reject`) re-validates the approval's status and
expiry server-side, **recomputes the payload hash and compares it** against what was
requested (protecting against a stale or tampered client), then resumes the *same*
checkpointed graph via `Command(resume=...)` — this is also a blocking call, for the
same reason as run creation. Approve proceeds to `tool_execution`; reject routes
straight to `retry_recovery` without ever running the tool.

## 5. Failure recovery and replanning

A failed tool call goes to `retry_recovery`: if `retry_count < max_retries_per_task`
(default 3), it retries the *same* task; once exhausted, it goes to `replanning`,
which regenerates a plan **with the real failure fed back** — the failed task's
description, status, and error message, plus any provider-level error — as
`prior_results_summary`/`prior_errors` in the next planning prompt. This is the
mechanism that makes "plan only what you can right now" (§2) survivable: a task that
had to be deferred because its arguments weren't yet knowable will genuinely fail
(e.g. `web_research.open_url` fails validation immediately if the model faked a URL,
or fails to load if the model guessed at a real one), and that failure is what feeds
the next replanning attempt — there is no separate "plan intentionally incomplete,
please continue" signal today; the replanning path is the only continuation mechanism
that actually exists, so a plan should still aim to fully accomplish the goal with
tasks it can specify now, not deliberately stop short assuming it'll be picked back up.
This repeats up to `max_replanning_attempts` (default 3).

`completion_evaluation` runs once `task_selection` finds no more runnable tasks in the
current plan: if every task in that plan version succeeded, the run is done; if any
failed, back to `replanning`.

## 6. The final report

`final_report_generation` is the one node with a subtlety worth knowing about. If at
least one task was ever created for the run, it asks the LLM to summarize the real
task outcomes (`task_summaries` built from each task's actual `description`/`status`/
`error_message`) into a short report. **If zero tasks were ever created** — every
planning attempt failed to produce a valid plan (e.g. the model repeatedly timed out) —
it does **not** call the LLM at all, and instead builds a deterministic report
directly from the actual `plan_validation_errors`. This was a real bug found during
integration testing: with nothing to ground it, a real local model asked to explain a
run it never actually took any action on would write a plausible-sounding narrative
about research it never performed (specific platforms it claimed to have searched,
when no tool call was ever made). The fix keeps the report honest by construction in
exactly the one case where the model has no real grounding at all.

## Cancelling a run

`POST /agent/runs/{id}/cancel` sets a cooperative `cancel_requested` flag — the graph
has no true mid-node preemption, so this is checked at the top of every
`task_selection` cycle and takes effect before the *next* task starts, not
immediately. It does not (and cannot, from a concurrent request) interrupt an
in-flight tool call.

## Real-model latency, honestly

Every mechanism above (retry, replanning, the honest-failure-report fix, the
client-timeout derivation) exists because of what live integration testing against a
real local model (qwen3:4b) actually showed: planning latency for anything beyond a
trivial one-tool goal is significant and inconsistent on commodity hardware — complex,
multi-part goals were observed timing out repeatedly even at a 240-second per-attempt
budget, while simple goals ("run this one Python script") reliably plan in under a
minute. This is a genuine capability/hardware finding, not a bug to keep chasing with
an ever-larger timeout: if goals are consistently slow or unreliable to plan, the
practical remedy is a faster machine or a larger/faster model
(`TASKPILOT_OLLAMA_MODEL`), not a bigger number in `.env`.
