import sharp from "sharp";

/**
 * Post-process "cinematic enhance" pass. This is NOT AI super-resolution -
 * it's a Lanczos upscale plus sharpening/contrast/saturation grading applied
 * to the model's native-resolution output. It measurably improves perceived
 * sharpness and punch, but it does not invent detail the model didn't
 * generate, so we're explicit about that distinction in the UI copy.
 */
export async function cinematicEnhance(
  buffer: Buffer,
  multiplier = 3
): Promise<Buffer> {
  const meta = await sharp(buffer).metadata();
  const width = Math.round((meta.width ?? 1024) * multiplier);
  const height = Math.round((meta.height ?? 1024) * multiplier);

  return sharp(buffer)
    .resize(width, height, { kernel: sharp.kernel.lanczos3 })
    .modulate({ saturation: 1.08, brightness: 1.0 })
    .linear(1.06, -6) // gentle contrast boost
    .sharpen({ sigma: 1.1 })
    .png({ quality: 100 })
    .toBuffer();
}
