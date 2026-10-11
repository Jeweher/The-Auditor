"""
File: app/api/v1/routers/public.py
Folder: backend/app/api/v1/routers
Purpose: Unauthenticated endpoints reachable without an account — currently
         just the TISAX Teacher widget. Protected from abuse by a simple
         in-memory per-IP rate limit (see core/rate_limit.py).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.v1.deps import get_kb_query_service, get_llm_client
from app.application.schemas.public import AskAssistantRequest, AskAssistantResponse
from app.application.services.knowledge_base_query_service import KnowledgeBaseQueryService
from app.application.services.public_assistant_service import PublicAssistantService
from app.core.rate_limit import public_assistant_rate_limiter
from app.domain.ports.llm_client import LLMPort

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/public", tags=["public"])


def _enforce_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    if not public_assistant_rate_limiter.allow(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You've reached the question limit for now. Please try again later.",
        )


@router.post("/tisax-assistant", response_model=AskAssistantResponse)
def ask_tisax_assistant(
    payload: AskAssistantRequest,
    kb_query_service: Annotated[KnowledgeBaseQueryService, Depends(get_kb_query_service)],
    llm: Annotated[LLMPort, Depends(get_llm_client)],
    _rate_limit: Annotated[None, Depends(_enforce_rate_limit)],
) -> AskAssistantResponse:
    service = PublicAssistantService(kb_query_service, llm)
    history = [h.model_dump() for h in payload.history]
    try:
        reply = service.answer(payload.message, history)
    except Exception:
        # Log the real cause, but return a clean HTTP error so the browser
        # receives proper CORS headers instead of a misleading CORS failure.
        logger.exception("TISAX assistant failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The assistant is temporarily unavailable. Please try again.",
        )
    return AskAssistantResponse(reply=reply)