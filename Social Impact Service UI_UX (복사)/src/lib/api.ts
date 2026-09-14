import type {
  ActionStatus,
  AlertRecord,
  AssessmentRecord,
  CaseActionRecord,
  LoginResponse,
  YouthDetail,
  YouthListItem,
} from "../types";

let accessToken: string | null = null;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    let message = `요청을 처리하지 못했습니다. (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // JSON 오류 본문이 아니면 기본 안내문을 사용한다.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  async login(username: string, password: string, role: "youth" | "case_worker") {
    const result = await request<LoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password, role }),
    });
    accessToken = result.accessToken;
    return result;
  },

  logout() {
    accessToken = null;
  },

  listYouths(query = "", status = "") {
    const params = new URLSearchParams();
    if (query.trim()) params.set("query", query.trim());
    if (status) params.set("status", status);
    const suffix = params.size ? `?${params.toString()}` : "";
    return request<YouthListItem[]>(`/api/youths${suffix}`);
  },

  getYouth(youthId: string) {
    return request<YouthDetail>(`/api/youths/${encodeURIComponent(youthId)}`);
  },

  ensureCurrentAnalysis(youthId: string) {
    return request<AssessmentRecord>(`/api/youths/${encodeURIComponent(youthId)}/analysis/current`, {
      method: "POST",
    });
  },

  submitCheckin(payload: {
    youthId: string;
    responseType: string;
    responseText: string | null;
    followUps: string[];
  }) {
    return request<{ assessment: AssessmentRecord }>("/api/checkins", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listAlerts() {
    return request<AlertRecord[]>("/api/alerts");
  },

  updateAlert(alertId: string, status: string) {
    return request<AlertRecord>(`/api/alerts/${encodeURIComponent(alertId)}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  },

  createAction(youthId: string, status: ActionStatus, memo: string) {
    return request<CaseActionRecord>(`/api/youths/${encodeURIComponent(youthId)}/actions`, {
      method: "POST",
      body: JSON.stringify({ status, memo }),
    });
  },

  analyze(youthId: string, mode?: "rule" | "ai" | "hybrid") {
    return request<AssessmentRecord>(`/api/youths/${encodeURIComponent(youthId)}/analyze`, {
      method: "POST",
      body: JSON.stringify({ mode }),
    });
  },
};

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "알 수 없는 오류가 발생했습니다.";
}
