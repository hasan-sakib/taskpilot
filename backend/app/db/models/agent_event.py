from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import EventSeverity

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun


class AgentEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_events"
    __table_args__ = (Index("ix_agent_events_run_created", "run_id", "created_at"),)

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(nullable=False)
    node_name: Mapped[str | None] = mapped_column(nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    severity: Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity, values_callable=lambda e: [m.value for m in e]),
        default=EventSeverity.INFO,
        nullable=False,
    )

    run: Mapped["AgentRun"] = relationship(back_populates="events")
