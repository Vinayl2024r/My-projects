# PrintVector AI — Roadmap

Each milestone below is scoped to be **independently testable** — it
produces something that can be demoed and validated on its own, even
before later milestones exist. Milestones are sequential by dependency,
not necessarily equal in size.

## Milestone 1 — Foundation

**Goal:** the skeleton every later milestone builds on, with nothing
AI-specific yet.

- Repo structure per `PROJECT_STRUCTURE.md`.
- FastAPI app with `/health` and `/health/ready`.
- SQLite database + Alembic migrations for `jobs`, `files`, `stage_runs`,
  `presets` tables.
- `Job` state machine (`core/job_states.py`) fully unit tested, no
  pipeline execution yet — jobs can be created and manually transitioned.
- `StorageBackend` interface + `LocalDiskBackend` implementation.
- CI pipeline running lint, type-check, unit tests on every PR.

**Test/demo criteria:** create a job via a script or minimal API call,
see it persisted correctly, run the full migration + test suite in CI
green.

## Milestone 2 — Upload Engine

**Goal:** a real, secure file-upload path with nothing downstream yet.

- `POST /jobs` fully implemented: file validation (type sniffing, size
  limits, decompression-bomb checks per `SECURITY.md`), original file
  stored via `StorageBackend`, `Job` row created in `uploaded`/`queued`.
- `GET /jobs/{id}`, `GET /jobs`, `GET /jobs/{id}/files/{file_id}`.
- Redis + Celery wired in; job creation enqueues a task that (for now)
  just marks the job `completed` immediately with the original file as
  output — a no-op pipeline, proving the queue plumbing works end to end.
- Minimal Web UI: upload form, job list, status display, download link.

**Test/demo criteria:** a real user can drag a file into the browser UI
and get it back unchanged, through the full API → queue → worker → storage
→ UI round trip. This validates the entire "shell" before any AI risk is
introduced.

## Milestone 3 — Image Analysis

**Goal:** first real AI stage; pipeline goes from no-op to actually
inspecting the image.

- `stages/analysis` implemented per `AI_PIPELINE.md`: resolution/blur/
  noise/skew detection, content classification, background complexity
  estimate, color count estimate.
- `stage_runs` populated with real `result_metadata`.
- Orchestrator framework (`pipeline/orchestrator.py`, `pipeline/stage.py`,
  `pipeline/registry.py`) built out generally, even though only one real
  stage exists yet.
