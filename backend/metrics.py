"""FemScale Metrics Collection - Lightweight session-based metrics."""

import threading
from typing import Dict, List, Any
from collections import deque
from datetime import datetime

from redis_client import get_redis_client


class MetricsCollection:
    """Thread-safe metrics collection for FemScale."""

    def __init__(self, max_events: int = 100):
        """Initialize metrics collection.
        
        Args:
            max_events: Maximum number of events to keep in history
        """
        self.lock = threading.Lock()
        self.events: deque = deque(maxlen=max_events)
        self.jobs_completed_count = 0
        self.total_cost_usd = 0.0
        self.workers_active_count = 0
        self.workers_target_count = 0

    def add_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        Record a metrics event.
        
        Args:
            event_type: Type of event (e.g., 'worker_spawned', 'job_completed')
            details: Event details dict
        """
        with self.lock:
            event = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "type": event_type,
                **details,
            }
            self.events.append(event)

    def increment_job_completed(self, cost_usd: float = 0.0) -> None:
        """Record job completion."""
        with self.lock:
            self.jobs_completed_count += 1
            self.total_cost_usd += cost_usd

    def set_workers_state(self, active: int, target: int) -> None:
        """Update worker state."""
        with self.lock:
            self.workers_active_count = active
            self.workers_target_count = target

    def get_snapshot(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        redis_client = get_redis_client()

        with self.lock:
            # Query Redis for runtime state
            queue_depth = redis_client.get_queue_depth()

            # Count jobs by status
            jobs_running = self._count_jobs_by_status("running")

            return {
                "queue_depth": queue_depth,
                "workers_target": self.workers_target_count,
                "workers_active": self.workers_active_count,
                "jobs_running": jobs_running,
                "jobs_completed_session": self.jobs_completed_count,
                "total_cost_session_usd": self.total_cost_usd,
                "events": list(self.events),
            }

    def _count_jobs_by_status(self, status: str) -> int:
        """Count jobs in Redis by status (approximate)."""
        # For demo purposes, we scan Redis keys matching job:*
        # In production, you'd maintain indices or use a database
        redis_client = get_redis_client()
        count = 0

        try:
            # Try to scan Redis keys (real Redis)
            if hasattr(redis_client.backend, "keys"):
                pattern = "job:*"
                keys = redis_client.backend.keys(pattern)
                for key in keys:
                    job_data = redis_client.get_job(key.replace("job:", ""))
                    if job_data and job_data.get("status") == status:
                        count += 1
        except Exception:
            # Fall back to 0 if Redis doesn't support keys scanning
            pass

        return count


# Global metrics instance (singleton)
_metrics: MetricsCollection = None


def get_metrics() -> MetricsCollection:
    """Get or create global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollection()
    return _metrics


def init_metrics() -> MetricsCollection:
    """Initialize metrics collection."""
    global _metrics
    _metrics = MetricsCollection()
    return _metrics
