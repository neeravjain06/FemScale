#!/usr/bin/env python3
"""Test script demonstrating Phase 5 metrics endpoint."""

import json
import subprocess
import time
import sys


def test_metrics_endpoint():
    """Test the GET /v1/metrics endpoint."""
    print("=" * 60)
    print("  PHASE 5: METRICS ENDPOINT TEST")
    print("=" * 60)
    print()
    
    # Check if backend is running
    print("Checking if API is running on localhost:8000...")
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:8000/health"],
            capture_output=True,
            timeout=2,
        )
        if result.returncode != 0:
            print("✗ API is not running")
            print("\nStart the API first:")
            print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000")
            sys.exit(1)
        print("✓ API is running\n")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sys.exit(1)
    
    # Test 1: Get metrics before any jobs
    print("Test 1: Get metrics (no jobs yet)")
    print("-" * 60)
    result = subprocess.run(
        ["curl", "-s", "http://localhost:8000/v1/metrics"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        metrics = json.loads(result.stdout)
        print(json.dumps(metrics, indent=2))
        assert metrics["queue_depth"] == 0, "Queue should be empty"
        assert metrics["jobs_completed_session"] == 0, "No jobs completed yet"
        print("✓ Test 1 passed\n")
    else:
        print(f"✗ Failed to get metrics: {result.stderr}")
        sys.exit(1)
    
    # Test 2: Submit a job and check queue depth
    print("Test 2: Submit job and check queue depth")
    print("-" * 60)
    job_result = subprocess.run(
        [
            "curl",
            "-s",
            "-X",
            "POST",
            "http://localhost:8000/v1/jobs",
            "-H",
            "Content-Type: application/json",
            "-d",
            '{"code":"print(\'hello\')","timeout_sec":10}',
        ],
        capture_output=True,
        text=True,
    )
    
    if job_result.returncode == 0:
        job = json.loads(job_result.stdout)
        job_id = job["job_id"]
        print(f"✓ Job submitted: {job_id[:8]}...\n")
        
        # Check metrics
        result = subprocess.run(
            ["curl", "-s", "http://localhost:8000/v1/metrics"],
            capture_output=True,
            text=True,
        )
        metrics = json.loads(result.stdout)
        print(json.dumps(metrics, indent=2))
        assert metrics["queue_depth"] > 0, "Queue should have jobs"
        print("✓ Test 2 passed\n")
    else:
        print(f"✗ Failed to submit job: {job_result.stderr}")
        sys.exit(1)
    
    # Test 3: Check response structure
    print("Test 3: Verify metrics response structure")
    print("-" * 60)
    result = subprocess.run(
        ["curl", "-s", "http://localhost:8000/v1/metrics"],
        capture_output=True,
        text=True,
    )
    metrics = json.loads(result.stdout)
    
    required_fields = [
        "queue_depth",
        "workers_target",
        "workers_active",
        "jobs_running",
        "jobs_completed_session",
        "total_cost_session_usd",
        "events",
    ]
    
    for field in required_fields:
        assert field in metrics, f"Missing field: {field}"
        print(f"✓ {field}: {metrics[field]}")
    
    print("\n✓ Test 3 passed\n")
    
    # Test 4: Event structure
    print("Test 4: Check events structure")
    print("-" * 60)
    
    if len(metrics["events"]) > 0:
        event = metrics["events"][0]
        print(f"Sample event: {json.dumps(event, indent=2)}")
        assert "timestamp" in event, "Missing timestamp"
        assert "type" in event, "Missing type"
        print("✓ Event has correct structure")
    else:
        print("ℹ No events yet (wait for jobs to complete)")
    
    print("\n✓ Test 4 passed\n")
    
    # Print summary
    print("=" * 60)
    print("  METRICS ENDPOINT SUMMARY")
    print("=" * 60)
    print(f"""
Current Metrics:
  Queue depth: {metrics['queue_depth']} job(s)
  Workers: {metrics['workers_active']}/{metrics['workers_target']}
  Jobs running: {metrics['jobs_running']}
  Jobs completed: {metrics['jobs_completed_session']}
  Total cost: ${metrics['total_cost_session_usd']:.10f}
  Recent events: {len(metrics['events'])}

API Endpoint:
  GET /v1/metrics

Use Case:
  Real-time monitoring dashboard
  Auto-scaling observability
  Cost tracking

Example cURL:
  curl http://localhost:8000/v1/metrics | python -m json.tool
""")


if __name__ == "__main__":
    test_metrics_endpoint()
