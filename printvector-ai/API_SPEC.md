# PrintVector AI — API Specification

Base path: `/api/v1`. Format: JSON over HTTPS (HTTP for local dev). All
timestamps are ISO-8601 UTC. All IDs are UUIDv4 strings.

This document describes the intended contract; the authoritative,
always-current version is the OpenAPI schema FastAPI generates from the
implementation (`/api/v1/openapi.json`) — this file should be kept in sync
with it, not treated as a separate source of truth once code exists.

## Authentication (Phase 1)

None. Every endpoint is open on the internal network. The API is built
with an auth middleware slot already wired in (`api/auth_stub.py`) that
currently no-ops, so adding API-key or session auth later touches one
module, not every route. See `SECURITY.md`.

## Resources

### Jobs

#### `POST /jobs`
Create a new job by uploading an image.

**Request:** `multipart/form-data`
| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | binary | yes | the image (jpg/png/webp/heic/pdf — see `SECURITY.md` for accepted types) |
| `preset_slug` | string | no | e.g. `apparel_logo`; omitted = auto-detect |
| `params_override` | JSON string | no | per-job stage parameter overrides |

**Response:** `201 Created`
```json
{
  "id": "3e2f...b1",
  "status": "queued",
  "preset_slug": "apparel_logo",
  "original_file": {
    "id": "a1b2...",
    "mime_type": "image/jpeg",
    "size_bytes": 482331,
    "width_px": 1024,
    "height_px": 768
  },
  "created_at": "2026-07-13T10:15:00Z"
}
```

**Errors:**
- `400 Bad Request` — missing file, unsupported preset_slug
- `413 Payload Too Large` — exceeds max upload size
- `415 Unsupported Media Type` — file signature doesn't match an accepted
  image type (see `SECURITY.md` — checked by content sniffing, not
  extension)
- `422 Unprocessable Entity` — file fails integrity checks (corrupt,
  decompression-bomb heuristics triggered)

#### `GET /jobs/{job_id}`
Fetch current job status and summary.

**Response:** `200 OK`
```json
{
  "id": "3e2f...b1",
  "status": "completed",
  "confidence_score": 0.91,
  "preset_slug": "apparel_logo",
  "original_file": { "...": "..." },
  "final_output_file": {
    "id": "f9a0...",
    "kind": "vector_optimized",
    "mime_type": "image/svg+xml",
    "size_bytes": 18422
  },
  "failure_reason": null,
  "created_at": "2026-07-13T10:15:00Z",
  "updated_at": "2026-07-13T10:16:42Z"
}
```

**Errors:** `404 Not Found`

#### `GET /jobs`
List/filter jobs.

**Query params:** `status`, `preset_slug`, `created_after`, `created_before`,
`limit` (default 25, max 100), `cursor` (opaque pagination cursor).

**Response:** `200 OK`
```json
{
  "items": [ { "...": "job summary objects as above" } ],
  "next_cursor": "eyJ..." 
}
```

#### `GET /jobs/{job_id}/stage-runs`
Full pipeline trace for a job — every stage executed, its parameters,
result metadata, confidence, and timing. Powers the "show me what happened"
debugging/review UI.

**Response:** `200 OK`
```json
{
  "job_id": "3e2f...b1",
  "stage_runs": [
    {
      "id": "sr-1",
      "stage_name": "analysis",
      "implementation": "heuristics@1.0.0",
      "sequence_index": 0,
      "status": "succeeded",
      "confidence_score": 0.97,
      "result_metadata": {
        "blur_score": 0.12,
        "estimated_dpi_equivalent": 72,
        "content_type": "photo_with_background",
        "dominant_background_complexity": "high"
      },
      "duration_ms": 340,
      "started_at": "2026-07-13T10:15:01Z",
      "completed_at": "2026-07-13T10:15:01.34Z"
    }
  ]
}
```

**Errors:** `404 Not Found`

#### `GET /jobs/{job_id}/files/{file_id}`
Download a specific artifact (original, any intermediate, or final
output) by file id — used for before/after comparison in the UI.

**Response:** `200 OK` with the raw file bytes and appropriate
`Content-Type`. `404 Not Found` if the file/job doesn't exist or the file
doesn't belong to the job.

