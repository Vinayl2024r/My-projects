# PrintVector AI — Critical Architecture Review

This is the mandatory critical self-review of the design in
`ARCHITECTURE.md`, `TECH_STACK.md`, `DATABASE.md`, `AI_PIPELINE.md`, and
`PRODUCT_DECISIONS.md`, performed before any implementation begins. Its
purpose is to surface weaknesses honestly rather than restate the design's
own rationale. Several items here duplicate entries in `RISKS.md`
deliberately — this document is the design-review lens on the same
concerns, `RISKS.md` is the ongoing risk register.

## Potential Bottlenecks

1. **SQLite as a single-writer database.** Already flagged (ADR-002,
   Risk 3) as the single biggest structural bottleneck — fine for Phase 1,
   a hard blocker for any concurrent multi-writer deployment. The main
   danger isn't the limitation itself, it's the possibility that it gets
   discovered under production load rather than caught by the pre-agreed
   migration trigger. **Recommendation:** treat the Postgres migration
   path as something exercised (even just once, in a load test) well
   before Milestone 11, not something designed on paper and never run.

2. **GPU-dependent stages on CPU-only hardware.** Super-resolution
   upscaling and SAM-based background removal are the two stages most
   likely to become the pipeline's real latency bottleneck on typical
   internal workstations without a GPU. The CPU fallback exists but its
   *actual* latency under real load is currently an estimate, not a
   measurement. **Recommendation:** get real numbers from Milestone 4/5
   performance testing early — if CPU fallback latency badly misses the
   <3-minute median target, that's a scope/expectation problem to raise
   immediately, not something to discover post-launch.

3. **Sequential stage execution with no intra-job parallelism.** Because
   the Orchestrator is deliberately linear (ADR-006), a job's total
   latency is the sum of every stage's latency — there's no
   parallelization even where it might be safe (e.g. computing multiple
   candidate vectorization strategies concurrently). This is the right
   call for Phase 1 simplicity, but it does mean total latency scales
   directly with stage count as more stages get added over time.
   **Recommendation:** watch total pipeline latency as a trend across
   milestones, not just per-stage; don't let "just add one more stage"
   erode the overall time budget without deliberate tradeoff discussion.

4. **Subprocess-based stages (SVGO) as a throughput ceiling.** Shelling out
   to a Node process per job adds process-spawn overhead that a
   pure-in-process library call wouldn't have. Likely negligible at
   internal-tool volume, but worth watching if batch processing
   (Milestone 9) pushes throughput expectations up significantly.

## Technical Debt Risks

1. **Two vectorization backends (ADR-008) are two things to maintain,
   test, and keep in sync with the regression suite** — every benchmark
   category split (line-art vs. photographic) effectively doubles the
   "does this still work after a dependency bump" surface. Accepted
   deliberately, but worth naming explicitly as ongoing maintenance cost,
   not a one-time complexity tax.

2. **The Node.js dependency for SVGO (ADR-009) is the single most
   likely-to-be-revisited decision in the stack.** It's already flagged
   with a documented fallback (`scour`), which is good practice — but if
   it does get revisited during Milestone 10, that's effectively rework
   of a Milestone 7 decision. **Recommendation:** if there's any early
   signal during Milestone 7 that packaging Node alongside Python is
   painful, make the `scour` swap *then*, not after building a whole
   desktop installer around the two-runtime assumption.

