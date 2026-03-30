"""FemScale Auto-Scaler - Dynamic worker scaling based on queue depth."""

import time
import signal
import sys
from multiprocessing import Process
from typing import Dict, List
from datetime import datetime

from redis_client import get_redis_client
from metrics import get_metrics
from worker import worker_process_main
from config import SCALING_TIERS, SCALER_CHECK_INTERVAL_SEC


class WorkerManager:
    """Manages worker process lifecycle and auto-scaling."""

    def __init__(self):
        """Initialize worker manager."""
        self.redis_client = get_redis_client()
        self.active_workers: Dict[int, Process] = {}  # pid -> Process
        self.target_workers = 0
        self.scale_history: List[str] = []

    def get_target_worker_count(self, queue_depth: int) -> int:
        """
        Determine target worker count based on queue depth.

        Args:
            queue_depth: Current number of jobs in queue

        Returns:
            Target number of workers to have active
        """
        for tier in SCALING_TIERS:
            if tier["queue_depth_min"] <= queue_depth < tier["queue_depth_max"]:
                return tier["target_workers"]
        return 1

    def spawn_worker(self) -> Process:
        """
        Spawn a new worker process.

        Returns:
            Process object for the spawned worker
        """
        process = Process(target=worker_process_main, daemon=False)
        process.start()
        return process

    def terminate_worker(self, pid: int) -> None:
        """
        Terminate a worker process gracefully.

        Args:
            pid: Process ID to terminate
        """
        if pid in self.active_workers:
            process = self.active_workers[pid]
            process.terminate()
            process.join(timeout=5)  # Wait up to 5 seconds
            if process.is_alive():
                process.kill()  # Force kill if still alive
            del self.active_workers[pid]
            
            # Record metrics event
            metrics = get_metrics()
            metrics.add_event("worker_terminated", {"worker_pid": pid})

    def scale_up(self, count: int) -> None:
        """
        Spawn additional workers.

        Args:
            count: Number of workers to spawn
        """
        metrics = get_metrics()
        for _ in range(count):
            process = self.spawn_worker()
            self.active_workers[process.pid] = process
            
            # Record metrics event
            metrics.add_event("worker_spawned", {"worker_pid": process.pid})
            
            print(f"  ➕ Spawned worker {process.pid}")

    def scale_down(self, count: int) -> None:
        """
        Terminate workers.

        Args:
            count: Number of workers to terminate
        """
        pids_to_remove = list(self.active_workers.keys())[:count]
        for pid in pids_to_remove:
            self.terminate_worker(pid)
            print(f"  ➖ Terminated worker {pid}")

    def log_scale_event(self, event: str) -> None:
        """Log scaling event."""
        timestamp = datetime.now().isoformat()
        message = f"[{timestamp}] {event}"
        self.scale_history.append(message)
        print(message)

    def run(self) -> None:
        """
        Main scaler loop: monitor queue and adjust worker count.

        Runs indefinitely, checking queue depth every 3 seconds.
        """
        print("🚀 FemScale Auto-Scaler started")
        print(f"   Check interval: {SCALER_CHECK_INTERVAL_SEC}s")
        print(f"   Scaling tiers: {SCALING_TIERS}\n")

        metrics = get_metrics()

        try:
            while True:
                # Get current queue depth
                queue_depth = self.redis_client.get_queue_depth()

                # Determine target worker count
                target_count = self.get_target_worker_count(queue_depth)

                # Get current worker count (clean up dead processes)
                self.active_workers = {
                    pid: p for pid, p in self.active_workers.items() if p.is_alive()
                }
                current_count = len(self.active_workers)

                # Update metrics with worker state
                metrics.set_workers_state(active=current_count, target=target_count)

                # Log status
                status = f"📊 Queue depth: {queue_depth}, Workers: {current_count}/{target_count}"

                # Scale if needed
                if current_count < target_count:
                    diff = target_count - current_count
                    self.log_scale_event(f"{status} → Scaling UP by {diff}")
                    self.scale_up(diff)
                elif current_count > target_count:
                    diff = current_count - target_count
                    self.log_scale_event(f"{status} → Scaling DOWN by {diff}")
                    self.scale_down(diff)
                else:
                    print(status)

                # Wait before next check
                time.sleep(SCALER_CHECK_INTERVAL_SEC)

        except KeyboardInterrupt:
            print("\n⛔ Shutting down scaler...")
            self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shutdown all worker processes."""
        print(f"Terminating {len(self.active_workers)} worker processes...")
        for pid in list(self.active_workers.keys()):
            self.terminate_worker(pid)
        print("✓ All workers terminated")
        sys.exit(0)


def main():
    """Entry point for the auto-scaler."""
    manager = WorkerManager()
    manager.run()


if __name__ == "__main__":
    main()
