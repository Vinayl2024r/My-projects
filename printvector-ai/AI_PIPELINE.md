# PrintVector AI — AI Pipeline

This document details the AI/CV processing pipeline referenced at a high
level in `ARCHITECTURE.md`. It defines the stage contract, each stage's
responsibility, how the orchestrator decides which stages to run, and how
individual models get swapped over time without destabilizing the system.

## Design Contract: The `Stage` Interface

Every AI capability — regardless of which model or library implements it —
conforms to the same shape:

```
StageInput:
    primary_image: ImageHandle       # reference to a File row, lazily loadable
    job_context: JobContext          # job id, preset params, prior stage outputs
    params: dict                     # resolved parameters for this stage/preset

StageOutput:
    output_image: ImageHandle | None # the produced artifact, if any (some stages, e.g. validation, produce no image)
    result_metadata: dict            # structured, stage-specific findings (JSON-serializable)
    confidence_score: float          # 0.0-1.0, this stage's confidence in its own output
    warnings: list[str]              # non-fatal issues surfaced to the operator

Stage:
    name: str                        # capability key, e.g. "background_removal"
    implementation_id: str           # e.g. "rembg_remover", versioned as "rembg_remover@1.2.0"
    def run(input: StageInput) -> StageOutput
```

This contract is what allows the Orchestrator, the API, and the database
(`stage_runs.result_metadata`, `stage_runs.confidence_score`) to treat every
stage identically regardless of internal implementation — a hand-rolled
OpenCV heuristic and a deep-learning segmentation model look the same from
the outside.

## Processing Stages

### 1. Image Analysis
**Purpose:** Decide *what kind of problem this image is* before doing any
expensive processing, and produce the routing information the Orchestrator
uses to build the rest of the stage plan.

**Checks performed:**
- Resolution / estimated print DPI at likely target size.
- Blur/sharpness score (Laplacian variance or similar).
- Noise level and compression-artifact estimate (JPEG blockiness).
- Skew/rotation angle.
- Content classification: **flat vector-like line art** vs.
  **photographed physical object/logo** vs. **photo with complex
  background** vs. **screenshot** (UI chrome/borders likely present).
- Background complexity estimate (near-uniform vs. cluttered) — informs
  whether Background Removal is needed and which implementation to use.
- Dominant/approximate color count — informs Vectorization strategy
  (flat low-color vs. full-color/photographic).
- Text presence (rough OCR-free heuristic or lightweight text detector) —
  surfaced as a warning if text looks likely to need manual legibility
  review, since automated tracing of small text is a known weak point.

**Output feeds directly into:** which Enhancement operations run, whether
Background Removal runs and with which implementation, and which
Vectorization backend is selected.

**Confidence:** low confidence here (e.g. ambiguous content classification)
propagates forward as a lowered overall job confidence, increasing the
chance of landing in `needs_review` even if later stages succeed cleanly —
garbage routing decisions produce garbage output even from good stages.

### 2. Enhancement
**Purpose:** Clean up the raster image so downstream stages have the best
possible input.

**Operations (each individually toggleable based on Analysis output):**
- **Deskew**: rotate to correct detected skew (common in phone photos of
  printed material).
- **Denoise**: reduce sensor/JPEG noise without destroying edges needed
  for clean tracing.
- **Contrast/white-balance normalization**: correct uneven lighting/shadow
  common in phone photos.
- **Super-resolution upscaling**: invoked only when Analysis flags the
  image as low-resolution relative to the target print size; uses
  Real-ESRGAN when a suitable runtime/GPU is available, falling back to
  classical Lanczos+sharpen otherwise (see `TECH_STACK.md`).

**Output:** a cleaned raster image, plus metadata recording exactly which
operations ran (needed for both debugging and regression testing — a
regression test can assert "denoise ran" without asserting exact pixel
output, which would be too brittle).

### 3. Background Removal
**Purpose:** Isolate the subject (logo, product, artwork) from whatever is
behind it, producing a transparent-background raster ready for tracing.

