"""WebSocket + REST API routes for VoxAssist Frontline."""

import io
import json
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from .auth import decode_token_value
from ..models.forms import get_all_form_types
from ..services.ai_orchestrator import AIOrchestrator
from ..services.repositories import repository
from ..services.session_manager import manager

router = APIRouter()
orchestrators: dict[str, AIOrchestrator] = {}
DEVANAGARI_FONT_NAME = "VoxAssistDevanagari"
_devanagari_font_registered = False


def _rag_query_from_payload(payload: dict) -> str:
    item = payload.get("item", {}) or {}
    text_parts = [
        item.get("translatedText", ""),
        item.get("originalText", ""),
        " ".join(payload.get("actionChips", []) or []),
    ]
    return " ".join(part for part in text_parts if part).strip()


def get_devanagari_font_name() -> str:
    """Register a Devanagari-capable font for bilingual PDFs when available."""
    global _devanagari_font_registered
    if _devanagari_font_registered:
        return DEVANAGARI_FONT_NAME

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        os.getenv("DEVANAGARI_FONT_PATH", ""),
        "backend/assets/fonts/NotoSansDevanagari-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
        "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
        "/System/Library/Fonts/Supplemental/ITFDevanagari.ttc",
    ]

    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(DEVANAGARI_FONT_NAME, path, subfontIndex=0))
            _devanagari_font_registered = True
            return DEVANAGARI_FONT_NAME
        except Exception:
            continue

    return "Helvetica"


