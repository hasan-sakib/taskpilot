from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_preference import UserPreference


async def load_confirmed_preferences_snapshot(session: AsyncSession) -> dict:
    """Build the {key: value} snapshot a run starts with.

    Only explicitly confirmed, future-run-eligible preferences are ever loaded into a
    run -- an agent-proposed-but-unconfirmed preference (confirmed_by_user=False) stays
    completely inert until a human confirms it. This is the one place that boundary is
    enforced for the run-start path; permission_evaluation trusts whatever snapshot it
    is handed, so it must never be handed anything the user hasn't explicitly approved.
    """
    prefs = await session.scalars(
        select(UserPreference).where(
            UserPreference.confirmed_by_user, UserPreference.available_to_future_runs
        )
    )
    return {p.key: p.value for p in prefs}
