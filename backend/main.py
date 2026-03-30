"""FemScale FastAPI application - FINAL VERSION (CRUD + RERUN)."""

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
from config import MAX_CODE_SIZE_BYTES
from redis_client import init_redis
from metrics import init_metrics, get_metrics
from code_analyzer import analyze_code
from complexity_analyzer import estimate_complexity

app = FastAPI(
    title="FemScale",
    description="Serverless Python function execution platform",
    version="2.0.0",
)

redis_client = None
metrics = None


# -------------------------------
# 🔧 STARTUP
# -------------------------------
@app.on_event("startup")
async def startup_event():
    global redis_client, metrics
    redis_client = init_redis()
    metrics = init_metrics()


def get_iso8601_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


# -------------------------------
# 🚀 CREATE JOB
# -------------------------------
@app.post(
    "/v1/jobs",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_job(request: JobSubmissionRequest):

    code_size = len(request.code.encode("utf-8"))
    if code_size > MAX_CODE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"code must not exceed {MAX_CODE_SIZE_BYTES} bytes",
        )

    job_id = str(uuid4())
    created_at = get_iso8601_utc()

    insights = analyze_code(request.code)
    complexity, complexity_note = estimate_complexity(request.code)

    job = {
        "job_id": job_id,
        "code": request.code,
        "timeout_sec": request.timeout_sec,
        "input": request.input,
        "status": StatusEnum.QUEUED.value,
        "stdout": "",
        "stderr": "",
        "error": None,
        "error_info": None,
        "duration_ms": 0,
        "memory_mb": 0.0,
        "cost_usd": 0.0,
        "created_at": created_at,
        "completed_at": None,
        "insights": insights,
        "complexity": complexity,
        "complexity_note": complexity_note,
    }

    redis_client.store_job(job_id, job)
    redis_client.enqueue_job(job_id)

    return JobSubmissionResponse(
        job_id=job_id,
        status=StatusEnum.QUEUED,
    )


# -------------------------------
# 📊 READ JOB
# -------------------------------
@app.get(
    "/v1/jobs/{job_id}",
    response_model=JobResultResponse,
)
def get_job(job_id: str):

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
        error_info=job.get("error_info"),
        duration_ms=job["duration_ms"],
        memory_mb=job["memory_mb"],
        cost_usd=job["cost_usd"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
        insights=job.get("insights", []),
        complexity=job.get("complexity"),
        complexity_note=job.get("complexity_note"),
    )


# -------------------------------
# ✏️ UPDATE (EDIT + RERUN)
# -------------------------------
@app.put("/v1/jobs/{job_id}")
def update_job(job_id: str, new_data: dict):

    job = redis_client.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    # 🔥 edit code
    if "code" in new_data:
        job["code"] = new_data["code"]

    # optional edits
    if "timeout_sec" in new_data:
        job["timeout_sec"] = new_data["timeout_sec"]

    if "input" in new_data:
        job["input"] = new_data["input"]

    # 🔥 reset job
    job["status"] = "queued"
    job["stdout"] = ""
    job["stderr"] = ""
    job["error"] = None
    job["error_info"] = None
    job["completed_at"] = None

    # 🔥 requeue
    redis_client.store_job(job_id, job)
    redis_client.enqueue_job(job_id)

    return {
        "message": "job updated and re-queued",
        "job_id": job_id
    }


# -------------------------------
# ❌ DELETE JOB
# -------------------------------
@app.delete("/v1/jobs/{job_id}")
def delete_job(job_id: str):

    job = redis_client.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    redis_client.backend.delete(f"job:{job_id}")

    return {"message": "job deleted"}


# -------------------------------
# 📈 METRICS
# -------------------------------
@app.get("/v1/metrics", response_model=MetricsResponse)
def get_metrics_endpoint():

    snapshot = get_metrics().get_snapshot()

    return MetricsResponse(
        queue_depth=snapshot["queue_depth"],
        workers_target=snapshot["workers_target"],
        workers_active=snapshot["workers_active"],
        jobs_running=snapshot["jobs_running"],
        jobs_completed_session=snapshot["jobs_completed_session"],
        total_cost_session_usd=snapshot["total_cost_session_usd"],
        events=snapshot["events"],
    )


# -------------------------------
# ❤️ HEALTH CHECK
# -------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}


# -------------------------------
# 🏃 RUN SERVER
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)