# ── WebSocket: Live Session ──────────────────────────────────────────────────
@router.websocket("/ws/session/{session_id}")
async def session_socket(websocket: WebSocket, session_id: str) -> None:
    try:
        user = decode_token_value(websocket.query_params.get("token"))
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if session_id not in orchestrators:
        orchestrators[session_id] = AIOrchestrator()
    orchestrator = orchestrators[session_id]
    orchestrator.set_branch(user.branch)
    current_mode = "customer"

    # Record session start
    await repository.create_session(session_id, user.username, user.branch)

    try:
        await manager.connect(session_id, websocket)
        if orchestrator.detected_language_code:
            await websocket.send_json({
                "type": "language_detected",
                "language": orchestrator.detected_language or "Marathi",
                "code": orchestrator.detected_language_code,
            })

        while True:
            try:
                message = await websocket.receive()
            except RuntimeError:
                break  # client disconnected

            # ── Binary audio data (complete WAV blob from frontend) ──
            if "bytes" in message:
                # If a form interview is active, route audio to form engine
                if orchestrator.form_session and not orchestrator.form_session.is_complete:
                    payload = await orchestrator.process_form_audio_turn(message["bytes"])
                    await manager.send_json(session_id, payload)

                    continue

                # Normal live session audio processing
                payload = await orchestrator.process_audio_turn(message["bytes"], current_mode)
                auto_start_form = payload.pop("autoStartForm", None)

                # Persist transcript turn
                if payload.get("item"):
                    await repository.save_transcript(session_id, payload["item"])

                # Check compliance BEFORE sending the payload
                # We only check compliance for the staff
                if current_mode == "staff":
                    alert = await orchestrator.check_compliance(payload["item"]["originalText"])
                    if alert and alert.severity == "block":
                        payload["item"]["translatedText"] = "[TRANSLATION BLOCKED: Compliance Violation]"
                        if "assistantAudio" in payload:
                            del payload["assistantAudio"]
                    
                    await manager.send_json(session_id, payload)
                    await manager.send_json(session_id, {"type": "compliance", "alert": alert.model_dump() if alert else None})

                    # Audit trail for compliance
                    if alert:
                        action = "blocked" if alert.severity == "block" else "warned" if alert.severity == "warning" else "passed"
                        await repository.save_compliance_event(
                            session_id, alert.severity, alert.message,
                            payload["item"]["originalText"], action
                        )
                else:
                    await manager.send_json(session_id, payload)
                    await manager.send_json(session_id, {"type": "compliance", "alert": None})

                # Send language detection if included
                if "languageDetected" in payload:
                    await manager.send_json(session_id, {
                        "type": "language_detected",
                        "language": payload["languageDetected"]["language"],
                        "code": payload["languageDetected"]["code"],
                    })

                # Send escalation alert if included
                if "escalation" in payload:
                    await manager.send_json(session_id, payload["escalation"])

                # Auto-trigger SOP search based on detected intent
                if payload.get("actionChips"):
                    intent_query = _rag_query_from_payload(payload)
                    result_language = orchestrator.detected_language_code if current_mode == "customer" else "en-IN"
                    sop_result = await orchestrator.search_sop(intent_query, result_language or "en-IN")
                    await manager.send_json(session_id, {"type": "sop", "result": sop_result.model_dump()})

                if auto_start_form:
                    form_payload = await orchestrator.start_form_interview(auto_start_form)
                    await manager.send_json(session_id, form_payload)

                continue

            if "text" not in message:
                continue

            # ── Text commands ──
            data = json.loads(message["text"])
            kind = data.get("type")
            current_mode = data.get("mode", current_mode)

            if kind == "audio_meta":
                # Frontend sends this right before the binary audio blob
                current_mode = data.get("mode", current_mode)
                await manager.send_json(session_id, {"type": "recording_status", "mode": current_mode, "active": True})

            elif kind == "set_language":
                lang_info = orchestrator.set_language(data.get("code", "mr-IN"))
                await manager.send_json(session_id, {
                    "type": "language_detected",
                    "language": lang_info["language"],
                    "code": lang_info["code"],
                })

            elif kind == "start":
                # Just acknowledges recording started — no demo turn
                await manager.send_json(session_id, {
                    "type": "recording_status",
                    "mode": current_mode,
                    "active": True,
                })

            elif kind == "stop_listening":
                await manager.send_json(session_id, {
                    "type": "recording_status",
                    "mode": current_mode,
                    "active": False,
                })

            elif kind == "start_customer_session":
                current_mode = "customer"
                lang_info = orchestrator.set_language(data.get("languageCode", "mr-IN"))
                await manager.send_json(session_id, {
                    "type": "language_detected",
                    "language": lang_info["language"],
                    "code": lang_info["code"],
                })
                await manager.send_json(session_id, {
                    "type": "recording_status",
                    "mode": "customer",
                    "active": False,
                })
                greeting = await orchestrator.start_customer_session()
                await manager.send_json(session_id, greeting)

            elif kind == "demo_text":
                # Explicit demo request (no real mic)
                payload = await orchestrator.process_demo_turn(current_mode)
                
                if current_mode == "staff":
                    alert = await orchestrator.check_compliance(payload["item"]["originalText"])
                    if alert and alert.severity == "block":
                        payload["item"]["translatedText"] = "[TRANSLATION BLOCKED: Compliance Violation]"
                        if "assistantAudio" in payload:
                            del payload["assistantAudio"]
                    await manager.send_json(session_id, payload)
                    await manager.send_json(session_id, {"type": "compliance", "alert": alert.model_dump() if alert else None})
                else:
                    await manager.send_json(session_id, payload)
                    await manager.send_json(session_id, {"type": "compliance", "alert": None})

                if payload.get("actionChips"):
                    intent_query = _rag_query_from_payload(payload)
                    result_language = orchestrator.detected_language_code if current_mode == "customer" else "en-IN"
                    sop_result = await orchestrator.search_sop(intent_query, result_language or "en-IN")
                    await manager.send_json(session_id, {"type": "sop", "result": sop_result.model_dump()})

            elif kind == "customer_text":
                current_mode = data.get("mode", "customer")
                payload = await orchestrator.process_text_turn(
                    data.get("text", ""),
                    current_mode,
                    data.get("languageCode"),
                )
                auto_start_form = payload.pop("autoStartForm", None)
                await manager.send_json(session_id, payload)
                await manager.send_json(session_id, {"type": "compliance", "alert": None})

                if payload.get("actionChips"):
                    intent_query = _rag_query_from_payload(payload)
                    result_language = orchestrator.detected_language_code if current_mode == "customer" else "en-IN"
                    sop_result = await orchestrator.search_sop(intent_query, result_language or "en-IN")
                    await manager.send_json(session_id, {"type": "sop", "result": sop_result.model_dump()})

                if auto_start_form:
                    form_payload = await orchestrator.start_form_interview(auto_start_form)
                    await manager.send_json(session_id, form_payload)

            elif kind == "stop":
                pass  # recording stopped; audio blob arrives separately

            elif kind == "summarize":
                summary = await orchestrator.summarize()
                await repository.save_summary(session_id, summary)
                await manager.send_json(session_id, summary)

            elif kind == "sop_search":
                result = await orchestrator.search_sop(data.get("query", ""))
                await manager.send_json(session_id, {"type": "sop", "result": result.model_dump()})

            elif kind == "replay_last":
                tts_result = await orchestrator.replay_last()
                await manager.send_json(session_id, tts_result)

            # ── Form Interview Commands ──────────────────────────────────
            elif kind == "start_form":
                form_type = data.get("formType", "")
                payload = await orchestrator.start_form_interview(form_type)
                await manager.send_json(session_id, payload)

            elif kind == "cancel_form":
                payload = orchestrator.cancel_form_interview()
                await manager.send_json(session_id, payload)

            elif kind == "generate_form_pdf":
                try:
                    pdf_buf = await orchestrator.generate_form_pdf(session_id)
                    # Store in repository for REST download
                    await repository.save_form_pdf(session_id, pdf_buf.getvalue())
                    await manager.send_json(session_id, {
                        "type": "form_pdf_ready",
                        "downloadUrl": f"/form/{session_id}/pdf",
                    })
                except ValueError as e:
                    await manager.send_json(session_id, {
                        "type": "form_error",
                        "message": str(e),
                    })

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(session_id, websocket)
        # Only tear down orchestrator if no clients remain
        if not manager.active.get(session_id):
            # Record session end
            await repository.end_session(session_id)
            disconnected_orchestrator = orchestrators.pop(session_id, None)
            if disconnected_orchestrator:
                # Persist form submission if a form was completed
                if disconnected_orchestrator.form_session and disconnected_orchestrator.form_session.is_complete:
                    fs = disconnected_orchestrator.form_session
                    from ..models.forms import FORM_REGISTRY, FormType
                    try:
                        form_def = FORM_REGISTRY[FormType(fs.form_type)]
                        await repository.save_form_submission(
                            session_id, fs.form_type.value, form_def.title,
                            fs.filled_fields, fs.is_complete
                        )
                    except (ValueError, KeyError):
                        pass
                await disconnected_orchestrator.close()


