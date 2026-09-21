from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import ArtifactType

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun


class WorkspaceArtifact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspace_artifacts"
    __table_args__ = (
        UniqueConstraint("run_id", "relative_path", name="uq_workspace_artifact_run_path"),
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True
    )
    relative_path: Mapped[str] = mapped_column(nullable=False)
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType, values_callable=lambda e: [m.value for m in e]),
        default=ArtifactType.OTHER,
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(default=0, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(nullable=True)
    mime_type: Mapped[str | None] = mapped_column(nullable=True)
    created_by_tool: Mapped[str | None] = mapped_column(nullable=True)

    run: Mapped["AgentRun"] = relationship(back_populates="artifacts")
