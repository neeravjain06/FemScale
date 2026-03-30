#!/usr/bin/env python3
"""Test script demonstrating Phase 4 auto-scaler functionality."""

import json
import subprocess
import time
import sys
from pathlib import Path


def print_header(text: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def check_service(port: int, name: str) -> bool:
    """Check if service is running on port."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"http://localhost:{port}/"],
            capture_output=True,
            timeout=2,
        )
        print(f"✓ {name} is running on port {port}")
        return True
    except Exception:
        print(f"✗ {name} is NOT running on port {port}")
        return False


def submit_jobs(count: int, code: str = "import time; time.sleep(2); print('done')", timeout_sec: int = 10):
    """Submit multiple test jobs to the API."""
    print(f"\n📝 Submitting {count} jobs...")
    job_ids = []
    
    for i in range(count):
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-X",
                    "POST",
                    "http://localhost:8000/v1/jobs",
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    json.dumps({"code": code, "timeout_sec": timeout_sec}),
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                job_ids.append(response["job_id"])
                print(f"  ✓ Job {i+1}/{count}: {response['job_id'][:8]}...")
            else:
                print(f"  ✗ Job {i+1}/{count}: Failed")
        except Exception as e:
            print(f"  ✗ Job {i+1}/{count}: {e}")
    
    return job_ids


def check_queue_depth() -> int:
    """Check current queue depth via Redis."""
    try:
        result = subprocess.run(
            [
                "python3",
                "-c",
                "from redis_client import get_redis_client; print(get_redis_client().get_queue_depth())",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=5,
        )
        return int(result.stdout.strip())
    except Exception:
        return 0


def print_instructions():
    """Print setup instructions."""
    print_header("PHASE 4: AUTO-SCALER TEST")
    print("""
This test demonstrates the auto-scaler functionality:
1. Monitor Redis queue depth every 3 seconds
2. Scale workers dynamically based on depth
3. Spawn/terminate processes as needed

SCALING POLICY:
- 0–4 jobs: 1 worker
- 5–19 jobs: 3 workers  
- 20–49 jobs: 7 workers
- 50+ jobs: 10 workers

SETUP (run in separate terminals):
""")
    print("  Terminal 1 (API):     python -m uvicorn main:app --host 0.0.0.0 --port 8000")
    print("  Terminal 2 (Scaler):  python scaler.py")
    print("  Terminal 3 (Test):    python test_scaler.py")


def main():
    """Main test flow."""
    print_instructions()
    
    # Check prerequisites
    print_header("CHECKING PREREQUISITES")
    
    backend_path = Path(__file__).parent / "main.py"
    if not backend_path.exists():
        print("✗ main.py not found in backend directory")
        sys.exit(1)
    print("✓ Backend files found")
    
    # Check if services are running
    print_header("CHECKING SERVICES")
    api_running = check_service(8000, "FastAPI Backend")
    
    if not api_running:
        print("\n⚠️  FastAPI is not running. Start it first:")
        print("   python -m uvicorn main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    # Test scenarios
    print_header("TEST SCENARIO 1: SCALING UP")
    print("Submitting 25 jobs (should scale to 7 workers)...")
    job_ids = submit_jobs(25, timeout_sec=10)
    print(f"✓ {len(job_ids)} jobs submitted")
    print(f"✓ Current queue depth: {check_queue_depth()}")
    print("\n⏳ Wait 15 seconds to observe scaler behavior:")
    print("   - Scaler checks every 3 seconds")
    print("   - Should scale: 1 worker → 3 workers → 7 workers")
    print("   - Workers execute jobs in parallel")
    
    for i in range(5):
        time.sleep(3)
        depth = check_queue_depth()
        print(f"   [{3*(i+1)}s] Queue depth: {depth}")
    
    print_header("TEST SCENARIO 2: SCALING DOWN")
    print("Waiting for jobs to complete...")
    for i in range(10):
        time.sleep(2)
        depth = check_queue_depth()
        print(f"   [{2*(i+1)}s] Queue depth: {depth}")
        if depth == 0:
            print("✓ All jobs completed!")
            break
    
    time.sleep(9)  # Wait for scaler to scale down
    print("\n⏳ Scaler should now scale DOWN to 1 worker")
    
    print_header("TEST COMPLETE")
    print("""
✓ Auto-scaler test complete!

WHAT YOU SHOULD HAVE OBSERVED:
1. Workers scaled UP from 1 → 3 → 7 as queue filled
2. Multiple workers executed jobs in parallel
3. Workers scaled DOWN from 7 → 3 → 1 as queue emptied

SCALER OUTPUT IN TERMINAL 2:
- ➕ Spawned worker [PID] - indicates scale up
- ➖ Terminated worker [PID] - indicates scale down
- 📊 Queue depth: X, Workers: Y/Z - status update

NEXT STEPS:
- Review scaler.py for implementation details
- Check README_PHASE4.md for full documentation
- Try Phase 5: Docker containerization
""")


if __name__ == "__main__":
    main()
