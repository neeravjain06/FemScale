# FemScale Phase 4: Auto-Scaler

## Overview

The auto-scaler dynamically adjusts the number of worker processes based on Redis queue depth using a simple tiered scaling policy.

## Architecture

```
┌─────────────────────────────────────┐
│   FastAPI (POST/GET /v1/jobs)       │
│   Enqueues jobs to Redis            │
└─────────────────────────────────────┘
              ↓
    ┌─────────────────────────────┐
    │    Redis Queue (FIFO)       │
    │  - store_job(job_id, job)   │
    │  - enqueue_job(job_id)      │
    │  - get_queue_depth()        │
    └─────────────────────────────┘
              ↑
     ┌────────────────────────────────────┐
     │  Scaler (monitors queue depth)     │
     │  - Check every 3 seconds           │
     │  - Calculate target worker count   │
     │  - Spawn/terminate worker processes│
     └────────────────────────────────────┘
              ↓
     ┌────────────────────────────────────┐
     │ Worker Pool (multiprocessing)      │
     │ - 1-10 processes (dynamic)         │
     │ - Each polls Redis queue           │
     │ - Executes jobs via subprocess     │
     └────────────────────────────────────┘
```

## Scaling Policy

The scaler automatically adjusts the number of workers based on queue depth:

| Queue Depth | Target Workers |
|---|---|
| 0–4 | 1 |
| 5–19 | 3 |
| 20–49 | 7 |
| 50+ | 10 |

(Configured in `config.py`: `SCALING_TIERS`)

## Usage

### Start the scaler

```bash
python scaler.py
```

### Example output

```
🚀 FemScale Auto-Scaler started
   Check interval: 3s
   Scaling tiers: [...]

📊 Queue depth: 0, Workers: 0/1 → Scaling UP by 1
  ➕ Spawned worker 12345
📊 Queue depth: 5, Workers: 1/3 → Scaling UP by 2
  ➕ Spawned worker 12346
  ➕ Spawned worker 12347
📊 Queue depth: 2, Workers: 3/1 → Scaling DOWN by 2
  ➖ Terminated worker 12346
  ➖ Terminated worker 12347
```

### Graceful shutdown

Press `Ctrl+C` to shutdown the scaler and terminate all worker processes.

## Implementation Details

### scaler.py

**WorkerManager class:**
- `get_target_worker_count(queue_depth)` - Determines target workers from policy
- `spawn_worker()` - Creates new worker process
- `terminate_worker(pid)` - Gracefully stops a worker process
- `scale_up(count)` / `scale_down(count)` - Adds/removes workers
- `run()` - Main monitoring loop (checks every 3 seconds)
- `shutdown()` - Graceful cleanup

**Constraints:**
- Simple implementation using Python's `multiprocessing.Process`
- No external orchestration (Kubernetes, Docker Swarm, etc.)
- Runs on a single machine
- All processes share same Redis instance

### worker.py (update)

New entry point function:
- `worker_process_main()` - Called by scaler to spawn each worker
- Ensures each worker process initializes its own Redis connection
- Prevents Redis connection sharing issues across processes

## Testing

### 1. Start backend and scaler

```bash
# Terminal 1: Backend API
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Scaler
python scaler.py
```

### 2. Submit multiple jobs to trigger scaling

```bash
# Terminal 3: Submit 30 jobs
for i in {1..30}; do
  curl -s -X POST http://localhost:8000/v1/jobs \
    -H "Content-Type: application/json" \
    -d "{\"code\":\"import time; time.sleep(2); print('done')\",\"timeout_sec\":10}" &
done
```

### 3. Observe scaler output

The scaler should:
1. Detect queue depth increasing
2. Scale UP to 1 → 3 → 7 workers
3. Workers execute jobs in parallel
4. Scale DOWN as queue empties

## Design Decisions

### Why multiprocessing instead of threading?

- **CPU-bound work**: Job execution via subprocess is CPU-intensive
- **GIL avoidance**: Multiprocessing bypasses Python's Global Interpreter Lock
- **Isolation**: Each worker runs in isolated process with own memory space

### Why not Docker yet?

- Phase 4 uses simple subprocess execution (local mode)
- Docker container spawning comes in Phase 5
- Scaler architecture remains the same; only execution backend changes

### Why simple scale-in strategy?

Current implementation uses FIFO termination (terminate oldest workers first).
A more sophisticated approach could:
- Drain jobs from workers being terminated
- Track worker age/efficiency
- But this adds complexity; simple FIFO is sufficient for now

## Integration with existing code

The scaler is completely **optional** and independent from the API/worker system:

- **Without scaler**: Run 1-N workers manually, handle scaling yourself
- **With scaler**: Run scaler once, let it manage workers automatically

To run a single worker manually (not via scaler):

```bash
python worker.py
```

To run scaler-managed workers: Use the scaler!

## Configuration

Edit `config.py`:
- `SCALING_TIERS` - Adjust queue depth ranges and target worker counts
- `SCALER_CHECK_INTERVAL_SEC` - How often to check queue (default: 3s)
- `MAX_WORKERS` - Absolute max workers allowed
- `MIN_WORKERS` - Minimum workers to keep alive

## Future Improvements

1. **Metrics tracking**: Log scaling events, worker utilization, throughput
2. **Graceful drain**: When scaling down, finish current jobs before termination
3. **Worker health checks**: Restart dead/hung workers
4. **Distributed scaler**: Multiple scaler instances for fault tolerance
5. **Docker integration**: Spawn containers instead of local processes
6. **Kubernetes operator**: Fully automated scaling via CRDs
