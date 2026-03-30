# FemScale Phase 5: Metrics Endpoint

## Overview

Phase 5 implements real-time metrics collection and a lightweight `/v1/metrics` endpoint for monitoring the FemScale system. This enables dashboard observability, cost tracking, and auto-scaling visibility.

**Status:** ✅ **COMPLETE**

---

## Metrics Endpoint

### GET /v1/metrics

Returns real-time system metrics and event history.

**Endpoint:** `http://localhost:8000/v1/metrics`

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

---

## Metrics Fields

| Field | Type | Description |
|---|---|---|
| `queue_depth` | int | Jobs currently waiting in Redis queue |
| `workers_target` | int | Target workers from scaling policy (1-10) |
| `workers_active` | int | Currently running worker processes |
| `jobs_running` | int | Jobs with status="running" in Redis |
| `jobs_completed_session` | int | Jobs completed since API startup |
| `total_cost_session_usd` | float | Total USD cost of completed jobs |
| `events` | array | Recent system events (last 100) |

---

## Event Types

### job_completed
Emitted when a job finishes (success, failed, or timeout).

```json
{
  "timestamp": "2026-03-30T12:00:45.123Z",
  "type": "job_completed",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "duration_ms": 250,
  "cost_usd": 0.0000001
}
```

### worker_spawned
Emitted when scaler creates a new worker process.

```json
{
  "timestamp": "2026-03-30T12:00:40.000Z",
  "type": "worker_spawned",
  "worker_pid": 12345
}
```

### worker_terminated
Emitted when scaler terminates a worker process.

```json
{
  "timestamp": "2026-03-30T12:00:50.000Z",
  "type": "worker_terminated",
  "worker_pid": 12345
}
```

---

## Implementation Details

### metrics.py (New)

Thread-safe metrics collection with singleton pattern.

**MetricsCollection class:**
- `add_event(event_type, details)` - Record an event
- `increment_job_completed(cost_usd)` - Update job counter and total cost
- `set_workers_state(active, target)` - Update worker state from scaler
- `get_snapshot()` - Get current metrics dictionary
  - Queries Redis for queue_depth and jobs_running
  - Returns in-memory counters and event log

**Features:**
- Thread-safe via `threading.Lock()`
- Bounded event history (max 100 events via `deque.maxlen`)
- Singleton pattern via module-level `get_metrics()` function
- Lightweight: no database, all in-memory with Redis queries

### Integration Points

#### main.py
- Import and initialize `MetricsCollection` on startup
- Add `GET /v1/metrics` endpoint
- Return `MetricsResponse` model

#### worker.py
- Import `get_metrics()`
- Call `metrics.add_event("job_completed", {...})` when job finishes
- Call `metrics.increment_job_completed(cost_usd)` to update counters

#### scaler.py
- Import `get_metrics()`
- Call `metrics.set_workers_state(active, target)` on each check loop
- Call `metrics.add_event("worker_spawned", {...})` when spawning
- Call `metrics.add_event("worker_terminated", {...})` when terminating

#### models.py
- Add `MetricsResponse` Pydantic model
- Add `MetricsEvent` model for type documentation

---

## Usage Examples

### Curl to Check Metrics

```bash
curl http://localhost:8000/v1/metrics | python -m json.tool
```

### Python Polling

```python
import requests
import json

response = requests.get("http://localhost:8000/v1/metrics")
metrics = response.json()

print(f"Queue depth: {metrics['queue_depth']}")
print(f"Active workers: {metrics['workers_active']}/{metrics['workers_target']}")
print(f"Total cost: ${metrics['total_cost_session_usd']:.10f}")
```

### Dashboard Integration

```javascript
// Fetch metrics every 5 seconds for dashboard
setInterval(async () => {
  const response = await fetch('http://localhost:8000/v1/metrics');
  const metrics = await response.json();
  
  // Update dashboard
  document.getElementById('queue').textContent = metrics.queue_depth;
  document.getElementById('workers').textContent = 
    `${metrics.workers_active}/${metrics.workers_target}`;
  document.getElementById('cost').textContent = 
    `$${metrics.total_cost_session_usd.toFixed(10)}`;
  
  // Append latest event
  if (metrics.events.length > 0) {
    const event = metrics.events[metrics.events.length - 1];
    console.log(`${event.type}: ${JSON.stringify(event)}`);
  }
}, 5000);
```

---

## Testing

### Run Metrics Test Script

```bash
python test_metrics.py
```

Tests:
1. Metrics available with no jobs
2. Queue depth increases when jobs submitted
3. Response has all required fields
4. Event structure is correct

### Manual Testing

