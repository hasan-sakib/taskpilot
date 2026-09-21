from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import BrowserSessionStatus

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun


class BrowserSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "browser_sessions"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[BrowserSessionStatus] = mapped_column(
        Enum(BrowserSessionStatus, values_callable=lambda e: [m.value for m in e]),
        default=BrowserSessionStatus.ACTIVE,
        nullable=False,
    )
    playwright_context_id: Mapped[str | None] = mapped_column(nullable=True)
    current_url: Mapped[str | None] = mapped_column(nullable=True)
    storage_state_path: Mapped[str | None] = mapped_column(nullable=True)
    headless: Mapped[bool] = mapped_column(default=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    run: Mapped["AgentRun"] = relationship(back_populates="browser_sessions")
