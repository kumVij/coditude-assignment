const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";

export interface Job {
  id: string;
  title: string;
  description: string;
  must_have_skills: string;
  screening_questions: string;
  language: string;
  voice_persona: string;
  hunar_agent_id: string | null;
  created_at: string;
}

export interface Candidate {
  id: string;
  name: string;
  mobile_number: string;
  email: string | null;
  resume_notes: string;
  consent_obtained: boolean;
}

export interface ScreeningCall {
  id: string;
  hunar_call_id: string | null;
  candidate: Candidate;
  status: string;
  lifecycle_status: string;
  recording_url: string | null;
  result: Record<string, unknown> | null;
  duration_minutes: number | null;
  engagement_status: string | null;
  updated_at: string;
}

export interface ScreeningEnqueue {
  batch_id: string;
  status: string;
  candidate_count: number;
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
  listJobs: () => request<Job[]>("/api/jobs"),
  getJob: (id: string) => request<Job>(`/api/jobs/${id}`),
  createJob: (data: Partial<Job>) =>
    request<Job>("/api/jobs", { method: "POST", body: JSON.stringify(data) }),
  provisionAgent: (jobId: string) =>
    request<Job>(`/api/jobs/${jobId}/provision-agent`, { method: "POST" }),
  deleteJob: (jobId: string) => request<{ ok: true }>(`/api/jobs/${jobId}`, { method: "DELETE" }),

  listCandidates: (jobId: string) => request<Candidate[]>(`/api/jobs/${jobId}/candidates`),
  addCandidates: (jobId: string, candidates: Partial<Candidate>[]) =>
    request<Candidate[]>(`/api/jobs/${jobId}/candidates`, {
      method: "POST",
      body: JSON.stringify({ candidates }),
    }),
  deleteCandidate: (jobId: string, candidateId: string) =>
    request<{ ok: true }>(`/api/jobs/${jobId}/candidates/${candidateId}`, { method: "DELETE" }),
  recordConsent: (jobId: string, candidateId: string) =>
    request<Candidate>(`/api/jobs/${jobId}/candidates/${candidateId}/consent`, { method: "POST" }),

  startScreening: (jobId: string, candidateIds?: string[]) =>
    request<ScreeningEnqueue>(`/api/jobs/${jobId}/screen`, {
      method: "POST",
      body: JSON.stringify({ candidate_ids: candidateIds ?? null }),
    }),
  listCalls: (jobId: string, refresh = false) =>
    request<ScreeningCall[]>(`/api/jobs/${jobId}/calls${refresh ? "?refresh=true" : ""}`),
};
