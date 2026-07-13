# PrintVector AI — Product Vision

## Product Vision

PrintVector AI turns whatever artwork a customer happens to have — a blurry
WhatsApp photo of a logo, a screenshot pulled off Instagram, a phone photo of
a printed flyer, a low-res email attachment — into a clean, professional,
print-ready vector graphic (SVG, and eventually EPS/PDF) with minimal human
intervention.

The application acts as an automated pre-press assistant: it looks at an
incoming image, figures out what's wrong with it (noise, low resolution,
skew, background clutter, JPEG artifacts, non-vector line art, etc.), chooses
an appropriate processing pipeline, and produces output a print shop can put
directly onto a press, cutter, or embroidery machine — or hand back to a
human operator for a quick review instead of a from-scratch redraw.

Phase 1 is an **internal tool** used by the pre-press/production team to
speed up a task they currently do by hand in Illustrator or by outsourcing to
offshore vector-tracing services. Phase 2+ is a candidate for a
customer-facing or reseller-facing **SaaS product**.

## Problem Statement

Digital print shops (apparel, signage, promotional products, packaging)
constantly receive artwork that is not print-ready:

- Customers send logos as WhatsApp images (recompressed, low-res, color
  shifted) instead of original vector files.
- Photos of printed materials or embroidered patches are used as "the logo."
- Screenshots introduce UI chrome, compression artifacts, and banding.
- Scans/photos are skewed, rotated, or have uneven lighting and shadows.
- Backgrounds are cluttered (desks, fabric, skin, other logos) and need to be
  removed before the subject can be traced.
- None of the above are vector data, so they cannot be scaled, plotted, cut,
  or embroidered without a redraw.

Today this redraw work is done manually: a graphic artist opens Illustrator,
uses Image Trace or draws paths by hand, cleans anchor points, and exports an
SVG/EPS. This is slow (10–45 minutes per job), inconsistent (quality depends
on the artist), and a bottleneck during high-volume periods. Outsourcing it
adds turnaround time and recurring cost.

PrintVector AI's job is to automate the 80% of this work that is
mechanical — analysis, cleanup, background removal, tracing, path
optimization, print validation — and leave only genuinely ambiguous judgment
calls (illegible text, contradictory instructions) to a human.

## Success Metrics

Phase 1 (internal tool) is successful if it measurably reduces the cost and
latency of turning raw customer art into print-ready vectors. Concrete
targets:

| Metric | Baseline (manual) | Target (PrintVector, Phase 1) |
|---|---|---|
| Median turnaround per job | 15–45 min | < 3 min automated, < 8 min with one review pass |
| % of jobs needing zero manual touch-up | ~0% | ≥ 40% within 6 months of internal use |
| % of jobs requiring full manual redraw | ~100% | < 20% |
| Vector output accepted by production without edits | N/A | ≥ 70% acceptance rate on first pass |
| Processing pipeline failure rate (crashes/errors) | N/A | < 2% of submitted jobs |
| Cost per job (compute + labor) | outsourcing fee or 100% artist time | < 25% of current cost |

Longer-term / SaaS-phase metrics (directional, not committed):
- Self-serve conversion rate (upload → paid download) for external users.
- Gross margin per job at scale (compute cost vs. price charged).
- Net Promoter Score among print shop customers using it as a white-label
  tool.

## Non-Goals

To keep scope sane, PrintVector AI explicitly does **not** try to:

- **Replace a human designer for creative work.** It converts existing
  artwork; it does not invent logos, generate original artistic designs from
  a text prompt, or perform brand design.
- **Guarantee perfect output for every input.** Some inputs (extremely low
  resolution, heavily occluded, ambiguous line art) will always need a human
  in the loop. The system should recognize this and flag low-confidence
  jobs rather than silently producing bad output.
- **Support arbitrary generic image editing.** It is not a Photoshop
  replacement; it is a purpose-built pipeline for the "raster → print-ready
  vector" problem.
- **Be a multi-tenant billed SaaS platform in Phase 1.** No auth, no
  billing, no customer accounts initially — but the architecture must not
  preclude adding these later (see Architecture doc).
- **Do color-managed, press-calibrated output in Phase 1.** Print
  validation checks structural/vector correctness (stroke widths, path
  count, color count, bleed) but full ICC color management is a future
  roadmap item, not a v1 requirement.
- **Run exclusively offline/on-device with no server component.** A
  desktop-first packaging is a goal (see Roadmap), but the core is designed
  as a client/server system from day one so it can run locally *or* in the
  cloud without a rewrite.

## Future Roadmap (Directional)

See `ROADMAP.md` for the detailed, milestone-by-milestone plan. At a high
level:

1. **Foundation → Upload → Analysis → Enhancement → Background Removal →
   Vectorization → SVG Optimization → Print Validation** — the core
   single-image pipeline, usable internally via a simple web UI.
2. **Batch processing** — process folders/zip files of hundreds of images
   with a review queue.
3. **Desktop packaging** — ship the tool as an installable desktop app for
   production staff who are not comfortable with a browser-hosted internal
   tool, or who need offline operation.
4. **SaaS evolution** — multi-tenant auth, billing, usage quotas, public
   API, self-serve upload portal for end customers, white-label embedding
   for print-shop websites.
5. **Model quality improvements** — swap in better open-source or
   commercial models over time (upscaling, segmentation, vectorization)
   without touching business logic, thanks to the plugin architecture.
6. **Human-in-the-loop editor** — an in-browser vector touch-up editor so
   the "needs review" 20–30% of jobs can be fixed in-app instead of round-
   tripping to Illustrator.
