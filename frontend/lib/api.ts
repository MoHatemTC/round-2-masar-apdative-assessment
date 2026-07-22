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

export interface CompetencyRef {
  id: string;
  name: string;
}

export interface AssessmentInfo {
  assessment_id: string;
  title: string;
  competencies: CompetencyRef[];
}

export interface CvUploadResult {
  session_id: string;
  filename: string;
  characters_extracted: number;
  message: string;
}

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

// ---- Candidate entry flow (session start via link/token -> intake -> loop) ----

// Resolves a `?token=` share link into the assessment's id, title, and the competencies the
// candidate needs to self-rate. Read-only, unauthenticated — the token itself is the credential.
export async function getAssessmentByToken(token: string): Promise<AssessmentInfo> {
  return apiRequest(`/assessments/by-token/${encodeURIComponent(token)}`);
}

export async function startSession(assessmentId: string): Promise<{ session_id: string }> {
  return apiRequest("/session/start", {
    method: "POST",
    body: JSON.stringify({ assessment_id: assessmentId }),
  });
}

// selfRatings is {competency_id: 1-5, ...} — matches POST /session/{id}/intake's contract exactly.
export async function submitIntake(
  sessionId: string,
  selfRatings: Record<string, number>
): Promise<Record<string, unknown>> {
  return apiRequest(`/session/${sessionId}/intake`, {
    method: "POST",
    body: JSON.stringify({ self_ratings: selfRatings }),
  });
}

// Multipart upload — deliberately does NOT go through apiRequest(), because that helper always
// sets Content-Type: application/json. A FormData body needs the browser to set its own
// Content-Type (including the multipart boundary) automatically; setting it manually breaks the upload.
export async function uploadCv(sessionId: string, file: File): Promise<CvUploadResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/session/${sessionId}/cv`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${await response.text()}`);
  }
  return response.json() as Promise<CvUploadResult>;
}

// ---- Adaptive loop turn ----

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
// NOTE: only an admin-facing report route exists (/admin/sessions/{id}/report) as of this
// writing. No candidate-facing /report/{id} route exists yet.
export async function getReport(sessionId: string): Promise<Record<string, unknown>> {
  return apiRequest(`/admin/sessions/${sessionId}/report`);
}

export async function importBank(
  items: unknown[],
  setName?: string
): Promise<{
  questions: number;
  set?: {
    name: string;
    item_count: number;
  };
}> {
  return apiRequest("/question-bank/import", {
    method: "POST",
    body: JSON.stringify({
      items,
      set_name: setName,
    }),
  });
}