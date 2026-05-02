# VoxAssist Frontline Banking Dashboard - Project Study Documentation

## Problem Statement

VoxAssist Frontline is a Gen-AI powered multilingual voice assistant designed for frontline bank staff and branch customers. The system helps staff communicate with customers who speak different Indian languages, retrieve trusted banking SOPs, detect compliance-sensitive statements, fill banking forms through voice, generate receipts, and provide branch-level analytics.

The core problem addressed by the project is the communication, documentation, and policy-support gap at bank counters. Frontline staff often need to serve customers in regional languages, follow changing product rules, complete forms accurately, and avoid non-compliant promises. Manual translation, manual form filling, and manual SOP lookup increase service time and create operational risk. VoxAssist reduces these issues by combining live voice interaction, translation, grounded knowledge retrieval, form automation, session summaries, and analytics in one web application.

## Background of the Problem / Idea

Bank branches serve customers with varied languages, literacy levels, and service needs. A customer may ask about account opening, KYC update, fixed deposit rates, cards, loans, fund transfers, lockers, or government schemes. Staff must answer correctly, explain documents and charges, and complete required forms while maintaining compliance.

The project idea is to provide a voice-first assistant that sits between the customer and the bank staff. It listens to customer or staff speech, converts it into text, translates it when required, extracts important banking entities, suggests next actions, retrieves approved SOP content, and helps complete banking forms step by step. It also supports a customer kiosk mode for self-service voice conversations.

The implementation uses a React frontend and a FastAPI backend. The backend integrates with Sarvam AI for speech-to-text, translation, text-to-speech, and optional LLM responses. Trusted banking knowledge is loaded from JSON files and indexed through ChromaDB with a deterministic fallback retrieval method. MongoDB is used for users, session summaries, and analytics data, with in-memory fallback for demo use.

## Project Scope

The system covers:

- Secure staff and manager login with JWT-based authentication.
- Live voice session for customer and staff interaction.
- Multilingual support for Marathi, Hindi, English, Gujarati, Kannada, Tamil, Telugu, Bengali, Malayalam, and Punjabi.
- Speech-to-text, translation, and text-to-speech workflow.
- Trusted SOP and banking knowledge retrieval using RAG.
- Compliance guardrails for risky phrases such as guaranteed returns or misleading promises.
- AI-assisted voice form filling for KYC, account opening, fixed deposit, loan, and card applications.
- Session summaries, customer history lookup, receipt PDF generation, and form PDF generation.
- Branch analytics including top services, language mix, average handle time, form usage, compliance flags, and escalation alerts.
- Customer kiosk mode for simplified customer-facing voice interaction.

## Work Breakdown Structure

### Project Initiation and Planning

The initiation phase defines the branch banking problem, target users, main workflows, and expected project modules. The project identifies two major user groups: frontline staff and branch managers. Staff need live operational support, while managers need analytics and escalation visibility. The project also includes a customer kiosk route for direct customer interaction.

Key activities:

- Define problem statement and functional objectives.
- Identify user roles: staff, manager, customer kiosk.
- Select technology stack: React, Vite, Tailwind CSS, Redux Toolkit, FastAPI, MongoDB, ChromaDB, Sarvam AI.
- Define demo credentials and local development setup.
- Prepare knowledge-base data for SOP retrieval.

### System Design

The system follows a client-server architecture.

- Frontend: React single-page application with Redux Toolkit state management.
- Backend: FastAPI service with REST APIs and WebSocket communication.
- Real-time channel: WebSocket endpoint `/ws/session/{session_id}`.
- Persistence: MongoDB-ready repository layer with in-memory fallback.
- Knowledge retrieval: ChromaDB collection `banking_knowledge` backed by JSON knowledge files.
- AI orchestration: `AIOrchestrator` handles STT, translation, TTS, entity extraction, action suggestions, compliance checks, RAG, summaries, and form interviews.

Major design modules:

- Authentication module: login, JWT generation, token validation, role support.
- Session module: live transcript, listen mode, language selection, recording, assistant responses.
- RAG module: trusted SOP search with citations and confidence score.
- Form module: voice-based form interview and PDF generation.
- Analytics module: session aggregation and branch dashboard.
- Kiosk module: customer-facing continuous voice interaction.

### Frontend Development

The frontend is located in `frontend/src` and is built using React, Vite, TypeScript, Tailwind CSS, Redux Toolkit, and lucide-react icons.

Important frontend files:

