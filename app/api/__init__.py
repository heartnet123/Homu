from fastapi import APIRouter

from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.system import router as system_router
from app.core.settings import settings


api_router = APIRouter(prefix=settings.API_V1_PREFIX)
api_router.include_router(chat_router)
api_router.include_router(documents_router)
api_router.include_router(system_router)

__all__ = ["api_router"]
