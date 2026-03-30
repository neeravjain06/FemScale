"""FemScale Worker - FINAL (Error Explainer FIXED)."""

import json
import subprocess
import time
from datetime import datetime, timezone
from typing import Tuple

from error_explainer import explain_error
from redis_client import get_redis_client
from metrics import get_metrics
from config import AWS_LAMBDA_RATE_PER_GB_SECOND


class Worker:
    def __init__(self):
        self.redis_client = get_redis_client()

    def run_forever(self) -> None:
        print("Worker started...")
        while True:
            job_id = self.redis_client.dequeue_job()
            if job_id is None:
                continue

            try:
                self.process_job(job_id)
            except Exception as e:
                print(f"Error processing job {job_id}: {e}")

    def process_job(self, job_id: str) -> None:
        job = self.redis_client.get_job(job_id)
        if job is None:
            return

        self.redis_client.update_job_status(job_id, "running")
        start_time = time.time()

        try:
            stdout, stderr, exit_code = self.execute_code(
                code=job["code"],
                input_data=job.get("input", {}),
                timeout_sec=job["timeout_sec"],
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # 🔥 ERROR EXPLAINER
            error_info = explain_error(stderr)
            print("ERROR INFO GENERATED:", error_info)
            if exit_code == 0:
                status = "success"
                error = None
            else:
                status = "failed"
                error = stderr

            completed_at = self._get_iso8601_utc()

            # Cost calculation
            memory_mb = 0.1
            memory_gb = memory_mb / 1024
            duration_seconds = duration_ms / 1000
            cost_usd = (memory_gb * duration_seconds) * AWS_LAMBDA_RATE_PER_GB_SECOND

            # 🔥 SAVE EVERYTHING (IMPORTANT)
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
                error_info=error_info,  # 🔥 THIS MUST WORK
            )

            print(f"✓ Job {job_id} → {status}")

        except subprocess.TimeoutExpired:
            error_info = explain_error("timeout")

            self.redis_client.update_job_status(
                job_id,
                "timeout",
                stderr="Execution timeout exceeded",
                error="Timeout",
                error_info=error_info,
            )

            print(f"✗ Job {job_id} timeout")

        except Exception as e:
            stderr = str(e)
            error_info = explain_error(stderr)
            print("ERROR INFO GENERATED:", error_info)
            self.redis_client.update_job_status(
                job_id,
                "failed",
                stderr=stderr,
                error=stderr,
                error_info=error_info,
            )

            print(f"✗ Job {job_id} failed")

    def execute_code(
        self, code: str, input_data: dict, timeout_sec: int
    ) -> Tuple[str, str, int]:

        wrapper_code = f"""
import json
import sys

{code}

try:
    result = handler({json.dumps(input_data)})
    print(json.dumps(result))
    sys.exit(0)
except Exception as e:
    print(f"Error in handler: {{e}}", file=sys.stderr)
    sys.exit(1)
"""

        result = subprocess.run(
            ["python3", "-c", wrapper_code],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )

        return result.stdout, result.stderr, result.returncode

    @staticmethod
    def _get_iso8601_utc() -> str:
        return (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )


def main():
    from redis_client import init_redis
    init_redis()
    Worker().run_forever()


if __name__ == "__main__":
    main()