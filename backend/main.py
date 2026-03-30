"""FemScale FastAPI application - Phase 2: Redis Queue Integration."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status

from models import (
    StatusEnum,
    JobSubmissionRequest,
    JobSubmissionResponse,
    JobResultResponse,
    MetricsResponse,
)
from config import MAX_CODE_SIZE_BYTES, DEFAULT_TIMEOUT_SEC
from redis_client import get_redis_client, init_redis
from metrics import init_metrics, get_metrics


app = FastAPI(
    title="FemScale",
    description="Serverless Python function execution platform",
    version="1.0.0",
)

# Initialize Redis on startup
redis_client = None
metrics = None


@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection and metrics on app startup."""
    global redis_client, metrics
    redis_client = init_redis()
    metrics = init_metrics()




def get_iso8601_utc() -> str:
    """Get current timestamp in ISO8601 UTC format."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@app.post(
    "/v1/jobs",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a Python function for execution",
    tags=["Jobs"],
)
def submit_job(request: JobSubmissionRequest) -> JobSubmissionResponse:
    """
    Submit a Python function for asynchronous execution.

    **Request Body:**
    - `code`: Python function code (max 50KB)
    - `timeout_sec`: Execution timeout in seconds (1–30, default 30)
    - `input`: Optional input data for the function

    **Response:**
    - `job_id`: UUID4 identifier for polling
    - `status`: Always "queued" on successful submission

    **Errors:**
    - 413 Payload Too Large: code exceeds 50KB
    - 422 Unprocessable Entity: validation failed (empty code, invalid timeout)
    """
    # Validate code size
    code_size = len(request.code.encode("utf-8"))
    if code_size > MAX_CODE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"code must not exceed {MAX_CODE_SIZE_BYTES} bytes",
        )

    # Generate job_id and timestamps
    job_id = str(uuid4())
    created_at = get_iso8601_utc()

    # Create job object
    job = {
        "job_id": job_id,
        "code": request.code,
        "timeout_sec": request.timeout_sec,
        "input": request.input,
        "status": StatusEnum.QUEUED.value,
        "stdout": "",
        "stderr": "",
        "error": None,
        "duration_ms": 0,
        "memory_mb": 0.0,
        "cost_usd": 0.0,
        "created_at": created_at,
        "completed_at": None,
    }

    # Store job in Redis and enqueue
    redis_client.store_job(job_id, job)
    redis_client.enqueue_job(job_id)

    return JobSubmissionResponse(job_id=job_id, status=StatusEnum.QUEUED)


@app.get(
    "/v1/jobs/{job_id}",
    response_model=JobResultResponse,
    summary="Poll job status and results",
    tags=["Jobs"],
)
def get_job(job_id: str) -> JobResultResponse:
    """
    Poll the status and results of a submitted job.

    **Path Parameters:**
    - `job_id`: UUID4 job identifier from POST /v1/jobs

    **Response:**
    - Full job object including status, output, metrics, and timestamps

    **Status Values:**
    - `queued`: Waiting in queue
    - `running`: Container is executing
    - `success`: Completed successfully (exit code 0)
    - `failed`: Non-zero exit code
    - `timeout`: Exceeded timeout_sec limit

    **Errors:**
    - 404 Not Found: job_id does not exist
    """
    job = redis_client.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job not found",
        )

    return JobResultResponse(
        job_id=job["job_id"],
        status=StatusEnum(job["status"]),
        stdout=job["stdout"],
        stderr=job["stderr"],
        error=job["error"],
        duration_ms=job["duration_ms"],
        memory_mb=job["memory_mb"],
        cost_usd=job["cost_usd"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
    )


@app.get(
    "/v1/metrics",
    response_model=MetricsResponse,
    summary="Get system metrics and event log",
    tags=["Metrics"],
)
def get_metrics_endpoint() -> MetricsResponse:
    """
    Get real-time system metrics and recent events.

    **Response:**
    - `queue_depth`: Number of jobs waiting in queue
    - `workers_target`: Target worker count from scaler policy
    - `workers_active`: Currently running worker processes
    - `jobs_running`: Jobs in "running" status
    - `jobs_completed_session`: Total jobs completed this session
    - `total_cost_session_usd`: Total execution cost this session
    - `events`: Recent event log (worker spawned, job completed)

    **Use Case:**
    Real-time monitoring dashboard, auto-scaling observability
    """
    metrics_instance = get_metrics()
    snapshot = metrics_instance.get_snapshot()

    return MetricsResponse(
        queue_depth=snapshot["queue_depth"],
        workers_target=snapshot["workers_target"],
        workers_active=snapshot["workers_active"],
        jobs_running=snapshot["jobs_running"],
        jobs_completed_session=snapshot["jobs_completed_session"],
        total_cost_session_usd=snapshot["total_cost_session_usd"],
        events=snapshot["events"],
    )


@app.get("/health", tags=["System"])
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
