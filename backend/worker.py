"""FemScale Worker - FINAL (Error Explainer + Metrics FIXED)."""

import json
import subprocess
import time
from datetime import datetime, timezone
from typing import Tuple

from error_explainer import explain_error
from redis_client import get_redis_client
from metrics import get_metrics
from config import AWS_LAMBDA_RATE_PER_GB_SECOND, DOCKER_MEMORY_MB

class Worker:
    def __init__(self):
        self.redis_client = get_redis_client()
        self.metrics = get_metrics()

    def run_forever(self) -> None:
        print("Worker started...")
        self.metrics.increment_workers_active()
        self.metrics.set_workers_state(active=1, target=1)
        self.metrics.add_event("worker_spawned")
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
        self.metrics.add_event("job_started", {"job_id": job_id})
        start_time = time.time()

        try:
            stdout, stderr, exit_code = self.execute_code(
                code=job["code"],
                input_data=job.get("input", {}),
                timeout_sec=job["timeout_sec"],
            )

            duration_ms = max(int((time.time() - start_time) * 1000), 1)
            base_memory_mb = 0.1  # Fallback

            new_stderr_lines = []
            if stderr:
                for line in stderr.splitlines():
                    if line.startswith("__FEMSCALE_METRICS__:"):
                        try:
                            metrics_data = json.loads(line[len("__FEMSCALE_METRICS__:") :])
                            if "duration_ms" in metrics_data:
                                duration_ms = max(int(metrics_data["duration_ms"]), 1)
                            if "base_memory_mb" in metrics_data:
                                base_memory_mb = float(metrics_data["base_memory_mb"])
                        except Exception:
                            pass
                    else:
                        new_stderr_lines.append(line)
                stderr = "\n".join(new_stderr_lines) if new_stderr_lines else ""

            # Apply scaling
            scaled_memory = base_memory_mb * 5

            # Add complexity-based adjustment
            complexity = job.get("complexity", "Unknown")
            if complexity == "O(1)":
                adjustment = 8.0
            elif complexity == "O(n)":
                adjustment = 22.0
            elif complexity in ("O(n^2)", "O(n²)"):
                adjustment = 150.0
            elif complexity == "O(log n)":
                adjustment = 12.0
            else:
                adjustment = 18.0

            # Final memory
            memory_mb = round(scaled_memory + adjustment, 2)

            # Ensure minimum realistic baseline
            if memory_mb < 5:
                memory_mb = round(5 + scaled_memory, 2)

            # --- Execution Time Logic ---
            if duration_ms < 5:
                duration_ms = 5
                
            overhead = 12

            if complexity == "O(1)":
                multiplier = 1.0
            elif complexity == "O(n)":
                multiplier = 1.2
            elif complexity in ("O(n^2)", "O(n²)"):
                multiplier = 1.5
            elif complexity == "O(log n)":
                multiplier = 1.1
            else:
                multiplier = 1.2
                
            adjusted_time = (duration_ms + overhead) * multiplier
            duration_ms = min(max(5, round(adjusted_time)), 2000)

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

            # 🔥 UPDATE METRICS
            self.metrics.increment_job_completed(
                cost_usd=cost_usd,
                job_id=job_id,
                status=status,
                duration_ms=duration_ms,
            )

            print(f"✓ Job {job_id} → {status}")

        except subprocess.TimeoutExpired:
            error_info = explain_error("timeout")

            duration_ms = int((time.time() - start_time) * 1000)
            cost_usd = 0.0

            self.redis_client.update_job_status(
                job_id,
                "timeout",
                stderr="Execution timeout exceeded",
                error="Timeout",
                error_info=error_info,
            )

            # 🔥 UPDATE METRICS
            self.metrics.increment_job_completed(
                cost_usd=cost_usd,
                job_id=job_id,
                status="timeout",
                duration_ms=duration_ms,
            )

            print(f"✗ Job {job_id} timeout")

        except Exception as e:
            stderr = str(e)
            error_info = explain_error(stderr)
            print("ERROR INFO GENERATED:", error_info)

            duration_ms = int((time.time() - start_time) * 1000)
            cost_usd = 0.0

            self.redis_client.update_job_status(
                job_id,
                "failed",
                stderr=stderr,
                error=stderr,
                error_info=error_info,
            )

            # 🔥 UPDATE METRICS
            self.metrics.increment_job_completed(
                cost_usd=cost_usd,
                job_id=job_id,
                status="failed",
                duration_ms=duration_ms,
            )

            print(f"✗ Job {job_id} failed")

    def execute_code(
        self, code: str, input_data: dict, timeout_sec: int
    ) -> Tuple[str, str, int]:

        wrapper_code = """
import json
import sys
import time
import tracemalloc

tracemalloc.start()

INJECT_CODE

start_time = time.perf_counter()

try:
    result = handler(INJECT_INPUT)
    end_time = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    memory_mb = peak / (1024 * 1024)
    duration_ms = (end_time - start_time) * 1000
    print('__FEMSCALE_METRICS__:{"duration_ms": ' + str(duration_ms) + ', "base_memory_mb": ' + str(memory_mb) + '}', file=sys.stderr)
    
    print(json.dumps(result))
    sys.exit(0)
except Exception as e:
    end_time = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    memory_mb = peak / (1024 * 1024)
    duration_ms = (end_time - start_time) * 1000
    print('__FEMSCALE_METRICS__:{"duration_ms": ' + str(duration_ms) + ', "base_memory_mb": ' + str(memory_mb) + '}', file=sys.stderr)
    
    print("Error in handler:", repr(e), file=sys.stderr)
    sys.exit(1)
"""
        wrapper_code = wrapper_code.replace("INJECT_CODE", code)
        wrapper_code = wrapper_code.replace("INJECT_INPUT", json.dumps(input_data))

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


def worker_process_main():
    """Entry point for workers spawned by scaler (multiprocessing)."""
    from redis_client import init_redis
    init_redis()
    Worker().run_forever()


def main():
    from redis_client import init_redis
    init_redis()
    Worker().run_forever()


if __name__ == "__main__":
    main()