3. **Confidence score aggregation logic is underspecified.** The design
   documents state that per-stage `confidence_score` values are
   "aggregated (weighted, configurable)" into a job-level score, but the
   actual weighting scheme, thresholds, and how they map to
   `needs_review` are left as an implementation detail. This is the
   single highest-leverage piece of business logic in the whole system
   (it's the difference between "the tool works" and "the tool is
   trusted") and currently has the least design rigor behind it.
   **Recommendation:** before Milestone 8, write a short focused design
   note (or expand `AI_PIPELINE.md`) on the actual aggregation formula
   and calibrate initial thresholds against the benchmark dataset's
   known-good/known-bad fixtures — don't leave this to be improvised
   during implementation.

4. **`result_metadata`/`params` as loosely-typed JSON columns
   (`DATABASE.md`)** trade schema flexibility (easy to add new stage
   metadata without a migration) for weaker guarantees (no DB-level
   validation that a given stage's metadata has the shape callers expect).
   This is a reasonable and common tradeoff for this kind of
   heterogeneous, evolving data, but it does mean correctness here relies
   entirely on each stage's Pydantic schema discipline at the application
   layer — worth an explicit test-coverage expectation (every stage's
   `result_metadata` shape has a schema test) rather than assuming
   "it's JSON, anything goes" by default.

## Performance Concerns

1. **Storing every intermediate artifact (ADR-004) multiplies I/O and
   storage load per job**, and this cost is paid on every job, including
   the easy majority that don't need debugging. The retention-policy
   mitigation is named but not designed in detail (what exactly gets
   purged, on what schedule, is it automatic or manual). **Recommendation:**
   don't let "we'll add a retention policy later" linger past Milestone 8
   — disk pressure from artifact accumulation is one of the more
   boring-but-real risks of running this as a long-lived internal tool.

2. **Regression suite runtime growing unbounded.** The benchmark dataset
   is explicitly meant to grow continuously (`TESTING.md`, Risk 7). A
   nightly full-suite run is fine, but if it's ever needed synchronously
   (e.g. blocking a model-promotion decision under time pressure), suite
   runtime becomes a real friction point as the dataset grows. Worth
   deciding now whether the "fast subset" that runs per-PR needs a
   deliberate curation policy (representative sample, not just "the first
   N fixtures") so it stays meaningful as the full set grows.

## Maintainability Issues

1. **The module-boundary enforcement ("stages can't import each other or
   the API layer") is described as convention plus import-linting in
   CI**, but the specific linting mechanism isn't designed yet. Boundaries
   that rely on convention alone tend to erode under deadline pressure.
   **Recommendation:** get the import-linting rule (e.g. `import-linter`
   or an equivalent architectural-boundary test) working in Milestone 1,
   before there's any code for it to be retrofitted onto.

2. **Preset stage-plan JSON (`DATABASE.md`) has no schema validation
   described beyond "validated against unknown stage_name/implementation"
   at creation time.** As presets grow more complex (conditional
   parameters, per-stage overrides), a hand-validated JSON blob risks
   becoming its own ad hoc mini-language without a real spec.
   **Recommendation:** keep preset stage-plans deliberately simple
   (ordered list + flat param dict, no conditionals/expressions) for as
   long as possible; if genuine conditional logic is ever needed within a
   preset, that's a signal to revisit ADR-006 rather than organically
   growing an expression language inside a JSON column.

## Opportunities for Simplification

1. **Reconsider whether Redis/Celery is needed at all for the single-user
   desktop-packaged deployment (Milestone 10).** The roadmap already flags
   this ("explicitly revisit whether Celery/Redis is even needed in
   single-user desktop deployments") — it's a real opportunity to cut a
   whole operational dependency (bundling/managing a Redis process inside
   a desktop installer is genuine complexity) in favor of a simple
   in-process background task runner for the single-user case, keeping
   Celery/Redis only for the eventual multi-user/SaaS deployment profile.
   This is worth deciding with a real prototype, not assumed either way.

2. **The `Stage` interface's generality may be more than Phase 1 actually
   exercises.** Only two capabilities (`vectorization`, `background_removal`)
   currently have multiple registered implementations; everything else is
   a single implementation behind an interface built for many. This is a
   deliberate, justified bet (the whole point of `AI_PIPELINE.md`'s Model
   Replacement Strategy), not scope creep — but it's worth naming plainly
   that the interface's value is *unrealized* until a second
   implementation actually gets built for capabilities like `analysis` or
   `svg_optimization`. If that never happens for a given stage, the
   abstraction cost for that one stage was net-negative. Acceptable
   insurance premium; worth acknowledging rather than assuming the
   abstraction is free.

3. **Twelve separate design documents is a lot of surface to keep
   internally consistent as the project evolves.** Once implementation
   begins, consider whether some of these (e.g. `TECH_STACK.md` and
   `PRODUCT_DECISIONS.md`, which overlap substantially) should be
   consolidated or whether `PRODUCT_DECISIONS.md` should simply become
   the single source of truth that the others link into, to avoid the
   same decision being explained (and potentially drifting) in two
   places.

## Overall Assessment

The design is sound for its stated goals: it correctly resists
premature multi-tenancy and premature workflow-engine generality while
leaving deliberate, cheap seams (nullable FKs, a plugin registry, a
storage interface) for the features it explicitly wants to add later. The
biggest genuine open risks are not architectural but **empirical**: actual
AI output quality on hard real-world images (Risk 1), actual CPU-fallback
performance (Risk 5/Bottleneck 2), and actual confidence-aggregation
calibration (Tech Debt 3) — none of these can be resolved by more design,
only by building the early milestones and measuring against the benchmark
dataset. The architecture review's main recommendation is therefore
procedural: **treat Milestones 3–8 as a measurement exercise as much as a
build exercise**, and be willing to revisit ADR-006 (orchestrator
generality), ADR-009 (SVGO/Node), and the SQLite migration timeline
(ADR-002) based on what those milestones actually show, rather than
treating any of them as settled until real data confirms them.

**This architecture is approved for implementation to begin at
Milestone 1**, with the explicit understanding that the items flagged
above under "Recommendation" are tracked as near-term follow-ups, not
deferred indefinitely.
