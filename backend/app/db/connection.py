"""Centralized async MongoDB connection manager.

Provides a single shared Motor client with connection pooling,
startup health check, index creation, and graceful shutdown.
"""

import logging

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import ConfigurationError, PyMongoError, ServerSelectionTimeoutError

from ..core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_mongo_available: bool = False


def get_client() -> AsyncIOMotorClient:
    """Return (or create) the shared Motor client."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=2000,
            maxPoolSize=10,
            minPoolSize=1,
            tlsCAFile=certifi.where(),
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """Return the application database handle."""
    global _db
    if _db is None:
        _db = get_client()[settings.mongodb_db]
    return _db


def is_mongo_available() -> bool:
    """Check if MongoDB was reachable at startup."""
    return _mongo_available


async def ensure_indexes() -> None:
    """Create all required indexes and verify MongoDB connectivity."""
    global _mongo_available

    try:
        db = get_db()
        await get_client().admin.command("ping")
        _mongo_available = True
        logger.info("MongoDB connected: %s/%s", settings.mongodb_uri, settings.mongodb_db)
    except (ConfigurationError, PyMongoError, ServerSelectionTimeoutError) as exc:
        _mongo_available = False
        logger.warning("MongoDB unavailable — using in-memory fallback: %s", exc)
        return

    # ── users ─────────────────────────────────────────────────────────────
    await db.users.create_index([("username", ASCENDING)], unique=True)
    await db.users.create_index([("employee_id", ASCENDING)])

    # ── sessions ──────────────────────────────────────────────────────────
    await db.sessions.create_index([("session_id", ASCENDING)], unique=True)
    await db.sessions.create_index([("staff_username", ASCENDING)])
    await db.sessions.create_index([("started_at", DESCENDING)])
    await db.sessions.create_index([("branch", ASCENDING), ("started_at", DESCENDING)])

    # ── session_summaries ─────────────────────────────────────────────────
    await db.session_summaries.create_index([("session_id", ASCENDING)], unique=True)
    await db.session_summaries.create_index([("timestamp", DESCENDING)])
    await db.session_summaries.create_index([("summary.entities.pan", ASCENDING)])
    await db.session_summaries.create_index([("summary.entities.customerName", ASCENDING)])

    # ── transcripts ───────────────────────────────────────────────────────
    await db.transcripts.create_index([("session_id", ASCENDING), ("timestamp", ASCENDING)])

    # ── compliance_events ─────────────────────────────────────────────────
    await db.compliance_events.create_index([("session_id", ASCENDING)])
    await db.compliance_events.create_index([("severity", ASCENDING), ("timestamp", DESCENDING)])

    # ── form_submissions ──────────────────────────────────────────────────
    await db.form_submissions.create_index([("session_id", ASCENDING), ("form_type", ASCENDING)])

    # ── knowledge_audit ───────────────────────────────────────────────────
    await db.knowledge_audit.create_index([("documentId", ASCENDING), ("version", ASCENDING)])

    logger.info("All MongoDB indexes created successfully")


async def close_client() -> None:
    """Gracefully close the Motor client on shutdown."""
    global _client, _db, _mongo_available
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        _mongo_available = False
        logger.info("MongoDB client closed")
