const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8002";

export interface SourcedCandidate {
  id: string;
  full_name: string;
  job_title: string;
  company: string;
  location: string;
  linkedin_url: string;
  email: string;
  mobile_number: string;
  source: string;
  selected_for_reachout: boolean;
}

export interface Search {
  id: string;
  job_title: string;
  job_description: string;
  location_query: string;
  parsed_titles: string[];
  parsed_skills: string[];
  hunar_agent_id: string | null;
  created_at: string;
  candidates: SourcedCandidate[];
}

export interface ReachoutCall {
  id: string;
  hunar_call_id: string | null;
  candidate: SourcedCandidate;
  status: string;
  lifecycle_status: string;
  recording_url: string | null;
  result: Record<string, unknown> | null;
  duration_minutes: number | null;
  engagement_status: string | null;
  updated_at: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

export const api = {
  listSearches: () => request<Search[]>("/api/search"),
  getSearch: (id: string) => request<Search>(`/api/search/${id}`),
  createSearch: (data: { job_title: string; job_description: string; location_query?: string }) =>
    request<Search>("/api/search", { method: "POST", body: JSON.stringify(data) }),

  provisionAgent: (searchId: string) =>
    request<Search>(`/api/search/${searchId}/provision-agent`, { method: "POST" }),

  startReachout: (searchId: string, candidateIds: string[]) =>
    request<ReachoutCall[]>(`/api/search/${searchId}/reachout`, {
      method: "POST",
      body: JSON.stringify({ candidate_ids: candidateIds }),
    }),

  listCalls: (searchId: string, refresh = false) =>
    request<ReachoutCall[]>(`/api/search/${searchId}/calls${refresh ? "?refresh=true" : ""}`),
};
