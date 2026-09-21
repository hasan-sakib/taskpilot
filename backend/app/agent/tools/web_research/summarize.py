from pydantic import BaseModel, Field

from app.agent.llm.base import LLMProviderError
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext

MAX_INPUT_CHARS = 20_000


class SummarizeInput(BaseModel):
    text: str
    focus: str | None = Field(
        default=None, description="Optional instruction on what to focus the summary on"
    )


class SummarizeOutput(BaseModel):
    summary: str


class SummarizeTool(Tool):
    name = "web_research.summarize"
    category = ToolCategory.WEB_RESEARCH
    description = "Summarize a block of text, optionally focused on a specific aspect."
    input_schema = SummarizeInput
    output_schema = SummarizeOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 60

    async def run(self, args: SummarizeInput, ctx: ToolRunContext) -> SummarizeOutput:
        text = args.text[:MAX_INPUT_CHARS]
        prompt = "Summarize the following text concisely, in a few sentences."
        if args.focus:
            prompt += f" Focus specifically on: {args.focus}."
        prompt += f"\n\nText:\n{text}"

        try:
            summary = await ctx.llm_provider.complete_text(prompt)
        except LLMProviderError as exc:
            raise ToolError(f"Summarization is currently unavailable: {exc}") from exc

        return SummarizeOutput(summary=summary)
