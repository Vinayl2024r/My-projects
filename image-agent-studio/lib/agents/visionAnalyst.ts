import { getOpenAI, VISION_MODEL, extractJson } from "../openai";
import type { StyleAnalysis } from "../types";

/**
 * Vision Analyst Agent: looks at the user's reference asset (carousel slide,
 * poster, flyer, etc.) and extracts a structured style brief that later
 * agents use to keep the new creative visually consistent with it.
 */
export async function analyzeReference(
  imageDataUrl: string
): Promise<StyleAnalysis> {
  const openai = getOpenAI();

  const response = await openai.chat.completions.create({
    model: VISION_MODEL,
    temperature: 0.2,
    response_format: { type: "json_object" },
    messages: [
      {
        role: "system",
        content:
          "You are a senior art director analyzing a reference marketing asset " +
          "(poster, flyer, or carousel slide). Extract a precise, reusable style " +
          "brief so another designer could match the look without seeing the " +
          "original. Respond with strict JSON only, matching this shape: " +
          '{"summary": string, "palette": string[] (hex or named colors, 3-6 items), ' +
          '"composition": string, "mood": string, "typography": string, ' +
          '"subjectFocus": string}.',
      },
      {
        role: "user",
        content: [
          {
            type: "text",
            text: "Analyze this reference image and produce the style brief JSON.",
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
  return extractJson<StyleAnalysis>(raw);
}
