from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import ToolExecutionStatus

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun
    from app.db.models.agent_task import AgentTask


class ToolExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tool_executions"
    __table_args__ = (
        UniqueConstraint("task_id", "attempt_number", name="uq_tool_execution_task_attempt"),
        Index("ix_tool_executions_payload_hash", "payload_hash"),
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(nullable=False, default=1)
    tool_name: Mapped[str] = mapped_column(nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    payload_hash: Mapped[str] = mapped_column(nullable=False)
    approval_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ToolExecutionStatus] = mapped_column(
        Enum(ToolExecutionStatus, values_callable=lambda e: [m.value for m in e]),
        default=ToolExecutionStatus.STARTED,
        nullable=False,
    )
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    run: Mapped["AgentRun"] = relationship(back_populates="tool_executions")
    task: Mapped["AgentTask"] = relationship(back_populates="tool_executions")
