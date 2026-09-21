from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.db.models.agent_task import AgentTask


class RecordResultInput(BaseModel):
    task_id: str
    note: str


class RecordResultOutput(BaseModel):
    task_id: str
    result_summary: str


class RecordResultTool(Tool):
    name = "task.record_result"
    category = ToolCategory.TASK_MANAGEMENT
    description = (
        "Attach a free-form progress note to a task's result_summary, without changing "
        "its status. Useful for recording partial findings on a still-running task."
    )
    input_schema = RecordResultInput
    output_schema = RecordResultOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: RecordResultInput, ctx: ToolRunContext) -> RecordResultOutput:
        async with ctx.session_factory() as session:
            task = await session.get(AgentTask, args.task_id)
            if task is None or task.run_id != ctx.run_id:
                raise ToolError(f"Unknown task: {args.task_id}")

            task.result_summary = args.note
            await session.commit()

            return RecordResultOutput(task_id=task.id, result_summary=task.result_summary)