- `frontend/src/App.tsx`: Main application routing between login, live session, summary, analytics, history, and kiosk mode.
- `frontend/src/components/layout/AppShell.tsx`: Main authenticated shell with top navigation, sidebar, language status, timer, and alerts.
- `frontend/src/features/auth/LoginPage.tsx`: Staff and manager login screen.
- `frontend/src/features/session/LiveSession.tsx`: Main staff dashboard for transcript, action suggestions, form filling, SOPs, and guardrails.
- `frontend/src/features/session/useVoiceSession.ts`: WebSocket connection, recording, WAV conversion, message handling, and TTS playback.
- `frontend/src/features/session/sessionSlice.ts`: Redux state for transcript, entities, compliance, SOP result, summary, and form interview.
- `frontend/src/features/session/FormInterview.tsx`: AI voice form-filling UI.
- `frontend/src/features/session/SessionSummary.tsx`: Bilingual summary, extracted entities, receipt generation, and customer history.
- `frontend/src/features/session/SessionHistory.tsx`: Session list, search, filters, and detailed past session view.
- `frontend/src/features/analytics/AnalyticsDashboard.tsx`: Manager analytics dashboard.
- `frontend/src/features/kiosk/CustomerKiosk.tsx`: Customer-facing kiosk screen.
- `frontend/src/features/kiosk/useKioskSession.ts`: Continuous voice loop for kiosk mode using browser speech recognition or VAD audio fallback.

Frontend features:

- Login screen with staff and manager role selection.
- Push-to-talk recording and spacebar shortcut.
- Customer/staff listen modes.
- Live transcript with original text and auto-translation.
- Low-confidence ASR warning and re-record option.
- Suggested action chips based on detected banking intent.
- SOP search panel with trusted answer, citations, confidence, effective date, and verification warning.
- Compliance alert panel and escalation alert.
- AI form selection, question display, progress tracking, auto-filled field display, and PDF download.
- Summary and history pages for session records.
- Analytics dashboard for manager insights.
- Customer kiosk route at `/kiosk`.

### Backend Development

The backend is located in `backend/app` and is built using FastAPI, Pydantic, Motor, ChromaDB, httpx, PyJWT, passlib, and ReportLab.

Important backend files:

- `backend/app/main.py`: FastAPI app creation, CORS setup, route registration, startup database initialization, and health endpoint.
- `backend/app/api/auth.py`: Login route, JWT creation, token decoding, demo users, and role dependency helpers.
- `backend/app/api/routes.py`: WebSocket session route and REST endpoints for forms, PDFs, receipts, sessions, customer history, and analytics.
- `backend/app/services/ai_orchestrator.py`: Main AI workflow for STT, translation, TTS, entity extraction, action suggestions, RAG, compliance, sentiment, summaries, and form interviews.
- `backend/app/services/rag_service.py`: Grounded answer generation over trusted banking knowledge.
- `backend/app/services/vector_store.py`: ChromaDB vector store and lexical fallback retrieval.
- `backend/app/services/kb_loader.py`: Knowledge-base JSON loading and chunking.
- `backend/app/services/repositories.py`: MongoDB persistence layer with in-memory fallback and demo session seed data.
- `backend/app/services/session_manager.py`: WebSocket connection manager for broadcasting messages to multiple clients in a session.
- `backend/app/models/session.py`: Pydantic models for transcript, SOP result, citations, compliance alert, sentiment, and summary.
- `backend/app/models/forms.py`: Banking form definitions and form interview runtime state.

Backend REST endpoints:

- `GET /health`: Service health check.
- `POST /auth/login`: Staff or manager login.
- `GET /forms`: Available banking form types.
- `GET /form/{session_id}/pdf`: Download completed AI-filled form.
- `POST /session/{session_id}/receipt`: Generate bilingual session receipt PDF.
- `GET /sessions`: List session records.
- `GET /sessions/{session_id}`: Fetch one session record.
- `GET /customer/history`: Search previous sessions by PAN or customer name.
- `GET /analytics/branch`: Branch analytics.

Backend WebSocket endpoint:

- `/ws/session/{session_id}?token={jwt}`: Real-time voice session channel.

Supported WebSocket message types include:

- `set_language`
- `start`
- `stop_listening`
- `start_customer_session`
- `audio_meta`
- Binary audio blob
- `demo_text`
- `customer_text`
- `summarize`
- `sop_search`
- `replay_last`
- `start_form`
- `cancel_form`
- `generate_form_pdf`

