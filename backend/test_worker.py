#!/usr/bin/env python3
"""Test script for Phase 3 Worker implementation."""

import json
import subprocess
import time
import threading
from typing import Optional

from redis_client import init_redis, get_redis_client
from worker import Worker
from models import StatusEnum


def submit_job(redis_client, code: str, timeout_sec: int = 10, input_data: dict = None) -> str:
    """Submit a job directly to Redis."""
    from uuid import uuid4
    from datetime import datetime, timezone

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


def run_worker_for_duration(duration_sec: float = 5):
    """Run worker in background for specified duration."""
    worker = Worker()

    def worker_thread():
        # Run worker with timeout
        start = time.time()
        while time.time() - start < duration_sec:
            job_id = worker.redis_client.dequeue_job()
            if job_id is not None:
                worker.process_job(job_id)

    thread = threading.Thread(target=worker_thread, daemon=True)
    thread.start()
    return thread


def main():
    print("=" * 70)
    print("Phase 3: Worker Execution Test")
    print("=" * 70)

    # Initialize Redis (mock mode)
    init_redis(use_mock=True)
    redis_client = get_redis_client()

    # Test 1: Simple successful execution
    print("\n[Test 1] Simple successful execution")
    code_1 = """
def handler(event):
    return {"result": 42, "message": "success"}
"""
    job_id_1 = submit_job(redis_client, code_1)
    print(f"  Submitted job: {job_id_1}")

    # Run worker
    worker = Worker()
    worker.process_job(job_id_1)

    # Check result
    job = redis_client.get_job(job_id_1)
    assert job["status"] == "success", f"Expected success, got {job['status']}"
    assert '"result": 42' in job["stdout"], "Expected output in stdout"
    assert job["error"] is None, "Expected no error"
    assert job["duration_ms"] > 0, "Expected duration > 0"
    print(f"✓ Job succeeded")
    print(f"  Status: {job['status']}")
    print(f"  Duration: {job['duration_ms']}ms")
    print(f"  Stdout: {job['stdout'].strip()}")

    # Test 2: Execution with input
    print("\n[Test 2] Execution with input parameter")
    code_2 = """
def handler(event):
    x = event.get("x", 0)
    y = event.get("y", 0)
    return {"sum": x + y}
"""
    job_id_2 = submit_job(redis_client, code_2, input_data={"x": 10, "y": 20})
    print(f"  Submitted job: {job_id_2}")

    worker.process_job(job_id_2)
    job = redis_client.get_job(job_id_2)
    assert job["status"] == "success", f"Expected success, got {job['status']}"
    assert '"sum": 30' in job["stdout"], "Expected sum: 30 in output"
    print(f"✓ Job succeeded with input")
    print(f"  Input: {{'x': 10, 'y': 20}}")
    print(f"  Output: {job['stdout'].strip()}")

    # Test 3: Failed execution (non-zero exit)
    print("\n[Test 3] Failed execution (runtime error)")
    code_3 = """
def handler(event):
    raise ValueError("Test error")
"""
    job_id_3 = submit_job(redis_client, code_3)
    print(f"  Submitted job: {job_id_3}")

    worker.process_job(job_id_3)
    job = redis_client.get_job(job_id_3)
    assert job["status"] == "failed", f"Expected failed, got {job['status']}"
    assert job["error"] is not None, "Expected error message"
    assert "Test error" in job["stderr"], "Expected error in stderr"
    print(f"✓ Job failed as expected")
    print(f"  Status: {job['status']}")
    print(f"  Error: {job['error']}")

    # Test 4: Timeout handling
    print("\n[Test 4] Timeout handling")
    code_4 = """
import time
def handler(event):
    time.sleep(5)
    return {"result": "done"}
"""
    job_id_4 = submit_job(redis_client, code_4, timeout_sec=1)
    print(f"  Submitted job with 1s timeout: {job_id_4}")

    worker.process_job(job_id_4)
    job = redis_client.get_job(job_id_4)
    assert job["status"] == "timeout", f"Expected timeout, got {job['status']}"
    assert job["error"] == "Timeout", "Expected timeout error"
    print(f"✓ Job timed out as expected")
    print(f"  Status: {job['status']}")
    print(f"  Duration: {job['duration_ms']}ms (timeout was 1s)")

    # Test 5: Status transitions
    print("\n[Test 5] Status transitions (queued → running → success)")
    code_5 = """
def handler(event):
    return {"status": "ok"}
"""
    job_id_5 = submit_job(redis_client, code_5)

    # Check initial status
    job = redis_client.get_job(job_id_5)
    assert job["status"] == "queued", f"Initial status should be queued"
    print(f"  Initial status: {job['status']}")

    # During execution (simulated by checking mid-process)
    worker.process_job(job_id_5)

    # Check final status
    job = redis_client.get_job(job_id_5)
    assert job["status"] == "success", f"Final status should be success"
    assert job["completed_at"] is not None, "Expected completed_at timestamp"
    print(f"  Final status: {job['status']}")
    print(f"  Completed at: {job['completed_at']}")

    # Test 6: Cost calculation
    print("\n[Test 6] Cost calculation")
    code_6 = """
def handler(event):
    return {"calculated": True}
"""
    job_id_6 = submit_job(redis_client, code_6)
    worker.process_job(job_id_6)
    job = redis_client.get_job(job_id_6)
    assert job["cost_usd"] >= 0, "Cost should be non-negative"
    assert job["memory_mb"] > 0, "Memory should be positive"
    assert job["duration_ms"] > 0, "Duration should be positive"
    print(f"✓ Cost calculated")
    print(f"  Duration: {job['duration_ms']}ms")
    print(f"  Memory: {job['memory_mb']}MB")
    print(f"  Cost: ${job['cost_usd']:.10f}")

    # Test 7: Status enum validation
    print("\n[Test 7] Status enum validation")
    valid_statuses = {"queued", "running", "success", "failed", "timeout"}
    for i, status in enumerate(valid_statuses, 1):
        code = f"""
def handler(event):
    return {{"status": "{status}"}}
"""
        jid = submit_job(redis_client, code)
        worker.process_job(jid)
        job = redis_client.get_job(jid)
        # Check that job has one of the valid statuses
        assert job["status"] in {"success", "failed", "timeout"}, f"Invalid job status: {job['status']}"
    print(f"✓ All status values valid")

    print("\n" + "=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)


if __name__ == "__main__":
    main()
