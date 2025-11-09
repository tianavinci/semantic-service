from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.app.models.dto import ConvertPhysReq, ConvertLogiReq
from api.app.repo.db import get_session
from api.app.services.attribute_service import physical_to_logical, logical_to_physical

router = APIRouter(prefix="/v1/convert", tags=["convert"])

@router.post("/physical-to-logical")
async def phys_to_logi(req: ConvertPhysReq, session: AsyncSession = Depends(get_session)):
    return await physical_to_logical(session, req.namespace, req.entity, req.physical_names)

@router.post("/logical-to-physical")
async def logi_to_phys(req: ConvertLogiReq, session: AsyncSession = Depends(get_session)):
    return await logical_to_physical(session, req.namespace, req.entity, req.logical_names)
