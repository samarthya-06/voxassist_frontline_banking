# VoxAssist Frontline

Gen-AI powered multilingual voice assistant for frontline bank staff. The project is split into a React dashboard and a Python FastAPI AI/audio orchestration service.

## Stack

- Frontend: React + Vite + Tailwind + Shadcn-style components + Redux Toolkit
- Backend: FastAPI + async WebSockets
- Persistence: MongoDB-ready repository layer
- Vector search: persistent ChromaDB trusted knowledge retrieval
- AI adapters: Sarvam/Gemini integration points with grounded RAG fallback

## Project Structure

The source is organized around deployable apps and shared support folders:

- `frontend/src/app`: React app bootstrap, app shell, typed Redux hooks, and store setup
- `frontend/src/features`: product features such as auth, live session, kiosk, analytics, and history
- `frontend/src/shared`: reusable UI primitives and utilities
- `backend/app`: FastAPI API, configuration, models, services, and database access
- `backend/data`: trusted KB and SOP content used by RAG
- `deploy`: deployment scripts and infrastructure configuration
- `docs`: deployment docs plus archived design inspiration

Design-only HTML reference folders are preserved in `docs/design-inspiration` so they no longer clutter the repository root.

## Run Locally

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

Frontend defaults to `http://localhost:5173` and expects the backend WebSocket at `ws://localhost:8000/ws/session/demo-session`.

## Database and RAG Setup

Start MongoDB locally:

```bash
docker compose up -d mongo
```

Optional Mongo web UI:

```bash
docker compose up -d mongo-express
```

Mongo Express runs at `http://localhost:8081`. On backend startup, VoxAssist creates the required indexes and seeds demo users:

- `staff1` / `staff123`
- `manager1` / `manager123`

Trusted RAG content lives in `backend/data/kb`. The backend indexes these files into persistent ChromaDB at `CHROMA_PERSIST_DIR` and uses retrieval before Sarvam answers policy questions. If MongoDB, ChromaDB, or Sarvam is unavailable, the backend falls back gracefully to local in-memory/session behavior and deterministic trusted KB excerpts.

## Environment

Copy `backend/.env.example` to `backend/.env` when adding real providers.

```bash
SARVAM_API_KEY=
GEMINI_API_KEY=
MONGODB_URI=mongodb://localhost:27017
CHROMA_PERSIST_DIR=.chroma
KB_DATA_DIR=backend/data/kb
DEFAULT_BRANCH_ID=default
RAG_TOP_K=5
RAG_MIN_CONFIDENCE=0.18
RAG_USE_LLM=false
AI_FAST_MODE=true
```

## AWS Deployment

For HTTPS, WSS, EC2, S3, CloudFront, and custom-domain deployment, see [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md).
