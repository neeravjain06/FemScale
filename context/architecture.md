# FemScale Context
Follow this strictly. Do not deviate from API or rules.
##  System Architecture

FemScale follows a six-stage sequential execution pipeline. Each stage is independently
responsible for one concern, ensuring graceful degradation if any stage fails.

#### Execution Pipeline

```
Stage Name Description
1 Function Submission React UI sends code to POST /v1/jobs. Backend assigns job_id,
stores code in Redis, returns job_id.
2 Job Queuing Job object pushed to Redis FIFO list with status: queued. job_id
returned to client immediately.
```

```
Stage Name Description
```
```
3 Worker Execution Worker BLPOP dequeues job, spins Docker container (128MB / 1
CPU / 30s timeout), captures stdout + stderr.
4 Auto-Scaling Scaler process checks Redis queue depth every 3 seconds and
adjusts worker count per tiered policy.
5 Logging & Cost Completed job written to SQLite. Cost calculated using AWS Lambda
formula and stored with record.
6 Dashboard React polls GET /v1/metrics every 2s. Displays workers, queue
depth, recent jobs, and cumulative cost.
```
#### Auto-Scaling Tiered Policy

```
Queue Depth Target Workers Action
```
```
0 – 5 jobs 1 worker (minimum) Kill idle workers down to
minimum
5 – 20 jobs 3 workers Spawn additional workers
```
```
20 – 50 jobs 7 workers Spawn additional workers
50+ jobs 10 workers (maximum) Spawn to cap, reject no jobs
```
#### Docker Container Constraints

- Memory limit: 128MB enforced via --memory=128m
- CPU limit: 1 core enforced via --cpus=
- Execution timeout: 30 seconds enforced via subprocess timeout — container killed on
    breach, job set to timeout
- Network: none — fully isolated, no outbound internet access from container
- Filesystem: read-only host, ephemeral container write layer only
- Lifecycle: spawned per job, destroyed immediately on completion — no container reuse

#### Cost Estimation Formula

Calculated after every job completion and stored in SQLite:

```
Cost = (Memory_GB x Duration_seconds) x $0.
```
Mirrors the AWS Lambda pricing model. Surfaced per run and as a running session total on the
dashboard.

## Security Model

- No outbound network access from containers
- Read-only host filesystem; ephemeral container writes only
- Strict resource limits (128MB memory, 1 CPU, 30s timeout)
- One container per job; destroyed after execution

## Observability

- stdout and stderr captured per job
- Job metadata and results stored in SQLite
- Live metrics exposed via /v1/metrics
- Event log included in metrics response
- No distributed tracing in MVP

## Cold Start Behavior

- Each job runs in a fresh Docker container
- Container startup introduces execution latency (cold start)
- No container reuse in MVP

## System Flow

User → FastAPI → Redis Queue → Worker → Docker Container → SQLite → API → Frontend