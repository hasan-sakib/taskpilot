# TaskPilot

A local-first personal work agent. TaskPilot accepts goals expressed in natural
language, plans multi-step work, and executes it using controlled tools — web
research, workspace file management, task tracking, sandboxed Python execution,
and browser automation — pausing for your approval before anything consequential.
It runs entirely on local infrastructure via [Ollama](https://ollama.com); no
paid LLM API is required.

> **Status:** Phase 1 (foundation) complete. The agent execution engine,
> tools, and most UI screens are not yet implemented — see
> [Implementation phases](#implementation-phases) below.

## Architecture

- **Backend** — FastAPI + SQLAlchemy 2.x + Alembic (SQLite) + LangGraph for the
  agent execution graph + Ollama for local inference + Playwright for browser
  automation.
- **Frontend** — React + TypeScript + Vite + Tailwind CSS + shadcn/ui + Radix UI
  + TanStack Query.
- **Python runner** — a separate FastAPI service that owns the Docker socket
  and is the only component that can spawn sandboxed containers to execute
  agent-generated Python scripts. The main backend never touches Docker
  directly.

See [docs/architecture.md](docs/architecture.md) for the full design (agent
graph, database schema, tool contract, approval workflow) once written in a
later phase.

## Project structure

```
taskpilot/
├── backend/        # FastAPI app, agent graph, tools, Alembic migrations
├── frontend/        # React + Vite + Tailwind + shadcn/ui
├── python-runner/   # Isolated Python execution supervisor (Docker-socket owner)
├── docker/          # Dockerfiles + Compose configuration
├── workspace/        # Agent-managed files (documents, research, scripts, reports, exports)
└── docs/             # Architecture, security, and workflow documentation
```

## Prerequisites

- Python 3.11+ (developed against 3.13)
- Node.js 20+ / npm
- [Ollama](https://ollama.com), running locally with a model pulled (default:
  `qwen3:4b` — `ollama pull qwen3:4b`)
- Docker + Docker Compose (for the containerized Python execution sandbox and
  for `docker compose up`)

## Local development (without Docker)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

The API is served at `http://127.0.0.1:8000`, docs at `/docs`, health check at
`/api/v1/health`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI is served at `http://127.0.0.1:5173` and proxies `/api/*` requests to
the backend at `http://127.0.0.1:8000`.

## Docker Compose

```bash
cp .env.example .env   # adjust as needed
docker compose -f docker/compose.yaml up --build
```

This brings up `backend` (port 8000), `frontend` (port 5173), and
`python-runner` (not published to the host — reachable only from `backend`
over an internal Docker network). Both `backend` and `frontend` bind to
`127.0.0.1` only.

On macOS, Ollama typically runs natively on the host, not in Compose; the
backend container reaches it via `host.docker.internal`.

## Database migrations

Migrations live in `backend/alembic/`. After changing a model in
`backend/app/db/models/`:

```bash
cd backend && source .venv/bin/activate
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Testing

```bash
cd backend && source .venv/bin/activate
python -m pytest
```

Tests use an in-memory SQLite database — no external services required. A
deterministic test-mode LLM provider (added in Phase 2) lets the full agent
graph be tested without a running Ollama instance.

## Security model

TaskPilot has real access to your local files and browser. Key boundaries
(detailed in `docs/security.md` once written):

- All workspace filesystem operations are restricted to the configured
  workspace root; path traversal and symlink escapes are rejected.
- Tool permissions are enforced deterministically in backend code, never
  trusted to the LLM.
- Consequential actions (sending messages, submitting forms, running new
  scripts, deleting files) require explicit human approval, enforced
  server-side and bound to the exact action payload via a content hash.
- Python scripts run in ephemeral, network-isolated Docker containers, spawned
  by a dedicated supervisor service that is the only component with Docker
  socket access — a real but documented limitation (root-equivalent host
  access), not a claim of a perfect security boundary.
- `backend` and `frontend` bind to `127.0.0.1` by default; `python-runner` is
  not exposed to the frontend or the host at all.

## Known limitations (current phase)

- The LangGraph agent execution engine, tools, and approval workflow are not
  yet implemented (Phases 2–4).
- Most frontend screens are placeholders describing what will populate them —
  no fake data is shown anywhere.
- The Python sandbox container image and execution logic are not yet built;
  `python-runner` currently only exposes a health check.

## Implementation phases

1. **Foundation** (done) — project scaffolding, database schema + migrations,
   health check, Docker Compose, frontend shell.
2. **Core agent** — LangGraph execution graph, deterministic test mode.
3. **Tools** — web research, workspace, task management, Python sandbox,
   browser automation.
4. **Safety and memory** — approval workflow, preferences, audit logging.
5. **Frontend** — all eight screens wired to real data.
6. **Integration** — full stack end-to-end verification.
7. **Testing and deployment** — full test suite, documentation, final Docker
   verification.