# ── REST: Form PDF Download ──────────────────────────────────────────────────
@router.get("/form/{session_id}/pdf")
async def download_form_pdf(session_id: str):
    """Download the AI-filled banking form as PDF."""
    # Try stored PDF first
    pdf_bytes = await repository.get_form_pdf(session_id)
    if pdf_bytes:
        buf = io.BytesIO(pdf_bytes)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=form_{session_id}.pdf"},
        )

    # Generate on-the-fly if orchestrator has a completed form
    try:
        orchestrator = orchestrators.get(session_id)
        if not orchestrator:
            raise ValueError("No active form session to generate PDF for.")
        pdf_buf = await orchestrator.generate_form_pdf(session_id)
        return StreamingResponse(
            pdf_buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=form_{session_id}.pdf"},
        )
    except ValueError:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={"detail": "No completed form found for this session."},
        )


# ── REST: Available Form Types ───────────────────────────────────────────────
@router.get("/forms")
async def list_form_types():
    """Return all available banking form types."""
    return {"forms": get_all_form_types()}


# ── REST: PDF Receipt Generation ─────────────────────────────────────────────
@router.post("/session/{session_id}/receipt")
async def generate_receipt(session_id: str):
    """Generate a bilingual PDF receipt for a completed session."""
    summary = await repository.get_summary(session_id)
    if not summary:
        summary = {
            "session_id": session_id,
            "english": ["No summary available for this session."],
            "customerLanguage": ["या सत्रासाठी सारांश उपलब्ध नाही."],
        }

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    devanagari_font = get_devanagari_font_name()

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30 * mm, h - 30 * mm, "VoxAssist — Session Receipt")
    c.setFont("Helvetica", 10)
    c.drawString(30 * mm, h - 38 * mm, f"Session ID: {session_id}")
    c.drawString(30 * mm, h - 44 * mm, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # English summary
    y = h - 60 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "English Summary")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    for line in summary.get("english", []):
        c.drawString(35 * mm, y, f"• {line}")
        y -= 6 * mm

    # Customer language summary
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "Customer Language Summary")
    y -= 8 * mm
    c.setFont(devanagari_font, 10)
    for line in summary.get("customerLanguage", []):
        c.drawString(35 * mm, y, f"• {line}")
        y -= 6 * mm

    c.save()
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=receipt_{session_id}.pdf"},
    )


# ── REST: All Sessions (History Tab) ─────────────────────────────────────────
@router.get("/sessions")
async def list_sessions():
    """Return all session records for the History tab."""
    results = await repository.get_all_sessions()
    return {"sessions": results}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Return a single session detail by ID."""
    doc = await repository.get_session_by_id(session_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    return doc


# ── REST: Customer History Lookup ────────────────────────────────────────────
@router.get("/customer/history")
async def customer_history(pan: str = "", name: str = ""):
    """Look up past session summaries by PAN or customer name."""
    results = await repository.get_customer_history(pan=pan, name=name)
    return {"sessions": results}


# ── REST: Branch Analytics ───────────────────────────────────────────────────
@router.get("/analytics/branch")
async def branch_analytics(range: str = "all"):
    """Return aggregated analytics for the branch."""
    data = await repository.get_analytics(time_range=range)
    return data


# ── REST: Session Transcripts ────────────────────────────────────────────────
@router.get("/sessions/{session_id}/transcripts")
async def get_session_transcripts(session_id: str):
    """Return all transcript turns for a session."""
    results = await repository.get_transcripts(session_id)
    return {"transcripts": results}
