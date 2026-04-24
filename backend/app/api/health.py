from fastapi import APIRouter

from app.config import get_config

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check():
    config = get_config()
    return {
        "status": "ok",
        "name": config.app.name,
        "theme": config.app.theme,
        "version": "0.1.0",
        "llm_provider": config.llm.provider,
        "rag_enabled": config.rag.enabled,
        "voice_enabled": config.voice.enabled,
    }
