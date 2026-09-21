import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from sqlalchemy import select

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState, ToolResult
from app.agent.tools.base import ToolError, ToolRunContext
from app.db.base import utcnow
from app.db.models.agent_task import AgentTask
from app.db.models.enums import TaskStatus, ToolExecutionStatus
from app.db.models.tool_execution import ToolExecution

OUTPUT_SUMMARY_MAX_CHARS = 2000

# ToolExecution rows in this state (or later) already ran to completion on a prior
# attempt at the same (task_id, attempt_number) -- reuse the recorded result instead
# of re-running the tool. This is what makes resume-after-crash safe.
_COMPLETED_STATUSES = {
    ToolExecutionStatus.SUCCEEDED,
    ToolExecutionStatus.FAILED,
    ToolExecutionStatus.TIMED_OUT,
}


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def tool_execution(state: AgentState) -> dict:
        run_id = state["run_id"]
        task_id = state["current_task_id"]
        tool_call = state["current_tool_call"]
        assert task_id is not None and tool_call is not None

        attempt_number = state.get("retry_count", 0) + 1

        async with deps.session_factory() as session:
            task = await session.get(AgentTask, task_id)
            assert task is not None

            execution = await session.scalar(
                select(ToolExecution).where(
                    ToolExecution.task_id == task_id,
                    ToolExecution.attempt_number == attempt_number,
                )
            )
            if execution is not None and execution.status in _COMPLETED_STATUSES:
                result = ToolResult(
                    success=execution.status == ToolExecutionStatus.SUCCEEDED,
                    data=None,
                    error=execution.error_message,
                    duration_ms=execution.duration_ms,
                    exit_code=execution.exit_code,
                )
                return {"last_tool_result": result}

            if execution is None:
                execution = ToolExecution(
                    run_id=run_id,
                    task_id=task_id,
                    attempt_number=attempt_number,
                    tool_name=tool_call.tool_name,
                    input_payload=tool_call.args,
                    payload_hash=tool_call.payload_hash,
                    approval_request_id=state.get("pending_approval_id"),
                    status=ToolExecutionStatus.STARTED,
                    started_at=utcnow(),
                )
                session.add(execution)
                await session.flush()

            task.status = TaskStatus.IN_PROGRESS
            await session.commit()

            tool = deps.tool_registry.get(tool_call.tool_name)
            assert tool is not None

            run_ctx = ToolRunContext(
                workspace_root=Path(state["workspace_root"]),
                run_id=run_id,
                task_id=task_id,
                execution_id=execution.id,
            )

            start = time.monotonic()
            try:
                validated_args = tool.input_schema.model_validate(tool_call.args)
                output = await asyncio.wait_for(
                    tool.run(validated_args, run_ctx), timeout=tool.timeout_seconds
                )
                duration_ms = int((time.monotonic() - start) * 1000)
                output_data = output.model_dump()
                execution.status = ToolExecutionStatus.SUCCEEDED
                execution.output_summary = json.dumps(output_data)[:OUTPUT_SUMMARY_MAX_CHARS]
                result = ToolResult(success=True, data=output_data, duration_ms=duration_ms)
            except TimeoutError:
                duration_ms = int((time.monotonic() - start) * 1000)
                error = f"Tool '{tool.name}' timed out after {tool.timeout_seconds}s"
                execution.status = ToolExecutionStatus.TIMED_OUT
                execution.error_message = error
                result = ToolResult(success=False, error=error, duration_ms=duration_ms)
            except ToolError as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                execution.status = ToolExecutionStatus.FAILED
                execution.error_message = str(exc)
                result = ToolResult(success=False, error=str(exc), duration_ms=duration_ms)
            except Exception as exc:  # noqa: BLE001 - tool bugs must not crash the run
                duration_ms = int((time.monotonic() - start) * 1000)
                error = f"Unexpected error running '{tool.name}': {exc}"
                execution.status = ToolExecutionStatus.FAILED
                execution.error_message = error
                result = ToolResult(success=False, error=error, duration_ms=duration_ms)

            execution.duration_ms = duration_ms
            execution.completed_at = utcnow()
            await session.commit()

        return {"last_tool_result": result}

    return tool_execution
