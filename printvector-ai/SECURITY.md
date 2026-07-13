# PrintVector AI — Security

Phase 1 runs on a trusted internal network with no authentication. This
does **not** mean "no security work" — untrusted *file content* (customer
artwork of unknown provenance: WhatsApp forwards, downloaded social media
images, random PDFs) is exactly the kind of input that causes real
incidents (decompression bombs, malformed-file parser exploits, path
traversal via crafted filenames). The threat model below treats uploaded
files as hostile even though uploading users are trusted.

## Threat Model

**In scope (Phase 1):**
- Malicious or malformed image/PDF files designed to crash, hang, or
  exploit a parsing library (OpenCV, Pillow, PDF renderer, ONNX runtime).
- Resource-exhaustion attacks via oversized or decompression-bomb files
  (a 200KB PNG that decompresses to 10GB in memory).
- Path traversal / injection via filenames or embedded metadata used
  anywhere in file storage paths or shell/subprocess invocations (SVGO,
  Potrace, VTracer are invoked as subprocesses — argument/path handling
  matters).
- Storage of artifacts in a way that leaks one job's files to another
  (even without multi-tenancy, a bug here is a real bug).
- Secrets (none load-bearing in Phase 1, but the plumbing must not leak
  future ones — see below) ending up in logs, error responses, or version
  control.

**Explicitly out of scope for Phase 1** (revisit at SaaS phase — see
`ROADMAP.md`):
- Authentication/authorization of users (no multi-user trust boundary yet
  — internal network, single implicit workspace).
- Multi-tenant data isolation (no tenants yet).
- DDoS/rate-limit protection against external internet traffic (not
  internet-facing in Phase 1).
- Billing/fraud abuse vectors (no billing yet).

**Trust boundary today:** anyone who can reach the internal network can
call the API. The boundary worth defending is between "a file the API
accepted" and "code that processes that file" — that boundary is crossed
constantly and is where real vulnerabilities would live.

## File Validation

Applied at upload time, before the file is persisted or queued for
processing:

1. **Content-sniffed type checking, not extension trust.** The file's
   actual magic bytes/signature are checked against an explicit allowlist
   (JPEG, PNG, WEBP, HEIC, single/multi-page PDF). A `.jpg` file that is
   not actually a JPEG is rejected (`415 Unsupported Media Type`),
   regardless of what the client claims via `Content-Type` or filename.
2. **Size limits** enforced before the full body is even read into memory
   where possible (streaming size check), with a hard maximum (e.g.
   50MB configurable) rejected early (`413 Payload Too Large`).
3. **Decompression-bomb protection**: before running any real processing,
   check the *decoded* pixel dimensions (width × height) against a sane
   maximum (e.g. reject anything that would decode to more than ~100
   megapixels) using the image library's header-only inspection where
   available, so a tiny file claiming an enormous canvas is rejected
   without fully decoding it.
4. **PDF handling**: PDFs are parsed with a library configured to disable
   embedded JavaScript execution and external resource fetching; only
   rasterized page content is extracted (the pipeline treats a PDF page as
   "an image," not as a general document to be trusted/executed).
5. **EXIF/metadata stripping**: EXIF (and any embedded thumbnails/GPS/
   camera data) is stripped from stored originals and all derived
   artifacts — customers' photos may contain location/device metadata that
   has no business being retained or exposed via a download URL.
6. **Filename handling**: the original filename is stored as metadata only
   (for display), never used directly to construct a filesystem path.
   Storage keys are always server-generated (UUID-based), eliminating path
   traversal (`../../etc/passwd`-style) as an attack surface entirely
   rather than trying to sanitize it away.

## Input Sanitization

- **Subprocess invocations** (SVGO, Potrace, VTracer CLIs) are called with
  argument arrays (never shell-interpolated strings), fixed working
  directories, and server-generated file paths only — user-controlled data
  never reaches a shell interpreter.
