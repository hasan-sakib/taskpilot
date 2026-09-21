from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict = Field(default_factory=dict)


class PlanTaskSpec(BaseModel):
    description: str
    tool_name: str
    tool_args: dict = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list)  # 0-based indices into this plan


class PlanResponse(BaseModel):
    tasks: list[PlanTaskSpec] = Field(default_factory=list)


class PlanRequest(BaseModel):
    goal: str
    available_tools: list[ToolSpec] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict)
    prior_errors: list[str] = Field(default_factory=list)
    prior_results_summary: str | None = None


class ReportRequest(BaseModel):
    goal: str
    task_summaries: list[str] = Field(default_factory=list)
    overall_success: bool = True


class LLMProviderError(Exception):
    """Raised when the provider cannot produce a usable structured response.

    Nodes must catch this and degrade to an explicit failure state (e.g. an empty,
    invalid plan that plan_validation rejects) rather than letting it crash the run.
    """


class LLMProvider(ABC):
    @abstractmethod
    async def generate_plan(self, request: PlanRequest) -> PlanResponse: ...

    @abstractmethod
    async def generate_report(self, request: ReportRequest) -> str: ...

    @abstractmethod
    async def complete_text(self, prompt: str) -> str:
        """Free-form text completion, used by tools that need ad-hoc LLM help (e.g.
        web_research.summarize) rather than the structured plan/report flows above."""
