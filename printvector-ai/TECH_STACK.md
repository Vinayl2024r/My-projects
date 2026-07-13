# PrintVector AI — Technology Stack

For every major choice: **why**, **alternatives considered**, **tradeoffs**,
and **fit for an internal, desktop-first Phase 1**.

## Backend Language & Framework: Python + FastAPI

**Why:** The entire AI/CV ecosystem PrintVector depends on (OpenCV,
rembg/segmentation models, super-resolution models, PyTorch/ONNX runtimes,
Potrace/VTracer bindings) is Python-native or has first-class Python
bindings. Building the API in the same language as the pipeline avoids a
cross-language boundary (e.g., Node calling out to a Python microservice
for every stage), which simplifies debugging, deployment, and packaging —
especially important for the desktop-packaging milestone. FastAPI adds
async support, automatic OpenAPI schema generation (directly useful for
`API_SPEC.md` staying in sync with reality), and Pydantic-based request
validation.

**Alternatives considered:**
- *Node.js/TypeScript backend calling a Python "ML sidecar"*: keeps the web
  team in one language, but adds an IPC boundary, doubles the dependency
  surface, and complicates desktop packaging (two runtimes to bundle).
- *Django*: more batteries-included (admin panel, ORM), but heavier, more
  opinionated, and its sync-first request model fits this I/O-light,
  CPU/GPU-heavy workload less naturally than FastAPI's async model.
- *Flask*: simpler than Django, but lacks built-in async, request
  validation, and OpenAPI generation that FastAPI provides out of the box.

**Tradeoffs:** Python is slower than compiled languages for pure CPU-bound
code (mitigated because the hot paths — OpenCV, vectorization libraries —
are C/C++/Rust under the hood with Python bindings). Async FastAPI code
requires discipline to avoid blocking the event loop with long-running
CPU/GPU work — mitigated by pushing that work onto queue workers, never
running it inline in a request handler.

**Fit for internal desktop-first app:** Strong fit. Single-language stack
simplifies running the whole thing as one packaged app for internal
production staff.

## Frontend: React + TypeScript + Vite

**Why:** Mature, huge ecosystem, strong typing story with TypeScript, fast
dev loop with Vite. The UI needs are moderate (upload, job list/status,
before/after image compare, review queue) — nothing exotic — so a
mainstream, well-supported stack minimizes risk and hiring/onboarding
friction.

**Alternatives considered:**
- *Vue 3*: equally capable, smaller hiring pool for an internal tool that
  may eventually need external contributors.
- *Svelte/SvelteKit*: smaller bundle, less boilerplate, but smaller
  ecosystem for image-comparison/upload components; higher risk for a
  production-grade internal tool that should be boring and maintainable.
- *Server-rendered templates (Jinja2) with light JS*: minimal build
  tooling, but the review/compare UI genuinely benefits from a component
  model and client-side state; would become unmaintainable as features
  grow.

**Tradeoffs:** React + build tooling is heavier than server-rendered HTML
for what is initially a simple internal tool. Accepted because the UI is
expected to grow (batch review queues, in-app vector touch-up editor on
the roadmap) and a component framework pays for itself quickly.

**Fit for internal desktop-first app:** Good fit; also directly reusable
inside an Electron/Tauri shell for desktop packaging with no rewrite.

## Job Queue / Broker: Redis + Celery (RQ as lightweight alternative)

**Why:** Decoupling the API from pipeline execution is non-negotiable
(pipeline runs take seconds to minutes; HTTP requests must return fast).
Celery is the most mature, battle-tested Python task queue, with built-in
retries, rate limiting, and multi-queue routing (useful later to route
GPU-bound stages to GPU workers). Redis is a simple, well-understood
broker with minimal operational overhead — a single `redis-server` process
suffices for Phase 1.

**Alternatives considered:**
- *RQ (Redis Queue)*: simpler API, less operational surface, but fewer
  features (no built-in complex routing/rate limiting). A reasonable
  **downgrade path for an even simpler internal deployment** — noted as
  the "if Celery feels like overkill" option.
- *In-process background threads/asyncio tasks, no broker at all*:
  simplest possible Phase 1 (no Redis dependency), but doesn't survive
  process restarts, can't scale to multiple workers, and is a dead end for
  batch processing and SaaS. Rejected because it would need to be replaced
  entirely later — better to pay the small Redis setup cost now.
