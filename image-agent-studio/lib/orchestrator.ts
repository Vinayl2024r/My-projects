import { randomUUID } from "crypto";
import { analyzeReference } from "./agents/visionAnalyst";
import { draftPrompt } from "./agents/creativeDirector";
import { generateImage } from "./agents/imageGenerator";
import { critiqueImage } from "./agents/critic";
import { cinematicEnhance } from "./upscale";
import { saveRunImage } from "./storage";
import type { GenerationSettings, ProgressEvent, StyleAnalysis } from "./types";

export interface OrchestratorInput {
  topic: string;
  settings: GenerationSettings;
  referenceImage?: { buffer: Buffer; mimeType: string };
}

function toDataUrl(buffer: Buffer, mimeType: string): string {
  return `data:${mimeType};base64,${buffer.toString("base64")}`;
}

/**
 * Runs the full multi-agent pipeline: analyze reference -> draft prompt ->
 * generate -> critique -> (revise + regenerate) up to maxIterations, or
 * until the critic's overall score clears targetScore. Emits progress
 * events as it goes so the UI can render a live agent log.
 */
export async function runPipeline(
  input: OrchestratorInput,
  emit: (event: ProgressEvent) => void
): Promise<void> {
  const runId = randomUUID();
  const { topic, settings, referenceImage } = input;
  const { assetType, maxIterations, targetScore } = settings;

  let styleAnalysis: StyleAnalysis | undefined;

  if (referenceImage) {
    emit({ type: "status", message: "Vision Analyst: studying your reference image..." });
    styleAnalysis = await analyzeReference(
      toDataUrl(referenceImage.buffer, referenceImage.mimeType)
    );
    emit({ type: "analysis", data: styleAnalysis });
  }

  let prompt = "";
  let bestUrl = "";
  let bestOverall = -1;
  let lastIteration = 0;
  let passed = false;
  let lastFeedback: string | undefined;
  let lastPromptEdits: string | undefined;

  for (let iteration = 1; iteration <= maxIterations; iteration++) {
    lastIteration = iteration;
    emit({
      type: "status",
      message:
        iteration === 1
          ? "Creative Director: drafting the initial cinematic prompt..."
          : `Creative Director: revising the prompt for round ${iteration}...`,
    });

    prompt = await draftPrompt(
      iteration === 1
        ? { topic, assetType, styleAnalysis }
        : {
            topic,
            assetType,
            styleAnalysis,
            previousPrompt: prompt,
            critiqueFeedback: lastFeedback,
            promptEdits: lastPromptEdits,
          }
    );
    emit({ type: "prompt", iteration, prompt });

    emit({ type: "status", message: `Image Generator: rendering round ${iteration}...` });
    const rawBuffer = await generateImage({ prompt, assetType });

    emit({ type: "status", message: "Cinematic Enhance: upscaling + color grading..." });
    const enhanced = await cinematicEnhance(rawBuffer);
    const url = await saveRunImage(runId, `iter-${iteration}.png`, enhanced);
    emit({ type: "image", iteration, url });

    emit({ type: "status", message: "Critic: scoring this round against the brief..." });
    const critique = await critiqueImage({
      imageDataUrl: toDataUrl(rawBuffer, "image/png"),
      topic,
      prompt,
      targetScore,
      styleAnalysis,
    });
    emit({ type: "critique", iteration, result: critique });

    if (critique.overall > bestOverall) {
      bestOverall = critique.overall;
      bestUrl = url;
    }

    if (critique.passes) {
      passed = true;
      break;
    }

    lastFeedback = critique.feedback;
    lastPromptEdits = critique.promptEdits;
  }

  emit({
    type: "final",
    url: bestUrl,
    overall: bestOverall,
    iterations: lastIteration,
    passed,
  });
}
