# PrintVector AI — Risks

Ranked roughly by (likelihood × impact). Each risk includes concrete
mitigation, and, where relevant, the earliest point it should be actively
validated rather than assumed away.

## 1. AI output quality on genuinely hard inputs (highest risk)

**Risk:** The whole premise — that a pipeline can turn bad customer photos
into print-ready vectors — has a real ceiling. Highly intricate
photographic content, heavily occluded subjects, or ambiguous line art may
never automate well, no matter which models are plugged in.

**Impact:** If the "needs zero manual touch-up" rate (target ≥40% per
`VISION.md`) doesn't materialize, the tool's core value proposition
weakens to "makes manual work slightly faster" rather than "automates
most of it."

**Mitigation:** The architecture never pretends this away — `needs_review`
is a first-class, expected outcome, not a failure mode. Success is
measured honestly against the benchmark dataset from Milestone 3 onward,
so the real automation rate is known early (Milestone 6-8), not
discovered late. If rates are poor, the fallback value (faster manual
workflow, consistent tooling, artifact history) still justifies the tool,
but expectations should be reset early and explicitly with stakeholders
rather than over-promised.

**Validate by:** end of Milestone 8, using real accumulated internal job
data, not just the synthetic benchmark set.

## 2. Background removal quality on complex/ambiguous scenes

**Risk:** `rembg`'s default models handle common product-photo scenarios
well but can fail on cluttered, low-contrast, or unusual subjects (e.g. a
logo embroidered on textured fabric, photographed at an angle).

**Impact:** Bad background removal cascades into bad vectorization —
errors compound downstream rather than staying contained.

**Mitigation:** Confidence-based escalation to a SAM-based implementation
(higher quality, higher cost) is designed in from Milestone 5; Print
Validation and the confidence-aggregation logic are specifically meant to
catch this class of failure and route to `needs_review` rather than
silently shipping a bad trace.

**Validate by:** Milestone 5, against benchmark fixtures specifically
chosen to stress this (textured backgrounds, low contrast subject/
background).

## 3. SQLite single-writer limitation becoming load-bearing before it's swapped

**Risk:** If Milestone 11 (SaaS) work begins under time pressure and the
Postgres migration (ADR-002) is skipped or rushed, concurrent-writer
contention could cause real production issues (write locking, timeouts)
under multi-user load.

**Impact:** Data integrity/availability issues in a production multi-user
deployment — the most severe class of risk on this list because it's a
correctness issue, not just a quality one.

