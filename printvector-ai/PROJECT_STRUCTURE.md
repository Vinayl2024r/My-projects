# PrintVector AI — Project Structure

## Complete Folder Structure

```
printvector-ai/
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/                      # Alembic migration scripts
│   │   └── versions/
│   ├── printvector/
│   │   ├── __init__.py
│   │   ├── core/                        # Domain models, state machine, pure business logic
│   │   │   ├── __init__.py
│   │   │   ├── models.py                # Domain dataclasses (not ORM models)
│   │   │   ├── job_states.py            # Job state machine + valid transitions
│   │   │   ├── errors.py                # Domain-level exception types
│   │   │   └── validation_rules.py      # Print-readiness rule definitions
│   │   ├── db/                          # Persistence layer
│   │   │   ├── __init__.py
│   │   │   ├── session.py               # Engine/session management (SQLite/Postgres)
│   │   │   ├── orm_models.py            # SQLAlchemy ORM models
│   │   │   └── repositories/            # Repository pattern per aggregate
│   │   │       ├── jobs.py
│   │   │       ├── files.py
│   │   │       ├── stage_runs.py
│   │   │       └── presets.py
│   │   ├── api/                         # FastAPI app
│   │   │   ├── __init__.py
│   │   │   ├── main.py                  # App factory, middleware wiring
│   │   │   ├── deps.py                  # Dependency-injected services
│   │   │   ├── auth_stub.py             # No-op auth middleware slot (Phase 1)
│   │   │   ├── schemas/                 # Pydantic request/response models
│   │   │   │   ├── jobs.py
│   │   │   │   ├── files.py
│   │   │   │   └── presets.py
│   │   │   └── routes/
│   │   │       ├── jobs.py
│   │   │       ├── files.py
│   │   │       ├── presets.py
│   │   │       └── health.py
│   │   ├── services/                    # Application services
│   │   │   ├── job_service.py
│   │   │   ├── storage/
│   │   │   │   ├── base.py              # StorageBackend interface
│   │   │   │   ├── local_disk.py
│   │   │   │   └── s3_compatible.py
│   │   │   └── preset_service.py
│   │   ├── pipeline/                    # Orchestration engine (framework, no ML code)
│   │   │   ├── __init__.py
│   │   │   ├── stage.py                 # Stage Protocol/ABC + StageInput/StageOutput
│   │   │   ├── registry.py              # Capability -> implementation registry
│   │   │   ├── orchestrator.py          # DAG execution, branching, persistence hooks
│   │   │   └── pipeline_config.py       # Preset -> ordered stage plan resolution
│   │   ├── stages/                      # One package per AI capability (plugins)
│   │   │   ├── analysis/
│   │   │   │   ├── __init__.py          # Registers "analysis" capability
│   │   │   │   ├── heuristics.py        # Blur/noise/resolution/background heuristics
│   │   │   │   └── classifier.py        # Photo-vs-line-art classification
│   │   │   ├── enhancement/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── deskew.py
│   │   │   │   ├── denoise.py
│   │   │   │   └── upscale.py           # Real-ESRGAN + classical fallback
│   │   │   ├── background_removal/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── rembg_remover.py     # Default implementation
│   │   │   │   ├── sam_remover.py       # Opt-in high-quality implementation
│   │   │   │   └── chroma_key.py        # Classical fallback for simple backgrounds
│   │   │   ├── vectorization/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── vtracer_backend.py   # Color vectorization
│   │   │   │   └── potrace_backend.py   # Line-art / B&W vectorization
│   │   │   ├── svg_optimization/
│   │   │   │   ├── __init__.py
│   │   │   │   └── svgo_runner.py       # Subprocess wrapper around SVGO
│   │   │   └── print_validation/
│   │   │       ├── __init__.py
│   │   │       └── rules.py             # Stroke width, color count, bleed checks
│   │   ├── workers/                     # Celery app + task entry points
│   │   │   ├── celery_app.py
│   │   │   └── tasks.py
│   │   └── config/
│   │       ├── settings.py              # Pydantic Settings (env-driven)
│   │       └── presets/                 # Built-in preset YAML definitions
│   │           ├── apparel_logo.yaml
│   │           ├── signage_line_art.yaml
│   │           └── embroidery_prep.yaml
│   └── tests/
│       ├── unit/                        # Mirrors printvector/ package structure
│       │   ├── core/
│       │   ├── pipeline/
│       │   └── stages/
│       ├── integration/                 # Full pipeline, API + DB
│       ├── regression/                  # Golden-image benchmark suite
│       │   └── fixtures/                # Curated benchmark dataset (see TESTING.md)
│       └── conftest.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.tsx
│   │   ├── app/                         # Routing, layout shell
│   │   ├── features/
│   │   │   ├── upload/
│   │   │   ├── job-status/
│   │   │   ├── review-queue/
│   │   │   └── presets/
│   │   ├── components/                  # Shared/dumb UI components
│   │   ├── api-client/                  # Generated/typed client from OpenAPI spec
│   │   ├── hooks/
│   │   └── styles/
│   └── tests/
│       ├── unit/
│       └── e2e/                         # Playwright specs
│
├── desktop/                              # Desktop packaging shell (later milestone)
│   ├── tauri.conf.json (or electron equivalent)
│   └── sidecar/                          # Bundled backend build scripts
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.worker
│   │   └── docker-compose.yml            # api + worker + redis (+ postgres for SaaS profile)
│   └── scripts/
│       ├── setup_dev.sh
│       └── seed_benchmark_dataset.py
│
├── docs/                                  # This design documentation set
│   ├── VISION.md
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md
│   ├── PROJECT_STRUCTURE.md
│   ├── DATABASE.md
│   ├── API_SPEC.md
│   ├── AI_PIPELINE.md
│   ├── SECURITY.md
│   ├── TESTING.md
│   ├── ROADMAP.md
│   ├── PRODUCT_DECISIONS.md
│   └── RISKS.md
│
├── .github/ (or CI config equivalent)
│   └── workflows/
│       ├── backend-ci.yml
│       └── frontend-ci.yml
├── .env.example
└── README.md
```

