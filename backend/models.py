"""Pydantic models for FemScale API."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator

from typing import List, Dict, Any


class StatusEnum(str, Enum):
    """Exact status strings used throughout the system."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class JobSubmissionRequest(BaseModel):
    """Request body for POST /v1/jobs."""
    code: str = Field(..., min_length=1, description="Python function code, max 50KB")
    timeout_sec: int = Field(default=30, ge=1, le=30, description="Execution timeout in seconds")
    input: Optional[dict] = Field(default_factory=dict, description="Optional input for the function")

    @field_validator("code")
    @classmethod
    def validate_code_size(cls, v: str) -> str:
        """Validate code size does not exceed 50KB."""
        if len(v.encode("utf-8")) > 50 * 1024:
            raise ValueError("code must not exceed 50KB")
        return v


class JobSubmissionResponse(BaseModel):
    """Response body for POST /v1/jobs."""
    job_id: str = Field(..., description="UUID4 job identifier")
    status: StatusEnum = Field(..., description="Current job status")


class JobResultResponse(BaseModel):
    job_id: str = Field(..., description="UUID4 job identifier")
    status: StatusEnum = Field(..., description="Current job status")
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    insights: List[Dict[str, Any]] = Field(default_factory=list, description="Learning insights")
    error: Optional[str] = Field(default=None, description="Platform-level error message")
    error_info: Optional[Dict[str, Any]] = None
    duration_ms: int = Field(default=0, description="Execution time in milliseconds")
    memory_mb: float = Field(default=0.0, description="Peak memory usage in MB")
    complexity: str = Field(default="", description="Estimated time complexity")
    complexity_note: str = Field(default="", description="Explanation of complexity")
    cost_usd: float = Field(default=0.0, description="Calculated cost in USD")
    created_at: str = Field(..., description="ISO8601 UTC submission timestamp")
    completed_at: Optional[str] = Field(default=None, description="ISO8601 UTC completion timestamp")

class MetricsEvent(BaseModel):
    """A single event in the metrics event log."""
    timestamp: str = Field(..., description="ISO8601 UTC timestamp")
    type: str = Field(..., description="Event type (e.g., 'worker_spawned', 'job_completed')")
    # Additional fields depend on event type


class MetricsResponse(BaseModel):
    """Response body for GET /v1/metrics."""
    queue_depth: int = Field(..., description="Jobs waiting in queue")
    workers_target: int = Field(..., description="Target number of workers from scaler")
    workers_active: int = Field(..., description="Currently active worker processes")
    jobs_running: int = Field(..., description="Jobs currently in 'running' status")
    jobs_completed_session: int = Field(..., description="Jobs completed this session")
    total_cost_session_usd: float = Field(..., description="Total cost of completed jobs")
    events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent events (worker spawned, job completed)",
    )

