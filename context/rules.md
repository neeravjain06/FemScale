# FemScale Context
Follow this strictly. Do not deviate from API or rules.
## 11. Rules for the Coding Agent

These rules are absolute. The coding agent must follow them at all times when generating or
modifying any code in this project.

#### 11.1 Always Do


- Match API routes exactly as defined in Section 5 — no renaming, no extra prefixes, no
    shortcuts
- Use the exact status enum strings everywhere: queued, running, success, failed, timeout
- Apply all three Docker constraints on every container: memory, CPU, and timeout —
    never spawn unconstrained
- Use Redis as the only queue — do not introduce RabbitMQ, Kafka, or any other broker
- Use SQLite as the only persistent store — do not introduce PostgreSQL or any other DB
- Recalculate cost fresh on every job completion using the formula in Section 4.
- Format all timestamps as ISO8601 UTC
- Use polling on the frontend — do not implement WebSockets for MVP
- Add a FastAPI docstring to every route so /docs is useful for judges
- Use uuid4 for all job_id generation — never hardcode or reuse IDs

#### 11.2 Never Do

- Never store function code on disk on the host — only inside Docker container context
- Never allow a container to run without a timeout — always enforce the 30s limit
- Never expose raw Redis keys or SQLite schema fields directly through the API
- Never block the FastAPI main thread with execution logic — workers are separate
    processes
- Never implement authentication — explicitly out of scope for this hackathon
- Never reuse a Docker container across jobs — one container per job, destroyed after

#### 11.3 Code Style

- Python: PEP8, type hints on all function signatures, Pydantic models for all
    request/response bodies
- React: functional components only, no class components, useState + useEffect for all
    polling
- File naming: snake_case for Python files, PascalCase for React component files
- No magic numbers: all thresholds (128MB, 30s, queue tiers, cost constant) must be
    named constants

```
FemScale PRD v1.0 | WT'26 Hackathon | Coding Agent Reference Document
```

