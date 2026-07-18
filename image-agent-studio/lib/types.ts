export type AssetType = "carousel" | "poster" | "flyer" | "custom";

export interface StyleAnalysis {
  summary: string;
  palette: string[];
  composition: string;
  mood: string;
  typography: string;
  subjectFocus: string;
}

export interface CriticScores {
  conceptAccuracy: number;
  styleMatch: number;
  composition: number;
  cinematicQuality: number;
  textLegibility: number;
}

export interface CritiqueResult {
  scores: CriticScores;
  overall: number;
  passes: boolean;
  feedback: string;
  promptEdits: string;
}

export interface GenerationSettings {
  assetType: AssetType;
  maxIterations: number;
  targetScore: number;
}

export type ProgressEvent =
  | { type: "status"; message: string }
  | { type: "analysis"; data: StyleAnalysis }
  | { type: "prompt"; iteration: number; prompt: string }
  | { type: "image"; iteration: number; url: string }
  | { type: "critique"; iteration: number; result: CritiqueResult }
  | {
      type: "final";
      url: string;
      overall: number;
      iterations: number;
      passed: boolean;
    }
  | { type: "error"; message: string };
