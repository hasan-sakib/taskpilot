import httpx


class PythonRunnerError(Exception):
    """Raised when the python-runner-supervisor is unreachable or returns an error."""


class PythonRunnerClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def execute(
        self,
        *,
        execution_id: str,
        script: str,
        timeout_seconds: int,
        memory_limit_mb: int,
        cpu_limit: float,
    ) -> dict:
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds + 15) as client:
                response = await client.post(
                    f"{self._base_url}/execute",
                    json={
                        "execution_id": execution_id,
                        "script": script,
                        "timeout_seconds": timeout_seconds,
                        "memory_limit_mb": memory_limit_mb,
                        "cpu_limit": cpu_limit,
                    },
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise PythonRunnerError(f"Python runner request failed: {exc}") from exc
