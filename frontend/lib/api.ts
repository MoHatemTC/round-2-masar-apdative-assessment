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
  // Remaining time on the assessment's time limit, sent by /chat/turn on every turn.
  // Null when the assessment has no time limit.
  seconds_left?: number | null;
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

export interface Assessment {
  id: string;
  title: string;
  question_set_id: string;
  competency_ids: string[];
  time_limit_min: number | null;
}

export interface PaginationMeta {
  currentPage: number;
  totalPages: number;
  totalItems: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

export interface AssessmentCreate {
  title: string;
  question_set_id: string;
  time_limit_min: number;
}

export interface Invitation {
  id: string;
  session_id: string | null;
  candidate_email: string;
  status: "taken" | "in_progress" | "not_taken";
  invited_at: string;
}
export interface SandboxRunResult {
  provider_failed: boolean;
  timed_out: boolean;
  pass_rate: number;
  stderr: string;
  results: {
    passed: boolean;
    input: string;
    expected: string;
    actual: string;
    stderr: string;
  }[];
}


// ---- Report types ----

// Mirrors a `session_competency_results` row (005_reports.sql) as returned verbatim by
// GET /admin/sessions/{id}/report. The verified level and confidence are `final_level` /
// `final_confidence` — naming them level/confidence here made both read `undefined`, which
// rendered an empty Level column and a NaN confidence bar in the admin report.
export interface CompetencyResult {
  competency_id: string;
  self_rating: number | null;
  initial_estimate: number | null;
  final_level: number;
  final_confidence: number;
  questions_asked: number;
  converged_reason: string;
  low_confidence: boolean;
}

export interface AnswerDetail {
  question_number: number;
  question_body: string;
  tool_type: string;
  score: number;
  rationale: string;
  answer_text: string;
  flagged: boolean;
}

export interface SessionReport {
  session_id: string;
  overall_pct: number;
  level_label: string;
  has_low_confidence: boolean;
  competency_results: CompetencyResult[];
  answers: AnswerDetail[];
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
export async function runSandbox(params: {
  code: string;
  language: string;
  test_cases: unknown[];
}): Promise<SandboxRunResult> {
  return apiRequest("/sandbox/run", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
// ---- Candidate entry flow (session start via link/token -> intake -> loop) ----

// Resolves a `?token=` share link into the assessment's id, title, and the competencies the
// candidate needs to self-rate. Read-only, unauthenticated — the token itself is the credential.
export async function getAssessmentByToken(token: string): Promise<AssessmentInfo> {
  return apiRequest(`/assessments/by-token/${encodeURIComponent(token)}`);
}

// name/email are optional: an invite token already identifies the candidate server-side,
// so they only matter when someone opens an assessment without one.
export async function startSession(
  assessmentId: string,
  token?: string,
  candidateName?: string,
  candidateEmail?: string
): Promise<{ session_id: string }> {
  return apiRequest("/session/start", {
    method: "POST",
    body: JSON.stringify({
      assessment_id: assessmentId,
      token: token,
      candidate_name: candidateName,
      candidate_email: candidateEmail,
    }),
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
  question_number?: number;
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
// Candidate-facing report (GET /report/{id}). Deliberately narrower than SessionReport:
// no per-answer rows, no grading rationale — only what the candidate is allowed to see.
export interface CandidateReport {
  session_id: string;
  overall_pct: number;
  level_label: string;
  has_low_confidence: boolean;
  competency_results: CompetencyResult[];
}

export async function getCandidateReport(sessionId: string): Promise<CandidateReport> {
  return apiRequest<CandidateReport>(`/report/${sessionId}`);
}

export async function getReport(sessionId: string): Promise<SessionReport> {
  return apiRequest<SessionReport>(`/admin/sessions/${sessionId}/report`);
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

// Accepts the PRD flat format ({items, set_name}); the backend normalizes it and
// responds with the AdminImportSummary shape shared with /admin/import.
export async function importBank(
  items: unknown[],
  setName?: string
): Promise<AdminImportSummary> {
  return apiRequest("/admin/question-bank/import", {
    method: "POST",
    body: JSON.stringify({
      items,
      set_name: setName,
    }),
  });
}

export async function getAssessments(page: number = 1, limit: number = 10): Promise<PaginatedResponse<Assessment>> {
  return apiRequest<PaginatedResponse<Assessment>>(`/admin/assessments?page=${page}&limit=${limit}`);
}

// A row in the admin sessions list (GET /admin/sessions). Score and band come from
// final_reports and are null until the session finishes, so every result field is nullable.
export interface Session {
  id: string;
  session_id: string;
  assessment_id: string | null;
  candidate_name: string | null;
  candidate_email: string | null;
  status: string;
  created_at: string;
  completed_at: string | null;
  overall_pct: number | null;
  level_label: string | null;
  has_low_confidence: boolean | null;
}

export async function getSessions(assessmentId?: string, page: number = 1): Promise<PaginatedResponse<Session>> {
  const params = new URLSearchParams();
  if (assessmentId) params.append("assessment_id", assessmentId);
  params.append("page", String(page));
  return apiRequest<PaginatedResponse<Session>>(`/admin/sessions?${params.toString()}`);
}

export async function getInvitations(assessmentId: string, page: number = 1): Promise<PaginatedResponse<Invitation>> {
  return apiRequest<PaginatedResponse<Invitation>>(`/admin/assessments/${assessmentId}/invitations?page=${page}`);
}

export async function getCompetencies(setId: string): Promise<string[]> {
  return apiRequest<string[]>(`/admin/question-sets/${setId}/competencies`);
}

export interface QuestionSet {
  id: string;
  name: string;
  description?: string | null;
}

export async function getQuestionSets(): Promise<QuestionSet[]> {
  return apiRequest<QuestionSet[]>("/admin/question-sets/");
}

export interface CompetencyTrack {
  id: string;
  name: string;
  code?: string;
}

export async function getCompetencyTracks(): Promise<CompetencyTrack[]> {
  return apiRequest<CompetencyTrack[]>("/admin/competency-tracks");
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

export interface SendInvitationRequest {
  assessment_id: string;
  candidate_email: string;
}

export async function sendInvitation(payload: {
    assessment_id: string;
    candidate_email: string;
}) {
    return apiRequest("/admin/invitations", {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export interface QuestionBrowserItem {
  id: string;
  text: string;
  tool_type: string;
  difficulty: string;
  competency: {
    id: string;
    name: string;
  };
}

export async function browseQuestions(filters?: {
  tool_type?: string;
  competency?: string;
  difficulty?: number;
}, page: number = 1): Promise<PaginatedResponse<QuestionBrowserItem>> {
  const params = new URLSearchParams();

  if (filters?.tool_type)
    params.append("tool_type", filters.tool_type);

  if (filters?.competency)
    params.append("competency", filters.competency);

  if (filters?.difficulty)
    params.append("difficulty", String(filters.difficulty));

  params.append("page", String(page));

  return apiRequest<PaginatedResponse<QuestionBrowserItem>>(
    `/questions?${params.toString()}`
  );
}

export interface Competency {
  id: string;
  name: string;
  code: string;
}

export async function listCompetencies(): Promise<
  { id: string; name: string; code: string }[]
> {
  return apiRequest("/questions/competencies");
}