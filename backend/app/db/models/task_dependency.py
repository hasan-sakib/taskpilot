from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.agent_task import AgentTask


class TaskDependency(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency_pair"),
        Index("ix_task_dependencies_task_id", "task_id"),
        Index("ix_task_dependencies_depends_on_task_id", "depends_on_task_id"),
    )

    task_id: Mapped[str] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    depends_on_task_id: Mapped[str] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )

    task: Mapped["AgentTask"] = relationship(
        back_populates="dependencies", foreign_keys=[task_id]
    )
    depends_on_task: Mapped["AgentTask"] = relationship(foreign_keys=[depends_on_task_id])
