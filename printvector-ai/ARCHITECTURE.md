# PrintVector AI — Architecture

## Guiding Principles

1. **Separate orchestration from AI implementation.** Business logic (job
   lifecycle, validation rules, storage) never imports a specific model
   library directly; it talks to a `Stage` interface. Models are
   implementation details behind that interface.
2. **Every AI stage is a replaceable plugin.** Background removal,
   upscaling, vectorization, etc. are independently swappable without
   touching the orchestrator, the API, or the database schema.
3. **Local-first, cloud-ready.** Phase 1 runs as a single-machine
   client/server app (can even run entirely on one laptop). Nothing in the
   design assumes a single process or a single disk — storage and queueing
   are behind abstractions so the same code can later run distributed.
4. **No premature multi-tenancy, but no tenancy landmines either.** Phase 1
   has one implicit "workspace." The schema and API are shaped so adding
   `organization_id`/`user_id` later is an additive migration, not a
   rewrite.
5. **Deterministic, inspectable pipeline.** Every stage records its inputs,
   outputs, parameters, and timing. A job's full history can be
   reconstructed and replayed for debugging or regression testing.

## High-Level Architecture

```
                                ┌─────────────────────────┐
                                │        Web UI           │
                                │  (React SPA, internal)  │
                                └────────────┬─────────────┘
                                             │ HTTPS (REST + WS)
                                             ▼
                                ┌─────────────────────────┐
                                │       API Gateway        │
                                │   (FastAPI, REST + auth  │
                                │    middleware stub)      │
                                └────────────┬─────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    ▼                        ▼                        ▼
          ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
          │   Job Service      │   │  Storage Service   │   │  Config/Preset    │
          │ (create/track jobs)│   │ (files, artifacts)  │   │     Service       │
          └─────────┬──────────┘   └─────────┬──────────┘   └───────────────────┘
                    │                        │
                    ▼                        ▼
          ┌────────────────────────────────────────────┐
          │              Job Queue (broker)             │
          │        (Redis-backed task queue)            │
          └─────────────────────┬────────────────────────┘
                                 ▼
          ┌────────────────────────────────────────────┐
          │           Pipeline Orchestrator             │
          │   (DAG runner over pluggable Stages)        │
          └─────────────────────┬────────────────────────┘
                                 ▼
   ┌────────────────────────────────────────────────────────────────┐
   │                        AI Pipeline Stages                       │
   │                                                                   │
   │  Analysis → Enhancement → Background Removal → Vectorization →  │
   │           SVG Optimization → Print Validation                    │
   │                                                                   │
   │  Each stage = plugin behind a common interface (see AI_PIPELINE) │
   └────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Artifact Storage       │
                    │ (local disk / S3-compat) │
                    └─────────────────────────┘

          ┌────────────────────────────────────────────┐
          │        Metadata Database (SQL)              │
          │  Jobs, Files, StageRuns, Presets, (Users*)  │
          └────────────────────────────────────────────┘
```

`*` future entity, see `DATABASE.md`.

## System Components

