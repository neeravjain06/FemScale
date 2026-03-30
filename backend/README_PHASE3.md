# FemScale Backend - Phase 3: Worker Execution System

## Structure

```
backend/
├── __init__.py
├── main.py              # FastAPI app (POST /v1/jobs, GET /v1/jobs/{job_id})
├── models.py            # Pydantic request/response models + StatusEnum
├── config.py            # Constants and configuration
├── redis_client.py      # Redis operations + in-memory mock fallback
├── worker.py            # Worker process (job execution engine)
├── test_phase2.py       # Redis queue integration tests
├── test_worker.py       # Worker execution unit tests
├── test_e2e.py          # End-to-end integration tests
├── requirements.txt     # Dependencies
└── README.md            # This file
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Terminal 1: Start FastAPI server
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start worker (polling queue, executing jobs)
python worker.py

# Terminal 3: Test (submit jobs, watch execution)
python test_e2e.py
```

View API docs: http://localhost:8000/docs

## API Endpoints

### POST /v1/jobs
Submit a Python function for asynchronous execution.

**Request:**
```json
{
  "code": "def handler(event):\n    return {'result': 42}",
  "timeout_sec": 30,
  "input": {"key": "value"}
}
```

**Response (201 Created):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

### GET /v1/jobs/{job_id}
Poll job status and retrieve results.

**Response (200 OK):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "stdout": "{\"result\": 42}",
  "stderr": "",
  "error": null,
  "duration_ms": 124,
  "memory_mb": 0.1,
  "cost_usd": 0.0000000000,
  "created_at": "2026-03-30T10:00:00.000Z",
  "completed_at": "2026-03-30T10:00:00.124Z"
}
```

## Implementation Details

### Phase 1 (Complete) — API Foundation
- ✅ FastAPI app with /v1 prefix
- ✅ POST /v1/jobs with validation (code ≤50KB, timeout 1–30 sec)
- ✅ GET /v1/jobs/{job_id} with full job object
- ✅ UUID4 job IDs, ISO8601 UTC timestamps
- ✅ Pydantic models for all requests/responses
- ✅ Error handling (422, 413, 404)

### Phase 2 (Complete) — Redis Queue Integration
- ✅ Redis FIFO queue (`jobs_queue` list)
- ✅ Job storage in Redis (`job:{job_id}` keys with TTL)
- ✅ In-memory mock fallback (for dev mode)
- ✅ Queue depth tracking

### Phase 3 (Complete) — Worker Execution System
- ✅ Worker class polling Redis BLPOP with timeout
- ✅ Subprocess-based code execution (safe, isolated)
- ✅ Stdout/stderr capture
- ✅ Status transitions: queued → running → success|failed|timeout
- ✅ Timeout handling (kills subprocess, sets status timeout)
- ✅ Error capture (stderr, error messages)
- ✅ Cost calculation (AWS Lambda formula)
- ✅ ISO8601 timestamps for completion
- ✅ Comprehensive test coverage (unit + e2e)

### Not Yet Implemented (Phase 4+)
- Docker container execution (replacing subprocess)
- SQLite persistence
- Auto-scaling (based on queue depth)
- Dashboard metrics endpoint (/v1/metrics)
- Frontend (React UI)

## Worker: How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│ API (FastAPI)                                           │
│ • POST /v1/jobs → store in Redis, enqueue              │
│ • GET  /v1/jobs/{id} → retrieve from Redis             │
└────────────────┬────────────────────────────────────────┘
                 │ jobs_queue (FIFO)
                 ▼
        ┌────────────────────┐
        │ Redis Queue        │
        │ • job:{id} keys    │
        │ • jobs_queue list  │
        └────┬───────────────┘
             │ BLPOP
             ▼
    ┌──────────────────────┐
    │ Worker Process       │
    │ • Dequeue job       │
    │ • subprocess exec   │
    │ • Capture I/O      │
    │ • Update status    │
    └──────────────────────┘
```

### Worker Execution Flow

For each job in queue:

1. **Dequeue**: `BLPOP jobs_queue` (blocking)
2. **Load**: Get job object from `job:{id}` key
3. **Execute**: 
   - Wrap user code with handler invocation
   - Run via `subprocess.run()` with timeout
   - Capture stdout, stderr
4. **Process Results**:
   - Exit code 0 → status = "success"
   - Non-zero → status = "failed"
   - Timeout → status = "timeout"
5. **Calculate Metrics**:
   - duration_ms: execution time
   - cost_usd: `(Memory_GB × Duration_sec) × $0.0000000167`
6. **Update**: Write results back to Redis

### User Code Format

The submitted `code` must define a `handler` function:

```python
def handler(event):
    """
    Args:
        event: dict from input parameter (JSON-serializable)
    
    Returns:
        Anything JSON-serializable (result printed to stdout)
    """
    x = event.get("x", 0)
    y = event.get("y", 0)
    return {"sum": x + y}
```

On execution:
- Handler is called: `result = handler(input_data)`
- Result serialized: `json.dumps(result)` → stdout
- Errors printed: exceptions → stderr

## Testing

### Unit Tests (Worker)

```bash
python test_worker.py
```

Tests:
- ✅ Successful execution (exit 0)
- ✅ Failed execution (exit 1)
- ✅ Timeout handling
- ✅ Input parameter passing
- ✅ Cost calculation
- ✅ Status transitions
- ✅ Error messages

### Redis Queue Tests

```bash
python test_phase2.py
```

Tests:
- ✅ Job submission
- ✅ Queue population
- ✅ Job retrieval
- ✅ Timestamp formatting
- ✅ Error handling (404, 413, 422)

### End-to-End Integration

```bash
python test_e2e.py
```

Tests (in-memory, shared Redis):
- ✅ Simple job execution
- ✅ Input parameter processing
- ✅ Failed job handling
- ✅ Concurrent job execution
- ✅ Cost calculation

## Key Features

### Safety & Isolation
- Code runs via `subprocess.run()` (not `exec()`)
- User code cannot access worker process / host system
- Timeout enforced by subprocess (kills runaway code)
- Stderr captured for error visibility

### Reliability
- Status enum validation (exact strings)
- Graceful error handling
- Timeout not exceeding 30 seconds (hardcoded in PRD)
- Cost calculation persisted with every result

### Compatibility
- Redis fallback: Uses in-memory mock if Redis unavailable
- Works in dev (threads) and production (processes)
- Compatible with both real Redis and mock

## Redis Client Operations

```python
from redis_client import get_redis_client

rc = get_redis_client()

# Store a job
rc.store_job(job_id, job_dict)

# Retrieve a job
job = rc.get_job(job_id)

# Enqueue for execution
rc.enqueue_job(job_id)

# Dequeue next job (blocking, 1s timeout)
job_id = rc.dequeue_job()

# Get queue length
depth = rc.get_queue_depth()

# Update job status + fields
rc.update_job_status(
    job_id, 
    "success",
    stdout="output here",
    stderr="",
    duration_ms=123,
    memory_mb=0.1,
    cost_usd=0.00000001,
    completed_at="2026-03-30T10:00:00.123Z"
)
```

## Configuration

In `config.py`:

```python
MAX_CODE_SIZE_BYTES = 50 * 1024       # 50KB
MIN_TIMEOUT_SEC = 1                    # 1 second
MAX_TIMEOUT_SEC = 30                   # 30 seconds max
DEFAULT_TIMEOUT_SEC = 30

DOCKER_MEMORY_MB = 128
DOCKER_CPU_COUNT = 1
DOCKER_TIMEOUT_SEC = 30

AWS_LAMBDA_RATE_PER_GB_SECOND = 0.0000000167
```

## Example: Full Flow

### 1. Submit Job (curl)
```bash
curl -X POST http://localhost:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def handler(event):\n    return {\"sum\": event.get(\"x\",0) + event.get(\"y\",0)}",
    "timeout_sec": 10,
    "input": {"x": 2, "y": 3}
  }'
```
Response:
```json
{"job_id": "abc123", "status": "queued"}
```

### 2. Worker Picks It Up
Worker console:
```
✓ Job abc123 completed: success (duration: 87ms, cost: $0.0000000000)
```

### 3. Poll Results (curl)
```bash
curl http://localhost:8000/v1/jobs/abc123 | jq
```
Response:
```json
{
  "job_id": "abc123",
  "status": "success",
  "stdout": "{\"sum\": 5}",
  "stderr": "",
  "error": null,
  "duration_ms": 87,
  "memory_mb": 0.1,
  "cost_usd": 0.0000000000,
  "created_at": "2026-03-30T10:00:00.000Z",
  "completed_at": "2026-03-30T10:00:00.087Z"
}
```

## Status Enum (Exact Strings)

Used everywhere per PRD Section 11.1:

```python
StatusEnum = Enum('StatusEnum', {
    'QUEUED': 'queued',      # In queue, not yet picked up
    'RUNNING': 'running',    # Subprocess executing
    'SUCCESS': 'success',    # Exit code 0
    'FAILED': 'failed',      # Exit code non-zero
    'TIMEOUT': 'timeout',    # Exceeded timeout_sec
})
```

## Next Phase (Phase 4+)

- Docker container execution (256MB memory, 1 CPU per job)
- Network isolation (no outbound access)
- SQLite persistence (durability)
- Auto-scaling based on queue depth tiers
- Dashboard with live metrics (/v1/metrics)
- Frontend React UI