### Integration

Frontend and backend integration is mainly through WebSocket communication. The frontend records speech using `MediaRecorder`, converts browser audio to WAV, and sends the audio blob to the backend. The backend processes the audio through the AI orchestrator and sends structured JSON responses back to the frontend.

Integration flow:

1. User logs in through `/auth/login`.
2. Frontend stores token in local state.
3. Frontend opens WebSocket with token query parameter.
4. User records speech in customer or staff mode.
5. Audio is sent to the backend WebSocket.
6. Backend performs STT, translation, entity extraction, action suggestions, compliance checks, sentiment analysis, RAG, and TTS.
7. Backend broadcasts transcript, assistant response, SOP result, compliance alert, or form event to connected clients.
8. Frontend updates Redux state and UI panels.
9. For completed forms or receipts, frontend calls/downloads REST PDF endpoints.

Customer kiosk integration uses the same WebSocket session. This allows staff dashboard and kiosk screen to observe the same interaction.

### Testing and Quality Assurance

The repository includes backend RAG tests in `backend/tests/test_rag.py`. These tests verify:

- FD rate queries retrieve trusted fixed deposit rate-card content.
- Branch-specific policy can override default policy context.
- Unknown or unsupported policy queries require staff verification.

Recommended QA activities:

- Unit test AI fallback functions such as entity extraction, action suggestion, compliance keyword detection, and form intent detection.
- Unit test form registry and form progress calculations.
- Integration test WebSocket message flow for customer text, demo text, SOP search, form start, form completion, and summary.
- API test login, session list, customer history, analytics, form list, receipt generation, and form PDF download.
- Frontend test major flows: login, live session, action chips, SOP panel, form interview, session history, analytics, and kiosk.
- Manual voice test with microphone permissions, low-confidence behavior, replay TTS, and reconnect behavior.

### Deployment and Configuration

The project can run locally with separate frontend and backend services.

Frontend:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Backend:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

MongoDB:

```bash
docker compose up -d mongo
```

Mongo Express:

```bash
docker compose up -d mongo-express
```

Important environment variables:

- `SARVAM_API_KEY`: Sarvam AI API key.
- `GEMINI_API_KEY`: Gemini API key placeholder/integration point.
- `MONGODB_URI`: MongoDB connection URL.
- `CHROMA_PERSIST_DIR`: ChromaDB persistence directory.
- `KB_DATA_DIR`: Trusted knowledge-base directory.
- `DEFAULT_BRANCH_ID`: Default branch context for RAG.
- `RAG_TOP_K`: Number of retrieved chunks.
- `RAG_MIN_CONFIDENCE`: Minimum RAG score.
- `RAG_USE_LLM`: Whether to use LLM phrasing for RAG answers.
- `AI_FAST_MODE`: Use deterministic fallback logic for faster demo response.
- `JWT_SECRET`: JWT signing secret.

### Documentation

Project documentation should cover:

- Functional overview and user roles.
- Architecture and technology stack.
- Frontend module descriptions.
- Backend API and WebSocket message contracts.
- Database collections and indexes.
- RAG knowledge-base structure.
- Form definitions and form workflow.
- Testing approach and test cases.
- Deployment steps and environment variables.
- Limitations and future enhancements.

### Maintenance and Future Enhancements

Maintenance includes updating SOP JSON files, validating rates and charges, rotating secrets, monitoring AI provider availability, improving test coverage, updating dependencies, and reviewing compliance rules. Future work can include stronger RBAC, persistent form PDF storage in MongoDB/GridFS or object storage, production logging, audit trails, admin screens for knowledge-base updates, and integration with core banking systems.

### Project Closure

The project can be considered complete for study/demo purposes when:

- Staff login and manager login work.
- Live session WebSocket connects successfully.
- Customer and staff voice/text turns produce transcript entries.
- SOP search returns trusted answers with citations.
- Form interviews can start, progress, complete, and generate PDFs.
- Session summaries and receipt PDFs can be generated.
- Session history and analytics show seeded or real data.
- RAG tests pass.
- Documentation is prepared and reviewed.

## Resource Allocation Sheet

### Task-wise Resource Allocation

