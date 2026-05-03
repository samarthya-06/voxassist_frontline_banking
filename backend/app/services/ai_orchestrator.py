"""AI Orchestrator — Sarvam STT/TTS + Gemini translation, entities, compliance, summarization."""

import asyncio
import base64
import io
import json
import logging
import re
from datetime import datetime
from uuid import uuid4


import httpx

from ..core.config import settings
from ..models.forms import (
    FORM_REGISTRY,
    FormDefinition,
    FormSession,
    FormType,
    get_all_form_types,
    get_form_definition,
)
from ..models.session import ComplianceAlert, SentimentResult, SopResult, TranscriptItem
from .rag_service import rag_service

logger = logging.getLogger(__name__)

# ── Sarvam API base ──────────────────────────────────────────────────────────
SARVAM_BASE = "https://api.sarvam.ai"

LANGUAGE_NAMES = {
    "hi-IN": "Hindi",
    "mr-IN": "Marathi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "kn-IN": "Kannada",
    "gu-IN": "Gujarati",
    "bn-IN": "Bengali",
    "ml-IN": "Malayalam",
    "pa-IN": "Punjabi",
    "en-IN": "English",
}

FORM_INTENT_KEYWORDS = {
    "fd_application": ["open fd", "start fd", "apply fd", "fd form", "fixed deposit open", "fixed deposit apply", "fd application", "एफडी उघड", "एफडी करायचा", "fd करायचा"],
    "account_opening": [
        "open account", "new account", "account open", "open a bank", "start account",
        "account application", "खाते उघड", "खाते काढ", "अकाउंट उघड", "खाते उघडायचे",
    ],
    "loan_application": ["apply loan", "loan apply", "loan application", "loan form", "लोन अर्ज", "कर्ज अर्ज"],
    "kyc": ["kyc update", "kyc form", "update kyc", "kyc verification", "केवायसी अपडेट"],
    "card_application": ["apply card", "card application", "new card apply", "card form", "कार्ड अर्ज"],
}

FORM_TITLES = {
    "fd_application": "Fixed Deposit Application",
    "account_opening": "Account Opening",
    "loan_application": "Loan Application",
    "kyc": "KYC Verification",
    "card_application": "Card Application",
}

AFFIRMATIVE_TERMS = {
    "yes", "yeah", "yep", "sure", "ok", "okay", "start", "proceed", "continue",
    "करा", "हो", "होय", "चालू", "शुरू", "हाँ", "हा", "ji", "haan",
}

NEGATIVE_TERMS = {
    "no", "nope", "not now", "later", "cancel", "stop", "don't", "dont", "do not",
    "not interested", "i don't want", "i do not want", "नको", "नकोय", "नाही", "मत", "रद्द",
}

INFO_REQUEST_TERMS = {
    "document", "documents", "doc", "docs", "required", "requirement", "requirements",
    "need", "needed", "bring", "interest", "rate", "rates", "charges", "fee", "fees",
    "eligibility", "explain", "tell", "information", "info", "what", "how",
    "कागदपत्र", "कागदपत्रे", "डॉक्युमेंट", "डॉक्युमेंट्स", "लाग", "लागतील", "हवे",
    "काय", "कसा", "कशी", "माहिती", "व्याज", "दर", "चार्ज", "फी",
}

NEGATIVE_SENTIMENT_TERMS = {
    "angry", "upset", "frustrated", "bad", "worst", "complaint", "complain", "problem", "issue",
    "delay", "waiting", "नाराज", "राग", "तक्रार", "समस्या", "प्रॉब्लेम", "परेशान", "गुस्सा",
}

POSITIVE_SENTIMENT_TERMS = {"thanks", "thank you", "good", "great", "helpful", "धन्यवाद", "छान", "ठीक"}

PRODUCT_EXPLAINERS = {
    "fd_application": (
        "A fixed deposit lets you place a lump sum for a chosen tenure and earn a fixed rate. "
        "From the configured branch rate table, regular FD rates are typically 3.50% to 7.10% per annum, "
        "and senior citizens may get an additional 0.50%, subject to bank policy and tenure. "
        "You will usually need an existing savings account, PAN, Aadhaar or valid KYC, deposit amount, tenure, "
        "interest payout choice, and nominee details. Interest can be paid monthly, quarterly, or reinvested at maturity. "
        "Premature withdrawal may reduce the applicable rate and may attract a penalty, and TDS can apply as per tax rules. "
        "Would you like me to start the Fixed Deposit Application form now?"
    ),
    "account_opening": (
        "To open a bank account, you usually need PAN card, Aadhaar or another valid identity and address proof, "
        "mobile number, email if available, one passport-size photo if the branch requires it, nominee details, "
        "and the initial deposit amount if that account type has a minimum opening balance. "
        "The staff will verify KYC and explain charges or minimum balance rules before submission. "
        "Would you like me to start the Account Opening form now?"
    ),
    "loan_application": (
        "For a loan enquiry, we first collect income, employment type, loan amount, purpose, and existing EMI details. "
        "Interest rate, processing fee, and approval depend on credit assessment, so approval must not be promised. "
        "Would you like me to start the Loan Application form now?"
    ),
    "kyc": (
        "For KYC verification or update, we collect identity, address, PAN, Aadhaar, phone, and supporting details. "
        "The staff must verify documents and complete required authentication. Would you like me to start the KYC form now?"
    ),
    "card_application": (
        "For a debit or credit card request, we collect name, PAN, registered mobile number, card type, billing address, "
        "delivery address, and any credit limit preference for credit cards. Would you like me to start the Card Application form now?"
    ),
}

PRODUCT_EXPLAINERS_MR = {
    "fd_application": (
        "फिक्स्ड डिपॉझिटमध्ये तुम्ही ठराविक रक्कम ठराविक कालावधीसाठी ठेवता आणि निश्चित व्याज मिळते. "
        "या डेमोमधील शाखा दरांनुसार सामान्य FD दर साधारण 3.50% ते 7.10% वार्षिक असू शकतात, "
        "आणि ज्येष्ठ नागरिकांना धोरणानुसार अतिरिक्त 0.50% मिळू शकते. FD साठी साधारणपणे बचत खाते, PAN, Aadhaar किंवा वैध KYC, "
        "ठेव रक्कम, कालावधी, व्याज कसे घ्यायचे आणि nominee तपशील लागतात. Premature withdrawal केल्यास दर कमी होऊ शकतो, penalty लागू होऊ शकते, "
        "आणि कर नियमानुसार TDS लागू होऊ शकतो. आपण FD application form भरायला सुरुवात करू का?"
    ),
    "account_opening": (
        "बँक खाते उघडण्यासाठी साधारणपणे PAN card, Aadhaar किंवा इतर वैध ओळख आणि पत्त्याचा पुरावा, mobile number, email असल्यास email, "
        "शाखेला गरज असल्यास एक passport-size photo, nominee details आणि account type नुसार initial deposit amount लागते. "
        "Staff KYC verify करेल आणि minimum balance किंवा charges आधी समजावून सांगेल. आपण Account Opening form भरायला सुरुवात करू का?"
    ),
    "loan_application": (
        "Loan साठी आम्ही income, employment type, loan amount, purpose आणि existing EMI details घेतो. "
        "Interest rate, processing fee आणि approval credit assessment वर अवलंबून असते, म्हणून approval guarantee देता येत नाही. "
        "आपण Loan Application form भरायला सुरुवात करू का?"
    ),
    "kyc": (
        "KYC verification किंवा update साठी ओळख पुरावा, address proof, PAN, Aadhaar, phone number आणि supporting details लागतात. "
        "Staff documents verify करून required authentication पूर्ण करेल. आपण KYC form भरायला सुरुवात करू का?"
    ),
    "card_application": (
        "Debit किंवा Credit card request साठी card वर छापायचे नाव, PAN, registered mobile number, card type, billing address, delivery address "
        "आणि credit card असल्यास preferred credit limit लागते. आपण Card Application form भरायला सुरुवात करू का?"
    ),
}


