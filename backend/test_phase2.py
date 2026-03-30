#!/usr/bin/env python3
"""Test script for Phase 2 Redis queue integration."""

import json
import subprocess
import time

BASE_URL = "http://localhost:8000"


def submit_job(code: str, timeout_sec: int = 10) -> str:
    """Submit a job and return job_id."""
    cmd = [
        "curl", "-s", "-X", "POST", f"{BASE_URL}/v1/jobs",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"code": code, "timeout_sec": timeout_sec})
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    response = json.loads(result.stdout)
    return response["job_id"]


def get_job(job_id: str) -> dict:
    """Get job status and details."""
    cmd = ["curl", "-s", f"{BASE_URL}/v1/jobs/{job_id}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)


def main():
    print("=" * 60)
    print("Phase 2: Redis Queue Integration Test")
    print("=" * 60)

    # Test 1: Submit single job
    print("\n[Test 1] Submit single job")
    job_id_1 = submit_job("print('test 1')")
    print(f"✓ Job submitted: {job_id_1}")

    # Test 2: Retrieve job
    print("\n[Test 2] Retrieve job")
    job = get_job(job_id_1)
    print(f"✓ Job retrieved")
    print(f"  - Status: {job['status']}")
    print(f"  - Created: {job['created_at']}")

    # Test 3: Submit multiple jobs (queue depth)
    print("\n[Test 3] Submit 4 more jobs (queue depth = 5)")
    job_ids = [job_id_1]
    for i in range(2, 5):
        jid = submit_job(f"print('test {i}')")
        job_ids.append(jid)
        print(f"✓ Job {i} submitted: {jid}")

    # Test 4: Verify all jobs are queued
    print("\n[Test 4] Verify all jobs queued")
    for i, jid in enumerate(job_ids, 1):
        job = get_job(jid)
        assert job["status"] == "queued", f"Job {i} status is {job['status']}, expected queued"
        print(f"✓ Job {i} status: {job['status']}")

    # Test 5: Verify Redis storage (ISO8601 timestamps)
    print("\n[Test 5] Verify data storage")
    job = get_job(job_ids[0])
    assert job["created_at"], "Missing created_at"
    assert "T" in job["created_at"], "Timestamp not ISO8601 format"
    assert job["created_at"].endswith("Z"), "Timestamp not UTC"
    print(f"✓ Timestamp format: {job['created_at']} ✓")
    print(f"✓ stdout: '{job['stdout']}'")
    print(f"✓ stderr: '{job['stderr']}'")
    print(f"✓ Duration (ms): {job['duration_ms']}")
    print(f"✓ Memory (MB): {job['memory_mb']}")
    print(f"✓ Cost (USD): {job['cost_usd']}")

    # Test 6: Error handling (404)
    print("\n[Test 6] Error handling (404 - job not found)")
    cmd = ["curl", "-s", "-w", "\n%{http_code}", f"{BASE_URL}/v1/jobs/invalid-id"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")
    status_code = int(lines[-1])
    assert status_code == 404, f"Expected 404, got {status_code}"
    print(f"✓ 404 error returned correctly")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
