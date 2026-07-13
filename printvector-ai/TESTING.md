# PrintVector AI — Testing Strategy

Testing an image-in/image-out AI pipeline can't rely purely on exact-match
assertions the way normal business-logic testing does. This document
separates what *can* be tested deterministically (business logic, state
machine, API contracts) from what needs statistical/perceptual testing
(actual model output quality).

## Test Pyramid Overview

```
        ┌───────────────────────────┐
        │   E2E / UI (Playwright)    │   few, slow, high confidence
        ├───────────────────────────┤
        │  Regression (golden set)   │   moderate count, run in CI nightly
        ├───────────────────────────┤
        │     Integration tests      │   moderate count, run every PR
        ├───────────────────────────┤
        │        Unit tests          │   many, fast, run every PR/commit
        └───────────────────────────┘
```

## Unit Tests

**Scope:** `core/` (job state machine, validation rules), `pipeline/`
(orchestrator branching logic, registry), `services/` (storage backend
interface compliance, preset resolution), and each stage's *non-ML glue
code* (parameter validation, input/output contract adherence).

**Approach:**
- Pure business logic (state transitions, validation rules) is tested with
  standard example-based and property-based tests (e.g. "no job can move
  from `completed` back to `queued`" as an exhaustive transition-table
  test).
- Stage implementations are tested by constructing a `StageInput` with a
  small synthetic or fixture image and asserting on the *shape and
  invariants* of `StageOutput` (correct keys in `result_metadata`,
  confidence in `[0,1]`, output image has expected mode/format) rather
  than exact pixel output — exact-model-output assertions belong in the
  regression suite, not unit tests, so unit tests stay fast and don't
  break every time a model is retrained/upgraded.
- The `StorageBackend` interface is tested once against a shared
  contract-test suite, run against both `LocalDiskBackend` and (once it
  exists) `S3CompatibleBackend`, guaranteeing they're truly
  interchangeable.
- Target: unit tests run in well under a minute total and are part of
  every pre-commit/PR gate, no exceptions.

## Integration Tests

**Scope:** full pipeline execution through the real Orchestrator with real
(but lightweight) stage implementations, against a real (SQLite, ephemeral)
database, hit through the actual FastAPI app (via `TestClient`), including
the queue (using Celery's eager/synchronous test mode rather than a live
Redis broker, to keep CI simple and fast).

**What's covered:**
- `POST /jobs` → job reaches `completed`/`needs_review`/`failed` correctly
  for a handful of representative fixture images (one clean flat logo, one
  noisy photo-with-background, one deliberately corrupt file, one
  oversized file).
- `stage_runs` rows are created correctly, in order, with correct file
  lineage.
- Preset resolution end-to-end (custom preset with overridden params
  actually changes stage behavior/parameters passed).
- `rerun-stage` correctly re-executes only the targeted stage and
  downstream stages, leaving upstream `stage_runs` untouched.
- Error paths: a stage raising an exception correctly fails the job and
  surfaces `failure_reason` via the API.

