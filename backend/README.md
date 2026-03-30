# FemScale Backend - Phase 5: Metrics Endpoint

## Structure

```
backend/
├── __init__.py
├── main.py              # FastAPI app with jobs, metrics endpoints
├── models.py            # Pydantic request/response models
├── config.py            # Constants and configuration
├── redis_client.py      # Redis operations + in-memory mock fallback
├── worker.py            # Job execution worker (Phase 3)
├── scaler.py            # Auto-scaler for dynamic worker management (Phase 4)
├── metrics.py           # Metrics collection (Phase 5)
├── test_phase2.py       # Integration tests
├── test_worker.py       # Worker tests
├── test_scaler.py       # Scaler demonstration script
├── test_metrics.py      # Metrics endpoint tests (Phase 5)
├── requirements.txt     # Dependencies
├── README.md            # This file
├── README_PHASE3.md     # Phase 3 worker documentation
├── README_PHASE4.md     # Phase 4 scaler documentation
└── README_PHASE5.md     # Phase 5 metrics documentation
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Terminal 1: Start FastAPI backend with metrics enabled
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start auto-scaler (manages workers automatically)
python scaler.py

# Terminal 3: Submit test jobs
python test_scaler.py
```

## Running Individual Components

### Backend API Only (Manual Worker Management)
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Single Worker (Without Scaler)
```bash
python worker.py
```

### Auto-Scaler (Manages 1-10 Workers Dynamically)
```bash
python scaler.py
```

## API Endpoints

### POST /v1/jobs
Submit a Python function for execution.

**Request:**
```json
{
  "code": "print('hello world')",
  "timeout_sec": 30,
  "input": {}
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
  "status": "queued",
  "stdout": "",
  "stderr": "",
  "error": null,
  "duration_ms": 0,
  "memory_mb": 0.0,
  "cost_usd": 0.0,
  "created_at": "2026-03-30T10:00:00.000Z",
  "completed_at": null
}
```

### GET /v1/metrics
Get real-time system metrics and recent events.

**Response (200 OK):**
```json
{
  "queue_depth": 5,
  "workers_target": 3,
  "workers_active": 2,
  "jobs_running": 2,
  "jobs_completed_session": 15,
  "total_cost_session_usd": 0.0000025,
  "events": [
    {
      "timestamp": "2026-03-30T12:00:45.123Z",
      "type": "job_completed",
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "success",
      "duration_ms": 250,
      "cost_usd": 0.0000001
    },
    {
      "timestamp": "2026-03-30T12:00:40.000Z",
      "type": "worker_spawned",
      "worker_pid": 12345
    }
  ]
}
```

**Metrics Fields:**
- `queue_depth`: Jobs waiting in queue
- `workers_target`: Target worker count from scaling policy
- `workers_active`: Currently active worker processes
- `jobs_running`: Jobs currently executing
- `jobs_completed_session`: Total jobs finished this session
- `total_cost_session_usd`: Total execution cost this session
- `events`: Recent system events (worker spawned/terminated, job completed)

## Implementation Details

### Phase 1 (Complete)
- ✅ FastAPI app with /v1 prefix
- ✅ POST /v1/jobs with validation (code ≤50KB, timeout 1–30 sec)
- ✅ GET /v1/jobs/{job_id} with full job object
- ✅ UUID4 job IDs
- ✅ ISO8601 UTC timestamps
- ✅ Exact status enum (queued, running, success, failed, timeout)
- ✅ Pydantic models for all requests/responses
- ✅ FastAPI docstrings for /docs
- ✅ Error handling (422, 413, 404)

### Phase 2 (Complete) — Redis Queue Integration
- ✅ Redis FIFO queue (`jobs_queue` list)
- ✅ Job storage in Redis (`job:{job_id}` keys with JSON values, 1hr TTL)
- ✅ In-memory mock fallback (for development without Redis server)
- ✅ Queue depth tracking via `redis_client.get_queue_depth()`
- ✅ Job enqueue on POST /v1/jobs
- ✅ Job retrieval from Redis on GET /v1/jobs/{job_id}
- ✅ Automatic graceful fallback to in-memory storage if Redis unavailable

### Phase 3 (Complete) — Worker System
- ✅ Created `worker.py` with continuous queue polling
- ✅ BLPOP/LPOP queue consumption from Redis
- ✅ Safe code execution via `subprocess.run()` (never `exec`/`eval`)
- ✅ Timeout handling with `TimeoutExpired` exception
- ✅ Capture stdout, stderr, exit code, and duration
- ✅ Status transitions: queued → running → (success/failed/timeout)
- ✅ Results stored back to Redis atomically
- ✅ Cost calculation via AWS Lambda pricing formula
- ✅ Manual worker execution: `python worker.py`

### Phase 4 (Complete) — Auto-Scaler
- ✅ Created `scaler.py` for dynamic worker management
- ✅ Monitoring Redis queue depth every 3 seconds
- ✅ Scaling policy: 0-4→1, 5-19→3, 20-49→7, 50+→10 workers
- ✅ Spawn/terminate worker processes via multiprocessing
- ✅ Track active worker count and process PIDs
- ✅ Graceful process termination with timeout and kill fallback
- ✅ Test script with scaling demonstration
- ✅ Simple implementation (no Docker yet)

