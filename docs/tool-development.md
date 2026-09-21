# Adding a tool

Every tool TaskPilot can call is a subclass of `Tool` (`backend/app/agent/tools/base.py`).
This walks through adding a new one, using a hypothetical `workspace.count_lines` as
the running example.

## 1. Write the input/output schemas and the tool class

Put it under the right category directory (`backend/app/agent/tools/<category>/`) —
`web_research`, `workspace`, `task_management`, `python_execution`, or `browser`:

```python
# backend/app/agent/tools/workspace/count_lines.py
from pydantic import BaseModel

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext


class CountLinesInput(BaseModel):
    path: str


class CountLinesOutput(BaseModel):
    path: str
    line_count: int


class CountLinesTool(Tool):
    name = "workspace.count_lines"
    category = ToolCategory.WORKSPACE
    description = "Count the lines in a workspace text file."
    input_schema = CountLinesInput
    output_schema = CountLinesOutput
    default_permission = PermissionLevel.AUTO  # read-only -- see step 3
    timeout_seconds = 10

    async def run(self, args: CountLinesInput, ctx: ToolRunContext) -> CountLinesOutput:
        target = resolve_workspace_path(ctx.workspace_root, args.path)
        if not target.is_file():
            raise ToolError(f"No such file: {args.path}")
        line_count = sum(1 for _ in target.open(encoding="utf-8", errors="replace"))
        return CountLinesOutput(path=args.path, line_count=line_count)
```

A few things every tool must get right:

- **`name`** is namespaced `<category>.<verb>` and is what the planner LLM sees and
  emits verbatim — keep it short and unambiguous next to the other tools in its
  category.
- **`description`** is shown to the planner alongside the JSON schema of
  `input_schema` — it's the only context the model has for when to use this tool
  instead of another one. Be specific about what it does and doesn't do.
- **Any filesystem path** must go through `resolve_workspace_path()`
  (`backend/app/agent/policies/workspace_policy.py`) — never build a path directly
  from `ctx.workspace_root` and a user/model-supplied string. This is the one place
  path-traversal protection lives; bypassing it, even accidentally, reopens exactly
  the class of bug it exists to close. See [security.md](security.md).
- **Expected failures raise `ToolError`**, not a bare exception — a missing file, a
  bad argument, an external service being down. `tool_execution` treats a `ToolError`
  as a normal task failure to record and possibly retry, not a bug that crashes the
  run. Let genuinely unexpected exceptions propagate; they're caught and logged
  separately, one level up.
- **`run()` gets a validated `input_schema` instance**, not a raw dict — validation
  already happened (twice: once at `plan_validation`, again at `tool_execution`,
  since a plan can be validated well before it actually runs). Don't re-validate by
  hand.

## 2. Register it

Add it to `backend/app/agent/tools/registry.py`'s `build_default_registry()` — both
the import and a `registry.register(...)` call. A tool that exists but isn't
registered here is invisible to the planner and can never be selected.

## 3. Choose the permission level deliberately

`default_permission` is `PermissionLevel.AUTO` unless set otherwise, and it's a
**floor** — see [security.md](security.md) for the full model, but the short version:
a user preference can only ever raise a tool from `AUTO` to `REQUIRES_APPROVAL`, never
lower it back down, so getting this default right matters. Ask: if the LLM calls this
with arguments it invented, and nobody reviews it first, what's the worst realistic
outcome?

- Read-only, no side effects outside the sandbox (list a directory, read a file,
  search, fetch a page) → `AUTO`.
- Writes, deletes, or otherwise changes state outside the sandbox (write a file,
  delete a file, execute arbitrary code, submit a form) → `REQUIRES_APPROVAL`.

If a tool takes a genuinely sensitive argument (unlikely for anything currently
planned, but possible for a future integration), override `redact_for_audit()` rather
than relying on the default key-name heuristic — see the docstring on
`Tool.redact_for_audit()` for where it does and doesn't apply.

## 4. Test it

Follow the pattern in `backend/tests/agent/tools/test_workspace_tools.py` (or the
equivalent file for your category): construct the tool directly, call `.run()` against
a real `ToolRunContext` pointed at a `tmp_path` workspace, and assert on the output —
no mocking needed for anything that's pure Python. For anything touching the DB
(most `task_management` tools, or anything using `ctx.session_factory`), use the
`agent_session_factory`/`workspace_root` fixtures from `backend/tests/agent/conftest.py`.

At minimum, cover:

- The happy path.
- Every required field being rejected when missing
  (`tests/agent/tools/test_tool_input_validation.py` already does this automatically
  for every registered tool via a single parametrized test — nothing extra needed here
  unless the tool has a *non-obvious* validation rule beyond "field is required").
- The realistic failure case (`ToolError`) your tool can hit — a missing file, an
  unreachable service, an invalid path.
- If the tool touches the workspace filesystem: a path-traversal attempt
  (`../`, an absolute path, a symlink escape) is rejected. `resolve_workspace_path()`
  already handles this centrally, but a quick test here confirms your tool is actually
  routing through it.

Then add a happy-path task to the graph-level tests if the tool is meant to be a
realistic step in a real plan (see `backend/tests/agent/test_graph_transitions.py` for
the pattern) — this confirms the tool composes correctly with permission evaluation,
execution, and result verification, not just in isolation.
