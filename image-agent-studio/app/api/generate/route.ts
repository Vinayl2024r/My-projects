import { runPipeline } from "@/lib/orchestrator";
import type { AssetType, GenerationSettings, ProgressEvent } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ASSET_TYPES: AssetType[] = ["carousel", "poster", "flyer", "custom"];

export async function POST(request: Request) {
  const form = await request.formData();

  const topic = String(form.get("topic") ?? "").trim();
  if (!topic) {
    return new Response(JSON.stringify({ error: "Missing topic/idea." }), {
      status: 400,
    });
  }

  const assetTypeRaw = String(form.get("assetType") ?? "custom");
  const assetType: AssetType = ASSET_TYPES.includes(assetTypeRaw as AssetType)
    ? (assetTypeRaw as AssetType)
    : "custom";

  const maxIterations = clamp(Number(form.get("maxIterations") ?? 5), 1, 5);
  const targetScore = clamp(Number(form.get("targetScore") ?? 9), 5, 10);

  const settings: GenerationSettings = { assetType, maxIterations, targetScore };

  const file = form.get("referenceImage");
  let referenceImage: { buffer: Buffer; mimeType: string } | undefined;
  if (file instanceof File && file.size > 0) {
    referenceImage = {
      buffer: Buffer.from(await file.arrayBuffer()),
      mimeType: file.type || "image/png",
    };
  }

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const emit = (event: ProgressEvent) => {
        controller.enqueue(encoder.encode(JSON.stringify(event) + "\n"));
      };

      try {
        await runPipeline({ topic, settings, referenceImage }, emit);
      } catch (error) {
        emit({
          type: "error",
          message: error instanceof Error ? error.message : "Unknown error.",
        });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "application/x-ndjson; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
    },
  });
}

function clamp(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.min(max, Math.max(min, value));
}
