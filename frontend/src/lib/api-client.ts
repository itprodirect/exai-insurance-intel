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

  // Handle 204 No Content (e.g. DELETE responses).
  if (resp.status === 204) {
    return undefined as T;
  }

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

// ---------------------------------------------------------------------------
// Run history + ops types
// ---------------------------------------------------------------------------

export interface RunRecord {
  id: string;
  request_id?: string;
  run_id?: string;
  workflow: string;
  mode: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  query_preview?: string;
  cache_hit?: boolean;
  cost_summary?: Record<string, unknown>;
  artifact_location?: string;
  artifact_count: number;
  error_message?: string;
}

export interface RunListResponse {
  runs: RunRecord[];
  count: number;
}

export interface WorkflowBreakdown {
  workflow: string;
  count: number;
  avg_duration_ms?: number;
}

export interface ModeBreakdown {
  mode: string;
  count: number;
}

export interface OpsSummary {
  total_runs: number;
  completed: number;
  failed: number;
  cache_hits: number;
  avg_duration_ms?: number;
  max_duration_ms?: number;
  total_spent_usd: number;
  earliest_run?: string;
  latest_run?: string;
  by_workflow: WorkflowBreakdown[];
  by_mode: ModeBreakdown[];
}

export interface SavedQueryRecord {
  id: string;
  user_id: string;
  workflow: string;
  query: string;
  label?: string;
  created_at?: string;
}

export interface SavedQueryListResponse {
  queries: SavedQueryRecord[];
  count: number;
}

export interface UserWorkflowBreakdown {
  workflow: string;
  count: number;
}

export interface UserSummary {
  total_runs: number;
  completed: number;
  failed: number;
  cache_hits: number;
  avg_duration_ms?: number;
  max_duration_ms?: number;
  earliest_run?: string;
  latest_run?: string;
  total_spent_usd: number;
  by_workflow: UserWorkflowBreakdown[];
}

export interface MeResponse {
  user_id: string;
  usage: UserSummary;
  saved_query_count: number;
  can_access_ops: boolean;
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

  listRuns(params?: {
    limit?: number;
    offset?: number;
    workflow?: string;
    mode?: string;
    status?: string;
  }): Promise<RunListResponse> {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    if (params?.workflow) qs.set("workflow", params.workflow);
    if (params?.mode) qs.set("mode", params.mode);
    if (params?.status) qs.set("status", params.status);
    const query = qs.toString();
    return request<RunListResponse>(`/api/runs${query ? `?${query}` : ""}`);
  },

  getRun(id: string): Promise<RunRecord> {
    return request<RunRecord>(`/api/runs/${id}`);
  },
  opsSummary(): Promise<OpsSummary> {
    return request<OpsSummary>("/api/ops/summary");
  },

  me(): Promise<MeResponse> {
    return request<MeResponse>("/api/me");
  },

  myRuns(params?: {
    limit?: number;
    offset?: number;
    workflow?: string;
    status?: string;
  }): Promise<RunListResponse> {
    const qs = new URLSearchParams();
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    if (params?.workflow) qs.set("workflow", params.workflow);
    if (params?.status) qs.set("status", params.status);
    const query = qs.toString();
    return request<RunListResponse>(
      `/api/me/runs${query ? `?${query}` : ""}`
    );
  },

  listSavedQueries(): Promise<SavedQueryListResponse> {
    return request<SavedQueryListResponse>("/api/me/saved-queries");
  },

  saveQuery(body: {
    workflow: string;
    query: string;
    label?: string;
  }): Promise<SavedQueryRecord> {
    return request<SavedQueryRecord>("/api/me/saved-queries", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  deleteSavedQuery(id: string): Promise<void> {
    return request<void>(`/api/me/saved-queries/${id}`, {
      method: "DELETE",
    });
  },
};
