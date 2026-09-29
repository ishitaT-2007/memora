export type Account = {
  id: string;
  name: string;
  arr: number;
  segment: string;
  timezone: string;
  status: string;
};

export type AccountContext = {
  account: Account;
  stakeholders: { id: string; name: string; role: string; influence: string; preferences: string }[];
  commitments: {
    id: string;
    description: string;
    owner: string;
    due_date: string | null;
    status: string;
    source_record_id: string | null;
  }[];
  incidents: {
    id: string;
    severity: string;
    summary: string;
    started_at: string | null;
    resolved_at: string | null;
    impact: string;
  }[];
  memories: {
    id: string;
    memory_type: string;
    text: string;
    scope: string;
    status: string;
    source_ref: string;
    version: number;
  }[];
};

export type User = {
  id: string;
  email: string;
  name: string;
  role: string;
};

export type Recommendation = {
  action: string;
  rationale: string;
  evidence_ids: string[];
  owner_suggestion?: string | null;
  urgency?: string | null;
};

export type Avoidance = {
  action: string;
  rationale: string;
  evidence_ids: string[];
};

export type KnownFact = {
  text: string;
  source_ids: string[];
  date?: string | null;
  verification_status: string;
};

export type AnalysisOutput = {
  brief: string[];
  known_facts: KnownFact[];
  unknowns: string[];
  do: Recommendation[];
  dont: Avoidance[];
  reply_draft: string;
  memory_ids: string[];
  confidence_notes: string;
  memory_limited: boolean;
  classification: Record<string, unknown>;
};

export type Source = {
  id: string;
  type: string;
  title: string;
  body: string;
  source_ref: string;
  occurred_at?: string | null;
};

export type AnalyzeResponse = {
  request_id: string;
  escalation_id: string;
  analysis_id: string;
  latency_ms: number;
  model_version: string;
  account: Account;
  classification: Record<string, unknown>;
  output: AnalysisOutput;
  sources: Source[];
  review_state: string;
};

const TOKEN_KEY = "accrue.token";
const USER_KEY = "accrue.user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function setSession(token: string, user: User) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

const EMPTY_API_ERROR = "API returned empty response. Is the backend running on port 8000?";

function errorMessage(data: unknown, status: number): string {
  if (data && typeof data === "object") {
    const rec = data as Record<string, unknown>;
    if (typeof rec.message === "string" && rec.message.trim()) return rec.message;
    if (typeof rec.detail === "string" && rec.detail.trim()) return rec.detail;
    if (Array.isArray(rec.detail) && rec.detail[0] && typeof rec.detail[0] === "object") {
      const first = rec.detail[0] as { msg?: string };
      if (first.msg) return first.msg;
    }
  }
  if (typeof data === "string" && data.trim()) {
    const trimmed = data.trim();
    if (/^<!doctype html/i.test(trimmed) || trimmed.startsWith("<") || /proxy error|econnrefused/i.test(trimmed)) {
      return EMPTY_API_ERROR;
    }
    return trimmed.slice(0, 240);
  }
  if (!data || status === 502 || status === 503 || status === 504) return EMPTY_API_ERROR;
  return `Request failed (${status})`;
}

async function readBody(response: Response): Promise<unknown> {
  const raw = await response.text();
  if (!raw.trim()) return null;
  const contentType = (response.headers.get("content-type") || "").toLowerCase();
  const looksJson =
    contentType.includes("application/json") || raw.trimStart().startsWith("{") || raw.trimStart().startsWith("[");
  if (!looksJson) return raw;
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(EMPTY_API_ERROR);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers });
  } catch {
    throw new Error(EMPTY_API_ERROR);
  }
  const data = await readBody(response);
  if (!response.ok) {
    throw new Error(errorMessage(data, response.status));
  }
  if (data == null || typeof data === "string") {
    throw new Error(EMPTY_API_ERROR);
  }
  return data as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  accounts: () => request<{ accounts: Account[] }>("/api/accounts"),
  context: (id: string) => request<AccountContext>(`/api/accounts/${id}/context`),
  analyze: (payload: {
    account_id: string;
    escalation_text: string;
    severity: string;
    incident_facts: string;
    memory_mode: "full" | "limited";
  }) =>
    request<AnalyzeResponse>("/api/escalations/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  source: (id: string) => request<Source>(`/api/sources/${id}`),
  memory: (id: string) => request<{ memory: Record<string, unknown>; source: Source | null }>(`/api/memories/${id}`),
  previewCorrection: (escalationId: string, body: Record<string, string>) =>
    request<{ correction_id: string; preview: Record<string, string> }>(
      `/api/escalations/${escalationId}/corrections/preview`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  confirmCorrection: (escalationId: string, body: Record<string, unknown>, idempotency: string) =>
    request<{ memory_id: string; status: string }>(`/api/escalations/${escalationId}/corrections/confirm`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotency },
      body: JSON.stringify(body),
    }),
  exportText: (escalationId: string) => request<{ text: string }>(`/api/escalations/${escalationId}/export`),
  ask: (accountId: string, query: string, currentMail = "") =>
    request<{
      answer: string;
      unknown: boolean;
      citations: string[];
      query: string;
      account: { id: string; name: string };
    }>(`/api/accounts/${accountId}/ask`, {
      method: "POST",
      body: JSON.stringify({ query, current_mail: currentMail }),
    }),
  resetDemo: () => request<{ ok: boolean }>("/api/admin/reset-demo", { method: "POST" }),
  health: () => request<Record<string, unknown>>("/api/health"),
};
