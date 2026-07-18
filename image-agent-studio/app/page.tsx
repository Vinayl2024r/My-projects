"use client";

import { useRef, useState } from "react";
import type { AssetType, CritiqueResult, ProgressEvent, StyleAnalysis } from "@/lib/types";

interface IterationRecord {
  iteration: number;
  prompt?: string;
  imageUrl?: string;
  critique?: CritiqueResult;
}

interface LogEntry {
  id: number;
  text: string;
}

const ASSET_OPTIONS: { value: AssetType; label: string }[] = [
  { value: "carousel", label: "Carousel slide (1:1)" },
  { value: "poster", label: "Poster (2:3)" },
  { value: "flyer", label: "Flyer (2:3)" },
  { value: "custom", label: "Custom / other" },
];

export default function Page() {
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [referencePreview, setReferencePreview] = useState<string | null>(null);
  const [assetType, setAssetType] = useState<AssetType>("poster");
  const [topic, setTopic] = useState("");
  const [maxIterations, setMaxIterations] = useState(5);
  const [targetScore, setTargetScore] = useState(9);

  const [running, setRunning] = useState(false);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [styleAnalysis, setStyleAnalysis] = useState<StyleAnalysis | null>(null);
  const [iterations, setIterations] = useState<IterationRecord[]>([]);
  const [finalResult, setFinalResult] = useState<
    { url: string; overall: number; iterations: number; passed: boolean } | null
  >(null);

  const logIdRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function pushLog(text: string) {
    logIdRef.current += 1;
    setLog((prev) => [...prev, { id: logIdRef.current, text }]);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setReferenceFile(f);
    setReferencePreview(f ? URL.createObjectURL(f) : null);
  }

  function upsertIteration(iteration: number, patch: Partial<IterationRecord>) {
    setIterations((prev) => {
      const idx = prev.findIndex((r) => r.iteration === iteration);
      if (idx === -1) return [...prev, { iteration, ...patch }];
      const next = [...prev];
      next[idx] = { ...next[idx], ...patch };
      return next;
    });
  }

  async function handleGenerate() {
    if (!topic.trim() || running) return;

    setRunning(true);
    setLog([]);
    setStyleAnalysis(null);
    setIterations([]);
    setFinalResult(null);
    pushLog(`You: ${topic.trim()}`);

    const form = new FormData();
    form.set("topic", topic.trim());
    form.set("assetType", assetType);
    form.set("maxIterations", String(maxIterations));
    form.set("targetScore", String(targetScore));
    if (referenceFile) form.set("referenceImage", referenceFile);

    try {
      const res = await fetch("/api/generate", { method: "POST", body: form });
      if (!res.body) throw new Error("No response stream from server.");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line) as ProgressEvent;
          handleEvent(event);
        }
      }
    } catch (err) {
      pushLog(`Error: ${err instanceof Error ? err.message : "generation failed"}`);
    } finally {
      setRunning(false);
    }
  }

  function handleEvent(event: ProgressEvent) {
    switch (event.type) {
      case "status":
        pushLog(event.message);
        break;
      case "analysis":
        setStyleAnalysis(event.data);
        pushLog(`Vision Analyst: "${event.data.summary}"`);
        break;
      case "prompt":
        upsertIteration(event.iteration, { prompt: event.prompt });
        pushLog(`Round ${event.iteration} prompt ready.`);
        break;
      case "image":
        upsertIteration(event.iteration, { imageUrl: event.url });
        pushLog(`Round ${event.iteration} image rendered.`);
        break;
      case "critique":
        upsertIteration(event.iteration, { critique: event.result });
        pushLog(
          `Round ${event.iteration} score: ${event.result.overall}/10 - ${event.result.feedback}`
        );
        break;
      case "final":
        setFinalResult(event);
        pushLog(
          event.passed
            ? `Done: hit ${event.overall}/10 in ${event.iterations} round(s).`
            : `Stopped after ${event.iterations} round(s) at best score ${event.overall}/10 (target not reached).`
        );
        break;
      case "error":
        pushLog(`Error: ${event.message}`);
        break;
    }
  }

  return (
    <main className="min-h-screen max-w-7xl mx-auto px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold">Cinematic Multi-Agent Image Studio</h1>
        <p className="text-sm text-neutral-400 mt-1 max-w-2xl">
          Upload a reference carousel slide, poster, or flyer, describe your idea in the
          chat, and four cooperating agents (Vision Analyst, Creative Director, Image
          Generator, Critic) generate, score, and auto-refine the result. Scoring is an
          AI critic's honest 0-10 judgement, capped at {maxIterations} rounds - not a
          guarantee of perfection.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <section className="bg-panel/60 border border-white/10 rounded-xl p-5 flex flex-col gap-4">
          <div>
            <label className="text-sm font-medium block mb-2">
              Reference asset (carousel / poster / flyer) - optional
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="text-sm file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-accent file:text-white file:text-sm"
            />
            {referencePreview && (
              <img
                src={referencePreview}
                alt="Reference preview"
                className="mt-3 max-h-48 rounded-lg border border-white/10"
              />
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium block mb-2">Asset type</label>
              <select
                value={assetType}
                onChange={(e) => setAssetType(e.target.value as AssetType)}
                className="w-full bg-ink border border-white/10 rounded-lg px-3 py-2 text-sm"
              >
                {ASSET_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">
                Max rounds ({maxIterations})
              </label>
              <input
                type="range"
                min={1}
                max={5}
                value={maxIterations}
                onChange={(e) => setMaxIterations(Number(e.target.value))}
                className="w-full"
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium block mb-2">
              Target critic score ({targetScore}/10)
            </label>
            <input
              type="range"
              min={5}
              max={10}
              value={targetScore}
              onChange={(e) => setTargetScore(Number(e.target.value))}
              className="w-full"
            />
          </div>

          <div className="flex-1 min-h-[220px] max-h-[360px] overflow-y-auto bg-ink/60 rounded-lg border border-white/5 p-3 text-sm space-y-1">
            {log.length === 0 && (
              <p className="text-neutral-500">Agent activity will show up here.</p>
            )}
            {log.map((entry) => (
              <p key={entry.id} className="text-neutral-300">
                {entry.text}
              </p>
            ))}
          </div>

          <div className="flex gap-2">
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Describe your idea/topic, e.g. 'Summer rooftop DJ night, neon skyline, 21+ event'"
              rows={2}
              className="flex-1 bg-ink border border-white/10 rounded-lg px-3 py-2 text-sm resize-none"
            />
            <button
              onClick={handleGenerate}
              disabled={running || !topic.trim()}
              className="bg-accent disabled:opacity-50 disabled:cursor-not-allowed rounded-lg px-4 py-2 text-sm font-medium"
            >
              {running ? "Generating..." : "Generate"}
            </button>
          </div>
        </section>

        <section className="bg-panel/60 border border-white/10 rounded-xl p-5 flex flex-col gap-4">
          <h2 className="text-lg font-semibold">Result</h2>

          {finalResult ? (
            <div>
              <img
                src={finalResult.url}
                alt="Final generated creative"
                className="w-full rounded-lg border border-white/10"
              />
              <div className="flex items-center justify-between mt-3">
                <span className="text-sm">
                  Score {finalResult.overall}/10 - {finalResult.iterations} round
                  {finalResult.iterations > 1 ? "s" : ""} -{" "}
                  {finalResult.passed ? "target reached" : "best of capped rounds"}
                </span>
                <a
                  href={finalResult.url}
                  download
                  className="text-sm bg-white/10 hover:bg-white/20 rounded-lg px-3 py-1.5"
                >
                  Download
                </a>
              </div>
            </div>
          ) : (
            <p className="text-neutral-500 text-sm">
              No result yet. Describe an idea and hit Generate.
            </p>
          )}

          {iterations.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-2 text-neutral-400">
                Round-by-round history
              </h3>
              <div className="grid grid-cols-3 gap-3">
                {iterations.map((it) => (
                  <div
                    key={it.iteration}
                    className="border border-white/10 rounded-lg overflow-hidden"
                  >
                    {it.imageUrl ? (
                      <img src={it.imageUrl} alt={`Round ${it.iteration}`} className="w-full" />
                    ) : (
                      <div className="aspect-square bg-white/5 flex items-center justify-center text-xs text-neutral-500">
                        rendering...
                      </div>
                    )}
                    <div className="px-2 py-1 text-xs flex justify-between">
                      <span>Round {it.iteration}</span>
                      <span>{it.critique ? `${it.critique.overall}/10` : "..."}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