### Phase 5 (Complete) — Metrics Endpoint
- ✅ Created `metrics.py` for thread-safe metrics collection
- ✅ Implemented GET /v1/metrics endpoint
- ✅ Real-time metrics: queue_depth, workers_target, workers_active, jobs_running
- ✅ Session tracking: jobs_completed, total_cost_usd
- ✅ Event log: worker_spawned, worker_terminated, job_completed
- ✅ Integrated with worker.py (track job completion)
- ✅ Integrated with scaler.py (track worker lifecycle)
- ✅ Bounded event history (circular deque, max 100 events)
- ✅ Thread-safe metrics collection via locks

### Future Phases
- Phase 6: Docker container-based job execution (instead of subprocess)
- Phase 7: Kubernetes operator for cloud deployment
- Phase 8: Database persistence (SQLite for job history)
- Phase 9: Prometheus metrics export and alerting

## Testing

### Phase 2: Queue Integration Tests
```bash
python test_phase2.py
```

### Phase 3: Worker Tests  
```bash
python test_worker.py
```

### Phase 4: Scaler Demonstration
```bash
# This interactive script submits jobs and shows scaling in action
python test_scaler.py
```

### Phase 5: Metrics Endpoint Tests
```bash
python test_metrics.py
```

Required: Backend API and scaler must both be running.

## Configuration

All settings are in `config.py`:

```python
# Constraints
MAX_CODE_SIZE_BYTES = 50 * 1024  # 50KB limit
MIN_TIMEOUT_SEC = 1
MAX_TIMEOUT_SEC = 30
DEFAULT_TIMEOUT_SEC = 30

# Scaling policy (queue_depth → target_workers)
SCALING_TIERS = [
    {"queue_depth_min": 0, "queue_depth_max": 5, "target_workers": 1},
    {"queue_depth_min": 5, "queue_depth_max": 20, "target_workers": 3},
    {"queue_depth_min": 20, "queue_depth_max": 50, "target_workers": 7},
    {"queue_depth_min": 50, "queue_depth_max": float("inf"), "target_workers": 10},
]

# Scaler parameters
SCALER_CHECK_INTERVAL_SEC = 3  # Check every 3 seconds
MAX_WORKERS = 10
MIN_WORKERS = 1
```

## Example Workflow

### Full System Test (with auto-scaler):

```bash
# Terminal 1: Start API
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start auto-scaler
python scaler.py

# Terminal 3: Submit 30 jobs (will trigger scaling: 1→3→7 workers)
for i in {1..30}; do
  curl -X POST http://localhost:8000/v1/jobs \
    -H "Content-Type: application/json" \
    -d '{"code":"import time; time.sleep(2); print(\"done\")","timeout_sec":10}' &
done
```

Scaler output:
```
📊 Queue depth: 0, Workers: 0/1 → Scaling UP by 1
  ➕ Spawned worker 12345
📊 Queue depth: 10, Workers: 1/3 → Scaling UP by 2
  ➕ Spawned worker 12346
  ➕ Spawned worker 12347
📊 Queue depth: 25, Workers: 3/7 → Scaling UP by 4
  ➕ Spawned worker 12348
  ➕ Spawned worker 12349
  ➕ Spawned worker 12350
  ➕ Spawned worker 12351
```

## Features

✅ **In-Memory Mock Fallback** — Uses Python `deque` + dict if Redis unavailable  
✅ **Automatic Serialization** — Jobs stored as JSON with full history  
✅ **FIFO Queue** — Redis LPOP/RPUSH for proper queue semantics  
✅ **TTL Support** — Redis jobs expire after 1 hour (configurable)  
✅ **Queue Depth Metric** — Available for dashboard polling  
✅ **Dynamic Scaling** — Auto-scales 1-10 workers based on queue  
✅ **Graceful Shutdown** — Terminates all workers on Ctrl+C  
✅ **Process Monitoring** — Cleans up dead processes automatically  
✅ **Real-Time Metrics** — GET /v1/metrics for system observability  
✅ **Event Tracking** — Track worker lifecycle and job completions  

## Detailed Documentation

- [Phase 3: Worker Documentation](README_PHASE3.md) - Job execution details
- [Phase 4: Scaler Documentation](README_PHASE4.md) - Auto-scaling architecture
- [Phase 5: Metrics Documentation](README_PHASE5.md) - Metrics endpoint and monitoring

**Not Yet Implemented:**
- Worker execution (Phase 2)
- Docker container spawning (Phase 2)
- SQLite persistence (Phase 2)
- Auto-scaling (Phase 3)
- Dashboard metrics (Phase 3)

## Testing

All endpoints have been validated:
- ✅ POST /v1/jobs returns 201 with job_id and status
- ✅ GET /v1/jobs/{job_id} returns full job object
- ✅ /docs OpenAPI UI works
- ✅ Empty code returns 422
- ✅ Invalid job_id returns 404
