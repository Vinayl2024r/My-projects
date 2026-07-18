import { mkdir, writeFile } from "fs/promises";
import path from "path";

const GENERATED_ROOT = path.join(process.cwd(), "public", "generated");

export async function saveRunImage(
  runId: string,
  filename: string,
  buffer: Buffer
): Promise<string> {
  const dir = path.join(GENERATED_ROOT, runId);
  await mkdir(dir, { recursive: true });
  await writeFile(path.join(dir, filename), buffer);
  return `/generated/${runId}/${filename}`;
}
