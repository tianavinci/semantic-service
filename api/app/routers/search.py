from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.app.repo.attribute_repo import AttributeRepo
from api.app.models.dto import SearchResp
from api.app.repo.db import get_session

router = APIRouter(prefix="/v1/attributes", tags=["search"])

@router.get("/search", response_model=SearchResp)
async def search(namespace: str | None = None, entity: str | None = None, q: str | None = None,
                 by: str = "both", limit: int = 50, offset: int = 0,
                 session: AsyncSession = Depends(get_session)):
    repo = AttributeRepo(session)
    rows = await repo.search(namespace, entity, q, by, limit, offset)
    return SearchResp(items=[r.__dict__ for r in rows], total=None)
