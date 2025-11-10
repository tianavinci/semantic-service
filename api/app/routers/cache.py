from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.app.repo.attribute_repo import AttributeRepo
from api.app.repo.db import get_session
from api.app.services.cache import cache
from typing import Optional

router = APIRouter(prefix="/v1/cache", tags=["cache"])

@router.post("/refresh")
async def refresh_cache(namespace: Optional[str] = None, entity: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    """Refresh cache entries from the database. Both `namespace` and `entity` are optional filters.

    If neither param is provided all active attributes will be refreshed.
    Returns a summary: number of refreshed entries and list of example keys refreshed.
    """
    repo = AttributeRepo(session)
    rows = await repo.list_active(namespace, entity)
    if not rows:
        return {"refreshed": 0, "sample": []}

    refreshed = 0
    sample = []
    # Refresh each attribute in DB and update cache (best-effort)
    for r in rows:
        d = r.__dict__.copy()
        # ensure serializable fields are present; cache.set_both expects keys
        try:
            await cache.set_both(d)
            refreshed += 1
            if len(sample) < 10:
                sample.append({"namespace": d.get("namespace"), "entity": d.get("entity"), "physical_name": d.get("physical_name"), "logical_name": d.get("logical_name")})
        except Exception as e:
            # don't fail the whole operation for single-key errors
            # but surface a warning in the response
            sample.append({"error": str(e), "namespace": d.get("namespace"), "entity": d.get("entity")})

    return {"refreshed": refreshed, "sample": sample}
