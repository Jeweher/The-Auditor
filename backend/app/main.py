"""
File: app/main.py
Folder: backend/app
Purpose: FastAPI application factory. Wires together config, logging,
         exception handlers, and CORS. No business routes yet — those are
         added starting Phase 1. Exposes a /health endpoint for Docker/Nginx
         health checks.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers.admin import router as admin_router
from app.api.v1.routers.assessment import router as assessment_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.knowledge_base import router as knowledge_base_router
from app.api.v1.routers.public import router as public_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(knowledge_base_router)
app.include_router(assessment_router)
app.include_router(public_router)
app.include_router(admin_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("%s starting up in '%s' mode", settings.APP_NAME, settings.ENV)
