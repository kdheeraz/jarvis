from fastapi import APIRouter, Depends

from app.auth.middleware import require_admin
from app.config import get_config, reload_config, save_config, _deep_merge
from app.llm.agent import rebuild_agent
from app.voice.tts import reset_tts_model
from app.schemas.config import ConfigUpdateRequest

router = APIRouter(prefix="/api/admin/config", tags=["admin-config"], dependencies=[Depends(require_admin)])


@router.get("")
def get_current_config():
    config = get_config()
    data = config.model_dump()
    # Redact secrets
    if data.get("llm", {}).get("openai", {}).get("api_key"):
        data["llm"]["openai"]["api_key"] = "***"
    if data.get("llm", {}).get("anthropic", {}).get("api_key"):
        data["llm"]["anthropic"]["api_key"] = "***"
    if data.get("auth", {}).get("jwt_secret_key"):
        data["auth"]["jwt_secret_key"] = "***"
    return data


@router.put("")
def update_config(request: ConfigUpdateRequest):
    config = get_config()
    current = config.model_dump()

    updates = request.model_dump(exclude_none=True)
    merged = _deep_merge(current, updates)

    from app.config import JarvisConfig
    new_config = JarvisConfig(**merged)
    save_config(new_config)

    reload_config()
    rebuild_agent()
    reset_tts_model()

    return {"status": "ok", "message": "Configuration updated and reloaded"}


@router.post("/reload")
def reload():
    reload_config()
    rebuild_agent()
    reset_tts_model()
    return {"status": "ok", "message": "Configuration reloaded"}
