# PrintVector AI — Database Design

## Engine Strategy

Phase 1 default: **SQLite** (single file, zero setup, ideal for an internal
desktop-first tool). All access goes through SQLAlchemy models and Alembic
migrations written in a dialect-agnostic way (avoid SQLite- or
Postgres-only column types/features) so switching
`PRINTVECTOR_DB_URL` to a Postgres connection string is a config change,
not a schema rewrite. See `PRODUCT_DECISIONS.md` for the explicit tradeoff
and the trigger condition for migrating (more than one concurrent writer
process).

## Entity Overview

```
 Preset ───────────┐
                    │ (preset_id, nullable)
                    ▼
 Job ───────< StageRun >───── (references) ──── File (input/output per stage)
  │  \
  │   \___< Job.original_file_id, Job.final_output_file_id  (direct refs)
  │
  └──< File  (all files: original upload + every intermediate + final output)

 (future) Organization ──< User ──< Job     [added as nullable FKs later]
```

## Tables

### `jobs`

The unit of work: one customer image submitted for processing.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `status` | enum/text | `uploaded, queued, analyzing, processing, needs_review, completed, failed` |
| `preset_id` | UUID (FK → presets.id, nullable) | null = auto-detect / default preset |
| `original_file_id` | UUID (FK → files.id) | the raw uploaded file |
| `final_output_file_id` | UUID (FK → files.id, nullable) | set once completed |
| `confidence_score` | float, nullable | overall pipeline confidence, drives `needs_review` |
| `failure_reason` | text, nullable | populated on `failed` |
| `organization_id` | UUID, nullable | **future** multi-tenancy FK, unused/NULL in Phase 1 |
| `created_by_user_id` | UUID, nullable | **future** auth FK, unused/NULL in Phase 1 |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

Indexes: `status`, `created_at`, `(organization_id)` (future-ready, harmless
when always NULL today).

### `files`

Every physical artifact the system ever produces or ingests — originals,
intermediates, and final outputs — is one row here. This is what makes
full pipeline replay/debugging possible.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `job_id` | UUID (FK → jobs.id) | |
| `kind` | enum/text | `original, enhanced, background_removed, vector_raw, vector_optimized, print_validation_report, thumbnail` |
| `storage_backend` | text | `local`/`s3`, matches `StorageBackend` implementation used |
| `storage_key` | text | path or object key |
| `mime_type` | text | |
| `size_bytes` | integer | |
| `width_px` / `height_px` | integer, nullable | for raster kinds |
| `checksum_sha256` | text | for dedup/cache-key purposes and integrity checks |
| `created_at` | timestamp | |

Indexes: `job_id`, `(job_id, kind)`, `checksum_sha256` (supports the
content-addressed caching optimization noted in `ARCHITECTURE.md`).

### `stage_runs`

One row per execution of a pipeline stage for a job — the audit trail that
makes the pipeline inspectable and regression-testable.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `job_id` | UUID (FK → jobs.id) | |
| `stage_name` | text | registry capability key, e.g. `background_removal` |
| `implementation` | text | concrete plugin used, e.g. `rembg_remover@1.2.0` |
| `sequence_index` | integer | order within the job's executed plan |
| `input_file_id` | UUID (FK → files.id, nullable) | |
| `output_file_id` | UUID (FK → files.id, nullable) | |
| `params` | JSON | parameters passed to the stage (from preset + overrides) |
| `result_metadata` | JSON | stage-specific structured output (e.g. detected blur score, color count, validation warnings list) |
| `confidence_score` | float, nullable | stage-level confidence, rolled up into `jobs.confidence_score` |
| `status` | enum/text | `succeeded, failed, skipped` |
| `error_message` | text, nullable | |
| `duration_ms` | integer | for performance benchmarking (see `TESTING.md`) |
| `started_at` / `completed_at` | timestamp | |

Indexes: `job_id`, `(stage_name, implementation)` (supports model-version
regression comparisons over time).

### `presets`

Named, versioned pipeline configurations.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `name` | text | e.g. "Apparel logo — photo" |
| `slug` | text, unique | stable machine key, e.g. `apparel_logo` |
| `version` | integer | incremented on edit; historical jobs keep referencing the version they ran with |
| `stage_plan` | JSON | ordered list of `{stage_name, implementation?, params}` |
| `is_builtin` | boolean | seeded from `config/presets/*.yaml` vs. user-created |
| `created_at` / `updated_at` | timestamp | |

Because `stage_runs` and `jobs` reference a preset by id+version
semantics (or simply snapshot the resolved `stage_plan` onto the job at
creation time — see `PRODUCT_DECISIONS.md` for which was chosen and why),
editing a preset never silently changes the interpretation of a historical
job.

### (Future) `organizations`, `users`, `api_keys`, `subscriptions`

Not created in Phase 1. When SaaS work begins, these are added as new
tables plus nullable FK columns on existing tables
(`jobs.organization_id`, `jobs.created_by_user_id`) that get backfilled
with a single "default" organization/user for all Phase 1 historical data.
This is an additive migration, not a breaking one — see
`PRODUCT_DECISIONS.md`.

## Entity Relationships Summary

- One `Job` has exactly one `original_file` and at most one
  `final_output_file` (both `File` rows), plus **many** `File` rows overall
  (every intermediate).
- One `Job` has **many** `StageRun` rows (one per stage executed, including
  retries — a retried stage is a new `StageRun` row, not an overwrite, to
  preserve history).
- One `Preset` is referenced by **many** `Job`s (optional — a job may run
  without an explicit preset, using the auto-detected default).
- `StageRun.input_file_id`/`output_file_id` link stages together implicitly
  by file lineage (stage N's output file is stage N+1's input file),
  which is how a job's full processing graph can be reconstructed for
  display or debugging without a separate "edges" table.

## Migration Strategy

- **Tooling**: Alembic, one migration per meaningful schema change,
  generated via `alembic revision --autogenerate` and hand-reviewed
  (autogenerate is a starting point, not gospel — especially for enum/JSON
  columns which need manual attention across SQLite/Postgres).
- **Backward-compatible by default**: new columns are added nullable or
  with a server-side default; destructive changes (dropping/renaming a
  column, changing a type incompatibly) require a two-step migration
  (add new → backfill → dual-write period if needed → remove old) rather
  than a single breaking change, even in Phase 1, to build the habit before
  it's load-bearing in a live SaaS.
- **Seed data**: built-in presets are seeded idempotently from
  `config/presets/*.yaml` on startup/migration (upsert by `slug`), so
  editing a shipped YAML preset and redeploying updates the seeded row
  without duplicating it.
- **SQLite → Postgres cutover procedure** (documented, not automated,
  since it's a one-time event per deployment): export via
  `pg_loader`/custom script or simply re-run migrations against an empty
  Postgres DB and bulk-copy rows table by table (row counts are small —
  this is a pre-press tool, not a high-volume transactional system).
- **Testing migrations**: CI runs `alembic upgrade head` against a fresh
  SQLite DB (and, once Postgres is in play, a fresh Postgres container) on
  every PR that touches `db/orm_models.py` or `migrations/`, to catch
  dialect-specific breakage immediately rather than at deploy time.
