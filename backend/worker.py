"""FemScale Worker - Executes queued jobs from Redis."""

import json
import subprocess
import time
from datetime import datetime, timezone
from typing import Tuple

from redis_client import get_redis_client
from metrics import get_metrics
from config import AWS_LAMBDA_RATE_PER_GB_SECOND


class Worker:
    """Worker that continuously polls Redis queue and executes jobs."""

    def __init__(self):
        """Initialize worker with Redis client."""
        self.redis_client = get_redis_client()

    def run_forever(self) -> None:
        """
        Continuously poll Redis queue and process jobs.
        
        Blocks on queue until job arrives (BLPOP with 1s timeout).
        """
        print("Worker started, polling for jobs...")
        while True:
            job_id = self.redis_client.dequeue_job()
            if job_id is None:
                continue

            try:
                self.process_job(job_id)
            except Exception as e:
                print(f"Error processing job {job_id}: {e}")

    def process_job(self, job_id: str) -> None:
        """
        Process a single job: execute code and update Redis with results.
        
        Args:
            job_id: UUID4 job identifier
        
        Flow:
            1. Get job from Redis
            2. Update status -> running
            3. Execute user code
            4. Capture stdout, stderr, duration, memory
            5. Determine final status (success/failed/timeout)
            6. Update job in Redis with results
        """
        # Get job object
        job = self.redis_client.get_job(job_id)
        if job is None:
            print(f"Job {job_id} not found in Redis")
            return

        # Update status to running
        self.redis_client.update_job_status(job_id, "running")
        start_time = time.time()

        try:
            # Execute the user code
            stdout, stderr, exit_code = self.execute_code(
                code=job["code"],
                input_data=job.get("input", {}),
                timeout_sec=job["timeout_sec"],
            )

            # Calculate execution time
            duration_ms = int((time.time() - start_time) * 1000)

            # Determine final status based on exit code
            if exit_code == 0:
                status = "success"
                error = None
            else:
                status = "failed"
                error = f"Non-zero exit code: {exit_code}"

            # Get completion timestamp
            completed_at = self._get_iso8601_utc()

            # For now, memory is estimated as minimal (0.1 MB)
            # In production, this would be measured from container stats
            memory_mb = 0.1

            # Calculate cost: (Memory_GB × Duration_seconds) × $0.0000000167
            memory_gb = memory_mb / 1024
            duration_seconds = duration_ms / 1000
            cost_usd = (memory_gb * duration_seconds) * AWS_LAMBDA_RATE_PER_GB_SECOND

            # Update job with results
            self.redis_client.update_job_status(
                job_id,
                status,
                stdout=stdout,
                stderr=stderr,
                error=error,
                duration_ms=duration_ms,
                memory_mb=memory_mb,
                cost_usd=cost_usd,
                completed_at=completed_at,
            )

            # Record metrics
            metrics = get_metrics()
            metrics.add_event("job_completed", {
                "job_id": job_id,
                "status": status,
                "duration_ms": duration_ms,
                "cost_usd": cost_usd,
            })
            metrics.increment_job_completed(cost_usd)

            print(
                f"✓ Job {job_id} completed: {status} (duration: {duration_ms}ms, cost: ${cost_usd:.10f})"
            )

        except subprocess.TimeoutExpired:
            # Job exceeded timeout
            duration_ms = int((time.time() - start_time) * 1000)
            completed_at = self._get_iso8601_utc()
            memory_mb = 0.1

            self.redis_client.update_job_status(
                job_id,
                "timeout",
                stderr="Execution timeout exceeded",
                error="Timeout",
                duration_ms=duration_ms,
                memory_mb=memory_mb,
                cost_usd=0.0,
                completed_at=completed_at,
            )

            # Record metrics
            metrics = get_metrics()
            metrics.add_event("job_completed", {
                "job_id": job_id,
                "status": "timeout",
                "duration_ms": duration_ms,
                "cost_usd": 0.0,
            })
            metrics.increment_job_completed(0.0)

            print(f"✗ Job {job_id} timed out after {duration_ms}ms")

        except Exception as e:
            # Unexpected error during execution
            duration_ms = int((time.time() - start_time) * 1000)
            completed_at = self._get_iso8601_utc()

            self.redis_client.update_job_status(
                job_id,
                "failed",
                stderr=str(e),
                error=str(e),
                duration_ms=duration_ms,
                memory_mb=0.1,
                cost_usd=0.0,
                completed_at=completed_at,
            )

            # Record metrics
            metrics = get_metrics()
            metrics.add_event("job_completed", {
                "job_id": job_id,
                "status": "failed",
                "duration_ms": duration_ms,
                "cost_usd": 0.0,
            })
            metrics.increment_job_completed(0.0)

            print(f"✗ Job {job_id} failed: {e}")

    def execute_code(
        self, code: str, input_data: dict, timeout_sec: int
    ) -> Tuple[str, str, int]:
        """
        Execute Python user code safely via subprocess.
        
        The user code must define a handler(event) function.
        This method wraps the code and calls handler() with input_data.
        
        Args:
            code: Python function code containing def handler(event)
            input_data: Input dict to pass to handler() as event
            timeout_sec: Maximum execution time in seconds
        
        Returns:
            Tuple of (stdout, stderr, exit_code)
        
        Raises:
            subprocess.TimeoutExpired: If execution exceeds timeout_sec
            Exception: Any other runtime error
        """
        # Create wrapper that:
        # 1. Defines the user's handler function
        # 2. Calls it with input_data
        # 3. Prints result as JSON, or error to stderr
        wrapper_code = f"""
import json
import sys

# User-defined handler function
{code}

# Call handler with input
try:
    result = handler({json.dumps(input_data)})
    # Output result as JSON to stdout
    print(json.dumps(result))
    sys.exit(0)
except Exception as e:
    # Output error to stderr
    print(f"Error in handler: {{e}}", file=sys.stderr)
    sys.exit(1)
"""

        try:
            result = subprocess.run(
                ["python3", "-c", wrapper_code],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            return result.stdout, result.stderr, result.returncode

        except subprocess.TimeoutExpired:
            # Subprocess exceeded timeout - let caller handle
            raise

    @staticmethod
    def _get_iso8601_utc() -> str:
        """Get current timestamp in ISO8601 UTC format."""
        return (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )


def worker_process_main():
    """Entry point for worker spawned by multiprocessing/scaler.
    
    Ensures each worker process initializes its own Redis connection.
    Used by scaler.py to spawn worker processes.
    """
    from redis_client import init_redis
    
    # Initialize Redis fresh in this worker process
    init_redis(use_mock=False)
    
    worker = Worker()
    worker.run_forever()


def main():
    """Entry point for worker process."""
    import argparse

    parser = argparse.ArgumentParser(description="FemScale Worker")
    parser.add_argument(
        "--redis-host",
        default="localhost",
        help="Redis server host (default: localhost)",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        help="Redis server port (default: 6379)",
    )

    args = parser.parse_args()

    # Initialize Redis (real or mock)
    from redis_client import init_redis

    init_redis(host=args.redis_host, port=args.redis_port)

    worker = Worker()
    worker.run_forever()


if __name__ == "__main__":
    main()
