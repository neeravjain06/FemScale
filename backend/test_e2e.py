#!/usr/bin/env python3
"""Integration test: Job submission → worker execution → results retrieval."""

import json
import time
import threading
from uuid import uuid4
from datetime import datetime, timezone

# Direct integration test (bypasses HTTP API to share memory)
from redis_client import init_redis, get_redis_client
from worker import Worker
from models import StatusEnum


def submit_job_direct(redis_client, code: str, timeout_sec: int = 10, input_data: dict = None) -> str:
    """Submit a job directly to Redis queue."""
    job_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    job = {
        "job_id": job_id,
        "code": code,
        "timeout_sec": timeout_sec,
        "input": input_data or {},
        "status": StatusEnum.QUEUED.value,
        "stdout": "",
        "stderr": "",
        "error": None,
        "duration_ms": 0,
        "memory_mb": 0.0,
        "cost_usd": 0.0,
        "created_at": created_at,
        "completed_at": None,
    }

    redis_client.store_job(job_id, job)
    redis_client.enqueue_job(job_id)
    return job_id


def run_worker_thread(redis_client, duration: int = 20, max_jobs: int = None):
    """Run worker in background thread."""
    worker = Worker()
    worker.redis_client = redis_client

    def worker_loop():
        start = time.time()
        jobs_processed = 0
        while time.time() - start < duration:
            if max_jobs and jobs_processed >= max_jobs:
                break
            job_id = worker.redis_client.dequeue_job()
            if job_id is not None:
                worker.process_job(job_id)
                jobs_processed += 1
            else:
                time.sleep(0.05)

    thread = threading.Thread(target=worker_loop, daemon=True)
    thread.start()
    return thread


def test_submission_to_completion():
    print("=" * 70)
    print("Integration Test: Job Submission → Worker Processing → Results")
    print("=" * 70)

    # Initialize shared in-memory Redis
    init_redis(use_mock=True)
    redis_client = get_redis_client()

    # Start worker in background thread
    print("\n[Setup] Starting worker thread...")
    worker_thread = run_worker_thread(redis_client, duration=20, max_jobs=10)
    time.sleep(0.5)

    # Test 1: Simple job execution
    print("\n[Test 1] Simple job execution")
    code_1 = """
def handler(event):
    return {"status": "ok", "value": 42}
"""
    job_id_1 = submit_job_direct(redis_client, code_1)
    print(f"  Submitted job: {job_id_1}")

    # Wait for completion
    start = time.time()
    while time.time() - start < 5:
        job = redis_client.get_job(job_id_1)
        if job["status"] in ["success", "failed", "timeout"]:
            break
        time.sleep(0.05)

    job = redis_client.get_job(job_id_1)
    assert job["status"] == "success", f"Expected success, got {job['status']}"
    assert "42" in job["stdout"], "Expected value in output"
    print(f"✓ Job completed")
    print(f"  Status: {job['status']}")
    print(f"  Output: {job['stdout'].strip()}")
    print(f"  Duration: {job['duration_ms']}ms")

    # Test 2: Job with input
    print("\n[Test 2] Job with input processing")
    code_2 = """
def handler(event):
    items = event.get("items", [])
    return {"count": len(items), "sum": sum(items)}
"""
    job_id_2 = submit_job_direct(redis_client, code_2, input_data={"items": [1, 2, 3, 4, 5]})
    print(f"  Submitted job: {job_id_2}")

    start = time.time()
    while time.time() - start < 5:
        job = redis_client.get_job(job_id_2)
        if job["status"] in ["success", "failed", "timeout"]:
            break
        time.sleep(0.05)

    job = redis_client.get_job(job_id_2)
    assert job["status"] == "success"
    assert '"sum": 15' in job["stdout"], "Expected sum: 15"
    print(f"✓ Job completed")
    print(f"  Input: [1, 2, 3, 4, 5]")
    print(f"  Output: {job['stdout'].strip()}")

    # Test 3: Failed job (error handling)
    print("\n[Test 3] Failed job (error handling)")
    code_3 = """
def handler(event):
    raise ValueError("Intentional error")
"""
    job_id_3 = submit_job_direct(redis_client, code_3)
    print(f"  Submitted job: {job_id_3}")

    start = time.time()
    while time.time() - start < 5:
        job = redis_client.get_job(job_id_3)
        if job["status"] in ["success", "failed", "timeout"]:
            break
        time.sleep(0.05)

    job = redis_client.get_job(job_id_3)
    assert job["status"] == "failed", f"Expected failed, got {job['status']}"
    assert job["error"] is not None, "Expected error message"
    print(f"✓ Job failed as expected")
    print(f"  Status: {job['status']}")
    print(f"  Error: {job['error']}")

    # Test 4: Multiple concurrent jobs
    print("\n[Test 4] Multiple concurrent jobs")
    job_ids = []
    for i in range(3):
        code = f"""
def handler(event):
    return {{"id": {i}, "result": {i * 10}}}
"""
        jid = submit_job_direct(redis_client, code)
        job_ids.append(jid)
        print(f"  Submitted job {i + 1}: {jid}")

    # Wait for all to complete
    start = time.time()
    completed = 0
    while time.time() - start < 10 and completed < 3:
        completed = 0
        for jid in job_ids:
            job = redis_client.get_job(jid)
            if job["status"] in ["success", "failed", "timeout"]:
                completed += 1
        if completed < 3:
            time.sleep(0.1)

    for i, jid in enumerate(job_ids):
        job = redis_client.get_job(jid)
        assert job["status"] == "success"
        print(f"  ✓ Job {i + 1} completed: {job['status']}")

    # Test 5: Verify cost calculation
    print("\n[Test 5] Cost calculation verification")
    job = redis_client.get_job(job_id_1)
    assert job["cost_usd"] >= 0, "Cost should be non-negative"
    assert job["memory_mb"] > 0, "Memory should be positive"
    assert job["duration_ms"] > 0, "Duration should be positive"
    print(f"✓ Cost calculated correctly")
    print(f"  Duration: {job['duration_ms']}ms")
    print(f"  Memory: {job['memory_mb']}MB")
    print(f"  Cost: ${job['cost_usd']:.10f}")

    print("\n" + "=" * 70)
    print("Integration Test Passed! ✓")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_submission_to_completion()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
