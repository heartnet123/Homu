from fastapi import APIRouter, Depends

from app.dependencies import get_capabilities_payload

router = APIRouter(tags=["system"])


@router.get("/capabilities")
async def capabilities(payload=Depends(get_capabilities_payload)):
    return payload
