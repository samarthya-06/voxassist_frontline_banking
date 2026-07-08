"""MongoDB persistence layer with in-memory fallback."""

import logging
import re
import uuid
from datetime import date, datetime, time, timedelta

from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from ..core.config import settings
from ..db.connection import get_db, get_client, ensure_indexes, is_mongo_available

logger = logging.getLogger(__name__)

LANGUAGE_CODE_TO_NAME = {
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

UNKNOWN_LANGUAGE_VALUES = {"", "unknown", "unspecified", "auto-detected", "auto detected", "auto"}


class SessionRepository:
    def __init__(self) -> None:
        self.memory: dict[str, dict] = {}
        self.history_memory: list[dict] = []
        self.pdf_memory: dict[str, bytes] = {}
        self.transcript_memory: dict[str, list[dict]] = {}
        self.compliance_memory: list[dict] = []
        self.form_memory: list[dict] = []
        self.session_meta_memory: dict[str, dict] = {}

    @property
    def db(self):
        return get_db()

    # ── Database Setup ───────────────────────────────────────────────────────
    async def ensure_database(self) -> None:
        """Create indexes and seed demo users when MongoDB is available."""
        await ensure_indexes()
        if is_mongo_available():
            if settings.seed_demo_users or settings.seed_demo_data:
                await self._seed_demo_users()
            logger.info("MongoDB database '%s' is ready", settings.mongodb_db)

        if settings.seed_demo_data:
            self._seed_demo_sessions()

    async def _seed_demo_users(self) -> None:
        users = [
            {
                "username": "staff1",
                "password": "staff123",
                "role": "staff",
                "name": "Priya Sharma",
                "branch": "Central District",
                "desk_id": "FD-01",
                "system_id": "FRONTLINE-DESK-01",
                "employee_id": "104851",
                "active": True,
                "updatedAt": datetime.now().isoformat(),
            },
            {
                "username": "staff2",
                "password": "staff123",
                "role": "staff",
                "name": "Rohan Mehta",
                "branch": "Central District",
                "desk_id": "FD-02",
                "system_id": "FRONTLINE-DESK-02",
                "employee_id": "104852",
                "active": True,
                "updatedAt": datetime.now().isoformat(),
            },
            {
                "username": "staff3",
                "password": "staff123",
                "role": "staff",
                "name": "Neha Iyer",
                "branch": "Central District",
                "desk_id": "FD-03",
                "system_id": "FRONTLINE-DESK-03",
                "employee_id": "104853",
                "active": True,
                "updatedAt": datetime.now().isoformat(),
            },
            {
                "username": "staff4",
                "password": "staff123",
                "role": "staff",
                "name": "Amit Kulkarni",
                "branch": "Central District",
                "desk_id": "FD-04",
                "system_id": "FRONTLINE-DESK-04",
                "employee_id": "104854",
                "active": True,
                "updatedAt": datetime.now().isoformat(),
            },
            {
                "username": "staff5",
                "password": "staff123",
                "role": "staff",
                "name": "Farah Khan",
                "branch": "Central District",
                "desk_id": "FD-05",
                "system_id": "FRONTLINE-DESK-05",
                "employee_id": "104855",
                "active": True,
                "updatedAt": datetime.now().isoformat(),
            },
            {
                "username": "manager1",
                "password": "manager123",
                "role": "manager",
                "name": "Anil Deshmukh",
                "branch": "Central District",
                "active": True,
                "updatedAt": datetime.now().isoformat(),
            },
        ]
        for user in users:
            await self.db.users.update_one(
                {"username": user["username"]},
                {"$setOnInsert": user},
                upsert=True,
            )

    def _seed_demo_sessions(self) -> None:
        """Seed realistic demo sessions so History + Analytics tabs have data on fresh start."""
        if self.history_memory:
            return  # Already seeded

        now = datetime.now()
        demo_sessions = [
            {
                "session_id": "SES-20260502-001",
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "summary": {
                    "type": "summary",
                    "service": "Account Opening",
                    "status": "Completed",
                    "language": "Marathi",
                    "duration": "06:42",
                    "sentiment": "positive",
                    "entities": {
                        "customerName": "Rahul Patil",
                        "pan": "ABCDE1234F",
                        "phone": "98765*****",
                        "accountType": "Savings",
                        "product": "",
                        "amount": "",
                        "cardLast4": "",
                    },
                    "english": [
                        "Customer requested a new savings account.",
                        "All KYC documents verified — Aadhaar + PAN.",
                        "Account opening form completed via voice auto-fill.",
                    ],
                    "customerLanguage": [
                        "ग्राहकाने नवीन बचत खाते मागितले.",
                        "सर्व KYC कागदपत्रे तपासली — आधार + पॅन.",
                        "व्हॉइस ऑटो-फिल द्वारे खाते उघडण्याचा फॉर्म पूर्ण.",
                    ],
                    "formsFilled": ["Account Opening"],
                    "complianceFlags": 0,
                },
            },
            {
                "session_id": "SES-20260502-002",
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "summary": {
                    "type": "summary",
                    "service": "Fixed Deposit Enquiry",
                    "status": "Completed",
                    "language": "Marathi",
                    "duration": "04:18",
                    "sentiment": "positive",
                    "entities": {
                        "customerName": "Sunita Deshmukh",
                        "pan": "",
                        "phone": "",
                        "accountType": "",
                        "product": "Fixed Deposit",
                        "amount": "₹2,00,000",
                        "cardLast4": "",
                    },
                    "english": [
                        "Customer enquired about FD interest rates.",
                        "Explained 6.5% for 1-year tenure, 7.1% for senior citizen.",
                        "Customer decided to think and return tomorrow.",
                    ],
                    "customerLanguage": [
                        "ग्राहकाने FD व्याजदर विचारले.",
                        "1 वर्ष मुदतीसाठी 6.5%, ज्येष्ठ नागरिकांसाठी 7.1% समजावले.",
                        "ग्राहक उद्या येण्याचे ठरवले.",
                    ],
                    "formsFilled": [],
                    "complianceFlags": 0,
                },
            },
            {
                "session_id": "SES-20260501-003",
                "timestamp": (now - timedelta(hours=20)).isoformat(),
                "summary": {
                    "type": "summary",
                    "service": "Card Block + Replacement",
                    "status": "Escalated",
                    "language": "Hindi",
                    "duration": "08:55",
                    "sentiment": "negative",
                    "entities": {
                        "customerName": "Amit Sharma",
                        "pan": "",
                        "phone": "",
                        "accountType": "",
                        "product": "",
                        "amount": "",
                        "cardLast4": "7892",
                    },
                    "english": [
                        "Customer reported lost debit card — requested immediate block.",
                        "Card ending 7892 blocked successfully.",
                        "Replacement card application submitted.",
                        "Customer expressed frustration about wait time — escalated to manager.",
                    ],
                    "customerLanguage": [
                        "ग्राहकाने हरवलेले डेबिट कार्ड सांगितले — तात्काळ ब्लॉक मागितले.",
                        "7892 ने संपणारे कार्ड ब्लॉक केले.",
                        "बदली कार्ड अर्ज सबमिट केला.",
                        "ग्राहकाने प्रतीक्षा वेळेबद्दल नाराजी व्यक्त केली — व्यवस्थापकाकडे वर्ग केले.",
                    ],
                    "formsFilled": ["Card Application"],
                    "complianceFlags": 1,
                },
            },
            {
                "session_id": "SES-20260501-004",
                "timestamp": (now - timedelta(hours=24)).isoformat(),
                "summary": {
                    "type": "summary",
                    "service": "Locker Enquiry",
                    "status": "Completed",
                    "language": "Marathi",
                    "duration": "03:22",
                    "sentiment": "positive",
                    "entities": {
                        "customerName": "Priya Kulkarni",
                        "pan": "",
                        "phone": "",
                        "accountType": "",
                        "product": "Locker",
                        "amount": "",
                        "cardLast4": "",
                    },
                    "english": [
                        "Customer asked about safe deposit locker availability.",
                        "Explained locker rent: ₹1,500 to ₹12,000 per year based on size.",
                        "Savings account and KYC required for locker allotment.",
                    ],
                    "customerLanguage": [
                        "ग्राहकाने सेफ डिपॉझिट लॉकर उपलब्धता विचारली.",
                        "लॉकर भाडे: आकारानुसार ₹1,500 ते ₹12,000 प्रति वर्ष.",
                        "लॉकर वाटपासाठी बचत खाते आणि KYC आवश्यक.",
                    ],
                    "formsFilled": [],
                    "complianceFlags": 0,
                },
            },
            {
                "session_id": "SES-20260430-005",
                "timestamp": (now - timedelta(hours=46)).isoformat(),
                "summary": {
                    "type": "summary",
                    "service": "KYC Update",
                    "status": "Completed",
                    "language": "English",
                    "duration": "05:10",
                    "sentiment": "positive",
                    "entities": {
                        "customerName": "Rajesh Iyer",
                        "pan": "GHIJK5678L",
                        "phone": "87654*****",
                        "accountType": "",
                        "product": "",
                        "amount": "",
                        "cardLast4": "",
                    },
                    "english": [
                        "Customer needed address update on KYC records.",
                        "New Aadhaar with updated address verified.",
                        "KYC form filled and submitted for CBS update.",
                    ],
                    "customerLanguage": [
                        "Customer needed address update on KYC records.",
                        "New Aadhaar with updated address verified.",
                        "KYC form filled and submitted for CBS update.",
                    ],
                    "formsFilled": ["KYC Verification"],
                    "complianceFlags": 0,
                },
            },
            {
                "session_id": "SES-20260430-006",
                "timestamp": (now - timedelta(hours=48)).isoformat(),
                "summary": {
                    "type": "summary",
                    "service": "NEFT Transfer Help",
                    "status": "Completed",
                    "language": "Marathi",
                    "duration": "04:45",
                    "sentiment": "positive",
                    "entities": {
                        "customerName": "Meena Jadhav",
                        "pan": "",
                        "phone": "",
                        "accountType": "",
                        "product": "",
                        "amount": "₹50,000",
                        "cardLast4": "",
                    },
                    "english": [
                        "Customer needed help with NEFT transfer to another bank.",
                        "Explained NEFT charges and settlement timing.",
                        "Guided through transfer process — completed successfully.",
                    ],
                    "customerLanguage": [
                        "ग्राहकाला दुसऱ्या बँकेत NEFT ट्रान्सफरसाठी मदत हवी होती.",
                        "NEFT शुल्क आणि सेटलमेंट वेळ समजावले.",
                        "ट्रान्सफर प्रक्रिया मार्गदर्शित — यशस्वीरित्या पूर्ण.",
                    ],
                    "formsFilled": [],
                    "complianceFlags": 0,
                },
            },
            {
                "session_id": "SES-20260502-007",
                "timestamp": (now - timedelta(hours=3)).isoformat(),
                "summary": {
                    "type": "summary",
                    "service": "Loan Enquiry",
                    "status": "Completed",
                    "language": "Hindi",
                    "duration": "07:30",
                    "sentiment": "positive",
                    "entities": {
                        "customerName": "Vikram Singh",
                        "pan": "MNOPQ9012R",
                        "phone": "91234*****",
                        "accountType": "Savings",
                        "product": "Home Loan",
                        "amount": "₹25,00,000",
                        "cardLast4": "",
                    },
                    "english": [
                        "Customer enquired about home loan eligibility.",
                        "Explained 8.5% interest rate for salaried, 9.1% for self-employed.",
                        "Income documents checklist shared. Pre-approval initiated.",
                    ],
                    "customerLanguage": [
                        "ग्राहक ने होम लोन पात्रता पूछी.",
                        "वेतनभोगी के लिए 8.5%, स्वरोजगार के लिए 9.1% ब्याज दर बताया.",
                        "आय दस्तावेजों की चेकलिस्ट साझा की। प्री-अप्रूवल शुरू किया.",
                    ],
                    "formsFilled": ["Loan Application"],
                    "complianceFlags": 0,
                },
            },
            {
                "session_id": "SES-20260502-008",
                "timestamp": (now - timedelta(minutes=30)).isoformat(),
                "summary": {
                    "type": "summary",
                    "service": "Card Support",
                    "status": "Completed",
                    "language": "Kannada",
                    "duration": "03:55",
                    "sentiment": "positive",
                    "entities": {
                        "customerName": "Lakshmi Nair",
                        "pan": "",
                        "phone": "97531*****",
                        "accountType": "",
                        "product": "Credit Card",
                        "amount": "",
                        "cardLast4": "4521",
                    },
                    "english": [
                        "Customer requested credit card PIN reset.",
                        "Identity verified via registered mobile OTP.",
                        "New PIN set successfully. Card active.",
                    ],
                    "customerLanguage": [
                        "ಗ್ರಾಹಕರು ಕ್ರೆಡಿಟ್ ಕಾರ್ಡ್ PIN ಮರುಹೊಂದಿಸಲು ವಿನಂತಿಸಿದರು.",
                        "ನೋಂದಾಯಿತ ಮೊಬೈಲ್ OTP ಮೂಲಕ ಗುರುತು ಪರಿಶೀಲಿಸಲಾಯಿತು.",
                        "ಹೊಸ PIN ಯಶಸ್ವಿಯಾಗಿ ಹೊಂದಿಸಲಾಯಿತು. ಕಾರ್ಡ್ ಸಕ್ರಿಯ.",
                    ],
                    "formsFilled": [],
                    "complianceFlags": 0,
                },
            },
        ]

        for session in demo_sessions:
            self.memory[session["session_id"]] = session
            self.history_memory.append(session)

        logger.info("Seeded %d demo sessions into in-memory store", len(demo_sessions))

    async def get_user(self, username: str) -> dict | None:
        """Return a user from MongoDB, or None when MongoDB is unavailable."""
        try:
            user = await self.db.users.find_one({
                "$or": [{"username": username}, {"employee_id": username}],
                "active": True,
            })
            if user:
                user.pop("_id", None)
            return user
        except (PyMongoError, ServerSelectionTimeoutError):
            return None

    # ── Save Session Summary ─────────────────────────────────────────────────
    async def save_summary(self, session_id: str, summary: dict) -> None:
        doc = {
            "session_id": session_id,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            await self.db.session_summaries.update_one(
                {"session_id": session_id},
                {"$set": doc},
                upsert=True,
            )
        except (PyMongoError, ServerSelectionTimeoutError):
            self.memory[session_id] = doc
            self.history_memory.append(doc)
            logger.debug("MongoDB unavailable — saved to memory")

    # ── Get Session Summary ──────────────────────────────────────────────────
    async def get_summary(self, session_id: str) -> dict | None:
        try:
            doc = await self.db.session_summaries.find_one({"session_id": session_id})
            if doc:
                return doc.get("summary", doc)
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB summary lookup failed for %s; using memory fallback: %s", session_id, exc)
        return self.memory.get(session_id, {}).get("summary")

    # ── Session Records / History / Analytics ───────────────────────────────
    def _parse_timestamp(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def _range_bounds(
        self,
        time_range: str = "all",
        date_value: str = "",
        month_value: str = "",
        year_value: str = "",
    ) -> tuple[datetime | None, datetime | None]:
        now = datetime.now()
        if date_value:
            try:
                selected = date.fromisoformat(date_value)
                start = datetime.combine(selected, time.min)
                return start, start + timedelta(days=1)
            except ValueError:
                logger.debug("Ignoring invalid analytics date filter: %s", date_value)
        if month_value:
            try:
                start = datetime.strptime(month_value, "%Y-%m")
                end = datetime(start.year + (1 if start.month == 12 else 0), 1 if start.month == 12 else start.month + 1, 1)
                return start, end
            except ValueError:
                logger.debug("Ignoring invalid analytics month filter: %s", month_value)
        if year_value:
            try:
                year = int(year_value)
                return datetime(year, 1, 1), datetime(year + 1, 1, 1)
            except ValueError:
                logger.debug("Ignoring invalid analytics year filter: %s", year_value)
        if time_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return start, start + timedelta(days=1)
        if time_range == "week":
            start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            return start, start + timedelta(days=7)
        if time_range == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = datetime(start.year + (1 if start.month == 12 else 0), 1 if start.month == 12 else start.month + 1, 1)
            return start, end
        if time_range == "year":
            return datetime(now.year, 1, 1), datetime(now.year + 1, 1, 1)
        return None, None

    def _in_bounds(self, timestamp: str, start: datetime | None, end: datetime | None) -> bool:
        parsed = self._parse_timestamp(timestamp)
        if parsed is None:
            return True if start is None and end is None else False
        if start and parsed < start:
            return False
        if end and parsed >= end:
            return False
        return True

    def _seconds_to_mmss(self, seconds: int) -> str:
        safe_seconds = max(0, seconds)
        return f"{safe_seconds // 60:02d}:{safe_seconds % 60:02d}"

    def _duration_to_seconds(self, duration: str | None) -> int:
        if not duration or ":" not in duration:
            return 0
        parts = duration.split(":")
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0

    def _normalize_language(self, value: str | None) -> str:
        if not value:
            return ""
        normalized = str(value).strip()
        if normalized in LANGUAGE_CODE_TO_NAME:
            return LANGUAGE_CODE_TO_NAME[normalized]
        if normalized.lower() in UNKNOWN_LANGUAGE_VALUES:
            return ""
        return normalized

    def _infer_language(self, transcripts: list[dict], fallback: str = "") -> str:
        for item in transcripts:
            if item.get("speaker") == "customer":
                language = self._normalize_language(item.get("sourceLanguage"))
                if language:
                    return language
        return fallback

    def _infer_service(self, summary: dict, transcripts: list[dict], forms: list[dict]) -> str:
        if summary.get("service"):
            return summary["service"]
        if forms:
            return forms[0].get("form_title") or forms[0].get("form_type", "Form")
        text = " ".join(
            f"{item.get('originalText', '')} {item.get('translatedText', '')}"
            for item in transcripts
        ).lower()
        if not text.strip():
            return "Unclassified Session"
        service_keywords = [
            ("Fixed Deposit Enquiry", ("fixed deposit", "fd", "deposit", "term deposit", "interest rate", "maturity", "व्याज", "मुदत ठेव", "फिक्स्ड", "फिक्स डिपॉझिट", "सावधि जमा")),
            ("Account Opening", ("open account", "account opening", "savings account", "current account", "new account", "खाते", "खाता", "अकाउंट", "बचत खाते")),
            ("KYC Update", ("kyc", "aadhaar", "aadhar", "pan", "address update", "identity", "verification", "केवायसी", "आधार", "पॅन")),
            ("Card Support", ("card", "debit", "credit", "pin", "block", "replacement card", "lost card", "कार्ड", "डेबिट", "क्रेडिट")),
            ("Loan Enquiry", ("loan", "home loan", "personal loan", "vehicle loan", "emi", "कर्ज", "लोन", "ऋण")),
            ("Money Transfer", ("neft", "rtgs", "imps", "transfer", "upi", "fund transfer", "ट्रान्सफर", "हस्तांतरण")),
            ("Locker Enquiry", ("locker", "safe deposit", "लॉकर")),
            ("Cheque Services", ("cheque", "check book", "chequebook", "stop cheque", "चेक")),
            ("Balance / Statement", ("balance", "statement", "passbook", "mini statement", "बॅलन्स", "स्टेटमेंट", "पासबुक")),
            ("Nomination Update", ("nominee", "nomination", "nominate", "नामांकन", "नॉमिनी")),
        ]
        for label, keywords in service_keywords:
            if any(keyword in text for keyword in keywords):
                return label
        return "General Banking Help"

    def _merge_entities(self, summary: dict, transcripts: list[dict]) -> dict:
        entities = {
            "customerName": "",
            "pan": "",
            "phone": "",
            "accountType": "",
            "product": "",
            "amount": "",
            "cardLast4": "",
        }
        entities.update(summary.get("entities") or {})
        for item in transcripts:
            text = f"{item.get('originalText', '')} {item.get('translatedText', '')}"
            if not entities["customerName"]:
                # Keep this intentionally conservative; detailed extraction still
                # happens in the orchestrator during live calls.
                name = re.search(
                    r"(?:my name is|i am|i'm|this is|name is|mera naam|mera name|माझे नाव|माझं नाव|मेरा नाम)\s+([A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){0,3})",
                    text,
                    flags=re.IGNORECASE,
                )
                if name:
                    entities["customerName"] = " ".join(part.capitalize() for part in name.group(1).split())[:60]
        return entities

    def _normalize_session_record(
        self,
        session_id: str,
        summary_doc: dict | None,
        meta_doc: dict | None,
        transcripts: list[dict],
        forms: list[dict],
        compliance_events: list[dict],
    ) -> dict:
        summary = (summary_doc or {}).get("summary", {}) if summary_doc else {}
        timestamp = (
            (summary_doc or {}).get("timestamp")
            or (meta_doc or {}).get("started_at")
            or datetime.now().isoformat()
        )
        duration = summary.get("duration")
        duration_seconds = int((meta_doc or {}).get("duration_seconds") or 0)
        if not duration:
            duration = self._seconds_to_mmss(duration_seconds)

        status = summary.get("status")
        if not status:
            status = "Escalated" if compliance_events else ("Completed" if (meta_doc or {}).get("status") == "completed" else "Active")

        language = (
            self._normalize_language(summary.get("language"))
            or self._normalize_language((meta_doc or {}).get("customer_language"))
            or self._normalize_language((meta_doc or {}).get("customer_language_code"))
            or self._infer_language(transcripts)
            or "Unspecified"
        )
        forms_filled = summary.get("formsFilled")
        if forms_filled is None:
            forms_filled = [item.get("form_title") or item.get("form_type", "Form") for item in forms if item.get("is_complete")]

        english = summary.get("english")
        if english is None:
            english = [
                f"{item.get('speaker', 'speaker').title()}: {item.get('translatedText') or item.get('originalText')}"
                for item in transcripts[-8:]
            ]
        customer_language = summary.get("customerLanguage")
        if customer_language is None:
            customer_language = [
                f"{item.get('speaker', 'speaker').title()}: {item.get('originalText')}"
                for item in transcripts[-8:]
            ]

        normalized_summary = {
            "type": "summary",
            "service": self._infer_service(summary, transcripts, forms),
            "status": status,
            "language": language,
            "duration": duration,
            "sentiment": summary.get("sentiment") or ("negative" if status == "Escalated" else "neutral"),
            "entities": self._merge_entities(summary, transcripts),
            "english": english,
            "customerLanguage": customer_language,
            "formsFilled": forms_filled,
            "complianceFlags": summary.get("complianceFlags", len(compliance_events)),
            "staffUsername": (meta_doc or {}).get("staff_username", ""),
            "deskId": (meta_doc or {}).get("desk_id", ""),
            "branch": (meta_doc or {}).get("branch", ""),
        }
        
        # Override customerName if staff explicitly set it in metadata
        if meta_doc and meta_doc.get("customer_name"):
            normalized_summary["entities"]["customerName"] = meta_doc["customer_name"]

        return {
            "session_id": session_id,
            "timestamp": timestamp,
            "summary": normalized_summary,
        }

    async def get_session_records(
        self,
        time_range: str = "all",
        date_value: str = "",
        month_value: str = "",
        year_value: str = "",
        search: str = "",
        service: str = "",
        staff_username: str = "",
        limit: int = 200,
    ) -> list[dict]:
        """Return session records derived from real summaries, sessions, transcripts, forms, and compliance events."""
        seen_ids: set[str] = set()
        summary_docs: dict[str, dict] = {}
        meta_docs: dict[str, dict] = {}
        transcript_docs: dict[str, list[dict]] = {}
        form_docs: dict[str, list[dict]] = {}
        compliance_docs: dict[str, list[dict]] = {}

        try:
            cursor = self.db.session_summaries.find({}).sort("timestamp", -1).limit(limit)
            async for doc in cursor:
                doc.pop("_id", None)
                sid = doc.get("session_id", "")
                if sid:
                    summary_docs[sid] = doc

            cursor = self.db.sessions.find({}).sort("started_at", -1).limit(limit)
            async for doc in cursor:
                doc.pop("_id", None)
                sid = doc.get("session_id", "")
                if sid:
                    meta_docs[sid] = doc

            session_ids = list(set(summary_docs) | set(meta_docs))
            if session_ids:
                cursor = self.db.transcripts.find({"session_id": {"$in": session_ids}}).sort("timestamp", 1)
                async for doc in cursor:
                    doc.pop("_id", None)
                    transcript_docs.setdefault(doc.get("session_id", ""), []).append(doc)

                cursor = self.db.form_submissions.find({"session_id": {"$in": session_ids}})
                async for doc in cursor:
                    doc.pop("_id", None)
                    form_docs.setdefault(doc.get("session_id", ""), []).append(doc)

                cursor = self.db.compliance_events.find({"session_id": {"$in": session_ids}})
                async for doc in cursor:
                    doc.pop("_id", None)
                    compliance_docs.setdefault(doc.get("session_id", ""), []).append(doc)
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB session record aggregation failed; using memory fallback: %s", exc)

        for sid, doc in self.memory.items():
            if doc.get("summary"):
                summary_docs.setdefault(sid, doc)
        for sid, doc in self.session_meta_memory.items():
            meta_docs.setdefault(sid, doc)
        for sid, docs in self.transcript_memory.items():
            transcript_docs.setdefault(sid, docs)
        for doc in self.form_memory:
            form_docs.setdefault(doc.get("session_id", ""), []).append(doc)
        for doc in self.compliance_memory:
            compliance_docs.setdefault(doc.get("session_id", ""), []).append(doc)
        for doc in self.history_memory:
            sid = doc.get("session_id", "")
            if sid:
                summary_docs.setdefault(sid, doc)

        results: list[dict] = []
        for sid in set(summary_docs) | set(meta_docs) | set(transcript_docs):
            if not sid or sid in seen_ids:
                continue
            seen_ids.add(sid)
            record = self._normalize_session_record(
                sid,
                summary_docs.get(sid),
                meta_docs.get(sid),
                transcript_docs.get(sid, []),
                form_docs.get(sid, []),
                compliance_docs.get(sid, []),
            )
            results.append(record)

        results.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
        start, end = self._range_bounds(time_range, date_value, month_value, year_value)
        lowered_search = search.lower().strip()
        filtered: list[dict] = []
        for record in results:
            summary = record.get("summary", {})
            if not self._in_bounds(record.get("timestamp", ""), start, end):
                continue
            if service and service != "all" and summary.get("service") != service:
                continue
            if staff_username and summary.get("staffUsername") != staff_username:
                continue
            if lowered_search:
                haystack = " ".join([
                    record.get("session_id", ""),
                    summary.get("service", ""),
                    summary.get("language", ""),
                    summary.get("entities", {}).get("customerName", ""),
                    summary.get("entities", {}).get("pan", ""),
                    summary.get("entities", {}).get("phone", ""),
                ]).lower()
                if lowered_search not in haystack:
                    continue
            filtered.append(record)
        return filtered[:limit]

    # ── Get All Sessions (for History tab) ───────────────────────────────────
    async def get_all_sessions(self) -> list[dict]:
        """Return all session records ordered by timestamp descending."""
        return await self.get_session_records()

    # ── Get Single Session by ID ─────────────────────────────────────────────
    async def get_session_by_id(self, session_id: str) -> dict | None:
        """Return a single session record by session_id."""
        records = await self.get_session_records(limit=500)
        for record in records:
            if record.get("session_id") == session_id:
                return record
        return None

    # ── Customer History Lookup ──────────────────────────────────────────────
    async def get_customer_history(self, pan: str = "", name: str = "") -> list[dict]:
        records = await self.get_session_records(limit=200)
        lowered_name = name.lower().strip()
        normalized_pan = pan.upper().strip()
        results: list[dict] = []
        for record in records:
            entities = record.get("summary", {}).get("entities", {})
            if normalized_pan and entities.get("pan", "").upper() != normalized_pan:
                continue
            if lowered_name and lowered_name not in entities.get("customerName", "").lower():
                continue
            results.append(record)
        return results[:20]

    # ── Branch Analytics ─────────────────────────────────────────────────────
    async def get_analytics(
        self,
        time_range: str = "all",
        date_value: str = "",
        month_value: str = "",
        year_value: str = "",
    ) -> dict:
        """Return aggregated analytics computed from real session data."""
        all_sessions = await self.get_session_records(
            time_range=time_range,
            date_value=date_value,
            month_value=month_value,
            year_value=year_value,
        )

        if not all_sessions:
            return {
                "topServices": [],
                "languages": [],
                "alerts": [],
                "sessions": 0,
                "avgHandleTime": "00:00",
                "autoFillAccuracy": "0%",
                "complianceBlocks": 0,
            }

        # Compute service breakdown
        service_counts: dict[str, int] = {}
        language_counts: dict[str, int] = {}
        total_seconds = 0
        duration_count = 0
        sessions_with_forms = 0
        compliance_blocks = 0

        for doc in all_sessions:
            summary = doc.get("summary", {})
            service = summary.get("service", "Unclassified Session")
            language = self._normalize_language(summary.get("language"))
            duration_str = summary.get("duration", "")
            forms = summary.get("formsFilled", [])
            flags = summary.get("complianceFlags", 0)

            if service and service != "Unclassified Session":
                service_counts[service] = service_counts.get(service, 0) + 1
            if language:
                language_counts[language] = language_counts.get(language, 0) + 1

            if duration_str and ":" in duration_str:
                seconds = self._duration_to_seconds(duration_str)
                if seconds:
                    total_seconds += seconds
                    duration_count += 1

            if forms:
                sessions_with_forms += 1
            compliance_blocks += flags

        # Format service bars (as percentage of total sessions)
        total = len(all_sessions) or 1
        service_total = sum(service_counts.values()) or 1
        language_total = sum(language_counts.values()) or 1
        top_services = sorted(
            [{"label": k, "value": round(v / service_total * 100)} for k, v in service_counts.items()],
            key=lambda x: x["value"],
            reverse=True,
        )[:8]  # Top 8 services

        languages = sorted(
            [{"label": k, "value": round(v / language_total * 100)} for k, v in language_counts.items()],
            key=lambda x: x["value"],
            reverse=True,
        )[:6]  # Top 6 languages

        # Average handle time
        avg_seconds = total_seconds // duration_count if duration_count else 0
        avg_mm = str(avg_seconds // 60).zfill(2)
        avg_ss = str(avg_seconds % 60).zfill(2)

        # Auto-fill rate: percentage of sessions that had at least one completed form.
        accuracy = round((sessions_with_forms / total) * 100) if total else 0

        # Escalation alerts from sessions with negative sentiment
        alerts = []
        for i, doc in enumerate(all_sessions):
            summary = doc.get("summary", {})
            if summary.get("sentiment") == "negative":
                alerts.append({
                    "customer": summary.get("entities", {}).get("customerName") or doc.get("session_id", f"Session {i + 1}"),
                    "reason": summary.get("english", ["Negative sentiment detected"])[0] if summary.get("english") else "Negative sentiment detected",
                    "sentiment": "High frustration",
                })
            elif summary.get("complianceFlags", 0) > 0:
                alerts.append({
                    "customer": summary.get("entities", {}).get("customerName") or doc.get("session_id", f"Session {i + 1}"),
                    "reason": "Compliance flag triggered during session",
                    "sentiment": "Medium risk",
                })

        return {
            "topServices": top_services,
            "languages": languages,
            "alerts": alerts,
            "sessions": len(all_sessions),
            "avgHandleTime": f"{avg_mm}:{avg_ss}",
            "autoFillAccuracy": f"{accuracy}%",
            "complianceBlocks": compliance_blocks,
        }


    # ── Form PDF Storage ─────────────────────────────────────────────────────
    async def save_form_pdf(self, session_id: str, pdf_bytes: bytes) -> None:
        """Store generated form PDF bytes for later download."""
        self.pdf_memory[session_id] = pdf_bytes
        try:
            await self.db.form_pdfs.update_one(
                {"session_id": session_id},
                {"$set": {"session_id": session_id, "pdf_data": pdf_bytes, "timestamp": datetime.now().isoformat()}},
                upsert=True,
            )
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB form PDF save failed for %s; memory copy retained: %s", session_id, exc)

    async def get_form_pdf(self, session_id: str) -> bytes | None:
        """Retrieve stored form PDF bytes."""
        if session_id in self.pdf_memory:
            return self.pdf_memory[session_id]
        try:
            doc = await self.db.form_pdfs.find_one({"session_id": session_id})
            if doc:
                return doc.get("pdf_data")
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB form PDF lookup failed for %s; using memory fallback: %s", session_id, exc)
        return None

    # ── Session Lifecycle ─────────────────────────────────────────────────────
    async def create_session(self, session_id: str, staff_username: str, branch: str, desk_id: str | None = None) -> None:
        """Record that a new live session has started."""
        existing = self.session_meta_memory.get(session_id)
        if existing and existing.get("status") == "active":
            return
        try:
            existing_db = await self.db.sessions.find_one({"session_id": session_id, "status": "active"})
            if existing_db:
                existing_db.pop("_id", None)
                self.session_meta_memory[session_id] = existing_db
                return
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB active session lookup failed for %s: %s", session_id, exc)

        doc = {
            "session_id": session_id,
            "staff_username": staff_username,
            "desk_id": desk_id or "",
            "branch": branch,
            "status": "active",
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "duration_seconds": 0,
            "customer_language": "",
            "customer_name": "",
            "customer_pan": "",
        }
        self.session_meta_memory[session_id] = doc
        try:
            await self.db.sessions.update_one(
                {"session_id": session_id}, {"$set": doc}, upsert=True
            )
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB session create failed for %s; memory copy retained: %s", session_id, exc)

    async def update_session_metadata(self, session_id: str, updates: dict) -> None:
        if session_id in self.session_meta_memory:
            self.session_meta_memory[session_id].update(updates)
        try:
            await self.db.sessions.update_one(
                {"session_id": session_id}, {"$set": updates}
            )
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB session metadata update failed for %s: %s", session_id, exc)

    async def end_session(self, session_id: str) -> None:
        """Mark a session as completed and compute duration."""
        now = datetime.now()
        meta = self.session_meta_memory.get(session_id, {})
        started = meta.get("started_at", now.isoformat())
        try:
            started_dt = datetime.fromisoformat(started)
            duration = int((now - started_dt).total_seconds())
        except (ValueError, TypeError):
            duration = 0
        update = {"status": "completed", "ended_at": now.isoformat(), "duration_seconds": duration}
        if session_id in self.session_meta_memory:
            self.session_meta_memory[session_id].update(update)
        try:
            await self.db.sessions.update_one(
                {"session_id": session_id}, {"$set": update}
            )
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB session end update failed for %s: %s", session_id, exc)

    # ── Transcript Persistence ────────────────────────────────────────────────
    async def save_transcript(self, session_id: str, item: dict) -> None:
        """Persist a single transcript turn."""
        doc = {"session_id": session_id, **item}
        self.transcript_memory.setdefault(session_id, []).append(doc)
        try:
            await self.db.transcripts.insert_one(doc)
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB transcript save failed for %s; memory copy retained: %s", session_id, exc)

    async def get_transcripts(self, session_id: str) -> list[dict]:
        """Retrieve all transcript turns for a session."""
        try:
            cursor = self.db.transcripts.find({"session_id": session_id}).sort("timestamp", 1)
            results = []
            async for doc in cursor:
                doc.pop("_id", None)
                results.append(doc)
            if results:
                return results
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB transcript lookup failed for %s; using memory fallback: %s", session_id, exc)
        return self.transcript_memory.get(session_id, [])

    # ── Compliance Audit Trail ────────────────────────────────────────────────
    async def save_compliance_event(
        self, session_id: str, severity: str, message: str, staff_text: str, action_taken: str
    ) -> None:
        """Record a compliance check result for audit."""
        doc = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "severity": severity,
            "message": message,
            "staff_text": staff_text,
            "action_taken": action_taken,
            "timestamp": datetime.now().isoformat(),
        }
        self.compliance_memory.append(doc)
        try:
            await self.db.compliance_events.insert_one(doc)
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB compliance event save failed for %s; memory copy retained: %s", session_id, exc)

    # ── Form Submission Persistence ───────────────────────────────────────────
    async def save_form_submission(
        self, session_id: str, form_type: str, form_title: str,
        filled_fields: dict, is_complete: bool
    ) -> None:
        """Persist a completed or in-progress form submission."""
        doc = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "form_type": form_type,
            "form_title": form_title,
            "filled_fields": filled_fields,
            "is_complete": is_complete,
            "submitted_at": datetime.now().isoformat(),
        }
        self.form_memory.append(doc)
        try:
            await self.db.form_submissions.update_one(
                {"session_id": session_id, "form_type": form_type},
                {"$set": doc},
                upsert=True,
            )
        except (PyMongoError, ServerSelectionTimeoutError) as exc:
            logger.debug("MongoDB form submission save failed for %s; memory copy retained: %s", session_id, exc)


repository = SessionRepository()
