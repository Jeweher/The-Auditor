"""
File: app/api/v1/routers/knowledge_base.py
Folder: backend/app/api/v1/routers
Purpose: HTTP layer for the knowledge base. All routes require
         authentication. Routes contain no business logic — they parse
         input, call the query/ingestion services, and shape the response.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.v1.deps import get_current_user, get_kb_ingestion_service, get_kb_query_service
from app.application.schemas.knowledge_base import (
    CollectionStats,
    ControlSummary,
    DomainCounts,
    SearchResponse,
    SearchResultItem,
    UploadResponse,
)
from app.application.services.knowledge_base_ingestion_service import KnowledgeBaseIngestionService
from app.application.services.knowledge_base_query_service import KnowledgeBaseQueryService
from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.domain.entities.user import User

router = APIRouter(prefix="/api/v1/knowledge-base", tags=["knowledge-base"])

ALLOWED_UPLOAD_EXTENSIONS = (".xlsx", ".xlsm")


@router.get("/stats", response_model=CollectionStats)
def get_stats(
    query_service: Annotated[KnowledgeBaseQueryService, Depends(get_kb_query_service)],
    _user: Annotated[User, Depends(get_current_user)],
    collection: str | None = Query(default=None, description="Defaults to the default KB collection"),
) -> CollectionStats:
    stats = query_service.collection_stats(collection)
    return CollectionStats(**stats)


@router.get("/domains", response_model=DomainCounts)
def list_domains(
    query_service: Annotated[KnowledgeBaseQueryService, Depends(get_kb_query_service)],
    _user: Annotated[User, Depends(get_current_user)],
    collection: str | None = Query(default=None),
) -> DomainCounts:
    name = collection or get_settings().DEFAULT_KB_COLLECTION_NAME
    domains = query_service.list_domains(collection)
    return DomainCounts(collection=name, domains=domains)


@router.get("/controls", response_model=list[ControlSummary])
def list_controls(
    query_service: Annotated[KnowledgeBaseQueryService, Depends(get_kb_query_service)],
    _user: Annotated[User, Depends(get_current_user)],
    collection: str | None = Query(default=None),
    domain: str | None = Query(default=None, description="Filter by domain code, e.g. IS, PP, DP"),
) -> list[ControlSummary]:
    return [ControlSummary(**c) for c in query_service.list_controls(collection, domain)]


@router.get("/search", response_model=SearchResponse)
def search(
    query_service: Annotated[KnowledgeBaseQueryService, Depends(get_kb_query_service)],
    _user: Annotated[User, Depends(get_current_user)],
    q: str = Query(..., min_length=1, description="Natural-language query"),
    collection: str | None = Query(default=None),
    top_k: int = Query(default=5, ge=1, le=50),
    domain: str | None = Query(default=None),
) -> SearchResponse:
    name = collection or get_settings().DEFAULT_KB_COLLECTION_NAME
    results = query_service.search(q, collection, top_k=top_k, domain=domain)
    items = [
        SearchResultItem(
            id=doc.id,
            content=doc.content,
            score=doc.score,
            domain=str(doc.metadata.get("domain", "")),
            clause=str(doc.metadata.get("clause", "")),
            title=str(doc.metadata.get("title", "")),
            sheet=str(doc.metadata.get("sheet", "")),
        )
        for doc in results
    ]
    return SearchResponse(query=q, collection=name, results=items)


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_questionnaire(
    ingestion_service: Annotated[KnowledgeBaseIngestionService, Depends(get_kb_ingestion_service)],
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> UploadResponse:
    """Upload a VDA ISA questionnaire (.xlsx). Parsed, chunked, and embedded
    into a brand-new collection scoped to this upload — the default
    collection is never modified by this endpoint. Once assessments exist
    (Phase 3), the collection is linked to the assessment that owns it."""
    if not file.filename or not file.filename.lower().endswith(ALLOWED_UPLOAD_EXTENSIONS):
        raise ValidationError("Only .xlsx/.xlsm files are accepted.")

    settings = get_settings()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        raise ValidationError(f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit.")

    collection_name = f"kb_upload_{user.id.hex}_{uuid.uuid4().hex[:8]}"
    count = ingestion_service.ingest_excel_upload(collection_name, file_bytes, file.filename)

    return UploadResponse(collection=collection_name, chunks_ingested=count, filename=file.filename)
