from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from app.config import get_config, _project_root
from app.db.engine import init_db, get_session_factory
from app.db.repositories.user import ensure_default_admin

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    config = get_config()
    logger.info(f"Starting {config.app.name} v0.1.0")
    logger.info(f"LLM Provider: {config.llm.provider}")
    logger.info(f"RAG Enabled: {config.rag.enabled}")
    logger.info(f"Voice Enabled: {config.voice.enabled}")
    logger.info(f"Auth Enabled: {config.auth.enabled}")

    # Initialize database
    init_db()

    # Ensure default admin user exists
    factory = get_session_factory()
    db = factory()
    try:
        ensure_default_admin(db, config.auth.admin_username, config.auth.admin_password)
    finally:
        db.close()

    logger.info(f"{config.app.name} is ready")
    yield
    logger.info(f"{config.app.name} shutting down")


def create_app() -> FastAPI:
    config = get_config()

    app = FastAPI(
        title=config.app.name,
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST API routes
    from app.api.router import api_router
    app.include_router(api_router)

    # WebSocket routes
    from app.ws.chat import router as ws_router
    app.include_router(ws_router)

    # Voice WebRTC (mounted after app creation)
    from app.voice.stream import mount_voice_stream
    mount_voice_stream(app)

    # Serve built frontend (if exists) — enables single-origin deployment
    frontend_dist = _project_root() / "frontend" / "dist"
    if frontend_dist.exists():
        # Serve widget.js at top level
        widget_dir = frontend_dist / "widget"
        if widget_dir.exists():
            app.mount("/widget", StaticFiles(directory=str(widget_dir)), name="widget")

        # Serve frontend assets
        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # SPA fallback — serve index.html for all non-API routes
        index_html = frontend_dist / "index.html"
        if index_html.exists():
            @app.get("/{path:path}")
            async def serve_spa(path: str):
                file_path = frontend_dist / path
                if file_path.is_file():
                    return FileResponse(str(file_path))
                return FileResponse(str(index_html))

    return app


app = create_app()