| Task | Human Resource | Technical Resource | Output |
|---|---|---|---|
| Requirement analysis | Project guide, developer, domain observer | Existing banking process study | Problem statement and scope |
| UI/UX design | Frontend developer | React, Tailwind, lucide-react | Login, dashboard, kiosk, analytics, history screens |
| Frontend implementation | Frontend developer | React, Vite, TypeScript, Redux Toolkit | SPA with live session and state management |
| Backend API implementation | Backend developer | FastAPI, Pydantic, Uvicorn | REST APIs and WebSocket endpoint |
| AI orchestration | Backend/AI developer | Sarvam AI, httpx, deterministic fallback logic | STT, translation, TTS, entity extraction, compliance, summaries |
| RAG implementation | Backend/AI developer | ChromaDB, JSON KB, lexical fallback | Trusted SOP search with citations |
| Database implementation | Backend developer | MongoDB, Motor, in-memory fallback | Users, session summaries, analytics data |
| Form automation | Full-stack developer | Pydantic/dataclasses, React form UI, ReportLab | Voice form filling and PDF generation |
| Testing | Developer/tester | unittest, browser/manual tests | RAG tests and functional validation |
| Deployment setup | Developer | npm, Python venv, Docker Compose | Local runnable system |
| Documentation | Developer/student | Markdown/project report | Final project study document |

## Database Design

### Overview

The project does not use the `reports`, `social_posts`, or `hotspots` tables mentioned in the provided outline. Those names appear to belong to a different geospatial or social-monitoring project. In this project, the correct data model is banking-session oriented.

Actual persistent/logical data areas:

- Users for authentication and role access.
- Session summaries for past branch interactions.
- Form PDF storage for generated form documents.
- Knowledge audit metadata for approved knowledge versions.
- Trusted knowledge documents loaded from JSON and indexed into ChromaDB.
- Runtime WebSocket session state and Redux frontend state.

### Database Technology

Primary database technology:

- MongoDB 7, configured in `docker-compose.yml`.
- Motor async driver for Python.
- Database name: `voxassist`.
- In-memory fallback is used when MongoDB is unavailable.

Knowledge retrieval technology:

- ChromaDB persistent vector store.
- Collection name: `banking_knowledge`.
- Deterministic lexical/hash embedding fallback if ChromaDB is unavailable.

PDF storage:

- Currently stored in in-memory dictionary `pdf_memory` in the repository layer.
- Receipt PDFs are generated on demand using ReportLab.

### Data Dictionary

#### Users Collection (`users`)

Purpose: Store staff and manager login accounts.

| Field | Type | Description |
|---|---|---|
| `username` | string | Unique login username, for example `staff1` or `manager1`. |
| `password` | string | Demo plaintext password in current implementation. Should be hashed in production. |
| `role` | string | User role: `staff` or `manager`. |
| `name` | string | Display name of the employee. |
| `branch` | string | Branch name or branch context. |
| `active` | boolean | Whether the user is active. |
| `updatedAt` | string/datetime | Last updated timestamp. |

Seeded demo users:

- `staff1` / `staff123`
- `manager1` / `manager123`

#### Session Summaries Collection (`session_summaries`)

Purpose: Store completed interaction summaries and support history/analytics.

| Field | Type | Description |
|---|---|---|
| `session_id` | string | Unique session identifier. |
| `timestamp` | string/datetime | Date and time of saved session. |
| `summary.type` | string | Usually `summary`. |
| `summary.service` | string | Service type such as Account Opening, KYC Update, Loan Enquiry. |
| `summary.status` | string | Completed, Escalated, or other status. |
| `summary.language` | string | Customer language. |
| `summary.duration` | string | Interaction duration in `MM:SS`. |
| `summary.sentiment` | string | Positive, neutral, or negative. |
| `summary.entities.customerName` | string | Extracted customer name. |
| `summary.entities.pan` | string | Extracted PAN number if available. |
| `summary.entities.phone` | string | Extracted or masked phone number. |
| `summary.entities.accountType` | string | Account type such as Savings or Current. |
| `summary.entities.product` | string | Banking product such as FD, Loan, Card. |
| `summary.entities.amount` | string | Amount mentioned in conversation. |
| `summary.entities.cardLast4` | string | Last four card digits. |
| `summary.english` | array<string> | English bullet summary. |
| `summary.customerLanguage` | array<string> | Summary in customer language. |
| `summary.formsFilled` | array<string> | Forms completed in the session. |
| `summary.complianceFlags` | number | Count of compliance issues. |

#### Knowledge Documents (`backend/data/kb/*.json`)

