# Project Structure

VoxAssist is organized as a two-app workspace with clear source, data, deployment, and documentation boundaries.

```text
.
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI REST and WebSocket routes
│   │   ├── core/         # Runtime configuration
│   │   ├── db/           # Database client lifecycle
│   │   ├── models/       # Domain and form models
│   │   └── services/     # AI orchestration, RAG, repositories, sessions
│   ├── data/
│   │   ├── kb/           # Trusted banking knowledge base
│   │   └── sops/         # SOP source data
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/          # App bootstrap, layout shell, Redux store/hooks
│       ├── features/     # Auth, session, kiosk, analytics, history views
│       └── shared/       # Reusable UI primitives and utilities
├── deploy/               # AWS, nginx, systemd, and seed scripts
├── docs/                 # Project docs and preserved design references
└── docker-compose.yml    # Local MongoDB support services
```

## Frontend Rules

- Keep route-level and product-specific behavior inside `frontend/src/features`.
- Keep app-wide providers, the shell, and Redux setup inside `frontend/src/app`.
- Keep reusable UI and framework-neutral helpers inside `frontend/src/shared`.
- Do not import feature internals from another feature unless the type or behavior is intentionally shared.

## Backend Rules

- Keep HTTP/WebSocket entry points in `backend/app/api`.
- Keep provider orchestration, retrieval, persistence, and session lifecycle code in `backend/app/services`.
- Keep stable data contracts in `backend/app/models`.
- Keep trusted retrieval data under `backend/data`; generated vector stores belong in `.chroma` and should not be committed.

## Preserved Design References

The previous top-level HTML inspiration folders were moved to `docs/design-inspiration`. They are retained for reference, but they are not imported by the app or deployment scripts.