**Not covered here:** actual output *quality* (that's the regression
suite's job) — integration tests assert the pipeline *runs to completion
and wires things together correctly*, using real but possibly
lower-fidelity/faster model configurations where reasonable to keep CI
fast.

## Regression Testing (Benchmark Dataset Strategy)

This is the most important — and most PrintVector-specific — testing
layer, because "does the output actually look right" is the whole point of
the product and can't be answered by unit/integration tests alone.

**Benchmark dataset:**
- A curated, versioned set of real-world-representative input images,
  organized by category: `whatsapp_logo/`, `screenshot/`,
  `phone_photo_skewed/`, `low_res_upscale_needed/`,
  `complex_background/`, `flat_line_art/`, `pdf_source/`, etc. — deliberately
  spanning the range of "bad customer input" described in `VISION.md`.
- Sourced from real (permission-cleared/anonymized or synthetic
  recreations of) customer submissions collected during early internal
  use, supplemented with deliberately constructed edge cases (extremely
  low-res, extreme skew, near-solid-color logos, text-heavy artwork).
- Stored via Git LFS or a dedicated artifact store (kept out of the main
  repo history to avoid bloating clones), referenced by
  `infra/scripts/seed_benchmark_dataset.py`.
- Each fixture has an associated **expected/reference output** (a
  human-approved "good" SVG) and/or **expected metadata assertions**
  (e.g. "confidence should be ≥ 0.8," "background should be flagged as
  removed," "output color count should be ≤ 6").

**Scoring approach (not exact-match):**
- **Structural similarity (SSIM)** and/or **perceptual hashing** comparing
  a rendered PNG of the current output SVG against the rendered reference
  PNG, with a tolerance threshold rather than pixel-perfect equality —
  legitimate minor tracing differences (a slightly different Bezier
  control point) shouldn't fail the suite.
- **Metric assertions** on `result_metadata`/validation reports (color
  count, path count, confidence score) checked against expected
  ranges/thresholds per fixture, not exact values.
- **Aggregate pass-rate tracked over time** (dashboarded, not just
  pass/fail in CI) — a single fixture regressing slightly is informative
  even if it doesn't fail the build; a systematic drop across many
  fixtures after a model swap is a hard gate.

**When it runs:** nightly (full dataset, since it's slower than unit/
integration tests) and on-demand before promoting any new model
implementation to default (see `AI_PIPELINE.md` Model Replacement
Strategy) — a new implementation must match or beat the incumbent's
aggregate score on this suite before it becomes the default.

**Growing the dataset:** any `needs_review` job that an operator corrects
significantly, or any bug report about bad output, is a candidate to be
anonymized and added to the benchmark set — the dataset is a living asset
that gets more representative of real failure modes over time, not a
fixed set defined once upfront.

## Performance Testing

- **Per-stage latency benchmarks**: `stage_runs.duration_ms` is already
  captured in production (see `DATABASE.md`) and the same instrumentation
  is used in a dedicated perf-test run against the benchmark dataset,
  tracking p50/p95 latency per stage over time to catch regressions (e.g.
  a library upgrade that quietly makes tracing 3x slower).
- **End-to-end job latency** targets tied to the success metrics in
  `VISION.md` (median < 3 minutes automated) — tracked as a CI-visible
  metric, not just an aspiration.
- **Resource ceilings**: peak memory usage per stage is measured against
  the largest reasonable input (near the max upload size) to catch
  decompression/upscaling stages that could blow past a worker's memory
  budget.
- **Batch/load testing** (once batch processing ships): submitting N
  concurrent jobs and measuring queue drain time and worker resource
  usage, to validate worker pool sizing recommendations before the
  feature is considered production-ready.
- **Desktop packaging perf** (once relevant): cold-start time of the
  bundled app (including model loading) is tracked explicitly, since
  a slow-starting desktop app is a distinct UX complaint from slow
  per-job processing.

## UI Testing

- **Playwright** end-to-end smoke tests: upload a file → job appears in
  the list → status transitions are reflected → completed job's SVG is
  downloadable → review queue shows a deliberately-low-confidence fixture
  and supports the approve/rerun-stage actions.
- Kept intentionally small in number (a handful of critical-path
  scenarios) — the UI's correctness for complex cases is primarily
  validated through the API layer's integration tests, not by
  proliferating slow browser tests.

## CI Gates Summary

| Test layer | Runs on | Blocks merge? |
|---|---|---|
| Unit | every commit/PR | yes |
| Integration | every PR | yes |
| Regression (subset/smoke) | every PR (fast subset) | yes |
| Regression (full benchmark) | nightly + before model promotion | yes, for promotion decisions; informational for nightly drift |
| Performance | nightly + before model promotion | yes, for promotion decisions |
| UI/E2E | every PR (critical path only) | yes |
