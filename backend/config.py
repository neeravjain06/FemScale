"""Configuration and constants for FemScale."""

# Constraints
MAX_CODE_SIZE_BYTES = 50 * 1024  # 50KB
MIN_TIMEOUT_SEC = 1
MAX_TIMEOUT_SEC = 30
DEFAULT_TIMEOUT_SEC = 30

# Docker constraints (for reference during implementation)
DOCKER_MEMORY_MB = 128
DOCKER_CPU_COUNT = 1
DOCKER_TIMEOUT_SEC = 30

# Cost formula: (Memory_GB × Duration_seconds) × AWS_LAMBDA_RATE
AWS_LAMBDA_RATE_PER_GB_SECOND = 0.0000000167

# Auto-scaling tiers
SCALING_TIERS = [
    {"queue_depth_min": 0, "queue_depth_max": 5, "target_workers": 1},
    {"queue_depth_min": 5, "queue_depth_max": 20, "target_workers": 3},
    {"queue_depth_min": 20, "queue_depth_max": 50, "target_workers": 7},
    {"queue_depth_min": 50, "queue_depth_max": float("inf"), "target_workers": 10},
]

MAX_WORKERS = 10
MIN_WORKERS = 1
SCALER_CHECK_INTERVAL_SEC = 3
