"""Database package — centralized MongoDB connection."""

from .connection import get_db, get_client, close_client

__all__ = ["get_db", "get_client", "close_client"]