- *Cloud-managed queues (SQS, etc.)*: wrong fit for a local-first internal
  tool; adds a network dependency the tool shouldn't need.

**Tradeoffs:** Adds an operational dependency (Redis) to what could
otherwise be a single process. Accepted because it's a very light, well
understood dependency, and is a prerequisite for the batch-processing and
scaling milestones on the roadmap.

**Fit for internal desktop-first app:** Redis + a worker process can be
bundled/launched alongside the desktop app (e.g. via a bundled Redis
binary or `redis-server` shipped as a sidecar), so this doesn't block
desktop packaging — noted as a specific risk to validate early (see
`RISKS.md`).

## Database: SQLite (Phase 1 default) via SQLAlchemy + Alembic, Postgres-ready

**Why:** Phase 1 is a single-machine internal tool — SQLite requires zero
setup, is embedded (no separate DB server for a desktop-first product), and
is more than capable of the write volume of an internal pre-press tool.
Using SQLAlchemy as the ORM and Alembic for migrations means the *only*
thing that changes to move to Postgres later is a connection string plus
enabling a couple of Postgres-specific column types (e.g. JSONB vs JSON) —
the schema and application code are written to be dialect-agnostic from day
one.

**Alternatives considered:**
- *Postgres from day one*: better fit for eventual SaaS multi-tenancy and
  concurrent writers, but adds a server process to install/manage for a
  Phase 1 internal/desktop tool where that's pure friction with no near-term
  payoff.
- *No SQL DB at all, just JSON files on disk*: tempting for a "just a
  script" mentality, but job querying/filtering (status, date, preset)
  and referential integrity (job → files → stage runs) get painful fast
  without a real query engine.

**Tradeoffs:** SQLite has limited concurrent-write throughput (single
writer at a time) — a real constraint once there are multiple worker
processes hammering the DB simultaneously in the SaaS phase. This is the
**one component explicitly flagged to be swapped before any multi-user
production/SaaS deployment** (see `PRODUCT_DECISIONS.md` and `RISKS.md`).

**Fit for internal desktop-first app:** Excellent fit — zero-install,
single-file database that can even ship inside a desktop package.

## Object/Artifact Storage: Local Disk (Phase 1) behind an S3-compatible interface

**Why:** Phase 1 has one machine and no need for a separate object store.
But every stage's input/output is written through a `StorageBackend`
interface with two implementations (`LocalDiskBackend`,
`S3CompatibleBackend`), so switching to MinIO (self-hosted) or AWS S3 later
is a configuration change.

**Alternatives considered:**
- *MinIO from day one*: gives S3-API parity immediately, but is an extra
  service to run locally for no immediate benefit in a single-machine
  deployment.
- *Direct AWS S3 from day one*: wrong fit for an offline-capable, local-
  first internal/desktop tool — introduces a hard network/cloud dependency
  and cost from the start.

**Tradeoffs:** Local disk storage needs its own backup/retention story
(disk fills up with intermediate artifacts) — addressed with a retention
policy (see `DATABASE.md`/ops notes), not a technology choice.

**Fit for internal desktop-first app:** Ideal — files live next to the app,
easy to inspect/debug, no network dependency.

## Image Processing / Enhancement: OpenCV + Real-ESRGAN (optional GPU)

**Why:** OpenCV is the standard, mature toolkit for deskew, denoise,
contrast/white-balance normalization, and general raster preprocessing —
fast, CPU-friendly, no GPU required for these operations. Real-ESRGAN
(open-source, permissively licensed, ONNX-exportable) is used specifically
for the "customer sent a tiny/blurry image" case where genuine
super-resolution upscaling is needed before tracing; it runs acceptably on
CPU for occasional use and benefits from GPU if available, but is not
required for every job (Analysis stage decides when to invoke it).

**Alternatives considered:**
- *PIL/Pillow only*: fine for basic resize/format conversion, but lacks the
  deskew/denoise/adaptive-threshold primitives OpenCV provides.
- *Commercial upscalers (Topaz Gigapixel, etc.)*: often higher quality, but
  paid, closed-source, and harder to automate/bundle — kept as a **future
  pluggable alternative** behind the same stage interface, not a Phase 1
  dependency.