- **JSON/preset parameters** from API requests are validated against
  strict Pydantic schemas (type, range, allowlisted enum values) before
  being used to construct stage parameters — e.g. a "color count" param
  is validated as a bounded integer, not passed through to a library call
  unchecked.
- **SVG output review**: since the pipeline *produces* SVG (which can
  contain `<script>` tags or external references if a tracing library ever
  emitted them, which reputable ones don't, but this is checked, not
  assumed), Print Validation includes a check that output SVGs contain no
  script elements, no external `xlink:href`/`href` references, and no
  event-handler attributes — defense in depth against the pipeline itself
  ever becoming a vector for stored XSS if SVGs are later rendered inline
  in a browser-based review UI.
- **Error messages returned to the client** never include raw stack
  traces, file system paths, or library-internal exception text — the API
  translates internal exceptions to the stable `error.code`/`message`
  format defined in `API_SPEC.md`; full details go to server-side logs
  only.

## Authentication Strategy (Future)

Phase 1 ships with **no authentication**, by explicit product decision
(internal-only, trusted network — see `PRODUCT_DECISIONS.md`). The system
is built so this is additive, not a redesign, when it's time:

- The API already routes every request through an auth middleware slot
  (`api/auth_stub.py`) that currently no-ops. Enabling real auth means
  implementing that one module, not touching route handlers.
- **Planned progression:**
  1. **Internal SSO/reverse-proxy auth** (e.g. trusted header injected by
     an internal reverse proxy, or a simple shared API key) — lowest
     effort, appropriate for "more internal users, still one workspace."
  2. **Per-user accounts** (email/password or OAuth via an identity
     provider) once multiple named operators need individual
     accountability (who approved this job) — this is when
     `jobs.created_by_user_id` starts getting populated.
  3. **API keys per organization** for the SaaS phase, supporting
     programmatic/embedded integration (a print shop's own website calling
     PrintVector's API), plus standard session auth for the hosted web UI.
- Authorization model, once needed, is straightforward
  resource-ownership (a job belongs to an organization; users can only see
  their organization's jobs) — no complex role/permission system is
  anticipated for the print-shop use case, avoiding speculative RBAC
  complexity now.

## Secrets Management

Phase 1 has few real secrets (no third-party paid APIs wired in by
default), but the pattern is established now so it scales cleanly:

- **Local/dev**: secrets (e.g. an optional commercial background-removal
  or vectorization API key, if an operator opts into one) live in a
  gitignored `.env` file, loaded via `pydantic-settings` +
  `python-dotenv`. `.env.example` documents required keys with placeholder
  values, never real ones.
- **Never committed**: pre-commit hook / CI check scans staged diffs for
  common secret patterns (API key formats, private key headers) as a
  backstop, not a substitute for developer discipline.
- **Never logged**: settings values known to be secret-typed are excluded
  from any debug/startup log dump; structured logging redacts fields named
  `*_key`, `*_secret`, `*_token` by convention.
- **Desktop packaging implication**: a bundled desktop app cannot safely
  embed a shared secret (any local user can extract it from the binary) —
  so any Phase-3-desktop-packaged secret usage must be per-user/per-install
  (e.g. the operator enters their own optional third-party API key in a
  local settings screen, stored in the OS keychain via a library like
  `keyring`, not embedded in the app bundle).
- **SaaS phase**: secrets move to a proper secrets manager (cloud
  provider's secret manager or HashiCorp Vault), injected as environment
  variables at deploy time — the application code doesn't change, only
  *where* `pydantic-settings` reads values from, because it was never
  reading `os.environ` directly and haphazardly to begin with.

## Operational Notes

- Dependencies (especially image/PDF parsing libraries — historically a
  common source of CVEs) are kept current via automated dependency update
  tooling (Dependabot or equivalent) with CI running the test suite against
  updates before merge.
- The pipeline processes untrusted files inside worker processes only —
  never inline in an API request handler — so a worst-case crash/hang in a
  parsing library takes down a worker task, not the API serving other
  users' requests (see `ARCHITECTURE.md` queue-based decoupling).
