import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel


class ToolCategory(enum.StrEnum):
    WEB_RESEARCH = "web_research"
    WORKSPACE = "workspace"
    TASK_MANAGEMENT = "task_management"
    PYTHON_EXECUTION = "python_execution"
    BROWSER = "browser"


class PermissionLevel(enum.StrEnum):
    AUTO = "auto"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass(frozen=True)
class PermissionDecision:
    requires_approval: bool
    reason: str


@dataclass(frozen=True)
class ToolRunContext:
    workspace_root: Path
    run_id: str
    task_id: str
    execution_id: str


class ToolError(Exception):
    """Raised by a tool's run() for an expected, handled failure (bad input, missing file, ...).

    Distinct from an unhandled exception: tool_execution treats this as a normal task
    failure to record and possibly retry, not a bug to crash the run over.
    """


class Tool(ABC):
    name: ClassVar[str]
    category: ClassVar[ToolCategory]
    description: ClassVar[str]
    input_schema: ClassVar[type[BaseModel]]
    output_schema: ClassVar[type[BaseModel]]
    default_permission: ClassVar[PermissionLevel] = PermissionLevel.AUTO
    timeout_seconds: ClassVar[int] = 30

    def evaluate_permission(self, args: dict, preferences: dict) -> PermissionDecision:
        # Preferences will be able to ADD approval requirements once wired up in Phase 4,
        # but can never lower a tool below its own default -- that floor is enforced here,
        # not by trusting whatever the preference/LLM layer says.
        if self.default_permission == PermissionLevel.REQUIRES_APPROVAL:
            return PermissionDecision(True, f"{self.name} requires approval by default")
        return PermissionDecision(False, f"{self.name} is auto-approved")

    @abstractmethod
    async def run(self, args: BaseModel, ctx: ToolRunContext) -> BaseModel: ...

    def redact_for_audit(self, args: dict) -> dict:
        return args
