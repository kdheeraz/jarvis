from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.architecture import router as architecture_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.voice import router as voice_router
from app.api.admin.config import router as admin_config_router
from app.api.admin.tools import router as admin_tools_router
from app.api.admin.users import router as admin_users_router
from app.api.admin.conversations import router as admin_conversations_router
from app.api.admin.rag import router as admin_rag_router

api_router = APIRouter()

# Public routes
api_router.include_router(health_router)
api_router.include_router(architecture_router)
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(conversations_router)
api_router.include_router(voice_router)

# Admin routes
api_router.include_router(admin_config_router)
api_router.include_router(admin_tools_router)
api_router.include_router(admin_users_router)
api_router.include_router(admin_conversations_router)
api_router.include_router(admin_rag_router)