- UI surfaces analysis results (e.g. "detected: photo, complex
  background, low resolution") on the job detail view.

**Test/demo criteria:** upload the benchmark dataset's varied fixtures and
confirm each is classified correctly (unit + first slice of the
regression suite); no visual output change yet, but the routing
intelligence is visibly working.

## Milestone 4 — Enhancement

**Goal:** first stage that actually improves the image.

- `stages/enhancement`: deskew, denoise, contrast normalization, and
  conditional super-resolution upscaling (Real-ESRGAN + classical
  fallback).
- Orchestrator conditionally invokes based on Analysis output.
- UI before/after comparison view (critical UX proof point — this is
  where operators start trusting or distrusting the tool).

**Test/demo criteria:** visibly improved output on skewed/noisy/low-res
benchmark fixtures; regression suite asserts enhancement operations ran
where expected.

## Milestone 5 — Background Removal

**Goal:** isolate the subject from clutter.

- `stages/background_removal`: `rembg` default implementation, chroma-key
  classical fallback, conditional skip for flat line art.
- Confidence-based escalation path stubbed (SAM implementation can land
  as a fast-follow within this milestone or immediately after — flagged as
  the milestone's main quality-risk item, see `RISKS.md`).

**Test/demo criteria:** benchmark fixtures with backgrounds produce clean
transparent-background output; flat line-art fixtures correctly skip this
stage (verified via `stage_runs.status = skipped`).

## Milestone 6 — Vectorization

**Goal:** the core deliverable — raster to actual vector paths.

- `stages/vectorization`: Potrace backend for flat/line-art content,
  VTracer backend for full-color/photographic content, strategy selection
  driven by Analysis output.
- Output is a raw (not yet optimized) SVG, downloadable from the UI.

**Test/demo criteria:** for the first time, a job produces a genuine SVG
that opens correctly in Illustrator/Inkscape. This is the milestone where
the product's core promise becomes real and demoable to stakeholders.

## Milestone 7 — SVG Optimization

**Goal:** clean, minimal, production-quality SVG output.

- `stages/svg_optimization`: SVGO integration (subprocess wrapper),
  path simplification, precision rounding, dead-code removal.
- File size and path-count improvements measured and displayed.

**Test/demo criteria:** benchmark SVGs shrink meaningfully in file size
and path count with no visible shape degradation (SSIM comparison against
pre-optimization render, per `TESTING.md`).

## Milestone 8 — Print Validation

**Goal:** automated print-readiness quality gate; introduces the
`needs_review` state meaningfully for the first time.

- `stages/print_validation`: stroke width, color count, path sanity,
  raster-remnant, artboard checks per preset.
- Job confidence aggregation logic in the Orchestrator.
- Review queue UI: list of `needs_review` jobs, validation report display,
  approve / rerun-stage-with-override actions.
- First set of built-in presets (`apparel_logo`, `signage_line_art`,
  `embroidery_prep`) authored and seeded.

**Test/demo criteria:** deliberately "hard" benchmark fixtures correctly
land in `needs_review` with an actionable report; deliberately "easy"
fixtures land in `completed` with no operator action needed. This
milestone is the point at which internal production staff can start using
the tool for real work.

## Milestone 9 — Batch Processing

**Goal:** handle folders/zips of many images at once, matching how print
shops actually receive bulk orders.

- `POST /batches`, `GET /batches/{id}` per `API_SPEC.md`.
- Zip-file ingestion (extract, validate each member independently, one
  `Job` per valid file, clear reporting of any rejected members).
- Batch-aware review queue UI (bulk approve, filter by status within a
  batch).
- Worker pool sizing/throughput validated under realistic batch load (see
  `TESTING.md` performance testing).

**Test/demo criteria:** submit a 50–100 image zip mixing easy and hard
fixtures; verify correct per-file job creation, correct aggregate batch
status, and acceptable total wall-clock time.

## Milestone 10 — Desktop Packaging

**Goal:** ship as an installable desktop app for production staff who
prefer not to use a browser-hosted internal tool, or need offline
operation.

- Evaluate Tauri vs. Electron in practice (provisional lean: Tauri —
  see `TECH_STACK.md`) by building a throwaway spike bundling the Python
  backend as a sidecar for both, before committing.
- Bundle backend (PyInstaller), Redis (or replace with an in-process
  queue shim for single-user desktop mode — explicitly revisit whether
  Celery/Redis is even needed in single-user desktop deployments, see
  `PRODUCT_DECISIONS.md`), and frontend into one installable package per
  OS (Windows primary, given typical print-shop environments; macOS/Linux
  as resourcing allows).
- Auto-update mechanism for shipping model/bugfix updates to installed
  desktop clients.

**Test/demo criteria:** a non-technical staff member installs the app on
a clean workstation with no prior setup and successfully processes a job
fully offline.

## Milestone 11 — Future SaaS Evolution

**Goal:** multi-tenant, billable, externally-facing product — explicitly
a *future* phase, scoped here only at a planning level, not committed
work.

- Add `organizations`, `users`, `api_keys`, `subscriptions` tables
  (additive migration — see `DATABASE.md`).
- Real authentication (per the progression in `SECURITY.md`).
- Migrate default DB to Postgres; migrate default storage to
  S3/S3-compatible (both are config changes per `ARCHITECTURE.md`, but
  this milestone is where they're actually exercised in production for
  the first time under real concurrent multi-user load).
- Usage metering feeding a billing system.
- Public API + API-key-based programmatic access for print-shop websites
  to embed "upload your logo" widgets.
- Self-serve customer-facing upload portal (distinct from the internal
  operator UI).
- Rate limiting, abuse detection, and the DDoS/multi-tenant-isolation
  concerns explicitly deferred in `SECURITY.md`.

**Test/demo criteria:** two separate simulated organizations can use the
system concurrently with zero data cross-visibility, correct usage
metering, and acceptable performance under concurrent multi-tenant load —
validated via load testing before any real external customer is onboarded.
