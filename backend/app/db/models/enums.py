import enum


class RunStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED_FOR_APPROVAL = "paused_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(enum.StrEnum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED_ON_APPROVAL = "blocked_on_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ToolExecutionStatus(enum.StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ApprovalStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class BrowserSessionStatus(enum.StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"
    CRASHED = "crashed"


class ArtifactType(enum.StrEnum):
    DOCUMENT = "document"
    RESEARCH_NOTE = "research_note"
    SCRIPT = "script"
    REPORT = "report"
    SCREENSHOT = "screenshot"
    EXPORT = "export"
    OTHER = "other"


class EventSeverity(enum.StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
