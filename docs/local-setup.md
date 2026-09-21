# Local setup

This has been verified end-to-end (build, migrations, all three services, a real
approve/reject cycle through the deployed UI, and a real backend-container restart
mid-run) on macOS (Apple Silicon) with Docker Desktop.

## Prerequisites

- **[Ollama](https://ollama.com)**, running on the host (not in Docker), with a model
  pulled: `ollama pull qwen3:4b` (the configured default —
  `TASKPILOT_OLLAMA_MODEL` to use a different one). Confirm it's actually running:
  `curl http://localhost:11434/api/tags`.
- **Docker + Docker Compose** — required for the Python execution sandbox, and for
  running the whole stack via `docker compose up`. Not required for backend/frontend
  local dev without Docker (§"Local development without Docker" below), but
  `python.execute` will report the sandbox as unavailable without it.
- **Python 3.13** and **Node.js 20+** if running the backend/frontend outside Docker.

## Fastest path: Docker Compose

```bash
cp .env.example .env   # adjust if needed -- defaults work as-is
docker compose -f docker/compose.yaml up --build
```

This builds and starts `backend` (`127.0.0.1:8000`), `frontend`
(`127.0.0.1:5173`), and `python-runner` (internal only, not published to the host).
First build takes a few minutes (Playwright's Chromium download in the backend image
is the slow part); subsequent builds are fast via Docker layer caching as long as
`backend/pyproject.toml`/`frontend/package.json` haven't changed.

On macOS, the backend reaches host-native Ollama via `host.docker.internal` —
already wired in `docker/compose.yaml`, no extra configuration needed.

Verify it's actually healthy, not just running:

```bash
docker compose -f docker/compose.yaml ps                        # all 3 should show "healthy"
curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool
```

The health response's `ollama.reachable` field is the one that actually matters — a
"healthy" container status does *not* gate on it (Ollama being down at startup is
tolerated, e.g. if you're only using the deterministic test provider), so check this
JSON body if things aren't planning.

Then open `http://127.0.0.1:5173`.

## Local development without Docker

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Served at `http://127.0.0.1:8000` (docs at `/docs`, health at `/api/v1/health`).
`python.execute` calls will fail with "sandbox unavailable" unless `python-runner` is
also running somewhere reachable at `TASKPILOT_PYTHON_RUNNER_BASE_URL` — either via
`docker compose up python-runner python-sandbox`, or its own local venv:

```bash
cd python-runner
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8100
```

(This still needs a working Docker daemon — `python-runner` itself isn't sandboxed,
it's the thing that spawns the sandbox containers.)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Served at `http://127.0.0.1:5173`, proxying `/api/*` to `http://127.0.0.1:8000` (set
`VITE_BACKEND_URL` to point elsewhere).

## Database migrations

```bash
cd backend && source .venv/bin/activate
# after changing a model in app/db/models/:
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
# sanity check before committing a migration:
alembic check   # "No new upgrade operations detected" if the model already matches
```

## Testing

```bash
# Backend (fast, deterministic -- no Ollama/Docker required)
cd backend && source .venv/bin/activate && pytest

# Python sandbox (needs a real Docker daemon -- spins up real containers)
cd python-runner && source .venv/bin/activate && pytest

# Frontend (Vitest + Testing Library + MSW-mocked API -- no backend required)
cd frontend && npm test
```

All three suites are deterministic and don't need Ollama running. The backend suite
uses an isolated in-memory SQLite database per test and a scripted, deterministic LLM
provider (`ScriptedTestProvider`) — no network calls anywhere.

## Troubleshooting

- **`ollama.reachable: false` in the health check.** Confirm Ollama is actually
  running on the host (`curl http://localhost:11434/api/tags`) and the model is
  pulled (`ollama list`). From inside Docker on macOS, `host.docker.internal` should
  resolve automatically; on Linux, `docker/compose.yaml` adds an explicit
  `host-gateway` mapping for the same reason — if it still doesn't resolve, check
  `TASKPILOT_OLLAMA_BASE_URL` in `.env`.
- **A submitted goal seems to hang for minutes.** This is expected with a real local
  model, not a bug — `POST /agent/runs` blocks until the run pauses or finishes. The
  "Start run" button correctly shows a loading state the whole time. See
  [agent-workflow.md](agent-workflow.md#real-model-latency-honestly) for what's
  actually realistic to expect: a complex, multi-part goal can take several minutes
  and occasionally fails to plan at all on modest hardware — this is a genuine model/
  hardware capability limit, not something to work around by waiting longer.
- **`python.execute` always fails with "sandbox unavailable."** The `python-runner`
  service (or its Docker daemon access) isn't reachable. If running outside Compose,
  confirm `python-runner` is actually up (`curl http://localhost:8100/health`) and
  that the `taskpilot-python-sandbox:latest` image has been built at least once
  (`docker compose -f docker/compose.yaml up --build python-sandbox` builds it without
  starting a long-running service).
- **`alembic upgrade head` fails on a fresh clone.** Confirm `TASKPILOT_DATA_DIR`
  (defaults to `backend/data/`, or `/app/data` inside Docker) is writable and that
  nothing else has a lock on `taskpilot.db` — SQLite's file locking means two
  processes (e.g. a stray `uvicorn` and a fresh Alembic run) pointed at the same file
  can conflict.
- **Frontend shows stale data after an approval.** Confirm the browser console has no
  errors first — if TanStack Query's cache invalidation is working (it should be,
  it's covered by `frontend/src/routes/approvals.test.tsx`), the Approvals/Agent/Tasks
  views should update within a few seconds of any mutation without a manual refresh.
- **Port already in use (`8000`, `5173`, or `11434`).** Something else is already
  bound to it — `lsof -i :8000` (etc.) to find what, or override the port via the
  relevant `TASKPILOT_*_PORT`/Compose port mapping.

## Known limitations

See [security.md](security.md#the-python-sandbox--a-real-honestly-documented-limitation)
for the two accepted, documented gaps in the Python sandbox (Docker-socket access is
root-equivalent to the host; the sandboxed container's writable filesystem has no size
cap). Beyond that: there is no multi-tenant/auth model (this is a single-user, local
tool by design), and the frontend's "live" progress view is polling-based, not a true
push — see [architecture.md](architecture.md#frontend) for why that's a reasonable
trade-off here rather than a missing feature.
