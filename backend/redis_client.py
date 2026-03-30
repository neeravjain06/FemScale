"""Redis client for FemScale (FINAL FIXED VERSION)."""

import json
from typing import Optional, Dict, Any
from collections import deque

import redis  # 🔥 FORCE real Redis


# -------------------------------
# 🔹 OPTIONAL MOCK (ONLY IF NEEDED)
# -------------------------------
class InMemoryRedis:
    def __init__(self):
        self.store: Dict[str, str] = {}
        self.queue: deque = deque()

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.store[key] = value

    def get(self, key: str) -> Optional[str]:
        return self.store.get(key)

    def rpush(self, key: str, value: str) -> None:
        if key == "jobs_queue":
            self.queue.append(value)

    def blpop(self, key: str, timeout: int = 1):
        if key == "jobs_queue" and self.queue:
            return (key, self.queue.popleft())
        return None

    def llen(self, key: str) -> int:
        if key == "jobs_queue":
            return len(self.queue)
        return 0

    def ping(self):
        return "PONG"


# -------------------------------
# 🔹 REDIS CLIENT
# -------------------------------
class RedisClient:
    def __init__(self, host="localhost", port=6379, db=0, use_mock=False):

        if use_mock:
            print("⚠️ Using MOCK Redis (dev only)")
            self.backend = InMemoryRedis()
            self.use_mock = True
            return

        # 🔥 FORCE REAL REDIS (NO SILENT FALLBACK)
        try:
            self.backend = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
            )
            self.backend.ping()
            print(f"🔥 Connected to REAL Redis at {host}:{port}")
            self.use_mock = False

        except Exception as e:
            raise RuntimeError(
                f"❌ Redis connection failed. Start Redis first.\nError: {e}"
            )

    # -------------------------------
    # JOB STORAGE
    # -------------------------------
    def store_job(self, job_id: str, job_data: Dict[str, Any], ttl_seconds: int = 3600):
        key = f"job:{job_id}"
        self.backend.setex(key, ttl_seconds, json.dumps(job_data))

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        key = f"job:{job_id}"
        data = self.backend.get(key)
        if data is None:
            return None
        return json.loads(data)

    # -------------------------------
    # QUEUE
    # -------------------------------
    def enqueue_job(self, job_id: str):
        self.backend.rpush("jobs_queue", job_id)

    def dequeue_job(self) -> Optional[str]:
        result = self.backend.blpop("jobs_queue", timeout=1)
        if result is None:
            return None
        return result[1]

    def get_queue_depth(self) -> int:
        return self.backend.llen("jobs_queue")

    # -------------------------------
    # 🔥 FINAL STATUS UPDATE (FIXED)
    # -------------------------------
    def update_job_status(self, job_id: str, status: str, **kwargs):
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")

        job["status"] = status

        # 🔥 FORCE update EVERYTHING
        for key, value in kwargs.items():
            job[key] = value

        # 🔥 DEBUG
        print("FINAL JOB STORED:", job)

        self.store_job(job_id, job)

    # -------------------------------
    def ping(self):
        try:
            self.backend.ping()
            return True
        except Exception:
            return False


# -------------------------------
# 🔹 SINGLETON (IMPORTANT)
# -------------------------------
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient(use_mock=False)  # 🔥 FORCE REAL REDIS
    return _redis_client


def init_redis(host="localhost", port=6379, db=0, use_mock=False):
    global _redis_client
    _redis_client = RedisClient(host, port, db, use_mock=False)  # 🔥 FORCE REAL
    return _redis_client