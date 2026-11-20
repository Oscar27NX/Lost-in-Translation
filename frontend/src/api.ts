import type {
  ExampleSummary,
  FidelityMode,
  FlagCategory,
  HealthStatus,
  LineStatus,
  ModelConfig,
  TranslationSession,
} from "./types";

const BASE = "/api";

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => jsonFetch<HealthStatus>(`${BASE}/health`),

  listExamples: () => jsonFetch<ExampleSummary[]>(`${BASE}/examples`),

  createSession: (payload: {
    example_key?: string;
    title?: string;
    lean_source?: string;
    fidelity_mode?: FidelityMode;
  }) =>
    jsonFetch<TranslationSession>(`${BASE}/sessions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSession: (sessionId: string) =>
    jsonFetch<TranslationSession>(`${BASE}/sessions/${encodeURIComponent(sessionId)}`),

  updateLine: (
    sessionId: string,
    lineId: string,
    payload: {
      latex?: string;
      status?: LineStatus;
      flag_categories?: FlagCategory[];
      flag_comment?: string;
      resolve_flags?: boolean;
    }
  ) =>
    jsonFetch<TranslationSession>(
      `${BASE}/sessions/${encodeURIComponent(sessionId)}/lines/${encodeURIComponent(lineId)}`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      }
    ),

  regenerateLine: (
    sessionId: string,
    lineId: string,
    payload: {
      fidelity_mode: FidelityMode;
      instruction?: string;
      use_active_flags?: boolean;
      temperature?: number;
    }
  ) =>
    jsonFetch<TranslationSession>(
      `${BASE}/sessions/${encodeURIComponent(sessionId)}/lines/${encodeURIComponent(lineId)}/regenerate`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  revertRevision: (sessionId: string, lineId: string, revIdx: number) =>
    jsonFetch<TranslationSession>(
      `${BASE}/sessions/${encodeURIComponent(sessionId)}/lines/${encodeURIComponent(lineId)}/revert/${revIdx}`,
      { method: "POST" }
    ),

  retranslate: (sessionId: string, lean_source: string, fidelity_mode: FidelityMode) =>
    jsonFetch<TranslationSession>(
      `${BASE}/sessions/${encodeURIComponent(sessionId)}/retranslate`,
      {
        method: "POST",
        body: JSON.stringify({ lean_source, fidelity_mode }),
      }
    ),

  exportLatexText: async (sessionId: string, provenance = true): Promise<string> => {
    const res = await fetch(
      `${BASE}/sessions/${encodeURIComponent(sessionId)}/export/latex?provenance=${provenance}`
    );
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    return res.text();
  },

  exportDatasetText: async (sessionId: string): Promise<string> => {
    const res = await fetch(
      `${BASE}/sessions/${encodeURIComponent(sessionId)}/export/dataset`
    );
    if (!res.ok) throw new Error(`Dataset export failed: ${res.status}`);
    return res.text();
  },

  getModelConfig: () => jsonFetch<ModelConfig>(`${BASE}/config/model`),

  updateModelConfig: (cfg: ModelConfig) =>
    jsonFetch<ModelConfig>(`${BASE}/config/model`, {
      method: "PUT",
      body: JSON.stringify(cfg),
    }),

  testModelConnection: (cfg: ModelConfig) =>
    jsonFetch<{ ok: boolean; detail: string; available_models?: string[] }>(
      `${BASE}/config/model/test`,
      {
        method: "POST",
        body: JSON.stringify(cfg),
      }
    ),
};
