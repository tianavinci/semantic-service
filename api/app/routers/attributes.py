from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.app.models.dto import AttributeIn, AttributeOut
from api.app.repo.db import get_session, Attribute
from api.app.repo.attribute_repo import AttributeRepo, DuplicateError, MigrationError
from api.app.services.cache import cache
import sqlalchemy

router = APIRouter(prefix="/v1/attributes", tags=["attributes"])

@router.post("", response_model=list[AttributeOut])
async def create(attrs: list[AttributeIn], session: AsyncSession = Depends(get_session)):
    repo = AttributeRepo(session)
    try:
        rows = await repo.bulk_insert([a.model_dump() | {"version": 1} for a in attrs])
        await session.commit()
    except MigrationError as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=("Database schema not found: meta.attribute. "
                                                     "Ensure migrations have been applied and retry. "
                                                     f"(orig: {str(e)})"))
    except DuplicateError as e:
        await session.rollback()
        raise HTTPException(status_code=409, detail=f"Duplicate attribute(s): {e.duplicates}")
    except sqlalchemy.exc.IntegrityError as e:
        # Rollback the session to clear the failed transaction state, then return 409
        await session.rollback()
        # Provide a concise message for duplicate key violation
        msg = str(getattr(e, 'orig', e))
        raise HTTPException(status_code=409, detail=f"Duplicate attribute insertion: {msg}")

    outs: list[AttributeOut] = []
    for r in rows:
        # Build a Pydantic output model from the SQLAlchemy object and cache a serializable dict
        out = AttributeOut(**r.__dict__)
        await cache.set_both(out.model_dump(mode="json"))
        outs.append(out)
    return outs

@router.get("/{id}", response_model=AttributeOut)
async def get_one(id: int, session: AsyncSession = Depends(get_session)):
    obj = await session.get(Attribute, id)
    if not obj: raise HTTPException(404, "Not found")
    return AttributeOut(**obj.__dict__)

@router.put("/{id}")
async def update(id: int, payload: AttributeIn, session: AsyncSession = Depends(get_session)):
    repo = AttributeRepo(session)
    count = await repo.update(id, payload.model_dump())
    await session.commit()
    if count == 0: raise HTTPException(404, "Not found")
    await cache.invalidate(payload.namespace, payload.entity, payload.physical_name, payload.logical_name)
    return {"updated": count}

@router.delete("/{id}")
async def delete(id: int, session: AsyncSession = Depends(get_session)):
    obj = await session.get(Attribute, id)
    if not obj: raise HTTPException(404, "Not found")
    await cache.invalidate(obj.namespace, obj.entity, obj.physical_name, obj.logical_name)
    await session.delete(obj)
    await session.commit()
    return {"deleted": 1}