```bash
# Terminal 1: Start API
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: View metrics
curl http://localhost:8000/v1/metrics | python -m json.tool

# Terminal 3: Submit jobs (in background)
for i in {1..5}; do
  curl -X POST http://localhost:8000/v1/jobs \
    -H "Content-Type: application/json" \
    -d '{"code":"import time; time.sleep(1); print(\"done\")","timeout_sec":30}' &
done

# Terminal 2: Watch metrics update (run in loop)
watch -n 1 "curl -s http://localhost:8000/v1/metrics | python -m json.tool"
```

---

## Design Decisions

### 1. **In-Memory Metrics (No Database)**
**Decision:** Store metrics in thread-safe Python objects, not Redis  
**Rationale:**
- Metrics are session-based (ephemeral)
- No need for persistence across restarts
- Lightweight and demo-friendly
- Reduces latency (O(1) memory access vs Redis network)

### 2. **Event Log Bounded at 100**
**Decision:** Keep circular buffer of last 100 events  
**Rationale:**
- Prevents unbounded memory growth
- Sufficient for monitoring dashboards
- Typical session shows 10-20 events
- Full history available in production via database

### 3. **Session-Based Counters**
**Decision:** Count jobs/cost from startup, not persistent  
**Rationale:**
- Matches "demo-friendly" requirement
- Simplifies implementation
- Useful for per-session monitoring
- Production would persist to database

### 4. **Redis Queries for Queue/Running**
**Decision:** Query Redis each time instead of caching  
**Rationale:**
- Single Redis call per metrics snapshot (O(1) for `llen`, slower for jobs_running)
- Always accurate, never stale
- Redis operations are fast (<1ms local)
- Alternative: cache and accept eventual consistency

### 5. **Thread-Safe via Lock**
**Decision:** Use `threading.Lock()` for mutual exclusion  
**Rationale:**
- API (FastAPI) and workers may access metrics concurrently
- Simple lock simpler than async queue or message bus
- Lock contention minimal (millisecond holds)
- Sufficient for current scale

---

## Architecture Diagram

```
┌─────────────────────────────────────┐
│      FastAPI Application            │
│                                     │
│  POST /v1/jobs → enqueue            │
│  GET /v1/jobs/{id} → retrieve       │
│  GET /v1/metrics → metrics ◄────┐   │
│                                 │   │
└─────────────────────────────────┼───┘
                                  │
                    ┌─────────────────────────┐
                    │   MetricsCollection     │
                    │  (Thread-Safe)          │
                    │                         │
                    │ • events deque(100)     │
                    │ • counters              │
                    │ • lock                  │
                    │ • get_snapshot()        │
                    └─────────────────────────┘
                         ▲      ▲      ▲
                         │      │      │
                   ┌─────┴──┬───┴──┬───┴──────┐
                   │        │      │          │
            ┌──────▼──┐  (worker.py)   (scaler.py)
            │  Redis  │   │      │          │
            │         │   │  emit events   │
            │ jobs    │   │  track cost    │
            └─────────┘   └────────────────┘
```

---

## Performance Characteristics

| Operation | Latency | Note |
|---|---|---|
| GET /v1/metrics | <10ms | Local memory access + 1 Redis call |
| metrics.add_event() | <1ms | Append to deque |
| metrics.increment_job_completed() | <1ms | Update counters |
| metrics.set_workers_state() | <1ms | Update state |
| get_queue_depth() | <5ms | Redis LLEN call |
| get_jobs_running() | <100ms | Redis KEYS scan (worst case) |

---

## Configuration

No configuration needed for basic operation. Customize in `metrics.py`:

```python
class MetricsCollection:
    def __init__(self, max_events: int = 100):  # ← Change event buffer size
        ...
```

---

## Future Enhancements

1. **Persistent History** - Store snapshots to SQLite/PostgreSQL
2. **Metrics Export** - Prometheus `/metrics` endpoint
3. **Alerts** - Alert when queue depth > threshold
4. **Histograms** - Track job duration/cost distributions
5. **Throughput** - Jobs per second, latency percentiles
6. **Per-User Metrics** - Track cost per user/team
7. **Anomaly Detection** - Detect unusual patterns
8. **Grafana Dashboards** - Pre-built visualization

---

## Integration Checklist

- ✅ metrics.py created (thread-safe collection)
- ✅ models.py updated (MetricsResponse, MetricsEvent)
- ✅ main.py updated (GET /v1/metrics endpoint, startup init)
- ✅ worker.py updated (emit job_completed events, track cost)
- ✅ scaler.py updated (emit worker events, track state)
- ✅ test_metrics.py created (endpoint tests)
- ✅ Syntax validation passed
- ✅ Import tests passed
- ✅ No breaking changes

---

## Quick Reference

```bash
# Start API with metrics enabled
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Get metrics
curl http://localhost:8000/v1/metrics

# Run metrics tests
python test_metrics.py

# Watch metrics in real-time
watch -n 1 "curl -s http://localhost:8000/v1/metrics | jq ."
```

---

**Status:** Phase 5 Metrics Endpoint is complete and ready for integration.