**Conditional execution:** skipped entirely if Analysis classifies the
image as already-flat line art with no meaningful background (avoids
wasted compute and avoids a segmentation model introducing artifacts on an
image that didn't need it).

**Implementation selection:**
- Default: `rembg` (fast, good general quality).
- High-complexity backgrounds or low rembg confidence: escalate to the
  SAM-based implementation (slower, better on ambiguous edges) — either
  automatically when rembg's own confidence is low, or manually via the
  operator's `rerun-stage` override.
- Near-uniform simple background: classical chroma-key/GrabCut fallback
  (fast, no model, good enough for e.g. plain studio-shot product photos).

**Output:** RGBA image with background removed (or the original image,
untouched, when skipped — always explicit in `result_metadata`, never
ambiguous about whether removal happened).

### 4. Vectorization
**Purpose:** Convert the cleaned raster into actual vector paths — the
core value-delivering step.

**Strategy selection (from Analysis output):**
- **Flat, low-color, line-art content** (logos, simple graphics, already
  high-contrast): Potrace-based backend. Fast, produces very clean paths
  for this content type.
- **Full-color / photographic content**: VTracer backend — color
  quantization (reducing to a target color count suitable for the print
  method, e.g. screen printing wants few spot colors; direct-to-garment
  can handle more) followed by contour tracing per color layer.

**Key parameters (preset-driven, not hardcoded):** target color count,
corner threshold/smoothing aggressiveness, minimum feature size (avoid
paths so small they can't be cut/printed).

**Output:** raw SVG — functionally correct but not yet clean (may contain
redundant nodes, overlapping paths, more precision than needed).

### 5. SVG Optimization
**Purpose:** Turn the raw traced SVG into a clean, minimal, production-
quality SVG.

**Operations:** path simplification (reduce point count while preserving
shape within a tolerance), merging/removing redundant groups and defs,
numeric precision rounding, removing invisible/zero-area elements,
minification. Implemented via SVGO (see `TECH_STACK.md`).

**Output:** the optimized SVG that becomes (pending validation) the job's
final deliverable.

### 6. Print Validation
**Purpose:** Programmatically check the optimized SVG against
print-readiness rules before calling the job done, and produce the
confidence/warning signal that drives `completed` vs. `needs_review`.

**Checks:**
- Minimum stroke/feature width vs. the target print method's physical
  minimum (configurable per preset, e.g. embroidery has a much larger
  minimum feature size than digital print).
- Path count sanity (an absurdly high path count usually indicates a
  failed/noisy trace, not genuinely intricate art).
- Color count within the preset's target (e.g. flags if a "spot color"
  preset produced 40 colors).
- No embedded raster remnants (the output must be pure vector).
- Valid, well-formed SVG that opens cleanly (structural validation, not
  just XML well-formedness).
- Artboard/viewBox sanity (non-zero, reasonable aspect ratio vs. original).

**Output:** a structured validation report (pass/warn/fail per rule) plus
an overall confidence score. This stage produces no new image — it's the
pipeline's quality gate, not a transform.

## Pipeline Orchestration

The Orchestrator does **not** run a fixed, hardcoded stage sequence for
every job. It:

1. Always runs **Analysis** first.
2. Consults the job's **Preset** (`stage_plan`) to get the *candidate*
   ordered stage list and default parameters.
3. Applies **conditional skips** based on Analysis output (e.g. skip
   Background Removal for already-flat line art) — implemented as a
   predicate attached to each stage in the plan, not as special-cased
   orchestrator logic, so new conditional stages can be added without
   touching the orchestrator itself.
4. Executes remaining stages **in order**, persisting a `StageRun` row per
   execution (see `DATABASE.md`) before moving to the next.
5. Aggregates per-stage `confidence_score` values (weighted, configurable)
   into the job's overall `confidence_score`; if it's below the preset's
   threshold, or any stage produced a `warnings` entry marked as
   review-worthy, the job lands in `needs_review` instead of `completed`.
6. On any stage raising an unhandled error, the job moves to `failed` with
   the exception recorded — the Orchestrator does not attempt to "skip
   ahead" past a failed stage; a broken input to Vectorization means the
   job failed, not that it silently ships a blank SVG.
7. Supports **partial re-execution**: `POST /jobs/{id}/rerun-stage` re-enters
   the plan at a specific stage using its existing upstream outputs as
   input, re-running only that stage and everything downstream of it.

This is a straight-line pipeline with conditional skips, not a general
graph executor — deliberately. A full DAG-of-arbitrary-branches engine
would be over-engineering for a process that is, and is expected to
remain, fundamentally linear (analyze → clean → cut out → trace →
optimize → validate). If a genuinely branching/parallel need emerges
(e.g. running two vectorization strategies in parallel and picking the
better result), it should be added as a capability *within* the
Vectorization stage (an internal ensemble), not by generalizing the
Orchestrator — see `PRODUCT_DECISIONS.md`.

## Model Interfaces

Concretely, each stage package exposes:
- A **registration call** (executed at import time) that adds itself to
  the stage registry under its capability name and a unique
  `implementation_id`.
- A **pure function or small class** wrapping the actual model/library
  call, translating between the `StageInput`/`StageOutput` contract and
  whatever native format the underlying library needs (e.g. converting an
  `ImageHandle` to a `numpy` array for OpenCV, or to a `PIL.Image` for
  `rembg`).
- **No knowledge of the database, the API, or other stages.** A stage
  implementation can be unit tested by constructing a `StageInput` in
  memory and asserting on the `StageOutput` — no FastAPI app, no DB, no
  queue required.

## Model Replacement Strategy

This is the core promise of the plugin architecture applied to AI
specifically:

1. **Add, don't replace, at first.** A new/better model for a capability
   (e.g. a newer background-removal model) is added as a new
   `implementation_id` in that stage's package and registered alongside
   the existing one — it does not delete the old one.
2. **Evaluate against the regression benchmark** (see `TESTING.md`) before
   making it the default — the benchmark dataset and scoring harness let a
   new implementation be compared against the incumbent on the same fixed
   set of real-world-like images, quantitatively, before it touches
   production traffic.
3. **Flip the default via preset config**, not code changes elsewhere —
   presets reference an implementation by id (or leave it unset to use
   "current default"), so promoting a new model to default is a
   preset/registry config change.
4. **Keep the old implementation registered** for some period after a
   default flip, so historical jobs' `stage_runs.implementation` values
   remain meaningful and a `rerun-stage` against an old job can still use
   the implementation it originally used if needed for debugging/support.
5. **Retire deliberately**: an old implementation is only removed from the
   codebase once no active preset references it and enough time has passed
   that debugging old jobs against it is no longer a realistic need —
   recorded as a decision in `PRODUCT_DECISIONS.md` when it happens, not a
   silent deletion.

This strategy applies identically whether "a better model" means a newer
open-source checkpoint, a switch from open-source to a commercial API, or
eventually a custom-trained model specific to PrintVector's own accumulated
data — the interface doesn't care, which is the point.
