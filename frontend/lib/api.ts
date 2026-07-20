// lib/api.ts
// Typed client wrapping fetch calls to the FastAPI backend.

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// ---- Shared types ----

export interface GradeResult {
  score: number | null;
  rationale: string;
  flagged?: boolean;
}

export interface Question {
  id: string;
  question_number: number;
  tool_type: string;
  body: string;
  payload: Record<string, unknown>;
}

export interface TurnResponse {
  complete: boolean;
  emit: Question | Record<string, unknown>;
}

export type ToolResult =
  | { selected_id: string | null }
  | { answer_text: string }
  | { insights_text: string }
  | { skipped: true };

// ---- Core request helper ----

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${await response.text()}`);
  }

  return response.json() as Promise<T>;
}

// ---- Session lifecycle ----

export async function startSession(): Promise<{ session_id: string }> {
  return apiRequest("/session/start", { method: "POST" });
}

export async function submitIntake(sessionId: string, ratings: Record<string, unknown>): Promise<Record<string, unknown>> {
  return apiRequest(`/session/${sessionId}/intake`, {
    method: "POST",
    body: JSON.stringify(ratings),
  });
}

// NOTE: confirmed real path is /chat/turn, not /session/turn.
export async function turn(params: {
  session_id: string;
  tool_result?: ToolResult;
}): Promise<TurnResponse> {
  return apiRequest("/chat/turn", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// ---- Report ----
// NOTE: only an admin-facing report route was found (/admin/sessions/{id}/report).
// No candidate-facing /report/{id} route exists yet — this may need to change once
// that route is built, or the admin route may be the one to use here too.
export async function getReport(sessionId: string): Promise<Record<string, unknown>> {
  return apiRequest(`/admin/sessions/${sessionId}/report`);
}

// NOTE: no dedicated /answer route was found. Answer submission may happen
// entirely through turn() (tool_result gets graded server-side as part of
// /chat/turn), in which case this function may be unnecessary — confirm
// with whoever owns chat.py / candidate_intake.py before relying on this.
export async function submitAnswer(params: {
  session_id: string;
  question_id: string;
  tool_result: ToolResult;
}): Promise<GradeResult> {
  return apiRequest("/answer", {
    method: "POST",
    body: JSON.stringify(params),
  });
}