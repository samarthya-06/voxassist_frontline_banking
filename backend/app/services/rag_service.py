"""Grounded answer generation over trusted banking knowledge."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable

from ..core.config import settings
from ..models.session import SopCitation, SopResult
from .vector_store import RankedChunk, sop_store

logger = logging.getLogger(__name__)

LlmFn = Callable[[str, str], Awaitable[str]]
TranslateFn = Callable[[str, str, str], Awaitable[str]]


class BankingRagService:
    """Retrieve trusted bank context and optionally ask Sarvam to phrase it."""

    async def answer(
        self,
        query: str,
        *,
        branch_id: str | None = None,
        language_code: str = "en-IN",
        llm: LlmFn | None = None,
        translate: TranslateFn | None = None,
    ) -> SopResult:
        matches = await sop_store.retrieve(query, branch_id=branch_id, top_k=settings.rag_top_k)
        if not matches or matches[0].score < settings.rag_min_confidence:
            answer = "I could not find an approved bank policy for this query. Please check the latest approved circular or CBS rule before advising the customer."
            if translate and language_code != "en-IN":
                answer = await translate(answer, "en-IN", language_code)
            return SopResult(
                title="No approved policy found",
                answer=answer,
                source="Trusted KB",
                confidence=0.0,
                requiresStaffVerification=True,
            )

        generated = ""
        if llm:
            generated = await self._generate_answer(query, matches, language_code, llm)

        if not generated:
            generated = self._fallback_answer(matches)
            if translate and language_code != "en-IN":
                generated = await translate(generated, "en-IN", language_code)

        top = matches[0]
        citations = [_citation(match) for match in matches]
        return SopResult(
            title=top.chunk.title,
            answer=generated,
            source=top.chunk.source,
            citations=citations,
            confidence=round(top.score, 3),
            effectiveFrom=top.chunk.effective_from,
            effectiveTo=top.chunk.effective_to,
            branchId=_display_branch(top.chunk.branch_ids),
            requiresStaffVerification=top.score < 0.36,
        )

    async def _generate_answer(self, query: str, matches: list[RankedChunk], language_code: str, llm: LlmFn) -> str:
        context = "\n\n".join(
            (
                f"[{index}] Title: {match.chunk.title}\n"
                f"Source: {match.chunk.source}\n"
                f"Effective: {match.chunk.effective_from or 'not specified'} to {match.chunk.effective_to or 'current'}\n"
                f"Branch: {', '.join(match.chunk.branch_ids)}\n"
                f"Content: {match.chunk.content}"
            )
            for index, match in enumerate(matches, start=1)
        )
        prompt = (
            "Answer the banking query using ONLY the trusted context below. "
            "Do not use outside knowledge. If the context does not contain the answer, say an approved policy was not found. "
            "Preserve rates, fees, document names, penalties, timelines, and eligibility exactly. "
            "IMPORTANT: Keep the answer SHORT — maximum 3-4 sentences, under 400 characters. "
            "This answer will be spoken aloud, so be concise and conversational. "
            f"Respond in language code {language_code}. "
            "Return ONLY valid JSON: {\"answer\": \"...\"}.\n\n"
            f"Query: {query}\n\nTrusted context:\n{context}"
        )
        system = "You are a grounded RAG banking assistant. You must answer only from provided context. Keep answers SHORT and conversational."
        try:
            raw = await llm(prompt, system)
            raw = _strip_json_fence(raw)
            # Try JSON parse first
            try:
                data = json.loads(raw)
                return str(data.get("answer", "")).strip()
            except json.JSONDecodeError:
                # Fallback: try to extract answer from malformed JSON
                match = re.search(r'"answer"\s*:\s*"(.*?)(?:"|$)', raw, re.DOTALL)
                if match:
                    return match.group(1).strip()
                # Last resort: just use the raw text if it's not empty
                cleaned = raw.strip().strip('"').strip()
                if cleaned and len(cleaned) > 10:
                    return cleaned
                return ""
        except Exception as e:
            logger.error("RAG answer generation failed: %s", e)
            return ""

    def _fallback_answer(self, matches: list[RankedChunk]) -> str:
        top = matches[0].chunk
        if len(matches) == 1:
            return top.content
        support = " ".join(match.chunk.content for match in matches[1:3] if match.score >= settings.rag_min_confidence)
        if support:
            return f"{top.content}\n\nRelated policy context: {support}"
        return top.content


def _strip_json_fence(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return text


rag_service = BankingRagService()


def _citation(match: RankedChunk) -> SopCitation:
    chunk = match.chunk
    return SopCitation(
        documentId=chunk.document_id,
        chunkId=chunk.id,
        title=chunk.title,
        source=chunk.source,
        category=chunk.category,
        branchId=_display_branch(chunk.branch_ids),
        effectiveFrom=chunk.effective_from,
        effectiveTo=chunk.effective_to,
        version=chunk.version,
        score=round(match.score, 3),
        excerpt=chunk.content[:280],
    )


def _display_branch(branch_ids: tuple[str, ...]) -> str | None:
    if len(branch_ids) == 1 and branch_ids[0].lower() == "default":
        return "default"
    return ", ".join(branch_ids)