Purpose: Trusted policy and banking knowledge used for RAG.

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique knowledge document ID. |
| `title` | string | Human-readable policy title. |
| `category` | string | Service category such as FD Services or Compliance. |
| `contentType` | string | SOP, rate table, or policy type. |
| `branchIds` | array<string> | Branches for which the content applies. |
| `language` | string | Knowledge document language code. |
| `effectiveFrom` | string/date | Effective start date. |
| `effectiveTo` | string/date/null | Expiry date if applicable. |
| `version` | string | Knowledge version. |
| `approvedBy` | string | Approval owner or department. |
| `source` | string | Source manual, circular, or SOP reference. |
| `tags` | array<string> | Search tags. |
| `content` | string | Approved customer-facing policy content. |
| `structuredFacts` | object | Optional structured rates or rules. |

Examples of knowledge files:

- `fd_rates.json`
- `banking_services.json`
- `fees_documents_branch.json`
- `sbi_public_banking.json`
- `sops.json`

#### ChromaDB Collection (`banking_knowledge`)

Purpose: Persist searchable chunks of approved knowledge.

| Field | Type | Description |
|---|---|---|
| `id` | string | Chunk ID, generated as document ID plus chunk index. |
| `document` | string | Chunk text used for retrieval. |
| `embedding` | array<number> | Deterministic local embedding vector. |
| `metadata.documentId` | string | Original knowledge document ID. |
| `metadata.title` | string | Knowledge title. |
| `metadata.source` | string | Policy source. |
| `metadata.category` | string | Service category. |
| `metadata.branchIds` | string | Branch list encoded for metadata. |
| `metadata.effectiveFrom` | string | Effective date. |
| `metadata.effectiveTo` | string | Expiry date. |
| `metadata.version` | string | Version. |
| `metadata.tags` | string | Tags encoded for metadata. |

#### Form Definitions (Code-level Schema)

Purpose: Define available banking forms and fields. These are currently code-level definitions in `backend/app/models/forms.py`, not database collections.

Supported forms:

- KYC Verification
- Account Opening
- Fixed Deposit Application
- Loan Application
- Card Application

Common form definition fields:

| Field | Type | Description |
|---|---|---|
| `form_type` | enum/string | Form identifier. |
| `title` | string | Display title. |
| `description` | string | Form purpose. |
| `icon` | string | Frontend icon name. |
| `fields` | array | Ordered form field definitions. |

Form field attributes:

| Field | Type | Description |
|---|---|---|
| `key` | string | Machine-readable field key. |
| `label` | string | Display label. |
| `question` | string | Question asked by AI. |
| `field_type` | string | `text`, `date`, `number`, or `select`. |
| `options` | array/null | Options for select fields. |
| `required` | boolean | Whether the field is required. |
| `validation_hint` | string | Formatting or validation hint. |

#### Form PDF Store

Purpose: Store generated form PDF bytes temporarily.

Current implementation:

- `pdf_memory: dict[str, bytes]`
- Key: `session_id`
- Value: generated PDF bytes

Production recommendation:

- Store PDFs in MongoDB GridFS, S3-compatible object storage, or a secure document repository.

### Indexing Strategy

#### MongoDB Indexes

The repository creates the following indexes when MongoDB is available:

| Collection | Index | Purpose |
|---|---|---|
| `session_summaries` | `session_id` unique ascending | Fast lookup and upsert by session ID. |
| `session_summaries` | `timestamp` descending | Fast latest-session listing. |
| `session_summaries` | `summary.entities.pan` ascending | Customer history search by PAN. |
| `session_summaries` | `summary.entities.customerName` ascending | Customer history search by name. |
| `users` | `username` unique ascending | Fast login lookup and uniqueness. |
| `knowledge_audit` | `documentId`, `version` ascending | Track knowledge version metadata. |

#### Vector and Retrieval Indexes

ChromaDB indexes knowledge chunks in the `banking_knowledge` collection using cosine space. Retrieval applies:

- Top-k vector search.
- Effective-date filtering.
- Branch filtering.
- Branch-specific score boost.
- Lexical fallback if ChromaDB fails.
- Minimum confidence threshold before presenting an answer as reliable.

#### Spatial Indexes

Spatial indexes are not applicable to this project because the system does not store geographic coordinates, hotspots, map points, or geospatial reports.

#### Performance Indexes

Performance is improved through:

- MongoDB indexes for session history and customer lookup.
- ChromaDB persistent indexing for RAG retrieval.
- In-memory demo seed sessions for immediate dashboard availability.
- WebSocket broadcasting for live updates without polling.
- Parallel backend enrichment for entities and action suggestions.
- Browser-side Redux state to reduce repeated API calls.

