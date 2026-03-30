# FemScale Context
Follow this strictly. Do not deviate from API or rules.
## 6. Frontend Requirements

React SPA. Must be functional and clear — demo-ready, not pixel-perfect. Judges will interact
with it.

#### 6.1 Page 1 — Function Submission

- Monospaced code textarea for writing/pasting Python function
- Timeout dropdown: 5 / 10 / 30 seconds (default 30)
- Submit button: calls POST /v1/jobs, shows spinner, disables on click
- On success: displays job_id, auto-navigates to Job Result page

#### 6.2 Page 2 — Job Result

- Shows job_id and colour-coded status badge (see Section 6.4)
- Polls GET /v1/jobs/{job_id} every 2 seconds until terminal status reached
- stdout and stderr in separate monospaced code blocks
- Shows duration_ms, memory_mb, cost_usd
- Back button to return to submission page


#### 6.3 Page 3 — Live Dashboard

- Polls GET /v1/metrics every 2 seconds
- Four metric cards: Queue Depth, Active Workers, Jobs Running, Session Cost
- Recent executions table: job_id, status, duration, cost — last 10 rows
- Event log: scrollable feed of platform events from metrics.events array

#### 6.4 Status Badge Colours

```
Status Badge Colour
```
```
queued Gray
running Blue
```
```
success Green
```
```
failed Red
timeout Orange