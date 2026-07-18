# Cinematic Multi-Agent Image Studio

Upload a reference asset (carousel slide, poster, flyer), describe your idea in the
chat box, and four cooperating agents generate a creative and iterate on it
automatically:

1. **Vision Analyst** - looks at your reference image and extracts a style brief
   (palette, composition, mood, typography feel) so the new creative stays visually
   consistent with it.
2. **Creative Director** - turns your topic + the style brief into a dense, cinematic
   image-generation prompt.
3. **Image Generator** - renders the prompt with `gpt-image-1` at its native max
   resolution for the chosen asset type, then a Sharp-based "cinematic enhance" pass
   (Lanczos upscale + sharpen + color grade) upsizes and polishes it.
4. **Critic** - scores the render 0-10 across concept accuracy, style match,
   composition, cinematic quality, and text legibility, and returns concrete prompt
   edits. If the score is below your target, the Creative Director revises the prompt
   with that feedback and the loop generates another round - up to a capped number of
   rounds you control.

## Honest expectations

- **Resolution**: `gpt-image-1` natively renders up to 1536px on the long edge. The
  "cinematic enhance" pass upscales and sharpens that output - it's real image
  processing, not invented AI detail, and it will not produce a literal 24K image.
  There's no such thing as a model that natively renders 24K.
- **Scoring**: the "10/10" score is an AI critic's judgement, not a guarantee. The
  loop stops either when the critic's score clears your target or when it hits the
  round cap (default 5), whichever comes first - it can't loop forever chasing an
  unreachable perfect score.

## Setup

```bash
cp .env.example .env.local
# edit .env.local and set OPENAI_API_KEY
npm install
npm run dev
```

Open http://localhost:3000.

**Before you start:** `gpt-image-1` requires your OpenAI organization to be
"verified" (Platform Settings -> Organization -> Verifications) - without that, image
generation calls will fail with a permissions error even with a valid API key. The
critic/vision-analyst calls use `gpt-4o` and don't need this.

## Project layout

```
app/
  page.tsx                 chat + upload UI, streams progress from the API
  api/generate/route.ts    accepts the form, streams NDJSON progress events
lib/
  agents/
    visionAnalyst.ts       reference image -> style brief
    creativeDirector.ts    topic + style brief (+ critic feedback) -> prompt
    imageGenerator.ts      prompt -> rendered image (gpt-image-1)
    critic.ts              rendered image -> scores + feedback
  orchestrator.ts           the generate -> critique -> refine loop
  upscale.ts                Sharp-based cinematic enhance pass
  storage.ts                saves each round's image under public/generated/<runId>/
```

## Extending

- Swap providers by replacing the calls in `lib/agents/*` and `lib/openai.ts` - the
  orchestrator and API route don't know which provider is behind them.
- To persist runs across restarts or share results, add a database and point
  `lib/storage.ts` at object storage (S3/R2) instead of `public/generated`.
- To support multi-slide carousels, loop the orchestrator per slide and pass the
  previous slide's style brief forward for consistency.
