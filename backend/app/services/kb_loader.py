"""Trusted banking knowledge-base loader for RAG."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.config import settings


LEGACY_SOPS_JSON = Path(__file__).parent.parent.parent / "data" / "sops" / "sops.json"


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    title: str
    category: str
    content: str
    source: str
    content_type: str = "sop"
    branch_ids: tuple[str, ...] = ("default",)
    language: str = "en-IN"
    effective_from: str | None = None
    effective_to: str | None = None
    version: str | None = None
    approved_by: str | None = None
    tags: tuple[str, ...] = ()
    structured_facts: dict[str, Any] | None = None


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    document_id: str
    title: str
    category: str
    content: str
    source: str
    content_type: str
    branch_ids: tuple[str, ...]
    language: str
    effective_from: str | None
    effective_to: str | None
    version: str | None
    approved_by: str | None
    tags: tuple[str, ...]


def load_knowledge_documents() -> list[KnowledgeDocument]:
    """Load current KB JSON files plus legacy SOPs for compatibility."""
    docs: list[KnowledgeDocument] = []
    kb_dir = Path(settings.kb_data_dir)
    if not kb_dir.is_absolute():
        kb_dir = Path.cwd() / kb_dir

    for path in sorted(kb_dir.glob("*.json")):
        docs.extend(_load_json_documents(path))

    if LEGACY_SOPS_JSON.exists():
        docs.extend(_load_json_documents(LEGACY_SOPS_JSON, legacy=True))

    deduped: dict[str, KnowledgeDocument] = {}
    for doc in docs:
        deduped[doc.id] = doc
    return list(deduped.values())


def chunk_documents(docs: list[KnowledgeDocument]) -> list[KnowledgeChunk]:
    """Create retrieval chunks while preserving source metadata."""
    chunks: list[KnowledgeChunk] = []
    for doc in docs:
        content = _structured_content(doc)
        parts = _split_content(content)
        for index, part in enumerate(parts):
            chunks.append(
                KnowledgeChunk(
                    id=f"{doc.id}::chunk-{index}",
                    document_id=doc.id,
                    title=doc.title,
                    category=doc.category,
                    content=part,
                    source=doc.source,
                    content_type=doc.content_type,
                    branch_ids=doc.branch_ids,
                    language=doc.language,
                    effective_from=doc.effective_from,
                    effective_to=doc.effective_to,
                    version=doc.version,
                    approved_by=doc.approved_by,
                    tags=doc.tags,
                )
            )
    return chunks


def _load_json_documents(path: Path, legacy: bool = False) -> list[KnowledgeDocument]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    items = raw if isinstance(raw, list) else raw.get("documents", [])
    docs: list[KnowledgeDocument] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        doc = _normalize_document(item, legacy=legacy)
        if doc:
            docs.append(doc)
    return docs


def _normalize_document(item: dict[str, Any], legacy: bool = False) -> KnowledgeDocument | None:
    content = str(item.get("content", "")).strip()
    title = str(item.get("title", "")).strip()
    doc_id = str(item.get("id", "")).strip()
    if not content or not title or not doc_id:
        return None

    branch_ids = item.get("branchIds") or item.get("branch_ids") or ["default"]
    if isinstance(branch_ids, str):
        branch_ids = [branch_ids]

    tags = item.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]

    return KnowledgeDocument(
        id=doc_id if not legacy else f"legacy-{doc_id}",
        title=title,
        category=str(item.get("category", "General SOP")),
        content=content,
        source=str(item.get("source", "Branch SOP Manual")),
        content_type=str(item.get("contentType", item.get("content_type", "legacy_sop" if legacy else "sop"))),
        branch_ids=tuple(str(branch).strip() for branch in branch_ids if str(branch).strip()) or ("default",),
        language=str(item.get("language", "en-IN")),
        effective_from=item.get("effectiveFrom") or item.get("effective_from"),
        effective_to=item.get("effectiveTo") or item.get("effective_to"),
        version=item.get("version"),
        approved_by=item.get("approvedBy") or item.get("approved_by"),
        tags=tuple(str(tag).strip() for tag in tags if str(tag).strip()),
        structured_facts=item.get("structuredFacts") or item.get("structured_facts"),
    )


def _structured_content(doc: KnowledgeDocument) -> str:
    # The approved prose already carries the customer-facing facts. Structured
    # facts stay available on the source document for future tools, but keeping
    # retrieval chunks prose-first prevents answers from starting with raw JSON.
    return doc.content


def _split_content(content: str, max_chars: int = 1200) -> list[str]:
    normalized = re.sub(r"\s+", " ", content).strip()
    if len(normalized) <= max_chars:
        return [normalized]

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks
