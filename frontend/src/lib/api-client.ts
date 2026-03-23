/**
 * Centralized API client for the exai-insurance-intel backend.
 *
 * All calls go through the Next.js proxy at /api/* which forwards
 * to the FastAPI backend, avoiding CORS issues.
 */

export interface SearchRequest {
  query: string;
  mode?: string;
  search_type?: string;
  num_results?: number;
}

export interface AnswerRequest {
  query: string;
  mode?: string;
}

export interface ResearchRequest {
  query: string;
  mode?: string;
}

export interface SearchResult {
  title: string | null;
  url: string | null;
  highlights: string[];
  summary: string | null;
  text: string | null;
}

export interface SearchRecord {
  query: string;
  result_count: number;
  results: SearchResult[];
  relevance_score: number;
  credibility_score: number;
  actionability_score: number;
  confidence_score: number;
  failure_reasons: string[];
  cache_hit: boolean;
  estimated_cost_usd: number;
}

export interface SearchResponse {
  run_id: string;
  artifact_dir: string;
  record: SearchRecord;
  summary: Record<string, unknown>;
  taxonomy: Record<string, unknown>;
  recommendation: { headline_recommendation?: string };
}

export interface Citation {
  title?: string;
  url?: string;
  snippet?: string;
}

export interface AnswerResponse {
  workflow: string;
  run_id: string;
  answer: string | null;
  citations: Citation[];
  citation_count: number;
  cache_hit: boolean;
  summary: Record<string, unknown>;
}

export interface ResearchResponse {
  workflow: string;
  run_id: string;
  query: string;
  report: string | null;
  report_preview: string | null;
  citations: Citation[];
  citation_count: number;
  cache_hit: boolean;
  summary: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const data = await resp.json();

  if (!resp.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : typeof data?.error === "string"
          ? data.error
          : `Request failed with status ${resp.status}`;
    throw new ApiError(resp.status, detail);
  }

  return data as T;
}

export const api = {
  health(): Promise<HealthResponse> {
    return request<HealthResponse>("/api/health");
  },

  search(body: SearchRequest): Promise<SearchResponse> {
    return request<SearchResponse>("/api/search", {
      method: "POST",
      body: JSON.stringify({ mode: "smoke", ...body }),
    });
  },

  answer(body: AnswerRequest): Promise<AnswerResponse> {
    return request<AnswerResponse>("/api/answer", {
      method: "POST",
      body: JSON.stringify({ mode: "smoke", ...body }),
    });
  },

  research(body: ResearchRequest): Promise<ResearchResponse> {
    return request<ResearchResponse>("/api/research", {
      method: "POST",
      body: JSON.stringify({ mode: "smoke", ...body }),
    });
  },
};
