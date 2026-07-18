import { getOpenAI, TEXT_MODEL, extractJson } from "../openai";
import type { AssetType, StyleAnalysis } from "../types";

interface DirectorOutput {
  prompt: string;
}

const ASSET_GUIDANCE: Record<AssetType, string> = {
  carousel:
    "Design for a single square (1:1) social media carousel slide: bold focal " +
    "subject, clear breathing room for a headline, thumb-stopping composition.",
  poster:
    "Design for a vertical (2:3) event/promo poster: strong hierarchy, room for " +
    "a headline near the top or bottom third, dramatic lighting.",
  flyer:
    "Design for a vertical (2:3) flyer: clean layout zones for headline, " +
    "supporting text, and a call-to-action, high contrast and legible even at " +
    "small thumbnail size.",
  custom:
    "Design as an open creative brief with a strong single focal point and " +
    "balanced composition.",
};

/**
 * Creative Director Agent: turns the user's topic/idea plus the extracted
 * reference style into a single dense, cinematic image-generation prompt.
 * Also used on later loop rounds to revise the prompt using critic feedback.
 */
export async function draftPrompt(params: {
  topic: string;
  assetType: AssetType;
  styleAnalysis?: StyleAnalysis;
  previousPrompt?: string;
  critiqueFeedback?: string;
  promptEdits?: string;
}): Promise<string> {
  const openai = getOpenAI();
  const { topic, assetType, styleAnalysis, previousPrompt, critiqueFeedback, promptEdits } =
    params;

  const systemPrompt =
    "You are a creative director writing prompts for a state-of-the-art " +
    "text-to-image model. Write one dense, vivid, cinematic prompt (120-220 " +
    "words) describing subject, action, environment, lighting, lens/camera " +
    "language, color grade, and mood. Favor concrete visual detail over vague " +
    "adjectives. Never mention resolution numbers or file formats - the " +
    "renderer handles that. Respond with strict JSON: {\"prompt\": string}.";

  const contextParts: string[] = [
    `User's idea/topic: "${topic}"`,
    ASSET_GUIDANCE[assetType],
  ];

  if (styleAnalysis) {
    contextParts.push(
      "Match this reference style brief as closely as the new topic allows:\n" +
        `- Summary: ${styleAnalysis.summary}\n` +
        `- Palette: ${styleAnalysis.palette.join(", ")}\n` +
        `- Composition: ${styleAnalysis.composition}\n` +
        `- Mood: ${styleAnalysis.mood}\n` +
        `- Typography feel: ${styleAnalysis.typography}\n` +
        `- Subject focus: ${styleAnalysis.subjectFocus}`
    );
  }

  if (previousPrompt && critiqueFeedback) {
    contextParts.push(
      `Previous prompt attempt:\n"""${previousPrompt}"""\n\n` +
        `A critic scored the resulting image and gave this feedback:\n"""${critiqueFeedback}"""\n\n` +
        `Specific edits requested:\n"""${promptEdits ?? "none"}"""\n\n` +
        "Rewrite the prompt to directly fix these issues while keeping what already worked."
    );
  }

  const response = await openai.chat.completions.create({
    model: TEXT_MODEL,
    temperature: 0.7,
    response_format: { type: "json_object" },
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: contextParts.join("\n\n") },
    ],
  });

  const raw = response.choices[0]?.message?.content ?? "{}";
  const parsed = extractJson<DirectorOutput>(raw);
  return parsed.prompt;
}
