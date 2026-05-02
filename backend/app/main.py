from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.auth import auth_router
from .api.routes import router
from .core.config import settings
from .db.connection import close_client
from .services.repositories import repository

app = FastAPI(title="VoxAssist Frontline API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)


@app.on_event("startup")
async def startup() -> None:
    await repository.ensure_database()


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_client()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
