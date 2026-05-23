import { supabase } from "./supabase";
import type { CompanyCard, CompanyBrief, UserProfile, OutreachEntry } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function authHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (session?.access_token) {
    return { Authorization: `Bearer ${session.access_token}` };
  }
  return {};
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { ...headers, ...options?.headers },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || "Request failed");
  }

  return res.json();
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function fetchCompanies(params?: {
  industry?: string;
  reachability?: string;
  page?: number;
  limit?: number;
}): Promise<CompanyCard[]> {
  const query = new URLSearchParams();
  if (params?.industry) query.set("industry", params.industry);
  if (params?.reachability) query.set("reachability", params.reachability);
  if (params?.page) query.set("page", String(params.page));
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  return apiFetch<CompanyCard[]>(`/companies${qs ? `?${qs}` : ""}`);
}

export async function fetchBrief(id: number): Promise<CompanyBrief> {
  return apiFetch<CompanyBrief>(`/companies/${id}`);
}

export async function fetchProfile(): Promise<UserProfile> {
  return apiFetch<UserProfile>("/me");
}

export async function updateProfile(
  data: Partial<Pick<UserProfile, "skills" | "school" | "grad_year" | "bio" | "github_url" | "portfolio_url">>,
): Promise<UserProfile> {
  return apiFetch<UserProfile>("/me", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function fetchOutreach(): Promise<OutreachEntry[]> {
  return apiFetch<OutreachEntry[]>("/outreach");
}

export async function createOutreach(data: {
  company_id: number;
  status: OutreachEntry["status"];
  notes?: string;
  sent_at?: string;
}): Promise<OutreachEntry> {
  return apiFetch<OutreachEntry>("/outreach", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateOutreach(
  id: number,
  data: { status?: OutreachEntry["status"]; notes?: string },
): Promise<OutreachEntry> {
  return apiFetch<OutreachEntry>(`/outreach/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
