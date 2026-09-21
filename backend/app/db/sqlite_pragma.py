from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

_BUSY_TIMEOUT_MS = 5000


def configure_sqlite_connection(engine: AsyncEngine) -> None:
    """Apply the per-connection PRAGMAs every SQLite connection in this app needs.

    - foreign_keys=ON: SQLite ignores FK constraints (including ON DELETE) unless this
      is set per-connection.
    - journal_mode=WAL + busy_timeout: a single POST /agent/runs request can hold the DB
      "in play" synchronously for the run's full duration (up to max_run_duration_seconds).
      Without WAL + a busy timeout, a concurrent request hitting SQLite's default
      rollback-journal locking would fail immediately with "database is locked" instead
      of waiting. WAL is a no-op (harmlessly ignored) on ":memory:" test databases.
    """

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        cursor.close()
