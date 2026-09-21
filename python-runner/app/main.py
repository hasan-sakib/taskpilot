"""TaskPilot Python execution supervisor.

This service is the ONLY component with access to the host Docker socket.
It spawns ephemeral, network-isolated containers to run agent-generated
Python scripts, and returns their captured result to the main backend.
See app/sandbox.py for the isolation model and its documented limitations.
"""

import asyncio

from fastapi import FastAPI, HTTPException

from app.sandbox import SandboxUnavailableError, run_script
from app.schemas import ExecuteRequest, ExecuteResponse

app = FastAPI(title="TaskPilot Python Runner Supervisor", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest) -> ExecuteResponse:
    try:
        result = await asyncio.to_thread(
            run_script,
            request.script,
            timeout_seconds=request.timeout_seconds,
            memory_limit_mb=request.memory_limit_mb,
            cpu_limit=request.cpu_limit,
        )
    except SandboxUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # A genuine, unexpected Docker daemon error (not a timeout, not an
        # availability problem sandbox.py already distinguishes) -- report it as a
        # clean 500 rather than letting a raw exception/traceback leak to the caller.
        raise HTTPException(status_code=500, detail=f"Sandbox execution failed: {exc}") from exc

    return ExecuteResponse(
        execution_id=request.execution_id,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        timed_out=result.timed_out,
    )
