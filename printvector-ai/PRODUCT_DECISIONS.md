# PrintVector AI — Product & Architecture Decision Log

Lightweight ADR (Architecture Decision Record) log. Each entry: context,
decision, alternatives considered, consequences. New decisions are
appended, not edited retroactively — if a decision is later reversed, a
new entry supersedes it and links back.

---

### ADR-001: Python + FastAPI as the sole backend language

**Context:** The AI/CV ecosystem the product depends on is overwhelmingly
Python-native.

**Decision:** Build the entire backend (API, orchestration, pipeline,
workers) in Python.

**Alternatives considered:** Node.js API with a Python ML sidecar service.

**Consequences:** Simplifies desktop packaging (one language runtime to
bundle instead of two) and debugging (no cross-language IPC boundary in
the hot path). Cost: Python's weaker story for CPU-bound non-ML code is
accepted, mitigated by the fact that the actual CPU-heavy work
(OpenCV, VTracer, Potrace) is native code under Python bindings anyway.
See `TECH_STACK.md`.

---

### ADR-002: SQLite as the Phase 1 database, Postgres deferred

**Context:** Phase 1 is a single-machine internal/desktop-first tool.

**Decision:** Default to SQLite via SQLAlchemy + Alembic, written in a
dialect-agnostic way. Explicit trigger for migrating to Postgres: **the
moment there is more than one concurrent writer process** (multiple API
instances, or a hosted multi-user SaaS deployment) — SQLite's single-writer
limitation is a correctness/throughput risk at that point, not before.

**Alternatives considered:** Postgres from day one (rejected — pure
operational friction for a Phase 1 desktop-first deployment with no
concurrent-writer need yet).

**Consequences:** Zero-install Phase 1 experience. Explicit, tracked
technical debt: the schema and all queries must avoid SQLite-only or
Postgres-only features so the migration stays a config change. Flagged as
a **must-do-before-any-multi-user-hosted-deployment** item, not an
optional nice-to-have — see `RISKS.md`.

---

### ADR-003: Local disk storage behind an `S3CompatibleBackend`-ready interface

**Context:** Same reasoning as ADR-002 applied to file storage.

**Decision:** `StorageBackend` interface with `LocalDiskBackend` as the
Phase 1 default; `S3CompatibleBackend` implemented and interface-tested
(contract tests run against both) before it's ever load-bearing, so it's
proven to be a true drop-in rather than an aspirational stub.

**Alternatives considered:** MinIO self-hosted from day one (rejected —
unnecessary extra service for a single-machine deployment).

**Consequences:** Local disk needs its own retention/cleanup policy (job
artifacts accumulate) — deliberately treated as an operational concern
(a scheduled cleanup job/retention window) rather than a reason to
introduce object storage prematurely.

---

### ADR-004: Every intermediate artifact is persisted, not just final output

**Context:** Debuggability and regression testing require inspecting what
happened at each pipeline stage, not just the end result.

**Decision:** Every stage's input/output image is written as a `File` row
(see `DATABASE.md`), even though this multiplies storage usage per job
(potentially 5-8x the original file size across all intermediates).

**Alternatives considered:** Only persist final output, keep intermediates
in-memory/ephemeral during a single pipeline run (rejected — makes the
"why did this job produce this output" question unanswerable after the
fact, which is unacceptable for an internal tool operators need to trust
and for regression testing which explicitly needs per-stage comparison).

**Consequences:** Storage usage is higher than strictly necessary;
mitigated by a retention policy (e.g. purge intermediate — but not
original/final — artifacts for jobs older than N days) to be implemented
before this becomes a real disk-space problem, not before.

---

### ADR-005: Stage plans are snapshotted onto the job at creation time

**Context:** Presets are versioned and editable; a job must not
silently reinterpret which stages/parameters it ran with if the preset is
edited after the job completes.

**Decision:** When a job is created, the resolved `stage_plan` (from the
preset version in effect at that moment) is copied onto the job's own
execution plan, not re-resolved live from the mutable preset on every
stage run. `jobs`/`stage_runs` reference which preset *version* was used,
for traceability, but execution never depends on the preset row still
existing/being unchanged later.

**Alternatives considered:** Live-resolve the preset at each stage
execution (rejected — makes historical jobs non-reproducible and makes
`rerun-stage` semantics ambiguous if the preset changed in the meantime).

**Consequences:** Slight duplication (the resolved plan is stored twice —
once on the preset, once snapshotted per job) — accepted as the cost of
reproducibility.

---

### ADR-006: The Orchestrator is a linear pipeline with conditional skips, not a general DAG engine

