# AI Reporting & Workflow Nucleus

This repository delivers a minimal viable product for an AI-assisted reporting and workflow nucleus. A FastAPI **App** service captures outcome requests, validates generated automation code, and exposes a read-only SDK over HTTP. A sandboxed **Runner** service executes LLM-generated Python inside strict isolation using the SDK to interact with the business database and communication facilities. A PostgreSQL database stores business data, LLM artifacts, run metadata, and email activity.

## Features

- FastAPI App with SQLAlchemy 2.x ORM, Alembic migrations, and Pydantic v2 schemas.
- Outcome flow endpoints that manage prompts, specs, plans, and generated code.
- Policy gate enforcing strict import, size, and email allowlist rules.
- Read-only SQL SDK, email simulation, artifact persistence, and run logging.
- State machine engine backed by YAML DSL for Invoice lifecycle.
- Runner service that executes generated code inside a sandbox with CPU, memory, and wall-clock limits, forwarding SDK calls back to the App using JWT authentication.
- Seeded demo data (orders, invoices, payments) to exercise reports and state transitions.
- Example automation for emailing an Aging Accounts Receivable report and attaching a CSV artifact.

## Getting Started

1. Copy the example environment file and adjust if necessary:
   ```bash
   cp .env.example .env
   ```
2. Start the stack:
   ```bash
   make up
   ```
   This launches PostgreSQL, the App service, and the Runner with live code mounts. The App runs Alembic migrations and seeds demo data on startup.

3. Verify the services:
   - [http://localhost:8000/health](http://localhost:8000/health) should return `{ "status": "ok" }`.
   - [http://localhost:8000/reports/aging-ar](http://localhost:8000/reports/aging-ar) returns overdue invoice rows from the seeded dataset.

4. Run the test suite:
   ```bash
   make test
   ```
   This executes pytest in both the App and Runner containers.

## Outcome Flow Walkthrough

The MVP expects that an external LLM or human operator provides artifacts (spec, plan, code). Use `curl` or an API client to progress an automation through the lifecycle.

1. **Store the spec**
   ```bash
   curl -X POST http://localhost:8000/outcomes/spec \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "00000000-0000-0000-0000-000000000001",
       "prompt": "Email each buyer an Aging AR CSV every Monday",
       "spec_json": {"goal": "Send weekly aging AR report"}
     }'
   ```
   Response contains an `artifact_id` for subsequent steps.

2. **Attach the plan**
   ```bash
   curl -X POST http://localhost:8000/outcomes/plan \
     -H "Content-Type: application/json" \
     -d '{
       "artifact_id": "<artifact_id>",
       "plan_json": {"steps": ["Query overdue invoices", "Generate CSV", "Send email"]}
     }'
   ```

3. **Submit generated code**
   ```bash
   curl -X POST http://localhost:8000/outcomes/code \
     -H "Content-Type: application/json" \
     -d '{
       "artifact_id": "<artifact_id>",
       "code": "from nmc_sdk import query, to_csv, email, save_artifact, now\n..."
     }'
   ```
   The policy gate validates imports, line counts, and allowed email domains.

4. **Preview the effect**
   ```bash
   curl -X POST http://localhost:8000/outcomes/preview \
     -H "Content-Type: application/json" \
     -d '{
       "artifact_id": "<artifact_id>",
       "limits": {"cpu_ms": 500, "wall_ms": 2000, "mem_mb": 128}
     }'
   ```
   The App mints a short-lived run JWT, invokes the Runner in `preview` mode, and returns SQL samples, email previews, and SDK call logs. No emails are sent.

5. **Approve & execute**
   ```bash
   curl -X POST http://localhost:8000/outcomes/approve-run \
     -H "Content-Type: application/json" \
     -d '{
       "artifact_id": "<artifact_id>",
       "limits": {"cpu_ms": 500, "wall_ms": 2000, "mem_mb": 128}
     }'
   ```
   The Runner executes in `execute` mode; the App stores run metadata, SDK call receipts, and generated artifacts.

6. **Schedule runs**
   ```bash
   curl -X POST http://localhost:8000/outcomes/schedule \
     -H "Content-Type: application/json" \
     -d '{
       "artifact_id": "<artifact_id>",
       "cron": "0 13 * * 1"
     }'
   ```
   Trigger the simple scheduler manually for the MVP:
   ```bash
   curl -X POST http://localhost:8000/_internal/tick
   ```

## Preview vs. Execute

- Preview mode forces the App SDK gateway to simulate side effects. Queries run in read-only transactions, email endpoints return structured previews, and artifacts produce base64 previews only.
- Execute mode behaves similarly but records `sdk_calls` rows to simulate sending emails and saving artifacts.

## Security Posture

- `/sdk/query` rejects any non-`SELECT` statement using a lightweight parser and the DB user is read-only.
- Email recipients must belong to domains listed in `ALLOWED_EMAIL_DOMAINS`.
- Run tokens (JWT HS256) are short-lived (≤120 seconds) and scoped per run.
- Runner sandbox sets CPU/memory limits, disables dangerous builtins/imports, and only exposes the tiny `nmc_sdk` surface.

## Scheduler Notes

The MVP scheduler is manual: calling `POST /_internal/tick` scans enabled schedules and triggers Runner executions using the stored artifacts. A production system would integrate a persistent job queue and timer service.

## Next Steps

- Add guard expressions to the DSL.
- Allow editing DSL definitions via AI assistance.
- Expand the policy engine with richer static analysis and runtime monitoring.
- Implement role-based access control and multi-tenant scoping.
- Deliver more workflow primitives (approvals, change orders, cancellation flows).

