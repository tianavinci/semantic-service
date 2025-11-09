from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from api.app.repo.attribute_repo import AttributeRepo
from api.app.services.cache import cache

async def physical_to_logical(session: AsyncSession, ns: str, entity: str, physical_names: List[str]) -> Dict[str, dict | None]:
    repo = AttributeRepo(session)
    out: Dict[str, dict | None] = {}
    misses: list[str] = []
    for p in physical_names:
        hit = await cache.get_phys(ns, entity, p)
        if hit: out[p] = hit
        else: misses.append(p)
    for p in misses:
        row = await repo.get_by_physical(ns, entity, p)
        out[p] = row.__dict__ if row else None
        if row: await cache.set_both(row.__dict__)
    return out

async def logical_to_physical(session: AsyncSession, ns: str, entity: str, logical_names: List[str]) -> Dict[str, dict | None]:
    repo = AttributeRepo(session)
    out: Dict[str, dict | None] = {}
    misses: list[str] = []
    for l in logical_names:
        hit = await cache.get_logi(ns, entity, l)
        if hit: out[l] = hit
        else: misses.append(l)
    for l in misses:
        row = await repo.get_by_logical(ns, entity, l)
        out[l] = row.__dict__ if row else None
        if row: await cache.set_both(row.__dict__)
    return out
