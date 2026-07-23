const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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

export interface Assessment {
  id: string;
  title: string;
  question_set_id: string;
  competency_ids: string[];
  time_limit_min: number | null;
}

export interface AssessmentCreate {
  title: string;
  question_set_id: string;
  time_limit_min: number;
}

export interface Invitation {
  id: string;
  candidate_email: string;
  status: "taken" | "in_progress" | "not_taken";
  invited_at: string;
}

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

export async function startSession(): Promise<{ session_id: string }> {
  return apiRequest("/session/start", { method: "POST" });
}

export async function submitIntake(sessionId: string, ratings: Record<string, unknown>): Promise<Record<string, unknown>> {
  return apiRequest(`/session/${sessionId}/intake`, {
    method: "POST",
    body: JSON.stringify(ratings),
  });
}

export async function turn(params: {
  session_id: string;
  tool_result?: ToolResult;
}): Promise<TurnResponse> {
  return apiRequest("/chat/turn", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function getReport(sessionId: string): Promise<Record<string, unknown>> {
  return apiRequest(`/admin/sessions/${sessionId}/report`);
}

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

export async function getAssessments(): Promise<Assessment[]> {
  return apiRequest<Assessment[]>("/admin/assessments");
}

export async function getInvitations(assessmentId: string): Promise<Invitation[]> {
  return apiRequest<Invitation[]>(`/admin/assessments/${assessmentId}/invitations`);
}

export async function getCompetencies(setId: string): Promise<string[]> {
  return apiRequest<string[]>(`/admin/question-sets/${setId}/competencies`);
}

export async function createAssessment(payload: AssessmentCreate): Promise<Assessment> {
  return apiRequest<Assessment>("/admin/assessments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---- Admin Question Bank Import API ----
// Matches FastAPI:
// POST /admin/import
//
// Body:
// {
//   competencies: [],
//   questions: [],
//   question_set: {
//      name,
//      description,
//      items
//   }
// }
//
// Response:
// {
//   success,
//   competencies_imported,
//   questions_imported,
//   question_set_items_imported,
//   errors
// }


export interface ImportValidationError {
  row: number;
  field: string;
  message: string;
}

export interface AdminImportSummary {
  success: boolean;
  competencies_imported: number;
  questions_imported: number;
  question_set_items_imported: number;
  errors: ImportValidationError[];
}


export async function adminImportBank(
  payload: unknown
): Promise<AdminImportSummary> {

  return apiRequest("/admin/import", {
    method: "POST",
    body: JSON.stringify(payload),
  });

}