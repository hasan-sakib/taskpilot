from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import RunStatus

if TYPE_CHECKING:
    from app.db.models.agent_event import AgentEvent
    from app.db.models.agent_task import AgentTask
    from app.db.models.approval_request import ApprovalRequest
    from app.db.models.browser_session import BrowserSession
    from app.db.models.tool_execution import ToolExecution
    from app.db.models.workspace_artifact import WorkspaceArtifact


class AgentRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"

    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, values_callable=lambda e: [m.value for m in e]),
        default=RunStatus.PENDING,
        nullable=False,
    )
    plan_version: Mapped[int] = mapped_column(default=0, nullable=False)
    model_name: Mapped[str | None] = mapped_column(nullable=True)
    test_mode: Mapped[bool] = mapped_column(default=False, nullable=False)
    workspace_root: Mapped[str] = mapped_column(nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    final_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(default=False, nullable=False)

    tasks: Mapped[list["AgentTask"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    events: Mapped[list["AgentEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    browser_sessions: Mapped[list["BrowserSession"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["WorkspaceArtifact"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