#### `POST /jobs/{job_id}/rerun-stage`
Re-run a single stage with adjusted parameters without re-running the
whole pipeline (used for operator overrides, e.g. "force background
removal on" or "use SAM instead of rembg for this one").

**Request:**
```json
{ "stage_name": "background_removal", "implementation": "sam_remover", "params": { "confidence_threshold": 0.6 } }
```

**Response:** `202 Accepted` — job re-enters `processing`; downstream
stages from this point are automatically re-run against the new output.
```json
{ "job_id": "3e2f...b1", "status": "processing" }
```

**Errors:** `400 Bad Request` (unknown stage_name/implementation),
`404 Not Found`, `409 Conflict` (job is currently processing another
stage — must wait or cancel first).

#### `POST /jobs/{job_id}/approve`
Mark a `needs_review` job as accepted as-is, transitioning it to
`completed` without further processing. Used by the review queue UI.

**Response:** `200 OK` with the updated job summary.

#### `DELETE /jobs/{job_id}`
Delete a job and its artifacts (operator cleanup / storage management).

**Response:** `204 No Content`. **Errors:** `404 Not Found`,
`409 Conflict` if currently processing (cancel first, or force-delete via
`?force=true`).

### Presets

#### `GET /presets`
List available presets (built-in + user-created).

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "p-1", "slug": "apparel_logo", "name": "Apparel logo — photo",
      "version": 3, "is_builtin": true
    }
  ]
}
```

#### `GET /presets/{slug}`
Full preset definition including resolved stage plan.

#### `POST /presets`
Create a custom preset.
**Request:**
```json
{
  "name": "Embroidery digitizing prep",
  "slug": "embroidery_prep",
  "stage_plan": [
    { "stage_name": "analysis" },
    { "stage_name": "enhancement", "params": { "denoise_strength": "high" } },
    { "stage_name": "background_removal" },
    { "stage_name": "vectorization", "implementation": "potrace_backend", "params": { "max_colors": 6 } },
    { "stage_name": "svg_optimization" },
    { "stage_name": "print_validation", "params": { "min_stroke_width_mm": 1.2 } }
  ]
}
```
**Response:** `201 Created`. **Errors:** `400 Bad Request` (invalid stage
plan — unknown stage_name, unknown implementation for that stage),
`409 Conflict` (slug already exists).

#### `PUT /presets/{slug}`
Update a preset (creates a new `version`; does not retroactively change
historical jobs — see `DATABASE.md`).

#### `DELETE /presets/{slug}`
Delete a **user-created** preset. Built-in presets cannot be deleted
(`403 Forbidden`).

### Batch (Roadmap — Batch Processing milestone)

#### `POST /batches`
Submit multiple files (or a zip) for processing under one preset; creates
one `Job` per file and a `Batch` grouping record.

#### `GET /batches/{batch_id}`
Aggregate status (`N completed, M needs_review, K failed`) and links to
individual job resources.

### Health / Ops

#### `GET /health`
Liveness check — process is up. `200 OK`, no auth, no dependencies
checked.

#### `GET /health/ready`
Readiness check — DB reachable, queue broker reachable, storage backend
writable. `200 OK` or `503 Service Unavailable` with a breakdown per
dependency.

## Error Format (Consistent Across All Endpoints)

```json
{
  "error": {
    "code": "UNSUPPORTED_MEDIA_TYPE",
    "message": "The uploaded file does not appear to be a valid image.",
    "details": { "detected_mime_type": "application/octet-stream" }
  }
}
```

`code` is a stable machine-readable string (safe to branch on in the
frontend); `message` is human-readable; `details` is optional and
endpoint-specific. HTTP status code carries the category; `code` carries
the specifics.

## Error Handling Principles

- **Fail loudly, never silently degrade.** If a stage fails, the job moves
  to `failed` with `failure_reason` populated and the relevant
  `stage_runs` row records the exception — the API never returns a
  "best effort" result without marking it as such (`needs_review` is an
  explicit, visible state, not swept under a success response).
- **Validation errors are 4xx and specific.** Every `400`/`422` includes
  enough `details` for the UI to show an actionable message, not just
  "invalid input."
- **Idempotency**: `POST /jobs` is not idempotent by content (re-uploading
  the same file creates a new job) but stage execution is internally
  content-addressed/cacheable (see `ARCHITECTURE.md`) so re-processing
  identical inputs is cheap, not a correctness concern.
- **Rate limiting**: not enforced in Phase 1 (single internal network,
  trusted users). The auth middleware slot is the natural place to add
  it later without touching route handlers.
- **Versioning**: `/api/v1` prefix from day one; breaking changes get a
  `/api/v2`, old versions are not broken for existing internal tooling.
