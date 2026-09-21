import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    # Naive, not tz-aware: SQLite's DateTime columns (including server_default
    # CURRENT_TIMESTAMP, used below) always round-trip as naive datetimes -- there is
    # no SQLite-native timezone-aware type. Every datetime in this app is UTC by
    # convention; mixing naive and tz-aware values here would break arithmetic the
    # instant a value survives a DB round-trip (it did, until this was naive-only).
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(primary_key=True, default=new_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
