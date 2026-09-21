import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    # Naive, not tz-aware: SQLite's DateTime columns always round-trip as naive
    # datetimes -- there is no SQLite-native timezone-aware type. Every datetime in
    # this app is UTC by convention; mixing naive and tz-aware values here would break
    # arithmetic the instant a value survives a DB round-trip (it did, until this was
    # naive-only).
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(primary_key=True, default=new_uuid)


class TimestampMixin:
    # Python-side defaults (not server_default=func.now()/onupdate=func.now()):
    # SQLite's CURRENT_TIMESTAMP only has 1-second resolution, which made created_at
    # ties -- and therefore unstable ordering -- routine for anything created within
    # the same wall-clock second (e.g. several AgentEvent rows from one fast node
    # transition). utcnow() gives microsecond precision instead. This also sidesteps
    # the class of bug where a server-computed onupdate column needs an explicit
    # session.refresh() after commit before FastAPI's sync response serialization can
    # touch it (UPDATE, unlike INSERT, doesn't get a free RETURNING fetch) -- the
    # value is already known to the ORM before the write, no refresh needed.
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utcnow, onupdate=utcnow, nullable=False
    )
