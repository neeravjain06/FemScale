# FemScale Context
Follow this strictly. Do not deviate from API or rules.
## 7. Data Models

#### 7.1 Job Object — Redis (ephemeral, TTL 1 hour)

###### {

```
"job_id": "string (uuid4)",
"code": "string",
"timeout_sec": "integer",
"status": "queued | running | success | failed | timeout",
"created_at": "ISO8601 UTC timestamp"
}
```
#### 7.2 Execution Record — SQLite (persistent)

```
Column Type Description
job_id TEXT PRIMARY KEY UUID4 identifier
```
```
status TEXT Terminal status of the job
```
```
stdout TEXT Captured standard output
stderr TEXT Captured standard error
```
```
error TEXT NULLABLE Platform-level error message if any
```
```
duration_ms INTEGER Total execution time in milliseconds
memory_mb REAL Peak memory usage in MB
```
```
cost_usd REAL Calculated cost per formula in Section 4.
created_at TEXT ISO8601 UTC submission timestamp
```

```
Column Type Description
```
```
completed_at TEXT ISO8601 UTC completion timestamp