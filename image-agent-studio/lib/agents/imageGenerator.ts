import { getOpenAI, IMAGE_MODEL } from "../openai";
import type { AssetType } from "../types";

const SIZE_BY_ASSET: Record<AssetType, "1024x1024" | "1024x1536" | "1536x1024"> = {
  carousel: "1024x1024",
  poster: "1024x1536",
  flyer: "1024x1536",
  custom: "1024x1024",
};

const CINEMATIC_SUFFIX =
  ", ultra-detailed, cinematic lighting, professional color grade, sharp focus, " +
  "high dynamic range, award-winning commercial photography";

/**
 * Image Generator Agent: renders the current prompt at the model's maximum
 * native resolution for the chosen asset type. gpt-image-1 tops out at
 * 1536px on the long edge - anything beyond that is a post-process
 * upscale/enhance pass, not a bigger native render.
 */
export async function generateImage(params: {
  prompt: string;
  assetType: AssetType;
}): Promise<Buffer> {
  const openai = getOpenAI();

  const response = await openai.images.generate({
    model: IMAGE_MODEL,
    prompt: params.prompt + CINEMATIC_SUFFIX,
    size: SIZE_BY_ASSET[params.assetType],
    quality: "high",
  });

  const b64 = response.data?.[0]?.b64_json;
  if (!b64) {
    throw new Error("Image generation returned no data.");
  }
  return Buffer.from(b64, "base64");
}