### Table Relationships

Although MongoDB is document-based, the logical relationships are:

- One user can create or handle many sessions.
- One session has one summary record.
- One session can have zero or more completed forms.
- One session can have one generated receipt PDF.
- One completed form can have one generated form PDF.
- One SOP answer can cite many knowledge chunks.
- One knowledge document can produce multiple ChromaDB chunks.
- Analytics are derived from many session summaries.

Logical relationship view:

```text
users
  -> session_summaries
       -> summaries, entities, formsFilled, complianceFlags
       -> receipt PDF generation
       -> analytics aggregation

knowledge_documents
  -> knowledge_chunks
       -> ChromaDB banking_knowledge
       -> SopResult citations

form_definitions
  -> form_sessions
       -> filled_fields
       -> form PDF
```

## Testing and Evaluation of the System

### Introduction to Testing

Testing ensures that the voice assistant provides reliable, safe, and useful support to bank staff and customers. Because the system includes real-time voice, AI processing, trusted knowledge retrieval, form automation, and analytics, testing must include unit tests, integration tests, system tests, functional tests, and user acceptance testing.

### Objectives of Testing

The main objectives are:

- Verify authentication and role access.
- Verify WebSocket connection and reconnection behavior.
- Verify speech/text processing flow.
- Verify translation and TTS fallback behavior.
- Verify entity extraction and action suggestions.
- Verify trusted SOP retrieval with citations.
- Verify compliance block behavior.
- Verify sentiment escalation behavior.
- Verify voice form filling and PDF generation.
- Verify session summaries, receipts, history, and analytics.
- Verify graceful fallback when MongoDB, ChromaDB, microphone, or AI provider is unavailable.

### Testing Approach

The testing approach combines automated tests and manual functional testing.

Automated testing:

- Backend unit tests using `unittest`.
- RAG retrieval tests in `backend/tests/test_rag.py`.
- Recommended future API and WebSocket tests using pytest/httpx.

Manual testing:

- Login with demo credentials.
- Staff dashboard voice/text interaction.
- Customer kiosk interaction.
- SOP search and action chip behavior.
- Form interview completion.
- Receipt and form PDF download.
- Analytics and session history screens.

### Unit Testing

Existing unit tests:

- `test_fd_rates_retrieve_rate_card`: checks FD rate-card retrieval and confidence.
- `test_branch_policy_overrides_default_context`: checks branch-specific policy ranking.
- `test_unknown_policy_requires_staff_verification`: checks unsupported policy fallback.

Recommended unit tests:

- `AIOrchestrator._fast_extract_entities`
- `AIOrchestrator._fast_suggest_actions`
- `AIOrchestrator._keyword_compliance`
- `AIOrchestrator._fast_sentiment`
- `AIOrchestrator._detect_form_intent`
- `FormSession.progress`
- `get_form_definition`
- `chunk_documents`
- `_branch_allowed`
- `_is_active`

### Integration Testing

Integration testing should validate combined frontend-backend behavior.

Important integration flows:

- Login route returns JWT and user role.
- WebSocket accepts a valid token and rejects missing/invalid token.
- `customer_text` creates transcript, assistant response, action chips, and SOP result.
- `demo_text` works when microphone or AI provider is unavailable.
- `sop_search` returns answer, confidence, and citations.
- `start_form` starts the correct form.
- Form audio/text flow fills fields and completes the form.
- `generate_form_pdf` returns a downloadable URL.
- `summarize` stores summary and updates frontend state.
- `GET /sessions` and `GET /analytics/branch` reflect session data.

### System Testing

System testing validates the entire application in a realistic local environment:

1. Start MongoDB using Docker Compose.
2. Start FastAPI backend on port 8000.
3. Start Vite frontend on port 5173.
4. Login as staff.
5. Open live session dashboard.
6. Start a customer interaction.
7. Search or trigger a banking SOP.
8. Start an account opening or KYC form.
9. Complete fields through voice or demo mode.
10. Generate form PDF.
11. End session and view summary/history.
12. Login as manager and view analytics.
13. Open kiosk route and verify customer flow.

### Functional Testing

Functional testing checks whether each feature works according to expected behavior.

Key functional areas:

- Authentication
- Live transcript
- Language selection
- Voice recording
- Text fallback
- SOP search
- Compliance guardrails
- Escalation alert
- Form filling
- PDF generation
- Session summary
- Customer history
- Analytics dashboard
- Kiosk mode

