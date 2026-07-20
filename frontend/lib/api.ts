// Thin API client for the backend. Set NEXT_PUBLIC_API in .env.local (default localhost:8000).
const BASE = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? "Request failed");
  return res.json();
}

// ── Admin ──
export const getQuestionTypes = () => req<any[]>("/admin/question-bank/types");
export const importBank = (items: unknown[], setName?: string) =>
  req<{ questions: number; set: { id: string; name: string; item_count: number } | null }>(
    `/admin/question-bank/import${setName ? `?set_name=${encodeURIComponent(setName)}` : ""}`,
    { method: "POST", body: JSON.stringify(items) });
export const getSetCompetencies = (setId: string) =>
  req<any[]>(`/admin/question-sets/${setId}/competencies`);
export const createAssessment = (body: unknown) =>
  req<{ id: string }>("/admin/assessments", { method: "POST", body: JSON.stringify(body) });

// ── Candidate ──
export const startSession = (body: unknown) =>
  req<{ session_id: string }>("/session/start", { method: "POST", body: JSON.stringify(body) });
export const submitIntake = (sessionId: string, body: unknown) =>
  req(`/session/${sessionId}/intake`, { method: "POST", body: JSON.stringify(body) });
export const turn = (body: unknown) =>
  req<{ emit: any; complete: boolean }>("/chat/turn", { method: "POST", body: JSON.stringify(body) });
