from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import TaskStatus

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun
    from app.db.models.task_dependency import TaskDependency
    from app.db.models.tool_execution import ToolExecution


class AgentTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_tasks"
    __table_args__ = (
        Index("ix_agent_tasks_run_status", "run_id", "status"),
        UniqueConstraint(
            "run_id", "plan_version", "sequence_index", name="uq_agent_tasks_run_plan_seq"
        ),
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    plan_version: Mapped[int] = mapped_column(nullable=False, default=0)
    sequence_index: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str] = mapped_column(nullable=False)
    tool_args: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=lambda e: [m.value for m in e]),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(default=0, nullable=False)
    deadline: Mapped[str | None] = mapped_column(nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True
    )

    run: Mapped["AgentRun"] = relationship(back_populates="tasks")
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    dependencies: Mapped[list["TaskDependency"]] = relationship(
        back_populates="task",
        foreign_keys="TaskDependency.task_id",
        cascade="all, delete-orphan",
    )
    parent: Mapped["AgentTask | None"] = relationship(
        remote_side="AgentTask.id", back_populates="children"
    )
    children: Mapped[list["AgentTask"]] = relationship(
        back_populates="parent", foreign_keys=[parent_task_id]
    )
