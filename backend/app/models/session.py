from pydantic import BaseModel, Field


class TranscriptItem(BaseModel):
    id: str
    speaker: str
    sourceLanguage: str
    originalText: str
    translatedText: str
    confidence: float = Field(ge=0, le=1)
    timestamp: str


class ComplianceAlert(BaseModel):
    severity: str  # "info" | "warning" | "block"
    message: str


class SopCitation(BaseModel):
    documentId: str
    chunkId: str
    title: str
    source: str
    category: str = ""
    branchId: str | None = None
    effectiveFrom: str | None = None
    effectiveTo: str | None = None
    version: str | None = None
    score: float = 0.0
    excerpt: str = ""


class SopResult(BaseModel):
    title: str
    answer: str
    source: str
    citations: list[SopCitation] = []
    confidence: float = 0.0
    effectiveFrom: str | None = None
    effectiveTo: str | None = None
    branchId: str | None = None
    requiresStaffVerification: bool = False


class SentimentResult(BaseModel):
    sentiment: str  # "negative" | "neutral" | "positive"
    score: float = Field(ge=0, le=1)


class SessionSummary(BaseModel):
    session_id: str
    timestamp: str
    language: str
    entities: dict = {}
    english: list[str] = []
    customerLanguage: list[str] = []
