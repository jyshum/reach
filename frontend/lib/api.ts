import { supabase } from "./supabase";
import type { CompanyCard, CompanyBrief, UserProfile, OutreachEntry, EmailDraft, GmailStatus, UserRepo } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function authHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) return {};

  // Check if token expires within 60s and refresh proactively
  const expiresAt = session.expires_at ?? 0;
  if (expiresAt - Math.floor(Date.now() / 1000) < 60) {
    const { data } = await supabase.auth.refreshSession();
    if (data.session?.access_token) {
      return { Authorization: `Bearer ${data.session.access_token}` };
    }
  }

  return { Authorization: `Bearer ${session.access_token}` };
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(await authHeaders()),
  };
  if (options?.body) {
    headers["Content-Type"] = "application/json";
  }
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

export interface InterestCategory {
  name: string;
  tags: string[];
}

export async function fetchInterests(): Promise<InterestCategory[]> {
  const data = await apiFetch<{ categories: InterestCategory[] }>("/interests");
  return data.categories;
}

export async function fetchCompanies(params?: {
  industry?: string;
  reachability?: string;
  search?: string;
  page?: number;
  limit?: number;
}): Promise<CompanyCard[]> {
  const query = new URLSearchParams();
  if (params?.industry) query.set("industry", params.industry);
  if (params?.reachability) query.set("reachability", params.reachability);
  if (params?.search) query.set("search", params.search);
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
  data: Partial<Pick<UserProfile, "skills" | "school" | "grad_year" | "bio" | "github_url" | "portfolio_url" | "location" | "interests" | "projects" | "resume_url">>,
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

// --- Email ---

export async function getGmailAuthUrl(): Promise<{ url: string }> {
  return apiFetch("/email/gmail/auth-url");
}

export async function submitGmailCallback(code: string): Promise<{ gmail_email: string }> {
  return apiFetch("/email/gmail/callback", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export async function getGmailStatus(): Promise<GmailStatus> {
  return apiFetch("/email/gmail/status");
}

export async function disconnectGmail(): Promise<void> {
  return apiFetch("/email/gmail/disconnect", { method: "DELETE" });
}

export async function generateEmailDraft(
  companyId: number,
  tone: "curious" | "friendly" | "scrappy" | "earnest" = "curious"
): Promise<EmailDraft> {
  return apiFetch("/email/generate", {
    method: "POST",
    body: JSON.stringify({ company_id: companyId, tone }),
  });
}

export async function sendEmail(data: {
  company_id: number;
  subject_line: string;
  final_text: string;
  original_draft: string;
  tone: string;
}): Promise<{ status: string; thread_id: string }> {
  return apiFetch("/email/send", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function checkReplies(): Promise<{ replies_found: number; checked: number }> {
  return apiFetch("/email/check-replies", { method: "POST" });
}

// --- Repos ---

export async function fetchRepos(): Promise<UserRepo[]> {
  return apiFetch<UserRepo[]>("/me/repos");
}

export async function createRepo(repoUrl: string): Promise<UserRepo> {
  return apiFetch<UserRepo>("/me/repos", {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

export async function deleteRepo(repoId: number): Promise<void> {
  return apiFetch("/me/repos/" + repoId, { method: "DELETE" });
}

// --- Resume ---

export async function uploadResume(file: File): Promise<{ resume_url: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}/me/resume`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || "Upload failed");
  }
  return res.json();
}

export async function deleteResume(): Promise<void> {
  return apiFetch("/me/resume", { method: "DELETE" });
}
