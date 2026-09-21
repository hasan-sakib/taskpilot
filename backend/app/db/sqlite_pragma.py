from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine


def enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    """SQLite ignores FK constraints (including ON DELETE) unless this is set per-connection."""

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