Note: this document (`docs/`) currently lives at the repository location
where it was authored; when implementation begins, it should be moved into
`printvector-ai/docs/` as shown above so the design docs travel with the
codebase they describe.

## Naming Conventions

- **Python**: `snake_case` for modules/functions/variables, `PascalCase`
  for classes, `UPPER_SNAKE_CASE` for constants. Module names match their
  primary export where reasonable (e.g. `rembg_remover.py` defines
  `RembgRemover`).
- **Stage capability names**: lowercase, underscore-separated, stable
  strings used as registry keys and stored in `stage_runs.stage_name`
  (e.g. `background_removal`, `vectorization`). Renaming a capability key
  is a breaking change to historical data — treat as append-only; add new
  keys rather than renaming.
- **TypeScript/React**: `PascalCase` for components and types,
  `camelCase` for functions/variables/hooks, hooks prefixed `use*`.
  Feature folders under `features/` are `kebab-case`.
- **Database tables**: plural `snake_case` (`jobs`, `files`, `stage_runs`,
  `presets`). Columns `snake_case`. Foreign keys `<singular_table>_id`
  (e.g. `job_id`).
- **API routes**: plural nouns, kebab-case where multi-word
  (`/jobs`, `/jobs/{job_id}/stage-runs`).
- **Environment variables**: `PRINTVECTOR_<COMPONENT>_<NAME>`, e.g.
  `PRINTVECTOR_STORAGE_BACKEND`, `PRINTVECTOR_DB_URL`.
- **Preset files**: `snake_case.yaml`, named after the use case, not the
  implementation (`apparel_logo.yaml`, not `rembg_vtracer_preset.yaml`) —
  presets should read as business intent, not a list of library calls.

## Coding Standards

- **Formatting/linting**: `ruff` (lint + format) for Python, `eslint` +
  `prettier` for TypeScript. Both run in pre-commit hooks and CI; CI fails
  on violations, no exceptions.
- **Type checking**: `mypy` in strict-ish mode for `printvector/core`,
  `pipeline`, and `services` (the parts most worth protecting);
  `stages/` may be typed more loosely where third-party ML libraries lack
  stubs, but public stage interfaces (`StageInput`/`StageOutput`) are
  always fully typed. `tsc --strict` for the frontend.
- **Docstrings/comments**: default to none. A short comment is added only
  to explain a non-obvious *why* (a workaround, a tuned magic number, a
  library quirk) — never to restate what the code already says.
- **Function/module size**: prefer small, single-responsibility functions;
  a stage's `run()` method should read as a short sequence of named steps,
  with the actual algorithmic work in helper functions/modules.
- **No premature abstraction**: don't introduce a plugin/interface layer
  for something that has exactly one implementation and no near-term
  second one — the `Stage` interface exists because multiple
  implementations are a designed-in requirement (see `AI_PIPELINE.md`),
  not because "interfaces are good practice."
- **Error handling**: domain errors (`core/errors.py`) are raised for
  expected failure modes (unsupported file type, validation failure) and
  translated to proper HTTP status codes at the API boundary. Unexpected
  exceptions are not swallowed — they fail the job with a recorded
  stack trace, they don't get a fallback "best guess" result.
- **Commit/PR hygiene**: conventional commit-style prefixes
  (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`) recommended for
  changelog generation once the project has real release cadence.

## Configuration Strategy

- **Environment-driven settings** via `pydantic-settings` (`config/settings.py`):
  a single typed `Settings` object loaded from environment variables (with
  `.env` support for local dev via `python-dotenv`), never scattered
  `os.environ` calls throughout the codebase.
- **Layering**: `.env.example` documents every variable with a safe
  default or placeholder; `.env` (gitignored) holds actual local values;
  environment variables override `.env` in any real deployment (container,
  desktop package).
- **Storage backend selection** (`PRINTVECTOR_STORAGE_BACKEND=local|s3`)
  and **DB URL** (`PRINTVECTOR_DB_URL`) are the two settings that
  meaningfully change between "internal desktop-first" and "SaaS"
  deployments — everything else defaults sensibly for local use.
  See `PRODUCT_DECISIONS.md` for why these two are treated as first-class
  deployment toggles rather than being hardcoded.
- **Presets vs. settings**: environment settings configure *infrastructure*
  (where files live, which DB, queue broker URL). Presets
  (`config/presets/*.yaml`) configure *pipeline behavior* (which stages
  run, with which parameters) and are versioned data, not environment
  config — they're stored in the database (seeded from these YAML files)
  so they can be edited via the UI without redeploying.
- **Secrets**: never committed; loaded from environment variables locally
  and from the platform's secret manager in any hosted deployment — see
  `SECURITY.md` for details and the SaaS-phase evolution path.
- **No config in code**: any value that could plausibly differ between a
  developer's laptop, the internal server, and a future SaaS deployment
  lives in `Settings` or a preset, never as a hardcoded literal in
  `pipeline/`, `stages/`, or `api/`.
