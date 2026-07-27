"""
File: app/application/schemas/knowledge_base.py
Folder: backend/app/application/schemas
Purpose: Request/response models for the knowledge base API.
"""

from pydantic import BaseModel


class SearchResultItem(BaseModel):
    id: str
    content: str
    score: float | None
    domain: str
    clause: str
    title: str
    sheet: str


class SearchResponse(BaseModel):
    query: str
    collection: str
    results: list[SearchResultItem]


class ControlSummary(BaseModel):
    control_number: str
    title: str
    domain: str
    sheet: str


class DomainCounts(BaseModel):
    collection: str
    domains: dict[str, int]


class CollectionStats(BaseModel):
    collection: str
    total_chunks: int


class UploadResponse(BaseModel):
    collection: str
    chunks_ingested: int
    filename: str
