"""TaskPilot Python execution supervisor.

This service is the ONLY component with access to the host Docker socket.
It spawns ephemeral, network-isolated containers to run agent-generated
Python scripts, and returns their captured result to the main backend.

Phase 1 scope: health check only. Sandbox execution is implemented in
Phase 3 (see docs/security.md for the isolation model once written).
"""

from fastapi import FastAPI

app = FastAPI(title="TaskPilot Python Runner Supervisor", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
