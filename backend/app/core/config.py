import json
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so the path is correct regardless of
# where uvicorn / the test runner is launched from.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".env"
_ENV_FILE_BACKEND = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    sarvam_api_key: str | None = None
    gemini_api_key: str | None = None
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "voxassist"
    chroma_persist_dir: str = ".chroma"
    kb_data_dir: str = "backend/data/kb"
    default_branch_id: str = "default"
    rag_top_k: int = 5
    rag_min_confidence: float = 0.18
    rag_use_llm: bool = False
    ai_fast_mode: bool = True
    ai_async_tts: bool = True
    seed_demo_data: bool = False
    allowed_origins: list[str] = ["http://localhost:5173"]
    jwt_secret: str = "voxassist-dev-secret-change-in-production"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    # Fallback if JSON is malformed
                    pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    model_config = SettingsConfigDict(
        # Try both the project root and the backend/ folder
        env_file=[str(_ENV_FILE), str(_ENV_FILE_BACKEND)],
        env_file_encoding="utf-8",
    )


settings = Settings()
