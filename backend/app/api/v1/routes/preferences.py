from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid
from app.db.models.user_preference import UserPreference
from app.db.session import get_session
from app.schemas.preference import (
    CreatePreferenceRequest,
    PreferenceResponse,
    UpdatePreferenceRequest,
)

router = APIRouter(prefix="/memory/preferences", tags=["memory"])


@router.get("", response_model=list[PreferenceResponse])
async def list_preferences(session: AsyncSession = Depends(get_session)) -> list[UserPreference]:
    result = await session.scalars(select(UserPreference).order_by(UserPreference.key))
    return list(result)


@router.post("", response_model=PreferenceResponse, status_code=201)
async def create_preference(
    body: CreatePreferenceRequest, session: AsyncSession = Depends(get_session)
) -> UserPreference:
    preference = UserPreference(
        id=new_uuid(),
        key=body.key,
        value=body.value,
        description=body.description,
        confirmed_by_user=body.confirmed_by_user,
        available_to_future_runs=body.available_to_future_runs,
    )
    session.add(preference)
    try:
        await session.commit()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409, detail=f"Preference already exists: {body.key}"
        ) from exc
    return preference


@router.patch("/{preference_id}", response_model=PreferenceResponse)
async def update_preference(
    preference_id: str,
    body: UpdatePreferenceRequest,
    session: AsyncSession = Depends(get_session),
) -> UserPreference:
    preference = await session.get(UserPreference, preference_id)
    if preference is None:
        raise HTTPException(status_code=404, detail=f"No such preference: {preference_id}")

    if body.value is not None:
        preference.value = body.value
    if body.description is not None:
        preference.description = body.description
    if body.confirmed_by_user is not None:
        preference.confirmed_by_user = body.confirmed_by_user
    if body.available_to_future_runs is not None:
        preference.available_to_future_runs = body.available_to_future_runs

    await session.commit()
    return preference


@router.delete("/{preference_id}", status_code=204)
async def delete_preference(
    preference_id: str, session: AsyncSession = Depends(get_session)
) -> None:
    preference = await session.get(UserPreference, preference_id)
    if preference is None:
        raise HTTPException(status_code=404, detail=f"No such preference: {preference_id}")
    await session.delete(preference)
    await session.commit()
