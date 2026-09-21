from typing import Any

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_preferences"

    key: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    # Any JSON-compatible value, not just objects -- e.g. a bare `true` for a
    # tool.<name>.require_approval override, a number, a string, as well as a dict.
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    confirmed_by_user: Mapped[bool] = mapped_column(default=False, nullable=False)
    available_to_future_runs: Mapped[bool] = mapped_column(default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
