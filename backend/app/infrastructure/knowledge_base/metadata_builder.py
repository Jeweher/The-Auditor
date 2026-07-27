"""
File: app/infrastructure/knowledge_base/metadata_builder.py
Folder: backend/app/infrastructure/knowledge_base
Purpose: Faithful port of get_domain()/build_meta() from the Colab script,
         plus the single conversion function that turns raw chunk dicts
         (from either the Excel parser or the default corpus JSON) into
         typed KnowledgeChunk entities ready for embedding. This is the
         convergence point mentioned in the Phase 2 plan: both ingestion
         paths call chunks_to_knowledge_chunks() so metadata is built
         identically regardless of source.
"""

from app.domain.entities.knowledge_chunk import KnowledgeChunk


def get_domain(c: dict) -> str:
    sheet = c.get("sheet", "") or ""
    src = c.get("source", "") or ""
    if sheet == "Information Security":
        return "IS"
    if sheet == "Prototype Protection":
        return "PP"
    if sheet == "Data Protection":
        return "DP"
    if sheet == "Definitions":
        return "DEF"
    if sheet == "Examples KPI":
        return "KPI"
    if sheet == "Maturity levels":
        return "MATURITY"
    if src == "COLS":
        return "LEGAL"
    if src in ("TOC", "STYLE", "PARA"):
        return "GUIDE"
    return "OTHER"


def build_meta(c: dict, idx: int) -> dict:
    ctrl = c.get("control_number")
    return {
        "domain": get_domain(c),
        "sheet": str(c.get("sheet") or ""),
        "sheet_type": str(c.get("sheet_type") or c.get("source") or ""),
        "clause": str(ctrl) if ctrl else "",
        "has_clause": 1 if ctrl else 0,
        "section_l1": str(c.get("section_l1") or c.get("parent_title") or "")[:100],
        "title": str(c.get("title") or "")[:200],
        "char_count": int(c.get("content_length", 0)),
        "source": str(c.get("source") or ""),
        "is_subchunk": 1 if c.get("is_subchunk") else 0,
        "is_container": 1 if c.get("is_container") else 0,
        "sub_label": str(c.get("sub_label") or ""),
        "corpus_id": idx,
    }


def chunks_to_knowledge_chunks(raw_chunks: list[dict]) -> list[KnowledgeChunk]:
    """Convert raw chunk dicts (Excel parser or default corpus JSON) into
    typed KnowledgeChunk entities, with a fresh sequential id and metadata
    built the same way regardless of origin."""
    result: list[KnowledgeChunk] = []
    for idx, c in enumerate(raw_chunks):
        chunk_id = str(c.get("corpus_id", idx))
        result.append(
            KnowledgeChunk(
                id=chunk_id,
                content=c.get("content", "") or "",
                embedding_text=c.get("embedding_text", "") or "",
                metadata=build_meta(c, idx),
            )
        )
    return result