**Context:** The processing pipeline is fundamentally sequential
(analyze → enhance → remove background → vectorize → optimize → validate)
with occasional stage skips based on analysis output.

**Decision:** Build the Orchestrator to support exactly this shape —
ordered stages with per-stage skip predicates — rather than a
general-purpose arbitrary-graph workflow engine.

**Alternatives considered:** Adopt a general workflow/DAG orchestration
library (e.g. treating this like Airflow-style arbitrary task graphs) —
rejected as premature generalization; the domain doesn't currently need
arbitrary branching/fan-out/fan-in, and building for it now would add
real complexity for a hypothetical future need.

**Consequences:** If a genuine need for parallel/branching execution
emerges (e.g. running two vectorization strategies concurrently and
picking the better result by score), the first approach is to implement
it *inside* a single stage (an internal ensemble/compare step), not to
generalize the Orchestrator — revisit this ADR explicitly if that
approach proves insufficient.

---

### ADR-007: No authentication in Phase 1; auth middleware slot pre-wired

**Context:** Phase 1 is single-workspace, internal-network-only.

**Decision:** Ship with zero authentication, but route every request
through a currently-no-op auth middleware module so enabling real auth
later is additive.

**Alternatives considered:** Build basic auth (shared password) from day
one "just in case" (rejected — adds friction and a false sense of security
for a Phase 1 internal tool with no real multi-user trust boundary yet;
the pre-wired slot achieves the same "not a rewrite later" goal without
the upfront cost).

**Consequences:** The system is only as secure as the internal network it
runs on for Phase 1 — an explicit, accepted constraint, not an oversight
(see `SECURITY.md` for the full threat model and what *is* defended
against: hostile file content, regardless of the trusted-network
assumption for *users*).

---

### ADR-008: VTracer + Potrace over a single unified vectorization backend

**Context:** Print shop inputs span flat single-color line art and
full-color photographic content — no single open-source tracer excels at
both.

**Decision:** Route between two backends based on Analysis's content
classification rather than forcing one tracer to handle every case.

**Alternatives considered:** Use only VTracer for everything (rejected —
worse quality/performance on pure line art than a dedicated tool);
use only Potrace for everything (rejected — cannot handle full-color
content at all).

**Consequences:** Two vectorization code paths to maintain instead of
one; accepted because the quality difference on each backend's strong
suit is substantial and the `Stage` interface makes maintaining two
implementations of one capability cheap.

---

### ADR-009: SVGO (Node-based) accepted despite introducing a second language runtime

**Context:** SVGO is the strongest available SVG optimizer, but is a
Node.js tool, and the rest of the backend is Python.

**Decision:** Accept the Node dependency for Phase 1, isolated entirely
behind the `svg_optimization` stage's subprocess wrapper.

**Alternatives considered:** `scour` (pure Python, less capable) as the
single-language alternative.

**Consequences:** Explicitly flagged as a decision to revisit if it
causes real desktop-packaging pain (see Milestone 10 in `ROADMAP.md` and
`RISKS.md`) — `scour` is the documented fallback if bundling Node
alongside Python/Tauri proves not worth it in practice.

---

### ADR-010: Desktop packaging shell (Tauri vs. Electron) deliberately deferred

**Context:** Desktop packaging is Milestone 10, well after the core
pipeline is proven as a browser-based internal web app.

**Decision:** Do not commit to Tauri or Electron now; run early
milestones as a plain local web app (browser pointed at localhost), and
decide the packaging shell via a throwaway spike immediately before
Milestone 10.

**Alternatives considered:** Commit to Tauri now (rejected — locks in a
higher-uncertainty decision before it's needed, when a browser-based
internal tool already satisfies "desktop-first" for early milestones).

**Consequences:** Milestones 1-9 are fully validated on a stack-agnostic
foundation; the eventual packaging choice cannot invalidate any of that
work, since the API/pipeline/frontend are packaging-shell-agnostic by
construction.

---

### ADR-011: Multi-tenancy fields present but nullable/unused from day one

**Context:** SaaS evolution is an explicit future goal; retrofitting
tenancy onto a schema not designed for it is a common source of painful
migrations.

**Decision:** Add `organization_id`/`created_by_user_id` as nullable
columns on `jobs` now, even though Phase 1 never populates them, rather
than adding them only when SaaS work begins.

**Alternatives considered:** Add these fields only when actually building
multi-tenancy (rejected — the migration risk of adding a NOT-NULL-eventually
foreign key to a table with a year of un-tenanted historical data is
higher than carrying two unused nullable columns from the start).

**Consequences:** A small amount of schema "for future use" complexity in
Phase 1 in exchange for a materially safer SaaS-phase migration.
