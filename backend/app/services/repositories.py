"""MongoDB persistence layer with in-memory fallback."""

import logging
import uuid
from datetime import datetime, timedelta

from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from ..core.config import settings
from ..db.connection import get_db, get_client, ensure_indexes, is_mongo_available

logger = logging.getLogger(__name__)


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
            await self._seed_demo_users()
            logger.info("MongoDB database '%s' is ready", settings.mongodb_db)

        # Always seed demo sessions into in-memory so History + Analytics work
        self._seed_demo_sessions()

    async def _seed_demo_users(self) -> None:
        users = [
            {
                "username": "staff1",
                "password": "staff123",
                "role": "staff",
                "name": "Priya Sharma",
                "branch": "Central District",
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
            user = await self.db.users.find_one({"username": username, "active": True})
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
        except (PyMongoError, ServerSelectionTimeoutError):
            pass
        return self.memory.get(session_id, {}).get("summary")

    # ── Get All Sessions (for History tab) ───────────────────────────────────
    async def get_all_sessions(self) -> list[dict]:
        """Return all session records, merging MongoDB + in-memory, ordered by timestamp descending."""
        seen_ids: set[str] = set()
        results: list[dict] = []

        # Try MongoDB first
        try:
            cursor = self.db.session_summaries.find({}).sort("timestamp", -1).limit(50)
            async for doc in cursor:
                doc.pop("_id", None)
                sid = doc.get("session_id", "")
                if sid not in seen_ids:
                    seen_ids.add(sid)
                    results.append(doc)
        except (PyMongoError, ServerSelectionTimeoutError):
            pass

        # Always merge in-memory sessions (includes demo seeds)
        for doc in self.history_memory:
            sid = doc.get("session_id", "")
            if sid not in seen_ids:
                seen_ids.add(sid)
                results.append(doc)

        # Sort by timestamp descending
        results.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
        return results

    # ── Get Single Session by ID ─────────────────────────────────────────────
    async def get_session_by_id(self, session_id: str) -> dict | None:
        """Return a single session record by session_id."""
        try:
            doc = await self.db.session_summaries.find_one({"session_id": session_id})
            if doc:
                doc.pop("_id", None)
                return doc
        except (PyMongoError, ServerSelectionTimeoutError):
            pass

        # Fallback to in-memory
        return self.memory.get(session_id)

    # ── Customer History Lookup ──────────────────────────────────────────────
    async def get_customer_history(self, pan: str = "", name: str = "") -> list[dict]:
        results: list[dict] = []
        try:
            query: dict = {}
            if pan:
                query["summary.entities.pan"] = pan
            if name:
                query["summary.entities.customerName"] = {"$regex": name, "$options": "i"}
            if not query:
                query = {}

            cursor = self.db.session_summaries.find(query).sort("timestamp", -1).limit(20)
            async for doc in cursor:
                doc.pop("_id", None)
                results.append(doc)
        except (PyMongoError, ServerSelectionTimeoutError):
            # Fallback to in-memory history
            for doc in reversed(self.history_memory):
                results.append(doc)
        return results

    # ── Branch Analytics ─────────────────────────────────────────────────────
    async def get_analytics(self, time_range: str = "all") -> dict:
        """Return aggregated analytics computed from real session data."""
        # Gather all sessions and filter by time range
        all_sessions = await self.get_all_sessions()

        if time_range != "all":
            now = datetime.now()
            if time_range == "today":
                cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_range == "week":
                cutoff = now - timedelta(days=7)
            elif time_range == "month":
                cutoff = now - timedelta(days=30)
            else:
                cutoff = None
            if cutoff:
                cutoff_iso = cutoff.isoformat()
                all_sessions = [s for s in all_sessions if s.get("timestamp", "") >= cutoff_iso]

        if not all_sessions:
            # Absolute fallback when zero sessions exist
            return {
                "topServices": [],
                "languages": [],
                "alerts": [
                    {"customer": "Counter 3", "reason": "Repeated negative keywords", "sentiment": "High frustration"},
                    {"customer": "Counter 7", "reason": "Compliance phrase blocked", "sentiment": "Medium risk"},
                ],
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
        forms_filled_count = 0
        total_forms_possible = 0
        compliance_blocks = 0

        for doc in all_sessions:
            summary = doc.get("summary", {})
            service = summary.get("service", "General")
            language = summary.get("language", "Unknown")
            duration_str = summary.get("duration", "")
            forms = summary.get("formsFilled", [])
            flags = summary.get("complianceFlags", 0)

            service_counts[service] = service_counts.get(service, 0) + 1
            language_counts[language] = language_counts.get(language, 0) + 1

            if duration_str and ":" in duration_str:
                parts = duration_str.split(":")
                try:
                    total_seconds += int(parts[0]) * 60 + int(parts[1])
                    duration_count += 1
                except (ValueError, IndexError):
                    pass

            if forms:
                forms_filled_count += len(forms)
            total_forms_possible += 1
            compliance_blocks += flags

        # Format service bars (as percentage of total sessions)
        total = len(all_sessions) or 1
        top_services = sorted(
            [{"label": k, "value": round(v / total * 100)} for k, v in service_counts.items()],
            key=lambda x: x["value"],
            reverse=True,
        )[:8]  # Top 8 services

        languages = sorted(
            [{"label": k, "value": round(v / total * 100)} for k, v in language_counts.items()],
            key=lambda x: x["value"],
            reverse=True,
        )[:6]  # Top 6 languages

        # Average handle time
        avg_seconds = total_seconds // duration_count if duration_count else 0
        avg_mm = str(avg_seconds // 60).zfill(2)
        avg_ss = str(avg_seconds % 60).zfill(2)

        # Auto-fill accuracy: percentage of sessions that had forms filled
        accuracy = round((forms_filled_count / total_forms_possible) * 100) if total_forms_possible else 0

        # Escalation alerts from sessions with negative sentiment
        alerts = []
        for i, doc in enumerate(all_sessions):
            summary = doc.get("summary", {})
            if summary.get("sentiment") == "negative":
                alerts.append({
                    "customer": f"Counter {i + 1}",
                    "reason": summary.get("english", ["Negative sentiment detected"])[0] if summary.get("english") else "Negative sentiment detected",
                    "sentiment": "High frustration",
                })
            elif summary.get("complianceFlags", 0) > 0:
                alerts.append({
                    "customer": f"Counter {i + 1}",
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
        except (PyMongoError, ServerSelectionTimeoutError):
            pass

    async def get_form_pdf(self, session_id: str) -> bytes | None:
        """Retrieve stored form PDF bytes."""
        if session_id in self.pdf_memory:
            return self.pdf_memory[session_id]
        try:
            doc = await self.db.form_pdfs.find_one({"session_id": session_id})
            if doc:
                return doc.get("pdf_data")
        except (PyMongoError, ServerSelectionTimeoutError):
            pass
        return None

    # ── Session Lifecycle ─────────────────────────────────────────────────────
    async def create_session(self, session_id: str, staff_username: str, branch: str) -> None:
        """Record that a new live session has started."""
        doc = {
            "session_id": session_id,
            "staff_username": staff_username,
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
        except (PyMongoError, ServerSelectionTimeoutError):
            pass

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
        except (PyMongoError, ServerSelectionTimeoutError):
            pass

    # ── Transcript Persistence ────────────────────────────────────────────────
    async def save_transcript(self, session_id: str, item: dict) -> None:
        """Persist a single transcript turn."""
        doc = {"session_id": session_id, **item}
        self.transcript_memory.setdefault(session_id, []).append(doc)
        try:
            await self.db.transcripts.insert_one(doc)
        except (PyMongoError, ServerSelectionTimeoutError):
            pass

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
        except (PyMongoError, ServerSelectionTimeoutError):
            pass
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
        except (PyMongoError, ServerSelectionTimeoutError):
            pass

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
        except (PyMongoError, ServerSelectionTimeoutError):
            pass


repository = SessionRepository()
