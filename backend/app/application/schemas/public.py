"""
File: app/application/schemas/public.py
Folder: backend/app/application/schemas
Purpose: Request/response models for public, unauthenticated endpoints
         (currently: the TISAX Teacher widget on the Home page).
"""

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AskAssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)


class AskAssistantResponse(BaseModel):
    reply: str