**Tradeoffs:** GPU-accelerated super-resolution meaningfully improves
quality/speed but requires CUDA/GPU availability, which an internal
workstation may not have. The stage is designed to fall back to a
CPU-only classical upscaler (e.g. Lanczos + sharpening) when no GPU/ONNX
runtime is available, trading quality for universality.

**Fit for internal desktop-first app:** Good — CPU fallback keeps it usable
on any staff workstation; GPU is an optional speed/quality upgrade, not a
requirement.

## Background Removal: `rembg` (U²-Net / ISNet models via ONNX)

**Why:** `rembg` is open-source, actively maintained, ships pre-trained
ONNX models (no training required), runs on CPU (slower) or GPU, and
handles the common cases well (product photos, logos on varied
backgrounds, people/apparel shots). It's the pragmatic default for "remove
the background before tracing."

**Alternatives considered:**
- *Meta Segment Anything (SAM)*: higher quality, better on ambiguous/complex
  subjects, but heavier (larger model, more compute) and needs a prompt
  (point/box) for best results — better suited as an **opt-in high-quality
  mode or human-assisted correction tool** than the default fast path.
  Registered as an alternative implementation behind the same interface.
- *Commercial API (remove.bg)*: excellent quality, zero local compute, but
  a paid, network-dependent, per-image-cost external service — wrong
  default for an internal/offline-capable tool, but plugged in as an
  optional preset for operators who prioritize quality over cost/latency.
- *Classical approaches (GrabCut, chroma key)*: free, fast, no ML model
  needed, but fail badly on complex/non-uniform backgrounds — kept as a
  fast fallback for simple, near-flat backgrounds (e.g. plain studio shots)
  when Analysis detects a low-complexity background.

**Tradeoffs:** ONNX model file adds to bundle size (tens of MB) and cold-
start load time; acceptable for the quality gain.

**Fit for internal desktop-first app:** Good — CPU inference is slow-ish
(a few seconds per image) but acceptable for the "few images at a time"
internal use case; batch mode benefits from GPU if available.

## Vectorization: VTracer (primary) + Potrace (line-art fallback)

**Why:** VTracer (Rust, MIT license, available as a CLI and with Python
bindings) supports full-color image vectorization via clustering + contour
tracing, which is exactly the "photo/complex-color artwork → SVG" case
PrintVector needs, and produces reasonably clean, editable paths. Potrace
is the decades-proven standard for pure black/white or flat line-art
tracing (logos that are already single-color) and is faster/cleaner than
a color tracer would be for that specific case.

**Alternatives considered:**
- *Inkscape's built-in Trace Bitmap (CLI-automatable)*: capable, but
  automating Inkscape via CLI is comparatively brittle (GUI-app-as-CLI-tool
  smell) and heavier to bundle than a purpose-built library.
- *Commercial vectorization APIs (Vector Magic)*: often the best raw
  quality on hard cases, but paid, network-dependent, and closed — kept as
  a **pluggable premium option**, not the default, for the same reasons as
  the commercial background-removal API above.
- *Hand-rolled contour tracing (custom OpenCV contours + Bezier fit)*:
  full control, but reinvents a well-solved problem — not justified versus
  mature libraries.

**Tradeoffs:** Automatic tracing of complex photographic content never
perfectly matches a skilled human vectorization artist on very intricate
images — this is exactly why Print Validation + a "needs review" queue
exist rather than promising 100% automation.

**Fit for internal desktop-first app:** Strong fit — both are lightweight,
CPU-only, no external service or GPU required, easy to bundle in a desktop
package.

## SVG Post-Processing: SVGO

**Why:** SVGO is the de facto standard SVG optimizer/minifier (remove
redundant nodes, simplify paths, strip metadata) with a plugin system of
its own, mirroring PrintVector's own plugin philosophy. It's Node-based;
Phase 1 bundles a Node runtime (or a WASM build) specifically for this
stage, isolated behind the same `Stage` interface as everything else so
it's an implementation detail, not an architectural exception.

**Alternatives considered:**
- *`scour` (Python SVG optimizer)*: keeps everything in one language
  (avoids bundling Node), less actively maintained and less capable than
  SVGO on complex path simplification. **Candidate default if avoiding a
  Node dependency proves worth the tradeoff** — call this out explicitly in
  `PRODUCT_DECISIONS.md` as a decision to revisit.
