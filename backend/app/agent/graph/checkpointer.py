from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Pydantic model classes stored directly in AgentState (see graph/state.py) need to be
# explicitly allow-listed for msgpack deserialization, or LangGraph logs a deprecation
# warning today and will refuse to load them in a future version.
_ALLOWED_MSGPACK_MODULES: list[tuple[str, str]] = [
    ("app.agent.graph.state", "PlanTask"),
    ("app.agent.graph.state", "ToolCallRequest"),
    ("app.agent.graph.state", "ToolResult"),
    ("app.db.models.enums", "RunStatus"),
    ("app.db.models.enums", "TaskStatus"),
]


@asynccontextmanager
async def get_checkpointer(db_path: str) -> AsyncIterator[AsyncSqliteSaver]:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    serde = JsonPlusSerializer(allowed_msgpack_modules=_ALLOWED_MSGPACK_MODULES)
    async with aiosqlite.connect(db_path) as conn:
        yield AsyncSqliteSaver(conn, serde=serde)
