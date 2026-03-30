# FemScale Context
Follow this strictly. Do not deviate from API or rules.
# FemScale

### Product Requirements Document

```
Serverless Compute Platform | PS 2 | WT'26 Hackathon
Version 1.0 | For Coding Agent Reference
Assumed: Small team (2-3 people) | Local deployment for demo
```
## 1. Product Overview

FemScale is a lightweight serverless compute platform. Developers upload a function in any
supported language and it executes automatically — with no server configuration, no DevOps
knowledge, and no infrastructure management required. The platform handles job queuing,
isolated execution, elastic auto-scaling, logging, and cost estimation transparently.

The guiding principle: drop your function in, and it runs. Everything underneath is invisible.

##### Core Tech Stack

```
Layer Technology
```
```
Frontend React
Backend / API FastAPI (Python)
```
```
Queue & Cache Redis
Execution Runtime Docker
```
```
Persistent Logging SQLite
```
```
Cost Reference Model AWS Lambda Pricing
Supported Exec Language
(MVP)
```
```
Python
```
## 2. Goals & Non-Goals

#### 2.1 Goals — Must Have for Demo

- Developer can upload a Python function via the UI with zero config
- Function is queued, executed in an isolated Docker container, result returned
- Auto-scaling: worker count adjusts dynamically based on queue depth
- Live dashboard: active workers, queue depth, recent jobs, cost per run
- Simulated cost estimate per execution using AWS Lambda pricing formula
- All endpoints documented and interactive via FastAPI /docs


#### 2.2 Stretch Goals — Brownie Points (Achievable)

- Cost awareness: surfaced per-run and as cumulative session total on dashboard
- GitHub Actions trigger: POST /v1/jobs called from a CI pipeline via curl step

#### 2.3 Non-Goals

- Multi-language runtime support beyond Python (deferred post-MVP)
- Cloud / remote deployment (demo runs fully local)
- Authentication or user accounts
- Real billing or payment integration
- Persistent function versioning or storage