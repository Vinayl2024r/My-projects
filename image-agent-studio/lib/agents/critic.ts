import { getOpenAI, VISION_MODEL, extractJson } from "../openai";
import type { CritiqueResult, StyleAnalysis } from "../types";

/**
 * Critic / QA Agent: the loop-engineering half. Scores the freshly
 * generated image against the brief (and reference style, if any) on five
 * dimensions, then hands back concrete, actionable prompt edits so the
 * Creative Director can fix specific problems on the next round instead of
 * regenerating blind.
 */
export async function critiqueImage(params: {
  imageDataUrl: string;
  topic: string;
  prompt: string;
  targetScore: number;
  styleAnalysis?: StyleAnalysis;
}): Promise<CritiqueResult> {
  const openai = getOpenAI();
  const { imageDataUrl, topic, prompt, targetScore, styleAnalysis } = params;

  const referenceContext = styleAnalysis
    ? `The image should also match this reference style brief:\n${JSON.stringify(
        styleAnalysis
      )}\n\n`
    : "";

  const response = await openai.chat.completions.create({
    model: VISION_MODEL,
    temperature: 0,
    response_format: { type: "json_object" },
    messages: [
      {
        role: "system",
        content:
          "You are a ruthless, detail-obsessed creative QA reviewer scoring an " +
          "AI-generated marketing image. Score each dimension 0-10 (integers). " +
          "Be strict: reserve 9-10 for genuinely excellent, error-free results. " +
          "Look specifically for: extra/missing limbs or fingers, garbled or " +
          "misspelled text, warped objects, mismatched lighting, and anything " +
          "that contradicts the brief. Respond with strict JSON only: " +
          '{"scores": {"conceptAccuracy": number, "styleMatch": number, ' +
          '"composition": number, "cinematicQuality": number, "textLegibility": number}, ' +
          '"overall": number, "feedback": string, "promptEdits": string}. ' +
          '"overall" is the rounded average of the five scores. "feedback" ' +
          "explains what's wrong in 2-4 sentences. \"promptEdits\" is a short, " +
          "imperative list of concrete changes to make to the prompt (or " +
          '"none" if no changes needed).',
      },
      {
        role: "user",
        content: [
          {
            type: "text",
            text:
              `User's idea/topic: "${topic}"\n\n` +
              `Prompt used to generate this image:\n"""${prompt}"""\n\n` +
              referenceContext +
              `The pass threshold is ${targetScore}/10 overall.`,
          },
          {
            type: "image_url",
            image_url: { url: imageDataUrl, detail: "high" },
          },
        ],
      },
    ],
  });

  const raw = response.choices[0]?.message?.content ?? "{}";
  const parsed = extractJson<Omit<CritiqueResult, "passes">>(raw);
  return {
    ...parsed,
    passes: parsed.overall >= targetScore,
  };
}
