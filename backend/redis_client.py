"""Redis client for FemScale job storage and queueing.

Supports both real Redis and in-memory mock for development.
"""

import json
from typing import Optional, Dict, Any, List
from collections import deque

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class InMemoryRedis:
    """In-memory mock Redis for development (Python deque + dict)."""

    def __init__(self):
        """Initialize in-memory storage."""
        self.store: Dict[str, str] = {}  # key -> JSON value
        self.queue: deque = deque()  # FIFO job queue

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        """Store key-value with TTL (TTL ignored in mock)."""
        self.store[key] = value

    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return self.store.get(key)

    def rpush(self, key: str, value: str) -> None:
        """Push value to end of queue (only supports 'jobs_queue')."""
        if key == "jobs_queue":
            self.queue.append(value)

    def blpop(self, key: str, timeout: int = 1) -> Optional[tuple]:
        """Pop from front of queue (timeout ignored in mock)."""
        if key == "jobs_queue" and self.queue:
            return (key, self.queue.popleft())
        return None

    def llen(self, key: str) -> int:
        """Get queue length."""
        if key == "jobs_queue":
            return len(self.queue)
        return 0

    def ping(self) -> str:
        """Test connection."""
        return "PONG"


class RedisClient:
    """Redis operations for job storage and FIFO queue management."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, use_mock: bool = False):
        """Initialize Redis connection or fall back to mock."""
        self.use_mock = use_mock
        self.backend = None

        if not use_mock and REDIS_AVAILABLE:
            try:
                self.backend = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                self.backend.ping()
                print(f"✓ Connected to Redis at {host}:{port}")
            except Exception as e:
                print(f"Redis connection failed: {e}")
                print("Falling back to in-memory mock")
                self.backend = InMemoryRedis()
                self.use_mock = True
        else:
            print("Using in-memory Redis mock (development mode)")
            self.backend = InMemoryRedis()
            self.use_mock = True

    def store_job(self, job_id: str, job_data: Dict[str, Any], ttl_seconds: int = 3600) -> None:
        """
        Store a job object in Redis with TTL.

        Args:
            job_id: UUID4 job identifier
            job_data: Job object dict
            ttl_seconds: Time-to-live (default 1 hour)
        """
        key = f"job:{job_id}"
        self.backend.setex(key, ttl_seconds, json.dumps(job_data))

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a job object from Redis.

        Args:
            job_id: UUID4 job identifier

        Returns:
            Job dict or None if not found
        """
        key = f"job:{job_id}"
        data = self.backend.get(key)
        if data is None:
            return None
        return json.loads(data)

    def enqueue_job(self, job_id: str) -> None:
        """
        Push job_id to the end of the FIFO queue.

        Args:
            job_id: UUID4 job identifier
        """
        self.backend.rpush("jobs_queue", job_id)

    def dequeue_job(self) -> Optional[str]:
        """
        Pop job_id from the front of the FIFO queue (blocking).

        Returns:
            job_id or None if queue empty
        """
        result = self.backend.blpop("jobs_queue", timeout=1)
        if result is None:
            return None
        return result[1]  # blpop returns (key, value)

    def get_queue_depth(self) -> int:
        """Get number of jobs currently in queue."""
        return self.backend.llen("jobs_queue")

    def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """
        Update a job's status and optional fields.

        Args:
            job_id: UUID4 job identifier
            status: New status value
            **kwargs: Additional fields to update (stdout, stderr, duration_ms, etc.)
        """
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")

        job["status"] = status
        # Update all provided fields (even if not in initial job)
        for key, value in kwargs.items():
            job[key] = value

        self.store_job(job_id, job)

    def qlen(self) -> int:
        """Alias for get_queue_depth()."""
        return self.get_queue_depth()

    def ping(self) -> bool:
        """Test connection."""
        try:
            self.backend.ping()
            return True
        except Exception:
            return False


# Global Redis client (singleton)
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get or create global Redis client."""
    global _redis_client
    if _redis_client is None:
        # Try real Redis first, fall back to mock
        _redis_client = RedisClient(use_mock=False)
    return _redis_client


def init_redis(host: str = "localhost", port: int = 6379, db: int = 0, use_mock: bool = False) -> RedisClient:
    """Initialize Redis client with custom parameters."""
    global _redis_client
    _redis_client = RedisClient(host=host, port=port, db=db, use_mock=use_mock)
    return _redis_client
