"""Persistent SOP vector store with deterministic local embeddings."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..core.config import settings
from ..models.session import SopCitation, SopResult
from .kb_loader import KnowledgeChunk, chunk_documents, load_knowledge_documents

logger = logging.getLogger(__name__)

EMBED_DIM = 384
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for", "from", "how", "i", "in", "is",
    "it", "me", "my", "of", "on", "or", "our", "please", "should", "the", "to", "what", "when", "with",
    "you", "your", "hai", "hain", "kya", "mala", "mujhe",
}
SYNONYMS = {
    "fd": ["fixed", "deposit", "term"],
    "rate": ["interest", "rates"],
    "rates": ["interest", "rate"],
    "charge": ["fee", "fees"],
    "charges": ["fee", "fees"],
    "docs": ["documents", "requirements"],
    "document": ["documents", "requirements"],
    "kyc": ["aadhaar", "pan", "identity"],
}


@dataclass(frozen=True)
class RankedChunk:
    chunk: KnowledgeChunk
    score: float


class SopVectorStore:
    """ChromaDB retrieval with a deterministic lexical fallback."""

    def __init__(self) -> None:
        self.persist_dir = Path(settings.chroma_persist_dir)
        self._collection = None
        self._chunks: list[KnowledgeChunk] = []
        self._loaded = False

    def _load_chunks(self) -> list[KnowledgeChunk]:
        if not self._chunks:
            self._chunks = chunk_documents(load_knowledge_documents())
        return self._chunks

    def _ensure_collection(self):
        if self._loaded:
            return self._collection

        chunks = self._load_chunks()
        try:
            import chromadb

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.persist_dir))
            self._collection = client.get_or_create_collection(
                name="banking_knowledge",
                metadata={"hnsw:space": "cosine"},
            )
            if chunks:
                current_ids = {chunk.id for chunk in chunks}
                existing = self._collection.get(include=[])
                stale_ids = [chunk_id for chunk_id in existing.get("ids", []) if chunk_id not in current_ids]
                if stale_ids:
                    self._collection.delete(ids=stale_ids)
                self._collection.upsert(
                    ids=[chunk.id for chunk in chunks],
                    documents=[chunk.content for chunk in chunks],
                    embeddings=[_embed(_index_text(chunk)) for chunk in chunks],
                    metadatas=[_metadata(chunk) for chunk in chunks],
                )
            logger.info("Loaded %d trusted KB chunks into ChromaDB", len(chunks))
        except Exception as e:
            logger.warning("ChromaDB init failed, using local retrieval fallback: %s", e)
            self._collection = None

        self._loaded = True
        return self._collection

    async def retrieve(self, query: str, branch_id: str | None = None, top_k: int | None = None) -> list[RankedChunk]:
        """Return ranked KB chunks filtered by date and branch specificity."""
        if not query.strip():
            return []

        top_k = top_k or settings.rag_top_k
        branch = _normalize_branch(branch_id or settings.default_branch_id)
        chunks_by_id = {chunk.id: chunk for chunk in self._load_chunks()}
        collection = self._ensure_collection()

        ranked: list[RankedChunk] = []
        if collection:
            try:
                # Cap n_results to collection size to prevent HNSW crash
                collection_count = collection.count()
                n_results = min(max(top_k * 4, 8), max(collection_count, 1))
                results = collection.query(
                    query_embeddings=[_embed(query)],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"],
                )
                ids = results.get("ids", [[]])[0]
                distances = results.get("distances", [[]])[0]
                for chunk_id, distance in zip(ids, distances):
                    chunk = chunks_by_id.get(chunk_id)
                    if not chunk or not _is_active(chunk) or not _branch_allowed(chunk, branch):
                        continue
                    score = max(0.0, 1.0 - float(distance))
                    score += _branch_boost(chunk, branch)
                    ranked.append(RankedChunk(chunk=chunk, score=min(score, 1.0)))
            except Exception as e:
                logger.error("ChromaDB search failed: %s", e)

        if not ranked:
            ranked = self._fallback_rank(query, branch)

        return sorted(ranked, key=lambda item: item.score, reverse=True)[:top_k]

    async def search(self, query: str, branch_id: str | None = None) -> SopResult:
        """Compatibility helper for existing SOP search callers."""
        matches = await self.retrieve(query, branch_id=branch_id, top_k=settings.rag_top_k)
        if not matches or matches[0].score < settings.rag_min_confidence:
            return SopResult(
                title="No approved policy found",
                answer="I could not find a trusted bank policy for this query. Please check the latest approved circular or CBS rule before advising the customer.",
                source="Trusted KB",
                confidence=0.0,
                requiresStaffVerification=True,
            )

        top = matches[0]
        citations = [_citation(match) for match in matches]
        return SopResult(
            title=top.chunk.title,
            answer=top.chunk.content,
            source=top.chunk.source,
            citations=citations,
            confidence=round(top.score, 3),
            effectiveFrom=top.chunk.effective_from,
            effectiveTo=top.chunk.effective_to,
            branchId=_display_branch(top.chunk),
            requiresStaffVerification=top.score < 0.36,
        )

    def _fallback_rank(self, query: str, branch: str) -> list[RankedChunk]:
        query_tokens = _tokenize(_expand_query(query))
        if not query_tokens:
            return []

        ranked: list[RankedChunk] = []
        for chunk in self._load_chunks():
            if not _is_active(chunk) or not _branch_allowed(chunk, branch):
                continue

            text_tokens = _tokenize(_index_text(chunk))
            overlap = query_tokens & text_tokens
            if not overlap:
                continue

            title_tokens = _tokenize(chunk.title)
            tag_tokens = _tokenize(" ".join(chunk.tags))
            category_tokens = _tokenize(chunk.category)
            score = len(overlap) / max(len(query_tokens), 1)
            score += 0.16 * len(query_tokens & title_tokens)
            score += 0.12 * len(query_tokens & tag_tokens)
            score += 0.08 * len(query_tokens & category_tokens)
            score += _branch_boost(chunk, branch)
            ranked.append(RankedChunk(chunk=chunk, score=min(score, 1.0)))

        return sorted(ranked, key=lambda item: item.score, reverse=True)


def _metadata(chunk: KnowledgeChunk) -> dict:
    return {
        "documentId": chunk.document_id,
        "title": chunk.title,
        "source": chunk.source,
        "category": chunk.category,
        "contentType": chunk.content_type,
        "branchIds": "|".join(chunk.branch_ids),
        "branchKeys": "|".join(_normalize_branch(branch) for branch in chunk.branch_ids),
        "language": chunk.language,
        "effectiveFrom": chunk.effective_from or "",
        "effectiveTo": chunk.effective_to or "",
        "version": chunk.version or "",
        "approvedBy": chunk.approved_by or "",
        "tags": "|".join(chunk.tags),
    }


def _citation(match: RankedChunk) -> SopCitation:
    chunk = match.chunk
    return SopCitation(
        documentId=chunk.document_id,
        chunkId=chunk.id,
        title=chunk.title,
        source=chunk.source,
        category=chunk.category,
        branchId=_display_branch(chunk),
        effectiveFrom=chunk.effective_from,
        effectiveTo=chunk.effective_to,
        version=chunk.version,
        score=round(match.score, 3),
        excerpt=chunk.content[:280],
    )


def _index_text(chunk: KnowledgeChunk) -> str:
    return " ".join([chunk.title, chunk.category, " ".join(chunk.tags), chunk.content])


def _tokenize(text: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[\w]+", text.lower(), flags=re.UNICODE)
        if len(token) > 1 and token not in STOPWORDS
    }
    return tokens


def _expand_query(query: str) -> str:
    tokens = re.findall(r"[\w]+", query.lower(), flags=re.UNICODE)
    expansions: list[str] = [query]
    for token in tokens:
        expansions.extend(SYNONYMS.get(token, []))
    return " ".join(expansions)


def _embed(text: str) -> list[float]:
    vector = [0.0] * EMBED_DIM
    for token in _tokenize(_expand_query(text)):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % EMBED_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _normalize_branch(branch_id: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (branch_id or "default").lower()).strip("-") or "default"


def _branch_keys(chunk: KnowledgeChunk) -> set[str]:
    return {_normalize_branch(branch) for branch in chunk.branch_ids}


def _branch_allowed(chunk: KnowledgeChunk, branch: str) -> bool:
    keys = _branch_keys(chunk)
    return "default" in keys or branch in keys


def _branch_boost(chunk: KnowledgeChunk, branch: str) -> float:
    keys = _branch_keys(chunk)
    if branch != "default" and branch in keys:
        return 0.18
    return 0.0


def _display_branch(chunk: KnowledgeChunk) -> str | None:
    if len(chunk.branch_ids) == 1 and _normalize_branch(chunk.branch_ids[0]) == "default":
        return "default"
    return ", ".join(chunk.branch_ids)


def _is_active(chunk: KnowledgeChunk) -> bool:
    today = date.today().isoformat()
    if chunk.effective_from and chunk.effective_from > today:
        return False
    if chunk.effective_to and chunk.effective_to < today:
        return False
    return True


sop_store = SopVectorStore()
