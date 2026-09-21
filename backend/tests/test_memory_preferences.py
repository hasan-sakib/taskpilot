import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_preference import UserPreference
from app.memory.preferences import load_confirmed_preferences_snapshot


@pytest.mark.asyncio
async def test_snapshot_only_includes_confirmed_and_available(db_session: AsyncSession):
    db_session.add_all(
        [
            UserPreference(
                key="confirmed.available",
                value=1,
                confirmed_by_user=True,
                available_to_future_runs=True,
            ),
            UserPreference(
                key="unconfirmed", value=2, confirmed_by_user=False, available_to_future_runs=True
            ),
            UserPreference(
                key="confirmed.unavailable",
                value=3,
                confirmed_by_user=True,
                available_to_future_runs=False,
            ),
        ]
    )
    await db_session.commit()

    snapshot = await load_confirmed_preferences_snapshot(db_session)

    assert snapshot == {"confirmed.available": 1}


@pytest.mark.asyncio
async def test_snapshot_empty_when_no_preferences(db_session: AsyncSession):
    assert await load_confirmed_preferences_snapshot(db_session) == {}
