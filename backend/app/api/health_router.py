"""Operational health endpoints for local and hosted smoke checks."""

from __future__ import annotations

import httpx
from fastapi import APIRouter

from ..core.config import settings
from ..db.connection import get_client, is_mongo_available
from ..services.kb_loader import chunk_documents, load_knowledge_documents

router = APIRouter(tags=["health"])


def _kb_status() -> dict:
    docs = load_knowledge_documents()
    chunks = chunk_documents(docs)
    return {
        "status": "ok" if chunks else "degraded",
        "documents": len(docs),
        "chunks": len(chunks),
        "dataDir": settings.kb_data_dir,
    }


async def _db_status() -> dict:
    try:
        await get_client().admin.command("ping")
        return {"status": "ok", "database": settings.mongodb_db}
    except Exception as exc:
        return {
            "status": "degraded",
            "database": settings.mongodb_db,
            "message": str(exc),
        }


@router.get("/health")
async def health() -> dict:
    kb = _kb_status()
    db_status = "ok" if is_mongo_available() else "degraded"
    overall = "ok" if kb["status"] == "ok" else "degraded"
    return {
        "status": overall,
        "db": db_status,
        "kb": kb,
        "sarvam": "configured" if settings.sarvam_api_key else "missing_key",
    }


@router.get("/api/health")
async def api_health() -> dict:
    return await health()


@router.get("/api/health/db")
async def db_health() -> dict:
    return await _db_status()


@router.get("/api/health/sarvam")
async def sarvam_health() -> dict:
    if not settings.sarvam_api_key:
        return {"status": "degraded", "configured": False, "message": "SARVAM_API_KEY is not set"}

    try:
        async with httpx.AsyncClient(timeout=4) as client:
            response = await client.get("https://api.sarvam.ai")
        reachable = response.status_code < 500
    except Exception as exc:
        return {
            "status": "degraded",
            "configured": True,
            "reachable": False,
            "message": str(exc),
        }

    return {
        "status": "ok" if reachable else "degraded",
        "configured": True,
        "reachable": reachable,
    }