- *Custom path-simplification code (Ramer–Douglas–Peucker only)*: partial
  solution, doesn't address the many other cleanup concerns SVGO handles
  (redundant groups, unused defs, precision rounding).

**Tradeoffs:** Introduces a second language runtime dependency (Node) into
an otherwise Python stack, which slightly complicates desktop packaging.
Mitigated by treating it as an isolated, swappable stage — `scour` is a
documented drop-in alternative if this becomes a real packaging pain
point.

**Fit for internal desktop-first app:** Acceptable — Node is easy to bundle
alongside Python (both are common in desktop app tooling like
Electron/Tauri); flagged as a specific integration risk to validate early.

## Desktop Packaging: Tauri (Rust shell) with a bundled Python backend, evaluated against Electron

**Why (leaning Tauri):** Tauri produces much smaller, more secure desktop
binaries than Electron (no bundled Chromium+Node runtime for the shell
itself) while still hosting the React frontend. The Python backend runs as
a bundled sidecar process (packaged via PyInstaller) that Tauri launches
and manages.

**Alternatives considered:**
- *Electron*: much simpler to bundle a Python subprocess and Node tooling
  (SVGO) alongside it, larger existing community/tooling maturity, but
  ships a full Chromium + Node runtime per app (~150MB+ baseline) and has a
  larger historical security-footgun surface.
- *PyInstaller + native GUI (PyQt/PySide) instead of a web frontend*: avoids
  bundling a browser runtime at all, but throws away the React UI investment
  and is a worse fit for a team more comfortable in web technologies.

**Tradeoffs:** Tauri's Rust toolchain and sidecar-process model are less
battle-tested for "bundle a Python ML backend" than Electron's ecosystem;
this is explicitly the highest-uncertainty packaging decision in the
project and is deferred to the Desktop Packaging milestone (not committed
now) — see `ROADMAP.md` and `RISKS.md`. **Decision is provisional**:
Phase 1–3 development targets a browser-based internal web app first,
so this choice can be made later with more information and doesn't block
early milestones.

**Fit for internal desktop-first app:** This is precisely the milestone
this decision serves; early phases run as a normal local web app (browser
pointed at `localhost`), which is itself a perfectly valid "desktop-first"
internal deployment and de-risks the packaging decision by deferring it.

## Testing: pytest, Playwright (UI), pixel/structural diff libraries

**Why:** pytest is the standard for Python unit/integration testing with a
mature fixture and parametrization model well suited to "run this stage
against N golden images" regression tests. Playwright covers UI smoke
tests (upload → job appears → status updates). `scikit-image` (SSIM) and
perceptual hashing are used for image regression comparisons rather than
brittle byte-for-byte diffs (see `TESTING.md`).

**Alternatives considered:** unittest (stdlib, less ergonomic
parametrization/fixtures than pytest); Cypress (comparable to Playwright,
slightly weaker cross-browser story) — no strong reason to deviate from
the mainstream pytest/Playwright pairing.

**Tradeoffs:** None significant; low-risk, high-consensus choice.

**Fit for internal desktop-first app:** Straightforward fit.

## Summary Table

| Concern | Choice | Key Alternative | Why Chosen |
|---|---|---|---|
| Backend | Python + FastAPI | Node + Python sidecar | Single-language stack matches AI/CV ecosystem |
| Frontend | React + TS + Vite | Vue, Svelte | Mainstream, low hiring/maintenance risk |
| Queue | Redis + Celery | RQ, in-process asyncio | Mature, supports batch + future scale |
| Database | SQLite → Postgres-ready | Postgres day 1 | Zero-install for desktop-first Phase 1 |
| Storage | Local disk → S3-compatible | MinIO/S3 day 1 | No network dependency needed yet |
| Enhancement | OpenCV + Real-ESRGAN | Commercial upscalers | Open-source, CPU-capable fallback |
| Background removal | rembg | SAM, remove.bg | Best default cost/quality/offline balance |
| Vectorization | VTracer + Potrace | Vector Magic API | Open-source, offline, covers color + line art |
| SVG cleanup | SVGO | scour | Best-in-class simplification, plugin-aligned |
| Desktop packaging | Tauri (provisional) | Electron | Smaller/safer, deferred decision |
| Testing | pytest + Playwright | unittest, Cypress | Mainstream, low risk |
