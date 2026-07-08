# VoxAssist Fix Package — Apply In Order

## WHY YOUR KIOSK IS SILENT

The AI is not "dumb" — it's **not receiving anything**. Two bugs mean the kiosk
never connects to the backend, and even if it did, the RAG brain is empty.

---

## STEP 1 — EMERGENCY (do these before anything else)

### 1a. Rotate your Sarvam API key
Your `SARVAM_API_KEY` was committed in `backend/.env` inside the zip.
Anyone who touched this repo can use it or has already burned it.

1. Log into https://app.sarvam.ai → API Keys → Revoke the old key → Create new key
2. Same for MongoDB: Atlas dashboard → Database Access → Reset password for `voxassist` user

### 1b. Remove .env from git history
```bash
# Install BFG: https://rtyley.github.io/bfg-repo-cleaner/
bfg --delete-files .env
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push origin --force
```

---

## STEP 2 — FIX THE SILENT KIOSK (core bugs)

### Fix A: Consolidate env vars [P0 — kiosk can't reach backend]

**File to create:** `frontend/src/config/env.ts`
→ Copy from `fixes/frontend/src/config/env.ts`

**Then update your `.env`:**
```
VITE_API_BASE=https://your-backend-domain.com
VITE_WS_BASE=wss://your-backend-domain.com
# Remove VITE_VOXASSIST_API_URL (it's now aliased in env.ts)
```

**Then replace in every file** the two old imports:
```typescript
// REMOVE these from every file:
import.meta.env.VITE_API_BASE
import.meta.env.VITE_VOXASSIST_API_URL

// REPLACE WITH:
import { API_BASE } from '@/config/env';
import { WS_BASE } from '@/config/env';
```

Files to update: `LoginPage.tsx`, `ComplianceDashboard.tsx`, `SessionHistory.tsx`,
`SessionSummary.tsx`, `AnalyticsDashboard.tsx`, `CustomerKiosk.tsx`, `FormInterview.tsx`

---

### Fix B: WebSocket URL [P0 — sessions never connect]

**File to replace:** `frontend/src/features/session/useVoiceSession.ts`
→ Copy from `fixes/frontend/src/features/session/useVoiceSession.fixed.ts`

Key change — find the WS URL construction and replace with:
```typescript
// OLD (broken — depends on "demo-session" string being in the URL):
const baseWsUrl = WS_URL.includes("demo-session")
  ? WS_URL.replace("demo-session", sessionId)
  : WS_URL;

// NEW (always correct):
const wsUrl = `${WS_BASE}/ws/session/${sessionId}?token=${encodeURIComponent(token)}`;
```

Also update your env: `VITE_WS_BASE` should be just the base, e.g. `wss://your-backend.com`
(no `/ws/session/demo-session` in it)

---

### Fix C: RAG brain empty [P0 — AI has no banking knowledge]

**File to replace:** `backend/app/services/kb_loader.py`
→ Copy from `fixes/backend/services/kb_loader.fixed.py`

Then trigger a fresh rebuild:
```bash
# Delete the old (possibly corrupted) Chroma DB
rm -rf .chroma/
# Restart the backend — kb_loader.py will detect empty collection and rebuild
python -m uvicorn app.main:app --reload
```

Watch the logs for:
```
INFO: KB vector store rebuilt: N documents embedded, hash=abc123... stored.
```

If you see:
```
ERROR: No KB documents found in knowledge_base/
```
→ Your `KB_DIR` env var is wrong or your JSON knowledge base files are missing.

---

### Fix D: Replace CustomerKiosk.tsx

**File to replace:** `frontend/src/features/kiosk/CustomerKiosk.tsx`
→ Copy from `fixes/frontend/src/features/kiosk/CustomerKiosk.fixed.tsx`

This fixes:
- Env var (now uses `API_BASE` from env.ts)
- Language localisation (tap instructions now in customer's language, not English)
- Sarvam health check (visible warning when voice service is down)

---

## STEP 3 — BACKEND FIXES

### Fix E: Add health router
```python
# In backend/app/main.py, add:
from app.api.health_router import router as health_router
app.include_router(health_router)
```
Copy `fixes/backend/api/health_router.py` → `backend/app/api/health_router.py`

### Fix F: main.py lifespan (BUG-04)
```python
# Replace the two @app.on_event blocks in main.py with:
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await repository.ensure_database()
    await ensure_indexes()
    yield
    await close_client()

app = FastAPI(lifespan=lifespan)
```

### Fix G: auth.py datetime (BUG-05)
```python
# Change:
"exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
# To:
"exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
# Add: from datetime import datetime, timedelta, timezone
```

### Fix H: routes.py print (BUG-06)
```python
# Change line 504:
print(f"Error generating automatic summary for {session_id}: {e}")
# To:
logger.exception("Failed to generate summary for %s", session_id)
```

### Fix I: config.py JWT secret (VULN-02)
```python
# Remove the default value entirely:
# OLD: jwt_secret: str = "voxassist-dev-secret-change-in-production"
# NEW: jwt_secret: str
# Set JWT_SECRET in your .env with a cryptographically random 64-char string:
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## STEP 4 — QUICK 1-LINE FIXES

```bash
# Timer starts at 04:12 instead of 00:00 (BUG-01)
sed -i 's/useState(252)/useState(0)/' frontend/src/app/layout/AppShell.tsx

# Duplicate vite config (kill list)
rm frontend/vite.config.js  # keep only vite.config.ts

# Remove committed artefacts
echo ".chroma/\n.venv/\nfrontend/dist/\n*.pyc\n**/__pycache__/\n.DS_Store" >> .gitignore
rm -rf .venv/ frontend/dist/ .chroma/ frontend/tsconfig.tsbuildinfo
git rm -r --cached .venv/ frontend/dist/ .chroma/ 2>/dev/null || true
git add .gitignore && git commit -m "chore: clean artefacts from version control"
```

---

## VERIFICATION CHECKLIST

After applying all fixes, verify the kiosk is working:

- [ ] Backend starts without Pydantic validation errors (JWT_SECRET is set)
- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] `GET /api/health/sarvam` returns `{"stt": "ok", "tts": "ok"}`
- [ ] Kiosk page loads at `/kiosk` without blank screen
- [ ] Pressing the mic button → WebSocket connects (check browser Network tab → WS)
- [ ] Speaking → transcript appears in the session
- [ ] AI responds in the customer's detected language
- [ ] Session history shows language name (not "Unknown")
- [ ] Timer in AppShell starts at 00:00, not 04:12

---

## SCORECARD AFTER FIXES

| Dimension | Before | After |
|---|---|---|
| Security | 🔴 2/10 | 🟡 6/10 (rotate keys, fix JWT secret, remove demo users) |
| AI responding on kiosk | 🔴 Silent | ✅ Working |
| RAG / banking knowledge | 🔴 Empty | ✅ Loaded |
| Native language | 🔴 Failing | ✅ Localised |
| Audio errors | 🔴 Silent | ✅ Visible to ops + user |