### Test Cases

| Test Case | Input/Action | Expected Result |
|---|---|---|
| Login as staff | `staff1` / `staff123` | Staff enters dashboard with valid token. |
| Login as manager | `manager1` / `manager123` | Manager can access application views. |
| Invalid login | Wrong password | API returns invalid credentials error. |
| WebSocket connection | Valid token | Connection status becomes connected. |
| Missing WebSocket token | No token | Backend closes connection with policy violation. |
| Set language | Select Marathi/Hindi/etc. | UI updates detected language and backend uses language code. |
| Customer text | "I want to open an account" | Transcript is added and account-opening action/form suggestion appears. |
| SOP search | "FD rates senior citizen" | Trusted FD answer appears with citation and confidence. |
| Unknown SOP | "cryptocurrency custody for minors" | System asks staff to verify approved policy. |
| Compliance block | Staff says "guaranteed return" | Compliance block alert appears and unsafe translation/audio is blocked. |
| Negative sentiment | Repeated complaint terms | Escalation alert appears after threshold. |
| Start KYC form | Click KYC form | First question is shown with progress 0%. |
| Complete form | Answer all fields | Form reaches 100% and PDF generation becomes available. |
| Generate form PDF | Click Generate PDF | Download URL is returned. |
| Generate receipt | Click PDF Receipt | Bilingual receipt PDF downloads. |
| Session history | Open history page | Seeded or saved sessions are listed. |
| Analytics | Open analytics page | Services, languages, handle time, and alerts are displayed. |
| Kiosk start | Open `/kiosk` and tap mic | Customer greeting starts and voice loop begins. |

### User Acceptance Testing

User acceptance testing should be done with the target users:

- Frontline bank staff
- Branch manager
- Customer service evaluator

Acceptance criteria:

- Staff can understand customer speech through translated transcript.
- Staff can get policy guidance quickly from SOP panel.
- Staff can avoid risky statements through compliance alerts.
- Staff can complete common banking forms faster using voice flow.
- Customer can interact in a regional language.
- Manager can see branch service trends and escalations.
- Generated receipts and summaries are understandable.
- System remains usable even when external AI or database services are unavailable.

### Evaluation of the System

The system is evaluated on functionality, usability, performance, reliability, and safety.

Functional evaluation:

- Meets major project goals: multilingual voice support, SOP retrieval, form filling, summaries, and analytics.

Usability evaluation:

- Staff dashboard separates transcript, agentic workspace, and guardrails.
- Kiosk mode provides a simplified customer-facing interface.
- Action chips and form suggestions reduce manual navigation.

Performance evaluation:

- WebSocket communication supports real-time updates.
- Entity extraction and action suggestions run in parallel.
- ChromaDB and fallback retrieval provide fast SOP search.

Reliability evaluation:

- MongoDB has in-memory fallback.
- ChromaDB has lexical fallback.
- Sarvam AI calls have deterministic/demo fallback paths.
- Browser speech recognition fallback and audio VAD are used in kiosk mode.

Safety evaluation:

- RAG answers include citations and confidence.
- Low-confidence results require staff verification.
- Compliance keywords can block unsafe staff output.
- AI answers are designed to avoid unsupported policy claims.

### Conclusion of Testing

Testing confirms that VoxAssist is suitable as a functional prototype for frontline banking assistance. The strongest tested area in the current repository is RAG retrieval. For production readiness, the project should add broader automated coverage for WebSocket flows, authentication, form filling, frontend components, PDF generation, and end-to-end browser behavior.

## Limitations and Future Enhancements

### Introduction

VoxAssist demonstrates a strong proof of concept for AI-assisted branch operations, but it still has limitations that must be addressed before production deployment in a real bank environment.

### Limitations of the System

- Demo passwords are stored in plaintext in the current implementation.
- JWT secret defaults to a development value if not configured.
- Form PDFs are stored only in memory and are lost when the backend restarts.
- Session transcript history is mostly runtime state unless summarized and saved.
- MongoDB fallback is useful for demos but not durable.
- Real AI quality depends on Sarvam API availability and valid API keys.
- Browser microphone access and speech recognition behavior vary by browser.
- Compliance checking is keyword-based in fast mode and limited compared with full regulatory review.
- RAG knowledge depends on manually maintained JSON files.
- No admin interface exists for uploading or approving new SOP documents.
- No full audit trail for every AI answer, prompt, or staff action.
- No integration with actual core banking systems, CBS, CRM, KYC systems, card systems, or loan origination systems.
- Manager role is present, but frontend does not enforce deep role-based navigation restrictions.
- Export buttons in some frontend views are UI placeholders and need full implementation.
- Current analytics are derived from summaries and seeded demo sessions, not live production counters.
- The project does not implement geospatial `hotspots`, social post analysis, or public report tracking.

