from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_event import AgentEvent
from app.db.models.enums import EventSeverity


class NodeContext:
    """Bundles a node's DB session with a helper for writing the AgentEvent audit trail.

    Each node owns a short-lived session for its own execution (opened and committed
    within the node function), rather than one long-lived session shared across the
    whole graph run -- keeps nodes self-contained and safe to unit test in isolation.
    """

    def __init__(self, session: AsyncSession, run_id: str, node_name: str) -> None:
        self.session = session
        self.run_id = run_id
        self.node_name = node_name

    async def log_event(
        self,
        event_type: str,
        *,
        task_id: str | None = None,
        payload: dict | None = None,
        severity: EventSeverity = EventSeverity.INFO,
    ) -> AgentEvent:
        event = AgentEvent(
            run_id=self.run_id,
            task_id=task_id,
            event_type=event_type,
            node_name=self.node_name,
            payload=payload or {},
            severity=severity,
        )
        self.session.add(event)
        await self.session.flush()
        return event