def _truncate_for_tts(text: str, max_chars: int = 500) -> str:
    """Truncate text at sentence boundary for natural TTS playback."""
    if not text or len(text) <= max_chars:
        return text
    # Try to cut at sentence boundary (. । ! ?)
    truncated = text[:max_chars]
    # Find last sentence end
    for sep in ['. ', '। ', '? ', '! ', '\n']:
        last_pos = truncated.rfind(sep)
        if last_pos > max_chars * 0.4:  # At least 40% of text
            return truncated[:last_pos + 1].strip()
    # Fallback: cut at last space
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.4:
        return truncated[:last_space].strip()
    return truncated.strip()


class AIOrchestrator:
    """Provider boundary for STT, translation, entity extraction, RAG, and guardrails."""

    def __init__(self) -> None:
        self._http: httpx.AsyncClient | None = None
        self._gemini_model = None
        self.detected_language: str | None = None
        self.detected_language_code: str | None = None
        self.last_translated_text: str = ""
        self.last_language_code: str = "mr-IN"
        self.branch_id: str = settings.default_branch_id
        self.negative_streak: int = 0
        self.transcript_history: list[dict] = []
        # Form interview state
        self.form_session: FormSession | None = None
        self.pending_form_type: str | None = None
        self.awaiting_form_confirmation: bool = False

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=30)
        return self._http

    async def close(self) -> None:
        """Release per-session network resources."""
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()

    @property
    def sarvam_headers(self) -> dict:
        """Headers for JSON-bodied Sarvam endpoints (TTS, Chat)."""
        return {
            "api-subscription-key": settings.sarvam_api_key or "",
            "Content-Type": "application/json",
        }

    @property
    def sarvam_auth_headers(self) -> dict:
        """Headers for multipart Sarvam endpoints (e.g. STT). No Content-Type — httpx sets it."""
        return {"api-subscription-key": settings.sarvam_api_key or ""}

    # ── Sarvam: Speech-to-Text ───────────────────────────────────────────────
    async def _call_sarvam_stt(self, audio_bytes: bytes, language_code: str | None = None) -> dict:
        """POST audio to Sarvam saaras:v3 STT via multipart form-data.

        Returns {transcript, language_code, confidence}.
        """
        if not settings.sarvam_api_key:
            return {"transcript": None, "language_code": "mr-IN", "confidence": 0.0}

        try:
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            lang_code = language_code or self.detected_language_code or "hi-IN"
            data = {
                "model": "saaras:v3",
                "language_code": lang_code,
                "mode": "transcribe",
            }
            logger.info("Calling Sarvam STT with lang_code: %s", lang_code)
            resp = await self.http.post(
                f"{SARVAM_BASE}/speech-to-text",
                files=files,
                data=data,
                headers=self.sarvam_auth_headers,
            )
            if resp.status_code != 200:
                logger.error("Sarvam STT error response: %s", resp.text)
            resp.raise_for_status()
            result = resp.json()
            transcript = result.get("transcript", "")
            lang_code = result.get("language_code", "mr-IN")
            confidence = self._extract_stt_confidence(result)
            logger.info(
                "Sarvam STT result: lang=%s, confidence=%.2f, text=%s",
                lang_code,
                confidence,
                transcript[:80] if transcript else "(empty)",
            )
            return {"transcript": transcript or None, "language_code": lang_code, "confidence": confidence}
        except Exception as e:
            logger.error("Sarvam STT failed: %s", e)
            return {"transcript": None, "language_code": "mr-IN", "confidence": 0.0}

    def _normalize_confidence(self, value: object) -> float | None:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return None
        if score > 1:
            score = score / 100
        return max(0.0, min(1.0, score))

    def _extract_stt_confidence(self, result: dict) -> float:
        for key in ("confidence", "confidence_score", "transcript_confidence", "asr_confidence"):
            score = self._normalize_confidence(result.get(key))
            if score is not None:
                return score

        scores: list[float] = []
        for list_key in ("words", "word_timestamps", "tokens", "segments"):
            for item in result.get(list_key, []) or []:
                if not isinstance(item, dict):
                    continue
                for key in ("confidence", "confidence_score", "score"):
                    score = self._normalize_confidence(item.get(key))
                    if score is not None:
                        scores.append(score)
                        break

        if scores:
            return sum(scores) / len(scores)
        return 0.0

    def _language_info_from_code(self, lang_code: str | None) -> dict:
        code = lang_code or "mr-IN"
        return {"language": LANGUAGE_NAMES.get(code, "Hindi"), "code": code}

    def set_language(self, lang_code: str) -> dict:
        lang_info = self._language_info_from_code(lang_code)
        self.detected_language = lang_info["language"]
        self.detected_language_code = lang_info["code"]
        self.last_language_code = lang_info["code"]
        return lang_info

    def set_branch(self, branch_id: str | None) -> None:
        self.branch_id = branch_id or settings.default_branch_id

    # ── Sarvam: Text-to-Speech ───────────────────────────────────────────────
    async def _call_sarvam_tts(self, text: str, language_code: str) -> str | None:
        """POST to Sarvam bulbul:v2 TTS. Returns base64 audio string."""
        if not settings.sarvam_api_key:
            return None

        # Truncate to ~500 chars at a sentence boundary for natural speech
        tts_text = _truncate_for_tts(text, max_chars=500)

        try:
            resp = await self.http.post(
                f"{SARVAM_BASE}/text-to-speech",
                json={
                    "text": tts_text,
                    "target_language_code": language_code,
                    "speaker": "anushka",
                    "model": "bulbul:v2",
                },
                headers=self.sarvam_headers,
            )
            resp.raise_for_status()
            data = resp.json()
            # TTS returns {"audios": ["base64..."]}
            audios = data.get("audios", [])
            return audios[0] if audios else None
        except Exception as e:
            logger.error("Sarvam TTS failed: %s", e)
            return None

    async def build_assistant_message(self, text: str, language_code: str | None = None) -> dict:
        """Create a broadcastable assistant message with optional TTS audio."""
        lang_code = language_code or self.detected_language_code or "mr-IN"
        lang_name = LANGUAGE_NAMES.get(lang_code, "English")
        audio_b64 = None if settings.ai_async_tts else await self._call_sarvam_tts(text, lang_code)
        now = datetime.now().strftime("%H:%M")
        item = TranscriptItem(
            id=str(uuid4()),
            speaker="assistant",
            sourceLanguage=lang_name,
            originalText=text,
            translatedText=text,
            confidence=1.0,
            timestamp=now,
        )
        self.transcript_history.append(item.model_dump())
        self.last_translated_text = text
        self.last_language_code = lang_code
        payload = {
            "type": "transcript",
            "item": item.model_dump(),
            "entities": {},
            "actionChips": [],
        }
        if settings.ai_async_tts:
            payload["assistantTtsText"] = text
            payload["assistantTtsLanguageCode"] = lang_code
        else:
            payload["assistantAudio"] = audio_b64
        return payload

    async def build_tts_audio_message(self, text: str, language_code: str | None = None) -> dict:
        """Create a standalone TTS message for delayed audio playback."""
        lang_code = language_code or self.detected_language_code or "mr-IN"
        return {
            "type": "tts_audio",
            "audio_b64": await self._call_sarvam_tts(text, lang_code),
            "text": text,
        }

    async def start_customer_session(self) -> dict:
        """Greet the customer after the kiosk mic is pressed once."""
        lang_code = self.detected_language_code or "mr-IN"
        if lang_code.startswith("mr"):
            text = "शुभ सकाळ, आमच्या बँकेत आपले स्वागत आहे. आज मी आपली कशी मदत करू शकतो?"
        else:
            text = "Good morning, welcome to our bank. How can I help you today?"
        return await self.build_assistant_message(text, lang_code)

    # ── Sarvam: Text-to-Text Translation ─────────────────────────────────────
    async def _call_sarvam_translate(self, text: str, source_code: str, target_code: str = "en-IN") -> str:
        """Translate text using Sarvam's Translate API. Chunks long text to avoid 400 errors."""
        if not settings.sarvam_api_key or not text:
            return text

        # Sarvam translate has a ~900 char limit; chunk if needed
        max_chunk = 800
        if len(text) <= max_chunk:
            return await self._translate_chunk(text, source_code, target_code)

        # Split at sentence boundaries
        sentences = re.split(r'(?<=[.।!?\n])\s*', text)
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) > max_chunk and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}" if current else sentence
        if current.strip():
            chunks.append(current.strip())

        translated_parts = []
        for chunk in chunks:
            translated_parts.append(await self._translate_chunk(chunk, source_code, target_code))
        return " ".join(translated_parts)

    async def _translate_chunk(self, text: str, source_code: str, target_code: str) -> str:
        """Translate a single chunk of text."""
        try:
            resp = await self.http.post(
                f"{SARVAM_BASE}/translate",
                json={
                    "input": text[:900],
                    "source_language_code": source_code,
                    "target_language_code": target_code,
                    "model": "mayura:v1",
                },
                headers=self.sarvam_headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("translated_text", text)
        except Exception as e:
            logger.error("Sarvam translation failed: %s", e)
            return text

    # ── Sarvam: LLM (Chat) ───────────────────────────────────────────────────
    async def _call_sarvam_llm(self, prompt: str, system_prompt: str = "You are a helpful banking assistant.") -> str:
        """General purpose LLM call using Sarvam Chat API."""
        if not settings.sarvam_api_key:
            return ""

        try:
            resp = await self.http.post(
                f"{SARVAM_BASE}/v1/chat/completions",
                json={
                    "model": "sarvam-m",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                },
                headers=self.sarvam_headers,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # Robustly strip <think> blocks even if truncated
            original_content = content
            if "</think>" in content:
                content = content.split("</think>")[-1]
            elif "<think>" in content:
                content = content.split("<think>")[0]
            
            result = content.strip()
            if not result:
                # If everything was stripped (e.g. only reasoning), fallback to the original content
                result = original_content.replace("<think>", "").replace("</think>", "").strip()
            return result
        except Exception as e:
            logger.error("Sarvam LLM failed: %s", e)
            return ""

    # ── LLM: Entity Extraction ────────────────────────────────────────────
    async def _extract_entities(self, text: str) -> dict:
        """Extract banking entities from conversation text using Sarvam LLM."""
        fast_entities = self._fast_extract_entities(text)
        if settings.ai_fast_mode or not settings.sarvam_api_key:
            return fast_entities

        prompt = (
            "Extract banking entities from this customer conversation text. "
            "Return ONLY valid JSON with these keys (use empty string if not found): "
            "customerName, pan, phone, accountType, product, amount, cardLast4.\n\n"
            f"Text: {text}"
        )
        try:
            raw = await self._call_sarvam_llm(prompt, "Return only valid JSON.")
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            entities = json.loads(raw)
            return {**fast_entities, **{k: v for k, v in entities.items() if v}}
        except Exception:
            return fast_entities

    # ── LLM: Action Chip Suggestions ──────────────────────────────────────
    async def _suggest_actions(self, text: str) -> list[str]:
        """Suggest contextual action buttons for the bank teller using Sarvam LLM."""
        fast_actions = self._fast_suggest_actions(text)
        if settings.ai_fast_mode or not settings.sarvam_api_key:
            return fast_actions

        prompt = (
            "Given this banking customer conversation, suggest 2-4 quick action buttons "
            "for the bank teller. Return ONLY a JSON array of short action labels.\n\n"
            f"Text: {text}"
        )
        try:
            raw = await self._call_sarvam_llm(prompt, "Return only a JSON array of strings.")
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            actions = json.loads(raw)
            return actions if actions else fast_actions
        except Exception as e:
            logger.error("Sarvam action suggestion failed: %s", e)
            return fast_actions

    def _fast_extract_entities(self, text: str) -> dict:
        """Low-latency deterministic extraction for live UI responsiveness."""
        entities: dict = {}
        pan = re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", text.upper())
        if pan:
            entities["pan"] = pan.group(0)

        phone = re.search(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b", text)
        if phone:
            entities["phone"] = re.sub(r"\D", "", phone.group(0))[-10:]

        amount = re.search(r"(?:₹|rs\.?|inr)\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakh|lac|crore))?", text, flags=re.IGNORECASE)
        if amount:
            entities["amount"] = amount.group(0)

        last4 = re.search(r"(?:last\s*(?:four|4)|ending|ends?\s*with)\D*(\d{4})\b", text, flags=re.IGNORECASE)
        if last4:
            entities["cardLast4"] = last4.group(1)

        name = re.search(r"(?:my name is|i am|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})", text)
        if name:
            entities["customerName"] = name.group(1)

        lowered = text.lower()
        if "savings" in lowered or "saving" in lowered or "सेव्हिंग" in lowered:
            entities["accountType"] = "Savings"
        elif "current account" in lowered:
            entities["accountType"] = "Current"
        elif "salary" in lowered:
            entities["accountType"] = "Salary"

        if "fixed deposit" in lowered or re.search(r"\bfd\b", lowered) or "फिक्स" in lowered:
            entities["product"] = "Fixed Deposit"
        elif "personal loan" in lowered or "loan" in lowered or "कर्ज" in lowered:
            entities["product"] = "Loan"
        elif "credit card" in lowered:
            entities["product"] = "Credit Card"
        elif "debit card" in lowered or "card" in lowered:
            entities["product"] = "Card"
        elif "kyc" in lowered or "केवायसी" in lowered:
            entities["product"] = "KYC"
        return entities

    def _fast_suggest_actions(self, text: str) -> list[str]:
        lowered = text.lower()
        if "fixed deposit" in lowered or re.search(r"\bfd\b", lowered) or "interest" in lowered or "rate" in lowered or "व्याज" in lowered:
            return ["Show FD Rates", "Explain FD Documents", "Start Fixed Deposit Form"]
        if "open account" in lowered or "savings account" in lowered or "new account" in lowered or "खाते" in lowered:
            return ["Explain Account Documents", "Start Account Opening Form", "Check KYC Rules"]
        if "kyc" in lowered or "aadhaar" in lowered or "pan" in lowered or "address update" in lowered or "केवायसी" in lowered:
            return ["Check KYC Documents", "Start KYC Form", "Verify Identity"]
        if "lost" in lowered and "card" in lowered:
            return ["Block Card", "Read Card Charges", "Raise Dispute"]
        if "card" in lowered or "debit" in lowered or "credit" in lowered:
            return ["Read Card Charges", "Start Card Form", "Check Delivery Rules"]
        if "loan" in lowered or "कर्ज" in lowered:
            return ["Check Loan Eligibility", "Read Rate Disclosure", "Start Loan Application"]
        if "fee" in lowered or "fees" in lowered or "charge" in lowered or "charges" in lowered or "फी" in lowered:
            return ["Read Fee Disclosure", "Show Service Charges", "Check CBS"]
        return ["Search Policy", "Continue Conversation"]

    # ── Sarvam: Compliance Check ─────────────────────────────────────────────
    async def check_compliance(self, text: str) -> ComplianceAlert | None:
        """Check for mis-selling or compliance violations using Sarvam LLM."""
        keyword_alert = self._keyword_compliance(text)
        if keyword_alert or settings.ai_fast_mode or not settings.sarvam_api_key:
            return keyword_alert

        try:
            prompt = (
                "You are an RBI compliance checker for Indian bank staff conversations. "
                "Analyze this staff statement for compliance violations:\n"
                "- Guaranteed returns on mutual funds or market-linked products\n"
                "- Risk-free investment promises\n"
                "- Unauthorized fee waivers\n"
                "- Misleading product comparisons\n\n"
                "Return ONLY valid JSON: {\"compliant\": true/false, \"violation\": \"description or null\"}\n\n"
                f"Statement: {text}"
            )
            raw = await self._call_sarvam_llm(prompt, "Return only valid JSON.")
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            result = json.loads(raw)
            if not result.get("compliant", True):
                return ComplianceAlert(
                    severity="block",
                    message=result.get("violation", "Potential compliance violation detected."),
                )
            return None
        except Exception:
            return self._keyword_compliance(text)

    def _keyword_compliance(self, text: str) -> ComplianceAlert | None:
        """Keyword fallback when Gemini is unavailable."""
        restricted = ["guaranteed return", "risk free mutual fund", "no charges ever"]
        lowered = text.lower()
        if any(term in lowered for term in restricted):
            return ComplianceAlert(
                severity="block",
                message="Potential mis-selling phrase detected. Voice output is halted until the statement is corrected.",
            )
        return None

    # ── Sarvam: Sentiment Analysis ───────────────────────────────────────────
    async def _analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze customer sentiment for escalation detection using Sarvam LLM."""
        fast_sentiment = self._fast_sentiment(text)
        if settings.ai_fast_mode or not settings.sarvam_api_key:
            return fast_sentiment

        try:
            prompt = (
                "Analyze the sentiment of this banking customer statement. "
                "Return ONLY valid JSON: {\"sentiment\": \"negative\"|\"neutral\"|\"positive\", \"score\": 0.0-1.0} "
                "where 0.0 is most negative and 1.0 is most positive.\n\n"
                f"Text: {text}"
            )
            raw = await self._call_sarvam_llm(prompt, "Return only valid JSON.")
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)
            return SentimentResult(
                sentiment=data.get("sentiment", "neutral"),
                score=data.get("score", 0.5),
            )
        except Exception:
            return fast_sentiment

    def _fast_sentiment(self, text: str) -> SentimentResult:
        lowered = text.lower()
        if any(term in lowered for term in NEGATIVE_SENTIMENT_TERMS):
            return SentimentResult(sentiment="negative", score=0.22)
        if any(term in lowered for term in POSITIVE_SENTIMENT_TERMS):
            return SentimentResult(sentiment="positive", score=0.82)
        return SentimentResult(sentiment="neutral", score=0.55)

    # ── Sarvam: Summarize ────────────────────────────────────────────────────
    async def summarize(self, transcript: list[dict] | None = None) -> dict:
        """Generate bilingual session summary using Sarvam LLM."""
        history = transcript or self.transcript_history
        if not history:
            return self._demo_summary()

        try:
            conversation = "\n".join(
                f"[{t.get('speaker', 'unknown')}] {t.get('originalText', '')} → {t.get('translatedText', '')}"
                for t in history
            )
            lang = self.detected_language or "Marathi"
            prompt = (
                f"Summarize this banking conversation as 3-5 bullet points. "
                f"Provide the summary in two sections:\n"
                f"1. English bullet points\n"
                f"2. {lang} bullet points (same content translated)\n\n"
                f"Return ONLY valid JSON: {{\"english\": [\"...\"], \"customerLanguage\": [\"...\"]}}\n\n"
                f"Conversation:\n{conversation}"
            )
            raw = await self._call_sarvam_llm(prompt, "Return only valid JSON.")
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)
            return {
                "type": "summary",
                "english": data.get("english", []),
                "customerLanguage": data.get("customerLanguage", []),
            }
        except Exception as e:
            logger.error("Sarvam summarization failed: %s", e)
            return self._demo_summary()

    def _demo_summary(self) -> dict:
        return {
            "type": "summary",
            "english": [
                "Customer reported a lost credit card and requested immediate blocking.",
                "Staff must verify identity and last four card digits before confirming the block.",
                "Replacement card fee and dispute window should be disclosed in Marathi.",
            ],
            "customerLanguage": [
                "ग्राहकाने क्रेडिट कार्ड हरवल्याची माहिती दिली आणि ते ब्लॉक करण्याची विनंती केली.",
                "ब्लॉक करण्यापूर्वी ओळख आणि कार्डचे शेवटचे चार अंक तपासणे आवश्यक आहे.",
                "नवीन कार्ड शुल्क आणि व्यवहार तक्रार कालावधी मराठीत सांगावा.",
            ],
        }

    # ── Main Turn Processor ──────────────────────────────────────────────────
    async def process_audio_turn(self, audio: bytes, mode: str) -> dict:
        """Full pipeline: STT → translate → extract entities → suggest actions."""
        # 1. Speech-to-Text via Sarvam (Native Transcribe + auto language detection)
        stt_result = await self._call_sarvam_stt(audio, "en-IN" if mode == "staff" else None)

        lang_detected = None
        if self.detected_language is None:
            lang_detected = self._language_info_from_code(stt_result.get("language_code"))
            self.detected_language = lang_detected["language"]
            self.detected_language_code = lang_detected["code"]

        if not stt_result["transcript"]:
            if mode == "customer":
                lang_code = self.detected_language_code or "mr-IN"
                text = (
                    "मला नीट ऐकू आले नाही. कृपया पुन्हा सांगा, तुम्हाला कोणती बँक सेवा हवी आहे?"
                    if lang_code.startswith("mr")
                    else "I could not hear that clearly. Please tell me again which banking service you need."
                )
                payload = await self.build_assistant_message(text, lang_code)
                if lang_detected:
                    payload["languageDetected"] = lang_detected
                return payload
            return await self.process_demo_turn(mode, lang_detected=lang_detected)

        original_text = stt_result["transcript"]
        if mode == "customer" and self._is_echo_or_spam_text(original_text):
            lang_code = self.detected_language_code or stt_result.get("language_code") or "mr-IN"
            text = (
                "मला नीट ऐकू आले नाही. कृपया थोडक्यात पुन्हा सांगा, तुम्हाला कोणती बँक सेवा हवी आहे?"
                if lang_code.startswith("mr")
                else "I could not hear that clearly. Please briefly repeat which banking service you need."
            )
            payload = await self.build_assistant_message(text, lang_code)
            if lang_detected:
                payload["languageDetected"] = lang_detected
            return payload

        source_code = stt_result["language_code"]
        now = datetime.now().strftime("%H:%M")

        # 2. Translate via Sarvam (Text-to-Text)
        if mode == "customer" and source_code != "en-IN":
            translated = await self._call_sarvam_translate(original_text, source_code, "en-IN")
            speaker = "customer"
            language = self.detected_language or "Marathi"
        elif mode == "staff":
            # Staff speaks English, translate to customer's native language for display
            translated = await self._call_sarvam_translate(original_text, "en-IN", self.detected_language_code or "mr-IN")
            speaker = "staff"
            language = "English"
        else:
            translated = original_text
            speaker = "customer"
            language = "English"

        # Update last translated text for TTS replay
        self.last_translated_text = translated
        self.last_language_code = self.detected_language_code or "mr-IN"

        # 3. Extract entities from the English text
        # If customer spoke Marathi, entities come from the translation
        # If staff spoke English, entities come from the original
        english_text = translated if mode == "customer" else original_text

        # ── Parallel enrichment: entities + actions run concurrently ──
        entities_task = asyncio.create_task(self._extract_entities(english_text))
        chips_task = asyncio.create_task(self._suggest_actions(english_text))

        # 5. Sentiment analysis for escalation
        sentiment = None
        assistant_response_text = None
        assistant_audio_b64 = None

        if mode == "customer":
            # A. Sentiment (runs in parallel with entities + chips)
            sentiment_task = asyncio.create_task(self._analyze_sentiment(english_text))

            # B. Product/form intent flow. Explain first, then start only after consent.
            normalized = f"{original_text} {english_text}".lower()
            if self.awaiting_form_confirmation and self.pending_form_type:
                if self._is_affirmative(normalized):
                    assistant_response_text = await self._localized_text(
                        f"Great. I will start the {FORM_TITLES.get(self.pending_form_type, 'banking')} form now.",
                        self.detected_language_code or source_code,
                    )
                    result_auto_form = self.pending_form_type
                    self.awaiting_form_confirmation = False
                    self.pending_form_type = None
                elif self._is_negative(normalized):
                    assistant_response_text = await self._localized_text(
                        "No problem. Please tell me what else you would like help with.",
                        self.detected_language_code or source_code,
                    )
                    result_auto_form = None
                    self.awaiting_form_confirmation = False
                    self.pending_form_type = None
                elif self._is_info_request(normalized) or self._detect_form_intent(normalized):
                    intent_form = self._detect_form_intent(normalized) or self.pending_form_type
                    self.pending_form_type = intent_form
                    self.awaiting_form_confirmation = True
                    assistant_response_text = await self._localized_product_explanation(intent_form)
                    result_auto_form = None
                else:
                    assistant_response_text = await self._localized_text(
                        "Please say yes if you want me to start the form, or no if you want something else.",
                        self.detected_language_code or source_code,
                    )
                    result_auto_form = None
            else:
                intent_form = self._detect_form_intent(normalized)
                result_auto_form = None
                if intent_form:
                    self.pending_form_type = intent_form
                    self.awaiting_form_confirmation = True
                    assistant_response_text = await self._localized_product_explanation(intent_form)
                else:
                    # Always try RAG first for ANY customer question
                    rag_answer = await self._rag_customer_answer(english_text, self.detected_language_code or source_code)
                    if rag_answer and "could not find" not in rag_answer.lower() and "not found" not in rag_answer.lower() and len(rag_answer) > 10:
                        assistant_response_text = rag_answer
                    elif settings.ai_fast_mode:
                        assistant_response_text = await self._localized_text(
                            "I can help with account opening, fixed deposits, KYC, cards, loans, lockers, cheques, transfers, and other banking services. Please tell me what you need.",
                            self.detected_language_code or source_code,
                        )
                    else:
                        # RAG had no match — use LLM as a smart banking assistant
                        lang_code = self.detected_language_code or source_code
                        lang_name = self.detected_language or language or "Hindi"
                        prompt = (
                            f"Customer question: '{english_text}'\n"
                            f"Original language: {lang_name} ({lang_code})\n\n"
                            "You are a knowledgeable bank branch assistant. Answer this banking question "
                            "clearly, accurately, and helpfully in 2-3 sentences. Cover the key facts: "
                            "eligibility, documents needed, charges, timelines, or rules as applicable. "
                            "If you are not sure about specific rates or numbers, say 'please check with the branch staff for exact details'. "
                            f"Respond in {lang_name} language. Be warm and professional."
                        )
                        assistant_response_text = await self._call_sarvam_llm(
                            prompt,
                            f"You are VoxAssist, an expert Indian bank branch assistant. "
                            f"You know about all banking services: accounts, FDs, RDs, loans, cards, lockers, "
                            f"cheques, NEFT/RTGS/IMPS, PPF, KYC, insurance, nominations, ATM services, "
                            f"net banking, and government schemes. Answer in {lang_name}."
                        )
                        if not assistant_response_text:
                            assistant_response_text = await self._localized_text(
                                "I can help with account opening, fixed deposits, KYC, cards, loans, lockers, cheques, transfers, and other banking services. Please tell me what you need.",
                                lang_code,
                            )

            # Await sentiment that was running in parallel
            sentiment = await sentiment_task
            if sentiment.score < 0.3:
                self.negative_streak += 1
            else:
                self.negative_streak = 0

            # C. Convert response to TTS. In async mode, text goes to the UI first
            # and the WebSocket route sends audio in a follow-up message.
            if not settings.ai_async_tts:
                assistant_audio_b64 = await self._call_sarvam_tts(assistant_response_text, self.detected_language_code or "mr-IN")
        else:
            result_auto_form = None

        # Await parallel enrichment tasks
        entities = await entities_task
        chips = await chips_task

        # Override chips for form confirmation flows
        if mode == "customer":
            normalized_check = f"{original_text} {english_text}".lower()
            if self.awaiting_form_confirmation and self.pending_form_type:
                chips = [f"Explain {FORM_TITLES.get(self.pending_form_type, 'Service')}", f"Start {FORM_TITLES.get(self.pending_form_type, 'Form')}"]
            elif self.pending_form_type and result_auto_form:
                chips = [f"Start {FORM_TITLES.get(result_auto_form, 'Form')}"]

        item = TranscriptItem(
            id=str(uuid4()),
            speaker=speaker,
            sourceLanguage=language,
            originalText=original_text,
            translatedText=translated,
            confidence=stt_result["confidence"],
            timestamp=now,
        )

        self.transcript_history.append(item.model_dump())

        result: dict = {
            "type": "transcript",
            "item": item.model_dump(),
            "entities": entities,
            "actionChips": chips,
        }

        if mode == "staff" and translated:
            result["translatedSpeechText"] = translated
            result["translatedSpeechLanguageCode"] = self.detected_language_code or "mr-IN"
            result["translatedSpeechAudience"] = "customer"

        if assistant_response_text:
            result["assistantResponse"] = assistant_response_text
            if settings.ai_async_tts:
                result["assistantTtsText"] = assistant_response_text
                result["assistantTtsLanguageCode"] = self.detected_language_code or "mr-IN"
            else:
                result["assistantAudio"] = assistant_audio_b64
        if result_auto_form:
            result["autoStartForm"] = result_auto_form

        if lang_detected:
            result["languageDetected"] = lang_detected
        if sentiment:
            result["sentiment"] = sentiment.model_dump()
        if self.negative_streak >= 3:
            result["escalation"] = {
                "type": "escalation_alert",
                "message": f"Customer frustration detected ({self.negative_streak} consecutive negative turns). Consider manager intervention.",
            }

        return result

    async def process_text_turn(self, text: str, mode: str, language_code: str | None = None) -> dict:
        """Process browser speech-recognition text when provider STT is unavailable."""
        if mode == "staff":
            source_code = "en-IN"
            language = "English"
            english_text = text
            translated_text = await self._call_sarvam_translate(
                text,
                "en-IN",
                self.detected_language_code or language_code or "mr-IN",
            )
        else:
            lang_info = self.set_language(language_code or self.detected_language_code or "mr-IN")
            source_code = lang_info["code"]
            language = lang_info["language"]
            if source_code != "en-IN":
                english_text = await self._call_sarvam_translate(text, source_code, "en-IN")
                if english_text == text:
                    english_text = self._english_hint_for_native_text(text)
            else:
                english_text = text
            translated_text = english_text

        now = datetime.now().strftime("%H:%M")
        speaker = "staff" if mode == "staff" else "customer"
        item = TranscriptItem(
            id=str(uuid4()),
            speaker=speaker,
            sourceLanguage=language if speaker == "customer" else "English",
            originalText=text,
            translatedText=translated_text,
            confidence=1.0,
            timestamp=now,
        )
        self.transcript_history.append(item.model_dump())

        # ── Parallel enrichment: entities + actions run concurrently ──
        entities_task = asyncio.create_task(self._extract_entities(english_text))
        chips_task = asyncio.create_task(self._suggest_actions(english_text))
        assistant_response_text = None
        assistant_audio_b64 = None
        result_auto_form = None

        if speaker == "customer":
            normalized = f"{text} {english_text}".lower()
            if self.awaiting_form_confirmation and self.pending_form_type:
                if self._is_affirmative(normalized):
                    assistant_response_text = await self._localized_text(
                        f"Great. I will start the {FORM_TITLES.get(self.pending_form_type, 'banking')} form now.",
                        source_code,
                    )
                    result_auto_form = self.pending_form_type
                    self.awaiting_form_confirmation = False
                    self.pending_form_type = None
                elif self._is_negative(normalized):
                    assistant_response_text = await self._localized_text(
                        "No problem. Please tell me what else you would like help with.",
                        source_code,
                    )
                    self.awaiting_form_confirmation = False
                    self.pending_form_type = None
                elif self._is_info_request(normalized) or self._detect_form_intent(normalized):
                    intent_form = self._detect_form_intent(normalized) or self.pending_form_type
                    self.pending_form_type = intent_form
                    self.awaiting_form_confirmation = True
                    assistant_response_text = await self._localized_product_explanation(intent_form)
                else:
                    assistant_response_text = await self._localized_text(
                        "Please say yes if you want me to start the form, or no if you want something else.",
                        source_code,
                    )
            else:
                intent_form = self._detect_form_intent(normalized)
                if intent_form:
                    self.pending_form_type = intent_form
                    self.awaiting_form_confirmation = True
                    assistant_response_text = await self._localized_product_explanation(intent_form)
                else:
                    # Always try RAG first for ANY customer question
                    rag_answer = await self._rag_customer_answer(english_text, source_code)
                    if rag_answer and "could not find" not in rag_answer.lower() and "not found" not in rag_answer.lower() and len(rag_answer) > 10:
                        assistant_response_text = rag_answer
                    elif settings.ai_fast_mode:
                        assistant_response_text = await self._localized_text(
                            "I can help with account opening, fixed deposits, KYC, cards, loans, lockers, cheques, transfers, and other banking services. Please tell me what you need.",
                            source_code,
                        )
                    else:
                        # RAG had no match — use LLM as a smart banking assistant
                        lang_name = self.detected_language or "Hindi"
                        prompt = (
                            f"Customer question: '{english_text}'\n"
                            f"Original language: {lang_name} ({source_code})\n\n"
                            "You are a knowledgeable bank branch assistant. Answer this banking question "
                            "clearly, accurately, and helpfully in 2-3 sentences. Cover the key facts: "
                            "eligibility, documents needed, charges, timelines, or rules as applicable. "
                            "If you are not sure about specific rates or numbers, say 'please check with the branch staff for exact details'. "
                            f"Respond in {lang_name} language. Be warm and professional."
                        )
                        assistant_response_text = await self._call_sarvam_llm(
                            prompt,
                            f"You are VoxAssist, an expert Indian bank branch assistant. "
                            f"You know about all banking services: accounts, FDs, RDs, loans, cards, lockers, "
                            f"cheques, NEFT/RTGS/IMPS, PPF, KYC, insurance, nominations, ATM services, "
                            f"net banking, and government schemes. Answer in {lang_name}."
                        )
                        if not assistant_response_text:
                            assistant_response_text = await self._localized_text(
                                "I can help with account opening, fixed deposits, KYC, cards, loans, lockers, cheques, transfers, and other banking services. Please tell me what you need.",
                                source_code,
                            )

            if not settings.ai_async_tts:
                assistant_audio_b64 = await self._call_sarvam_tts(assistant_response_text, source_code)

        # Await parallel enrichment tasks
        entities = await entities_task
        chips = await chips_task

        # Override chips for form confirmation flows
        if speaker == "customer":
            if self.awaiting_form_confirmation and self.pending_form_type:
                chips = [f"Explain {FORM_TITLES.get(self.pending_form_type, 'Service')}", f"Start {FORM_TITLES.get(self.pending_form_type, 'Form')}"]
            elif result_auto_form:
                chips = [f"Start {FORM_TITLES.get(result_auto_form, 'Form')}"]

        result: dict = {
            "type": "transcript",
            "item": item.model_dump(),
            "entities": entities,
            "actionChips": chips,
        }
        if speaker == "staff" and translated_text:
            result["translatedSpeechText"] = translated_text
            result["translatedSpeechLanguageCode"] = self.detected_language_code or language_code or "mr-IN"
            result["translatedSpeechAudience"] = "customer"
        if assistant_response_text:
            result["assistantResponse"] = assistant_response_text
            if settings.ai_async_tts:
                result["assistantTtsText"] = assistant_response_text
                result["assistantTtsLanguageCode"] = source_code
            else:
                result["assistantAudio"] = assistant_audio_b64
        if result_auto_form:
            result["autoStartForm"] = result_auto_form
        return result

    def _detect_form_intent(self, english_text: str) -> str | None:
        lowered = english_text.lower()
        for form_type, keywords in FORM_INTENT_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return form_type
        return None

    def _is_affirmative(self, english_text: str) -> bool:
        return self._has_confirmation_term(english_text, AFFIRMATIVE_TERMS)

    def _is_negative(self, english_text: str) -> bool:
        return self._has_confirmation_term(english_text, NEGATIVE_TERMS)

    def _has_confirmation_term(self, text: str, terms: set[str]) -> bool:
        normalized = re.sub(r"[^\w\s'\u0900-\u0D7F]", " ", text.lower(), flags=re.UNICODE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        padded = f" {normalized} "
        tokens = set(normalized.split())
        for term in terms:
            normalized_term = re.sub(r"[^\w\s'\u0900-\u0D7F]", " ", term.lower(), flags=re.UNICODE)
            normalized_term = re.sub(r"\s+", " ", normalized_term).strip()
            if not normalized_term:
                continue
            if " " in normalized_term:
                if f" {normalized_term} " in padded:
                    return True
            elif normalized_term in tokens:
                return True
        return False

    def _is_info_request(self, text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in INFO_REQUEST_TERMS)

    async def _localized_product_explanation(self, form_type: str) -> str:
        explanation = PRODUCT_EXPLAINERS.get(
            form_type,
            "I can help with this banking service. Would you like me to start the form now?",
        )
        lang_code = self.detected_language_code or "en-IN"
        rag_query = (
            f"Explain {FORM_TITLES.get(form_type, form_type)} including current rates, fees, "
            "eligibility, document requirements, branch rules, and whether the customer should start the form."
        )
        rag_answer = await self._rag_customer_answer(rag_query, lang_code)
        if rag_answer and "could not find" not in rag_answer.lower():
            return f"{rag_answer} {await self._localized_text('Would you like me to start the form now?', lang_code)}"
        if lang_code.startswith("mr"):
            return PRODUCT_EXPLAINERS_MR.get(form_type, explanation)
        if lang_code != "en-IN":
            translated = await self._call_sarvam_translate(explanation, "en-IN", lang_code)
            if translated and translated != explanation:
                return translated
        return explanation

    async def _rag_customer_answer(self, query: str, lang_code: str) -> str:
        result = await rag_service.answer(
            query,
            branch_id=self.branch_id,
            language_code=lang_code,
            llm=self._call_sarvam_llm if settings.rag_use_llm and settings.sarvam_api_key else None,
            translate=self._call_sarvam_translate if settings.sarvam_api_key else None,
        )
        return result.answer

    async def _localized_text(self, english_text: str, lang_code: str) -> str:
        if lang_code.startswith("mr"):
            fallbacks = {
                "Great. I will start": "ठीक आहे. मी form सुरू करतो.",
                "No problem": "काही हरकत नाही. आणखी कशासाठी मदत हवी ते सांगा.",
                "Please say yes": "Form सुरू करायचा असेल तर हो म्हणा, नाहीतर नाही म्हणा.",
                "I can help": "मी account opening, fixed deposit, KYC, cards, loans, locker, cheque, fund transfer आणि इतर बँकिंग सेवांसाठी मदत करू शकतो. तुम्हाला काय हवे ते सांगा.",
            }
            for prefix, translated in fallbacks.items():
                if english_text.startswith(prefix):
                    return translated
        if lang_code != "en-IN":
            translated = await self._call_sarvam_translate(english_text, "en-IN", lang_code)
            if translated and translated != english_text:
                return translated
        return english_text

    def _english_hint_for_native_text(self, text: str) -> str:
        lowered = text.lower()
        if self._detect_form_intent(lowered) == "account_opening":
            return "Customer is asking about account opening documents."
        if self._detect_form_intent(lowered) == "fd_application":
            return "Customer is asking about fixed deposit."
        return text

    def _is_echo_or_spam_text(self, text: str) -> bool:
        normalized = re.sub(r"[^\w\s]", " ", text.lower(), flags=re.UNICODE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            return True

        last_assistant = next(
            (
                item.get("originalText", "")
                for item in reversed(self.transcript_history)
                if item.get("speaker") == "assistant"
            ),
            "",
        )
        if last_assistant:
            assistant_normalized = re.sub(r"[^\w\s]", " ", last_assistant.lower(), flags=re.UNICODE)
            assistant_normalized = re.sub(r"\s+", " ", assistant_normalized).strip()
            if len(normalized) > 8 and normalized in assistant_normalized:
                return True
            if len(assistant_normalized) > 8 and assistant_normalized[:40] in normalized:
                return True

        tokens = normalized.split()
        if len(tokens) < 10:
            return False

        max_repeat = max(tokens.count(token) for token in set(tokens))
        repeated_filler_count = sum(
            normalized.count(phrase)
            for phrase in ("ते हे", "जे आहे", "हे जे", "आहे ते", "this is", "that is", "so this")
        )
        return (max_repeat / len(tokens)) > 0.45 or repeated_filler_count >= 4

    # ── Demo Turn (fallback when no real audio/API) ──────────────────────────
    async def process_demo_turn(self, mode: str, lang_detected: dict | None = None) -> dict:
        now = datetime.now().strftime("%H:%M")
        if mode == "staff":
            text = "Please confirm the last four digits of your card. I will block it immediately."
            translated = "कृपया आपल्या कार्डचे शेवटचे चार अंक सांगा. मी ते लगेच ब्लॉक करतो."
            speaker = "staff"
            language = "English"
            entities: dict = {}
            chips = ["Confirm Identity", "Block Card", "Read Fee Disclosure"]
        else:
            text = "माझे नाव राहुल पाटील आहे आणि माझे सेव्हिंग अकाउंट आहे."
            translated = "My name is Rahul Patil and I have a savings account."
            speaker = "customer"
            language = "Marathi"
            entities = {"customerName": "Rahul Patil", "accountType": "Savings"}
            chips = ["Open KYC Form", "Check Account", "Continue Marathi"]

        self.last_translated_text = translated if mode == "staff" else text
        self.last_language_code = "mr-IN"

        item = TranscriptItem(
            id=str(uuid4()),
            speaker=speaker,
            sourceLanguage=language,
            originalText=text,
            translatedText=translated,
            confidence=1.0,
            timestamp=now,
        )
        self.transcript_history.append(item.model_dump())

        result: dict = {
            "type": "transcript",
            "item": item.model_dump(),
            "entities": entities,
            "actionChips": chips,
        }
        if lang_detected:
            result["languageDetected"] = lang_detected
        return result

    # ── Sarvam: SOP Search ───────────────────────────────────────────────────
    async def search_sop(self, query: str, language_code: str = "en-IN") -> SopResult:
        """Search trusted SOPs and generate a grounded answer."""
        return await rag_service.answer(
            query,
            branch_id=self.branch_id,
            language_code=language_code,
            llm=self._call_sarvam_llm if settings.rag_use_llm and settings.sarvam_api_key else None,
            translate=self._call_sarvam_translate if settings.sarvam_api_key else None,
        )

    # ── TTS Replay ───────────────────────────────────────────────────────────
    async def replay_last(self) -> dict:
        """Generate TTS audio for the last translated text."""
        audio_b64 = await self._call_sarvam_tts(
            self.last_translated_text or "कोणताही संदेश उपलब्ध नाही.",
            self.last_language_code or "mr-IN",
        )
        return {
            "type": "tts_audio",
            "audio_b64": audio_b64,
            "text": self.last_translated_text,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # FORM INTERVIEW ENGINE
    # ══════════════════════════════════════════════════════════════════════════

    async def start_form_interview(self, form_type_str: str) -> dict:
        """Initialize a form interview session and return the first question.

        Returns the form definition, first question text, and TTS audio of
        the greeting + first question spoken in the customer's detected language.
        """
        definition = get_form_definition(form_type_str)
        if not definition:
            return {"type": "form_error", "message": f"Unknown form type: {form_type_str}"}

        self.form_session = FormSession(form_type=definition.form_type)
        first_field = definition.field_at(0)
        if not first_field:
            return {"type": "form_error", "message": "Form has no fields."}

        # Build greeting + first question
        greeting = f"Welcome! I'll help you fill the {definition.title} form. Let's start."
        full_question = f"{greeting} {first_field.question}"

        # Generate TTS in customer's detected language
        lang_code = self.detected_language_code or "hi-IN"
        lang_name = self.detected_language or "Hindi"

        # Translate question to customer's language for TTS
        if lang_code != "en-IN":
            translated_question = await self._call_sarvam_translate(
                full_question, "en-IN", lang_code
            )
        else:
            translated_question = full_question

        audio_b64 = await self._call_sarvam_tts(translated_question, lang_code)

        return {
            "type": "form_started",
            "formDefinition": definition.to_dict(),
            "formState": self.form_session.to_dict(),
            "currentField": {
                "key": first_field.key,
                "label": first_field.label,
                "fieldType": first_field.field_type,
                "options": first_field.options,
            },
            "questionText": first_field.question,
            "questionTranslated": translated_question,
            "questionAudio": audio_b64,
        }

    async def process_form_audio_turn(self, audio: bytes) -> dict:
        """Process a single voice answer during an active form interview.

        Pipeline:
        1. STT → get native text
        2. Translate to English
        3. Extract the single field value using LLM
        4. Fill the field, advance to next
        5. Generate TTS for the next question in customer's language
        6. Return updated form state
        """
        if not self.form_session:
            return {"type": "form_error", "message": "No active form interview."}

        definition = FORM_REGISTRY[self.form_session.form_type]
        current_field = definition.field_at(self.form_session.current_field_index)
        if not current_field:
            return {"type": "form_error", "message": "No more fields to fill."}

        # 1. STT + auto-detect language if not yet known
        stt_result = await self._call_sarvam_stt(audio)
        if self.detected_language is None:
            lang_info = self._language_info_from_code(stt_result.get("language_code"))
            self.detected_language = lang_info["language"]
            self.detected_language_code = lang_info["code"]

        if not stt_result["transcript"]:
            # No speech detected — ask again
            retry_text = f"I didn't catch that. {current_field.question}"
            lang_code = self.detected_language_code or "hi-IN"
            if lang_code != "en-IN":
                retry_translated = await self._call_sarvam_translate(retry_text, "en-IN", lang_code)
            else:
                retry_translated = retry_text
            audio_b64 = await self._call_sarvam_tts(retry_translated, lang_code)
            return {
                "type": "form_retry",
                "formState": self.form_session.to_dict(),
                "currentField": {
                    "key": current_field.key,
                    "label": current_field.label,
                    "fieldType": current_field.field_type,
                    "options": current_field.options,
                },
                "questionText": retry_text,
                "questionTranslated": retry_translated,
                "questionAudio": audio_b64,
            }

        native_text = stt_result["transcript"]
        source_code = stt_result["language_code"]

        # 3. Translate to English for entity extraction
        if source_code != "en-IN":
            english_text = await self._call_sarvam_translate(native_text, source_code, "en-IN")
        else:
            english_text = native_text

        # 4. Extract the specific field value from the English answer
        extracted_value = await self._extract_form_field(
            english_text, current_field.key, current_field.label,
            current_field.validation_hint, current_field.options
        )

        # 5. Fill the field
        self.form_session.filled_fields[current_field.key] = extracted_value
        filled_field_key = current_field.key
        filled_field_label = current_field.label

        # 6. Advance to next field
        self.form_session.current_field_index += 1
        next_field = definition.field_at(self.form_session.current_field_index)

        if next_field is None:
            # All fields filled!
            self.form_session.is_complete = True
            completion_text = (
                f"All fields are filled. Your {definition.title} form is now complete. "
                "The staff can review and download the PDF."
            )
            lang_code = self.detected_language_code or "hi-IN"
            if lang_code != "en-IN":
                completion_translated = await self._call_sarvam_translate(
                    completion_text, "en-IN", lang_code
                )
            else:
                completion_translated = completion_text
            audio_b64 = await self._call_sarvam_tts(completion_translated, lang_code)

            return {
                "type": "form_complete",
                "formState": self.form_session.to_dict(),
                "filledFieldKey": filled_field_key,
                "filledFieldLabel": filled_field_label,
                "filledFieldValue": extracted_value,
                "nativeAnswer": native_text,
                "englishAnswer": english_text,
                "completionText": completion_text,
                "completionTranslated": completion_translated,
                "completionAudio": audio_b64,
            }

        # Build confirmation + next question
        confirmation = f"Got it. "
        next_question = f"{confirmation}{next_field.question}"
        lang_code = self.detected_language_code or "hi-IN"
        if lang_code != "en-IN":
            next_translated = await self._call_sarvam_translate(next_question, "en-IN", lang_code)
        else:
            next_translated = next_question
        audio_b64 = await self._call_sarvam_tts(next_translated, lang_code)

        return {
            "type": "form_field_filled",
            "formState": self.form_session.to_dict(),
            "filledFieldKey": filled_field_key,
            "filledFieldLabel": filled_field_label,
            "filledFieldValue": extracted_value,
            "nativeAnswer": native_text,
            "englishAnswer": english_text,
            "currentField": {
                "key": next_field.key,
                "label": next_field.label,
                "fieldType": next_field.field_type,
                "options": next_field.options,
            },
            "questionText": next_field.question,
            "questionTranslated": next_translated,
            "questionAudio": audio_b64,
        }

    async def _extract_form_field(
        self,
        text: str,
        field_key: str,
        field_label: str,
        validation_hint: str,
        options: list[str] | None = None,
    ) -> str:
        """Extract a single form field value from the customer's spoken answer."""
        options_str = f" Valid options are: {', '.join(options)}." if options else ""
        prompt = (
            f"The customer was asked for their '{field_label}' and replied: \"{text}\"\n"
            f"Extract ONLY the value for '{field_label}' from this response.{options_str}\n"
        )
        if validation_hint:
            prompt += f"Expected format: {validation_hint}\n"
        prompt += (
            "Return ONLY the extracted value as plain text — no JSON, no quotes, no explanation. "
            "If the answer contains the value along with filler words, extract just the value. "
            "The value must be in English."
        )

        try:
            value = await self._call_sarvam_llm(prompt, "Extract the exact value. Return only the value, nothing else.")
            value = value.strip().strip('"').strip("'")
            if not value:
                return text.strip()
            return value
        except Exception:
            # Fallback: return the English text as-is
            return text.strip()

    def cancel_form_interview(self) -> dict:
        """Cancel the active form interview."""
        self.form_session = None
        return {"type": "form_cancelled"}

    async def generate_form_pdf(self, session_id: str) -> io.BytesIO:
        """Generate a professional PDF for the completed (or partially filled) form."""
        if not self.form_session:
            raise ValueError("No active form session to generate PDF for.")
        if not self.form_session.filled_fields:
            raise ValueError("No fields have been filled yet.")

        from reportlab.lib.colors import Color, HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        definition = FORM_REGISTRY[self.form_session.form_type]
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4

        # ── Colors ──
        primary = HexColor("#1a237e")       # Deep indigo
        accent = HexColor("#283593")
        light_bg = HexColor("#e8eaf6")
        border = HexColor("#9fa8da")
        text_dark = HexColor("#212121")
        text_muted = HexColor("#616161")
        success = HexColor("#2e7d32")

        # ── Header Bar ──
        c.setFillColor(primary)
        c.rect(0, h - 35 * mm, w, 35 * mm, fill=True, stroke=False)

        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 20)
        c.drawString(20 * mm, h - 18 * mm, "VoxAssist Banking")
        c.setFont("Helvetica", 11)
        c.drawString(20 * mm, h - 26 * mm, definition.title.upper())

        # Right side — date & session
        c.setFont("Helvetica", 9)
        c.drawRightString(w - 20 * mm, h - 18 * mm, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        c.drawRightString(w - 20 * mm, h - 24 * mm, f"Session: {session_id[:16]}")

        # ── AI Badge ──
        badge_y = h - 45 * mm
        c.setFillColor(success)
        c.roundRect(20 * mm, badge_y - 2 * mm, 60 * mm, 7 * mm, 2 * mm, fill=True, stroke=False)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(23 * mm, badge_y, "✓  AI VOICE AUTO-FILLED")

        c.setFillColor(text_muted)
        c.setFont("Helvetica", 8)
        c.drawString(85 * mm, badge_y, f"Language: {self.detected_language or 'Auto-detected'}")

        # ── Form Fields Table ──
        y = h - 60 * mm
        row_height = 12 * mm
        label_x = 22 * mm
        value_x = 75 * mm
        col_width_label = 50 * mm
        col_width_value = w - value_x - 20 * mm

        # Table header
        c.setFillColor(accent)
        c.rect(20 * mm, y - 1 * mm, w - 40 * mm, 8 * mm, fill=True, stroke=False)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(label_x, y + 1.5 * mm, "FIELD")
        c.drawString(value_x, y + 1.5 * mm, "VALUE")

        y -= row_height * 0.6

        # Table rows
        for i, field_def in enumerate(definition.fields):
            value = self.form_session.filled_fields.get(field_def.key, "—")

            # Alternating row background
            if i % 2 == 0:
                c.setFillColor(light_bg)
                c.rect(20 * mm, y - 3 * mm, w - 40 * mm, row_height, fill=True, stroke=False)

            # Border bottom
            c.setStrokeColor(border)
            c.setLineWidth(0.3)
            c.line(20 * mm, y - 3 * mm, w - 20 * mm, y - 3 * mm)

            # Field label
            c.setFillColor(text_dark)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(label_x, y + 2 * mm, field_def.label)

            # Field value
            c.setFont("Helvetica", 10)
            if value and value != "—":
                c.setFillColor(text_dark)
                # Truncate long values
                display_value = value[:60] + ("..." if len(value) > 60 else "")
                c.drawString(value_x, y + 2 * mm, display_value)
                # AI checkmark
                c.setFillColor(success)
                c.setFont("Helvetica", 7)
                c.drawRightString(w - 22 * mm, y + 2 * mm, "✓ AI")
            else:
                c.setFillColor(text_muted)
                c.drawString(value_x, y + 2 * mm, "—")

            y -= row_height

            # Page break if needed
            if y < 40 * mm:
                c.showPage()
                y = h - 30 * mm

        # ── Footer section ──
        y -= 10 * mm

        # Signature box
        c.setStrokeColor(border)
        c.setLineWidth(0.5)
        c.rect(20 * mm, y - 20 * mm, 70 * mm, 20 * mm, fill=False, stroke=True)
        c.setFillColor(text_muted)
        c.setFont("Helvetica", 8)
        c.drawString(22 * mm, y - 17 * mm, "Customer Signature")

        c.rect(w - 90 * mm, y - 20 * mm, 70 * mm, 20 * mm, fill=False, stroke=True)
        c.drawString(w - 88 * mm, y - 17 * mm, "Bank Official Signature")

        # Footer line
        y -= 30 * mm
        c.setStrokeColor(primary)
        c.setLineWidth(1)
        c.line(20 * mm, y, w - 20 * mm, y)
        y -= 5 * mm
        c.setFillColor(text_muted)
        c.setFont("Helvetica", 7)
        c.drawString(20 * mm, y, f"Generated by VoxAssist AI • {datetime.now().strftime('%d %b %Y, %H:%M')} • Session: {session_id}")
        c.drawRightString(w - 20 * mm, y, "This form was auto-filled using AI voice technology.")

        c.save()
        buf.seek(0)
        return buf
