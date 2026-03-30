"""FemScale Metrics Collection - Redis-backed session metrics (cross-process)."""

import json
from datetime import datetime, timezone
from typing import Dict, List, Any

from redis_client import get_redis_client


# Redis keys for metrics
_KEY_JOBS_COMPLETED = "femscale:metrics:jobs_completed"
_KEY_TOTAL_COST = "femscale:metrics:total_cost"
_KEY_WORKERS_ACTIVE = "femscale:metrics:workers_active"
_KEY_WORKERS_TARGET = "femscale:metrics:workers_target"
_KEY_EVENTS = "femscale:metrics:events"
_MAX_EVENTS = 100


class MetricsCollection:
    """Redis-backed metrics collection for FemScale.

    Stores all counters in Redis so worker, scaler, and API
    processes share the same live data.
    """

    def __init__(self):
        """Initialize — nothing stored in-memory, everything in Redis."""
        self.redis = get_redis_client()

    # ─── helpers ───────────────────────────────────────
    def _r(self):
        """Returns the raw Redis backend."""
        return self.redis.backend

    @staticmethod
    def _now_iso() -> str:
        return (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

    # ─── events ────────────────────────────────────────
    def add_event(self, event_type: str, details: Dict[str, Any] = None) -> None:
        """Record a metrics event (stored in Redis list, capped at _MAX_EVENTS)."""
        event = {
            "timestamp": self._now_iso(),
            "type": event_type,
            "event": event_type,          # frontend reads both keys
            **(details or {}),
        }
        self._r().rpush(_KEY_EVENTS, json.dumps(event))
        # Trim so list doesn't grow unbounded
        self._r().ltrim(_KEY_EVENTS, -_MAX_EVENTS, -1)

    # ─── jobs ──────────────────────────────────────────
    def increment_job_completed(self, cost_usd: float = 0.0,
                                 job_id: str = None,
                                 status: str = "success",
                                 duration_ms: int = 0) -> None:
        """Record job completion — updates counter, cost, and adds event."""
        self._r().incr(_KEY_JOBS_COMPLETED)
        # INCRBYFLOAT for precise cost accumulation
        self._r().incrbyfloat(_KEY_TOTAL_COST, cost_usd)

        # Record event
        details = {}
        if job_id:
            details["job_id"] = job_id
        if status:
            details["status"] = status
        if duration_ms:
            details["duration_ms"] = duration_ms
        details["cost_usd"] = cost_usd
        self.add_event("job_completed", details)

    # ─── workers ───────────────────────────────────────
    def set_workers_state(self, active: int, target: int) -> None:
        """Update worker state (called by scaler)."""
        self._r().set(_KEY_WORKERS_ACTIVE, str(active))
        self._r().set(_KEY_WORKERS_TARGET, str(target))

    def increment_workers_active(self) -> None:
        self._r().incr(_KEY_WORKERS_ACTIVE)

    def decrement_workers_active(self) -> None:
        val = int(self._r().get(_KEY_WORKERS_ACTIVE) or 0)
        self._r().set(_KEY_WORKERS_ACTIVE, str(max(0, val - 1)))

    # ─── snapshot for GET /v1/metrics ──────────────────
    def get_snapshot(self) -> Dict[str, Any]:
        """Get current metrics snapshot — all data from Redis."""
        r = self._r()
        redis_client = get_redis_client()

        # Queue depth
        queue_depth = redis_client.get_queue_depth()

        # Jobs running (scan Redis for running jobs)
        jobs_running = self._count_jobs_by_status("running")

        # Counters
        jobs_completed = int(r.get(_KEY_JOBS_COMPLETED) or 0)
        total_cost = float(r.get(_KEY_TOTAL_COST) or 0.0)
        workers_active = int(r.get(_KEY_WORKERS_ACTIVE) or 0)
        workers_target = int(r.get(_KEY_WORKERS_TARGET) or 1)

        # Events list
        raw_events = r.lrange(_KEY_EVENTS, 0, -1)
        events = []
        for raw in raw_events:
            try:
                events.append(json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "queue_depth": queue_depth,
            "workers_target": workers_target,
            "workers_active": workers_active,
            "jobs_running": jobs_running,
            "jobs_completed_session": jobs_completed,
            "total_cost_session_usd": total_cost,
            "events": events,
        }

    def _count_jobs_by_status(self, status: str) -> int:
        """Count jobs in Redis by status."""
        redis_client = get_redis_client()
        count = 0
        try:
            if hasattr(redis_client.backend, "keys"):
                keys = redis_client.backend.keys("job:*")
                for key in keys:
                    job_id = key.replace("job:", "") if isinstance(key, str) else key.decode().replace("job:", "")
                    job_data = redis_client.get_job(job_id)
                    if job_data and job_data.get("status") == status:
                        count += 1
        except Exception:
            pass
        return count


# ─── Singleton ────────────────────────────────────────
_metrics: MetricsCollection = None


def get_metrics() -> MetricsCollection:
    """Get or create global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollection()
    return _metrics


def init_metrics() -> MetricsCollection:
    """Initialize metrics collection — resets session counters in Redis."""
    global _metrics
    _metrics = MetricsCollection()

    # Reset session counters only (not worker state — workers track themselves)
    r = _metrics._r()
    r.set(_KEY_JOBS_COMPLETED, "0")
    r.set(_KEY_TOTAL_COST, "0.0")
    r.delete(_KEY_EVENTS)
    # Don't reset workers_active / workers_target — workers register themselves

    return _metrics