### 1. Web UI (Client)
A React + TypeScript single-page app. Responsibilities: drag-and-drop
upload, job status/progress (polling or WebSocket), before/after preview,
manual override controls (e.g., "force background removal," "this is
line-art not a photo"), download of results, and a review queue for
low-confidence jobs. No business logic lives here beyond form validation and
optimistic UI state.

### 2. API Gateway
A FastAPI application exposing the REST API defined in `API_SPEC.md`. It:
- Validates and stores uploads via the Storage Service.
- Creates `Job` records and enqueues pipeline execution.
- Exposes job status/results endpoints.
- Hosts an (initially no-op) auth middleware slot — see `SECURITY.md` — so
  adding real authentication later doesn't require re-plumbing every route.
- Is stateless: all state lives in the database and storage backend, so
  multiple API instances can run behind a load balancer in the SaaS phase.

### 3. Job Service
Encapsulates job lifecycle rules: valid state transitions
(`uploaded → queued → analyzing → processing → needs_review → completed |
failed`), retry policy, and idempotency (re-submitting the same file
doesn't double-charge compute). This is pure business logic with no AI
dependencies — fully unit-testable without any model installed.

### 4. Storage Service
An abstraction (`StorageBackend` interface) with two implementations:
- `LocalDiskBackend` — default for Phase 1, single-machine deployments.
- `S3CompatibleBackend` — for MinIO (self-hosted) or AWS S3 (SaaS phase).

All other components depend on the interface, never on a specific backend,
so Phase 1 → SaaS migration is a config change, not a code change.

### 5. Config/Preset Service
Stores named pipeline configurations ("Apparel logo — photo," "Signage —
line art," "Embroidery digitizing prep") that bundle stage parameters (e.g.
target color count, minimum stroke width) so operators don't hand-tune every
job. Presets are versioned so historical jobs can be reproduced.

### 6. Job Queue / Broker
Redis-backed task queue (Celery or RQ — see `TECH_STACK.md`). Decouples the
API (must respond fast) from the pipeline (can take seconds to a couple of
minutes). Enables horizontal scaling of workers independent of the API
tier, and is a prerequisite for both batch processing and future SaaS
concurrency.

### 7. Pipeline Orchestrator
A small DAG runner that executes an ordered (mostly linear, with
conditional branches) sequence of `Stage` plugins for a given job. It:
- Resolves which stages to run based on the Analysis stage's output (e.g.
  skip background removal if the image is already flat vector line art).
- Persists a `StageRun` record per stage execution (inputs, outputs,
  parameters, duration, success/failure, confidence score).
- Supports re-running a single stage with adjusted parameters without
  re-running the whole pipeline (important for both operator overrides and
  regression testing).

### 8. AI Pipeline Stages
See `AI_PIPELINE.md` for full detail. Each stage is a plugin implementing a
shared interface (`analyze`/`process` in, structured result out). Stages in
v1: **Image Analysis, Enhancement (denoise/deskew/upscale), Background
Removal, Vectorization, SVG Optimization, Print Validation.**

### 9. Artifact Storage
Every intermediate and final file (original upload, enhanced raster,
background-removed PNG, raw traced SVG, optimized SVG, validation report)
is persisted, not just the final output. This is essential for debugging,
regression testing, and operator trust ("show me what changed at each
step").

### 10. Metadata Database
Relational database (SQLite for Phase 1 default, Postgres-ready) storing
jobs, file references, stage run history, and presets. See `DATABASE.md`.

## Data Flow (Single Job, Happy Path)

1. User uploads an image via the Web UI → `POST /jobs` with the file.
2. API Gateway validates the file (type, size, decompression-bomb checks —
   see `SECURITY.md`), stores the original via the Storage Service, creates
   a `Job` row (`status=queued`), and enqueues a pipeline task.
3. A worker picks up the task, transitions the job to `analyzing`, and runs
   the **Analysis** stage: detects resolution, blur, noise level, whether
   the source looks like a photo vs. flat art, dominant background type,
   presence of text, estimated color count.
4. Based on analysis output, the Orchestrator builds the stage plan for
   this job (e.g., "needs upscaling + denoise, needs background removal,
   photographic subject → segmentation model X").
5. **Enhancement** runs (deskew, denoise, contrast normalization, optional
   super-resolution upscaling).
6. **Background Removal** runs if the analysis flagged a non-flat
   background.
7. **Vectorization** converts the cleaned raster into SVG paths, choosing a
   strategy based on whether the content is flat-color line art (Potrace-
   style) or full-color/photographic (color quantization + multi-layer
   trace).
8. **SVG Optimization** cleans up the raw traced SVG (path simplification,
   merging redundant nodes, removing invisible elements, minifying).
9. **Print Validation** checks the result against print-readiness rules
   (minimum stroke width, path count sanity, color count, no raster
   remnants, artboard/bleed sanity) and produces a pass/warn/fail report
   with a confidence score.
10. Job transitions to `completed` (confidence above threshold) or
    `needs_review` (below threshold or validation warnings), and the UI
    is updated (poll or WebSocket push). All intermediate artifacts and a
    per-stage report remain available for the operator.

## AI Pipeline (Summary)

Detailed in `AI_PIPELINE.md`. Architecturally, the key point is that the
pipeline is a **DAG of independently pluggable stages** communicating via a
well-defined data contract (typed input/output objects, not raw bytes
passed ad hoc), so:
- New stages can be inserted (e.g. a future "auto color reduction for
  spot-color printing" stage) without touching earlier stages.
- Existing stages can be replaced (e.g. swap the vectorizer from
  Potrace-based to a commercial API) by implementing the same interface.
- Each stage can be tested, benchmarked, and versioned in isolation.

## Module Boundaries

The codebase is organized so each of these is an independently testable,
independently deployable-in-principle unit:

- **`core/`** — domain models, job state machine, validation rules. Zero
  dependency on any AI/ML library or web framework.
- **`api/`** — FastAPI routes, request/response schemas, auth middleware
  slot. Depends on `core/` and `services/`, not on pipeline internals
  directly.
- **`services/`** — Storage Service, Preset Service, Job Service
  implementations. Depend on `core/`.
- **`pipeline/`** — Orchestrator + `Stage` interface + stage registry.
  Depends only on `core/` data contracts.
- **`stages/`** — one package per AI stage (`stages/analysis`,
  `stages/enhancement`, `stages/background_removal`,
  `stages/vectorization`, `stages/svg_optimization`,
  `stages/print_validation`). Each depends only on `pipeline/`'s interface,
  never on each other directly, and never on `api/`.
- **`workers/`** — queue consumer entry points that wire `pipeline/` +
  `stages/` together and talk to `services/` for persistence.
- **`web/`** — the React client. Talks only to the public REST API.

This boundary is what makes the "plugin architecture" real rather than
aspirational: a stage package cannot reach into the API layer or another
stage's internals even if someone tries, because there's no import path
that allows it (enforced by directory convention + import-linting in CI).

## Plugin Architecture

Each AI capability is expressed as a class implementing a narrow interface,
conceptually:

```
class Stage(Protocol):
    name: str
    version: str

    def run(self, input: StageInput, params: dict) -> StageOutput: ...
```

Stages are registered in a **stage registry** keyed by capability name
(`"background_removal"`, `"vectorizer"`, ...), not by concrete class. The
Orchestrator asks the registry for "the current default background-removal
implementation" rather than importing `RembgBackgroundRemover` directly.
Swapping the default (e.g. from `rembg` to a SAM-based remover, or to a
paid API) is a one-line config/registry change. Multiple implementations
of the same capability can coexist (e.g. a fast/cheap default and an
opt-in high-quality one selectable per preset), which also gives a clean
path to **A/B testing model quality** later.

New stages are added by:
1. Implementing the `Stage` interface in a new `stages/<name>` package.
2. Registering it in the stage registry with a capability name.
3. Adding it to the relevant pipeline preset's stage list.

No changes to the Orchestrator, API, or database schema are required to add
or swap a stage (schema stores stage results as a generic
name/version/JSON-payload record — see `DATABASE.md`).

## Scalability Considerations

Phase 1 explicitly targets a **single internal deployment** (one small
server or even one workstation), but the following choices keep the door
open for scale without a rewrite:

- **Stateless API tier**: any number of API instances can run behind a load
  balancer once there's more than one; all state is in the DB/storage.
- **Queue-based workers**: pipeline execution is decoupled from HTTP
  request/response, so worker count scales independently of API traffic,
  and GPU-bound stages (upscaling, segmentation) can run on dedicated
  worker pools while CPU-bound stages (vectorization, SVG cleanup) run
  elsewhere.
- **Storage abstraction**: local disk today, S3-compatible object storage
  tomorrow, with no application code changes.
- **Database choice**: SQLite is fine for a single-machine internal tool;
  the ORM layer (SQLAlchemy) and migration tool (Alembic) make moving to
  Postgres a config change, not a schema rewrite — needed the moment there
  is more than one API/worker process writing concurrently.
- **Batch processing**: because jobs are already queue-based individual
  units of work, "batch" is just "enqueue many jobs," not a separate
  execution model.
- **Multi-tenancy-ready schema**: `organization_id`/`user_id` foreign keys
  can be added to existing tables as nullable columns, defaulted for
  existing rows, without breaking Phase 1 data (see `DATABASE.md` and
  `PRODUCT_DECISIONS.md`).
- **Caching**: stage results are content-addressed (hash of input +
  stage + params) so identical re-processing (common in batch mode when an
  operator retries with the same settings) can be served from cache instead
  of recomputed — an optimization, not a Phase 1 requirement, but the
  schema supports it from day one.
