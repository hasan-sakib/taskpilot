"""Spawns one ephemeral, network-isolated container per script execution.

The script is injected via `put_archive` (a tar stream copied into the container's
filesystem before it starts) rather than a bind mount. This process itself typically
runs inside a container with the *host's* Docker socket mounted (Docker-outside-of-
Docker) -- a bind mount would need a path that exists on the host, not inside this
container's own filesystem, so put_archive is the correct mechanism here, not just a
convenience.

Deliberately out of scope: the sandbox has no access to the real workspace filesystem
at all, in either direction. A script's only output is its stdout/stderr/exit code; if
the agent wants a script's output saved as a workspace file, that's a separate,
independently-permissioned workspace.write_file call. This is a stronger isolation
property than a "designated output mount" would give, not just a simplification.

Known, accepted limitation: the container's writable root filesystem has no size cap.
mem_limit/nano_cpus/pids_limit all bound resource use, and /tmp is capped via its own
tmpfs size, but nothing here bounds disk writes to the rest of the writable layer --
Docker's storage_opt size= quota isn't portable across storage drivers/backing
filesystems (it commonly doesn't work at all on the default overlay2-on-non-XFS setup,
including this project's target of Docker Desktop on macOS), so it isn't set. A
malicious or buggy script could write large files to disk until timeout_seconds cuts
it off. Documented here rather than silently ignored; not fixed in this phase because a
platform-dependent quota that fails to apply on the primary target platform would be
worse than an honestly-documented gap.
"""

import io
import tarfile
import time
from dataclasses import dataclass

import docker
from docker.errors import APIError, DockerException, ImageNotFound

SANDBOX_IMAGE = "taskpilot-python-sandbox:latest"
SCRIPT_DIR_IN_CONTAINER = "/sandbox"
SCRIPT_FILENAME = "script.py"
MAX_OUTPUT_CHARS = 100_000


class SandboxUnavailableError(Exception):
    """Raised when the sandbox image or Docker daemon isn't available."""


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool


def _script_archive(script: str) -> bytes:
    buffer = io.BytesIO()
    payload = script.encode("utf-8")
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        info = tarfile.TarInfo(name=SCRIPT_FILENAME)
        info.size = len(payload)
        info.mode = 0o444
        tar.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def run_script(
    script: str,
    *,
    timeout_seconds: int,
    memory_limit_mb: int,
    cpu_limit: float,
) -> ExecutionResult:
    try:
        client = docker.from_env()
    except DockerException as exc:
        raise SandboxUnavailableError(f"Cannot reach the Docker daemon: {exc}") from exc

    try:
        client.images.get(SANDBOX_IMAGE)
    except ImageNotFound as exc:
        raise SandboxUnavailableError(
            f"Sandbox image not built: {SANDBOX_IMAGE}. Build it before running scripts."
        ) from exc

    container = client.containers.create(
        SANDBOX_IMAGE,
        command=["python3", f"{SCRIPT_DIR_IN_CONTAINER}/{SCRIPT_FILENAME}"],
        network_mode="none",
        mem_limit=f"{memory_limit_mb}m",
        memswap_limit=f"{memory_limit_mb}m",  # no swap beyond the memory cap
        nano_cpus=int(cpu_limit * 1_000_000_000),
        pids_limit=64,
        # NOT read_only: put_archive (used below to inject the script without a shared
        # host path -- see module docstring) is rejected outright by the Docker daemon
        # against a read-only rootfs ("container rootfs is marked read-only"), even
        # though it writes through the daemon rather than a process inside the
        # container. The container is destroyed immediately after every run regardless
        # of outcome, so a writable rootfs here does not persist anything; isolation
        # instead comes from network_mode=none, dropped capabilities, no-new-privileges,
        # and the resource caps below.
        tmpfs={"/tmp": "rw,size=64m,noexec"},
        security_opt=["no-new-privileges"],
        cap_drop=["ALL"],
        working_dir=SCRIPT_DIR_IN_CONTAINER,
        detach=True,
        tty=False,
    )

    start = time.monotonic()
    timed_out = False
    try:
        container.put_archive(SCRIPT_DIR_IN_CONTAINER, _script_archive(script))
        container.start()
        wait_start = time.monotonic()
        try:
            result = container.wait(timeout=timeout_seconds)
            exit_code = result.get("StatusCode")
        except Exception:
            # docker-py's own docstring for Container.wait() claims this raises
            # requests.exceptions.ReadTimeout on a genuine timeout -- empirically (this
            # docker-py version, talking to the daemon over a Unix socket) it actually
            # raises requests.exceptions.ConnectionError wrapping a urllib3 read-timeout,
            # which is NOT reliably distinguishable by type/class from a genuine
            # connection failure to the daemon. Using elapsed wall-clock time against
            # the requested timeout is a version-independent way to tell them apart:
            # a failure that arrives near the requested timeout is the timeout firing;
            # one that arrives quickly is a real error and must not be mislabeled.
            if time.monotonic() - wait_start < timeout_seconds * 0.9:
                raise
            timed_out = True
            try:
                container.kill()
            except APIError:
                pass  # already stopped/removed in the race between timeout and kill()
            exit_code = None

        duration_ms = int((time.monotonic() - start) * 1000)
        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
    finally:
        container.remove(force=True)

    return ExecutionResult(
        stdout=stdout[:MAX_OUTPUT_CHARS],
        stderr=stderr[:MAX_OUTPUT_CHARS],
        exit_code=exit_code,
        duration_ms=duration_ms,
        timed_out=timed_out,
    )
