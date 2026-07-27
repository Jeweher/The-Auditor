"""
File: app/domain/entities/knowledge_chunk.py
Folder: backend/app/domain/entities
Purpose: Plain domain representation of a single retrievable chunk of the
         TISAX/VDA ISA knowledge base (either the default corpus or a
         user-uploaded questionnaire). Framework-free — no pandas, no
         chromadb, no SQLAlchemy. Both the Excel parser and the default
         corpus loader produce these; the ingestion service is the only
         thing that turns them into vectors.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class KnowledgeChunk:
    id: str
    content: str
    embedding_text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    # Convenience accessors (all sourced from metadata, kept here for readability)
    @property
    def domain(self) -> str:
        return str(self.metadata.get("domain", ""))

    @property
    def clause(self) -> str:
        return str(self.metadata.get("clause", ""))

    @property
    def title(self) -> str:
        return str(self.metadata.get("title", ""))