### Future Enhancements

- Store passwords using secure hashing and enforce password policies.
- Move all secrets to environment variables or a secret manager.
- Persist generated PDFs in GridFS or object storage.
- Persist full transcripts with timestamps and speaker metadata.
- Add proper role-based access control for staff, manager, admin, and auditor.
- Build an admin dashboard for SOP upload, review, approval, versioning, and expiry.
- Add stronger compliance models and configurable compliance rules.
- Add full audit logging for AI responses, citations, staff actions, and downloads.
- Integrate with CBS for live account status, rates, cards, KYC, and transaction reference checks.
- Integrate with CRM for customer profile and service history.
- Add multilingual quality evaluation and human correction workflows.
- Add end-to-end Playwright tests for major user journeys.
- Add automated WebSocket integration tests.
- Add analytics filters by branch, date, staff member, service type, and language.
- Add offline mode or branch-local cache for approved SOPs.
- Add better PDF templates matching real bank forms.
- Add support for scanned document verification and OCR.
- Add customer consent capture before recording or form filling.

## Conclusion

VoxAssist Frontline Banking Dashboard is a practical AI-enabled banking assistant that addresses real branch-service challenges: language barriers, slow form filling, policy lookup difficulty, and compliance risk. The project combines a React dashboard, FastAPI backend, WebSocket communication, Sarvam AI integration, trusted RAG, MongoDB persistence, ChromaDB retrieval, and PDF generation.

The system provides a complete prototype experience for staff, managers, and customers. Staff can conduct live multilingual sessions, receive action suggestions, search SOPs, handle compliance alerts, and fill forms through voice. Managers can review service patterns, languages, handle time, and escalation signals. Customers can use kiosk mode for a simpler voice-first interaction.

Overall, the project is suitable for academic demonstration and further development. With stronger security, persistence, audit logging, test coverage, and integration with actual banking systems, it can evolve into a production-grade frontline banking assistant.

## References

### Technical Documentation and Standards

- React documentation: https://react.dev/
- Vite documentation: https://vite.dev/
- Redux Toolkit documentation: https://redux-toolkit.js.org/
- Tailwind CSS documentation: https://tailwindcss.com/
- FastAPI documentation: https://fastapi.tiangolo.com/
- Pydantic documentation: https://docs.pydantic.dev/
- MongoDB documentation: https://www.mongodb.com/docs/
- Motor async MongoDB driver: https://motor.readthedocs.io/
- ChromaDB documentation: https://docs.trychroma.com/
- ReportLab documentation: https://docs.reportlab.com/
- JWT standard: https://datatracker.ietf.org/doc/html/rfc7519
- WebSocket protocol: https://datatracker.ietf.org/doc/html/rfc6455

### Conceptual and Academic References

- Retrieval-Augmented Generation for grounded question answering.
- Speech-to-text and text-to-speech systems for accessibility.
- Role-based access control in enterprise systems.
- Human-in-the-loop AI for regulated financial services.
- Banking compliance, customer consent, and auditability principles.
- Multilingual user interface design for public service systems.

### Project Resources

- `README.md`
- `frontend/src/App.tsx`
- `frontend/src/features/session/LiveSession.tsx`
- `frontend/src/features/session/useVoiceSession.ts`
- `frontend/src/features/session/sessionSlice.ts`
- `frontend/src/features/session/FormInterview.tsx`
- `frontend/src/features/session/SessionHistory.tsx`
- `frontend/src/features/analytics/AnalyticsDashboard.tsx`
- `frontend/src/features/kiosk/CustomerKiosk.tsx`
- `backend/app/main.py`
- `backend/app/api/auth.py`
- `backend/app/api/routes.py`
- `backend/app/services/ai_orchestrator.py`
- `backend/app/services/rag_service.py`
- `backend/app/services/vector_store.py`
- `backend/app/services/kb_loader.py`
- `backend/app/services/repositories.py`
- `backend/app/models/forms.py`
- `backend/app/models/session.py`
- `backend/tests/test_rag.py`
- `backend/data/kb/*.json`
- `docker-compose.yml`