**Mitigation:** The trigger condition is explicit and pre-agreed (ADR-002:
migrate the moment there's more than one concurrent writer process) —
this is a go/no-go gate for Milestone 11, not a "nice to have," and the
dialect-agnostic schema/query discipline from day one keeps the actual
migration mechanically simple when the time comes.

**Validate by:** load-testing the Postgres migration path *before*
Milestone 11 begins, not during it.

## 4. Node.js (SVGO) + Python + (eventually) Rust/Tauri packaging friction

**Risk:** Bundling three language runtimes (Python backend, Node for
SVGO, Rust/Tauri shell) into one desktop installer is more integration
work than it sounds, and could blow up Milestone 10's timeline or produce
a bloated/fragile installer.

**Impact:** Desktop packaging milestone slips or ships with rough edges
(slow startup, large install size, platform-specific bugs).

**Mitigation:** ADR-009 already flags `scour` (pure Python) as a fallback
for SVGO if this proves painful; ADR-010 defers the Tauri-vs-Electron
decision to a dedicated spike right before the milestone, specifically so
this risk is assessed with real prototype data instead of assumed away in
planning. Worst case, ship Milestone 10 as Electron (heavier but more
proven for exactly this "bundle Python via subprocess" pattern) rather
than slip further chasing the smaller Tauri bundle.

**Validate by:** the Milestone 10 pre-spike, explicitly before committing
engineering time to the full packaging build.

## 5. GPU availability variance across internal workstations

**Risk:** Super-resolution upscaling and (if escalated) SAM-based
background removal benefit significantly from a GPU; internal production
workstations may be CPU-only, making these stages slow or forcing the
CPU-fallback path to carry more real-world load than anticipated.

**Impact:** Slower-than-targeted latency (`VISION.md`'s <3 minute median
target) for a meaningful fraction of real jobs; inconsistent experience
depending on which machine a job runs on.

**Mitigation:** CPU fallbacks are a designed-in requirement for every
GPU-beneficial stage (Real-ESRGAN → classical upscale, rembg → still
CPU-capable, just slower), not an afterthought; queue-based worker
architecture allows routing GPU-heavy stages to a dedicated GPU-equipped
worker if/when one is available, without changing application code.

**Validate by:** Milestone 4/5 performance testing on representative
non-GPU hardware, not just a developer's GPU-equipped workstation.

## 6. Untrusted file content vulnerabilities in third-party parsing libraries

**Risk:** OpenCV, Pillow, PDF parsers, and ONNX runtimes are complex C/C++
codebases with a real history of parser vulnerabilities (crashes, memory
corruption) when fed malformed/hostile input — and customer-sourced files
are exactly that kind of untrusted input, per `SECURITY.md`'s threat
model.

**Impact:** Worker crashes/hangs (availability impact) or, in a worse
case, a genuine exploit if an unpatched CVE in a bundled library is hit by
a crafted file.

**Mitigation:** Defense in depth already designed in (`SECURITY.md`):
content-sniffed type validation, decompression-bomb size limits before
full decode, processing confined to isolated worker processes (a crash
takes down one task, not the API), and automated dependency updates with
CI gating. This is an ongoing operational risk, not a one-time fix —
requires continued vigilance on dependency freshness.

**Validate by:** ongoing (Dependabot/equivalent wired in at Milestone 1;
periodic fuzz-testing of the upload/analysis path is a reasonable
addition once the pipeline is stable, flagged here as a candidate for
`TESTING.md` expansion).

## 7. Benchmark dataset becoming stale or unrepresentative

**Risk:** If the regression benchmark set (`TESTING.md`) isn't
continuously grown from real production `needs_review`/bug-report cases,
it risks measuring "does the model still pass the same fixed quiz" rather
than "does it handle what customers actually send" — a classic regression
suite staleness failure mode.

**Impact:** False confidence when promoting a new model implementation to
default (ADR/`AI_PIPELINE.md` model replacement strategy) — a model could
pass the benchmark and still regress on real traffic patterns the
benchmark doesn't cover.

**Mitigation:** Explicit process (already stated in `TESTING.md`): any
significant `needs_review` correction or bug report is a candidate for
anonymized addition to the benchmark set. This needs to actually happen
as a habit, not just exist as a documented intention — worth a periodic
(e.g. monthly) explicit review as a process safeguard, not just a
one-time setup task.

**Validate by:** ongoing; first real test of this discipline is whatever
the first model-swap decision after Milestone 8 turns out to be.

## 8. Scope creep from "internal tool" into premature SaaS complexity

**Risk:** Given the explicit future SaaS ambition, there's a natural
temptation to over-build multi-tenancy, billing hooks, or generic
workflow abstractions "since we'll need them eventually," slowing down
Phase 1 delivery for speculative future needs.

**Impact:** Slower time-to-value for the actual, immediate internal-tool
goal; more surface area to maintain before it's earning its keep.

**Mitigation:** This is exactly what `PRODUCT_DECISIONS.md` ADR-006 and
the "no premature abstraction" principle in `PROJECT_STRUCTURE.md` guard
against — multi-tenancy fields are nullable placeholders (cheap), not
built-out multi-tenant logic (expensive); the Orchestrator stays a linear
pipeline, not a general workflow engine, until a concrete need proves
otherwise. Ongoing discipline required from whoever leads implementation:
resist building Milestone 11 features during Milestones 1-9.

**Validate by:** every PR/design review during Milestones 1-9 — this is a
process risk, not a one-time check.

## 9. Operator trust / adoption risk (non-technical)

**Risk:** Even a technically successful pipeline fails if production
staff don't trust or adopt it — e.g. if the review queue UI is more
friction than just redrawing in Illustrator, or if `needs_review` volume
feels overwhelming rather than helpful.

**Impact:** Low internal adoption undermines the Phase 1 success metrics
regardless of underlying model quality.

**Mitigation:** Before/after comparison UI (Milestone 4) and a genuinely
fast, low-friction review queue (Milestone 8) are treated as first-class
product surfaces, not afterthoughts bolted onto an API; early and
continuous feedback from actual pre-press staff during Milestones 4-8 is
the real mitigation, not a purely technical one.

**Validate by:** informal usability check-ins with actual internal
production staff starting at Milestone 4, not deferred to a "launch"
event at the end.

## 10. Dependency on actively-maintained but small open-source projects

**Risk:** VTracer, rembg, and similar smaller open-source projects (vs.
e.g. OpenCV's institutional backing) carry higher abandonment/maintenance
risk than mainstream dependencies.

**Impact:** A stalled upstream project could leave a stage implementation
without security patches or improvements over time.

**Mitigation:** This is precisely why the plugin/`Stage` interface and
Model Replacement Strategy (`AI_PIPELINE.md`) exist — no single stage
implementation is a permanent commitment; a stalled dependency is a
"swap the implementation" problem, not an architectural crisis, provided
the benchmark-driven promotion process (see Risk 7) is kept alive as an
ongoing practice rather than a one-time launch activity.

**Validate by:** periodic (e.g. quarterly) dependency health review once
Phase 1 is in real production use.
