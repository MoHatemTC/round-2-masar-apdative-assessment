"use client";
// Candidate flow: intake (self-ratings) → adaptive Q&A → report.  [TODO: build out]
import { useState } from "react";
import { turn } from "@/lib/api";

// Minimal driver: given a session_id (create via /session/start first), step through the loop.
export default function AssessPage() {
  const [sessionId, setSessionId] = useState("");
  const [question, setQuestion] = useState<any>(null);
  const [answer, setAnswer] = useState("");
  const [done, setDone] = useState<any>(null);

  async function next(toolResult?: unknown) {
    const r = await turn({ session_id: sessionId, tool_result: toolResult });
    if (r.complete) { setDone(r.emit); setQuestion(null); }
    else { setQuestion(r.emit); setAnswer(""); }
  }

  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h1>Take the assessment</h1>
      {/* TODO: build the real intake screen (1–5 self-rating per competency) + optional CV upload,
          then start the loop. This is a bare driver to prove the turn cycle. */}
      {!question && !done && (
        <div>
          <input placeholder="session_id" value={sessionId} onChange={(e) => setSessionId(e.target.value)}
                 style={{ padding: 8, width: "70%" }} />
          <button onClick={() => next()} disabled={!sessionId} style={{ marginLeft: 8, padding: 8 }}>Start</button>
        </div>
      )}
      {question && (
        <div>
          <p style={{ fontWeight: 600 }}>Q{question.question_number} · {question.tool_type}</p>
          <p>{question.body}</p>
          {/* TODO: render per-type input (MCQ options, code editor, textarea/voice, chart) from question.payload */}
          <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={4} style={{ width: "100%" }} />
          <button onClick={() => next({ answer_text: answer })} style={{ marginTop: 8, padding: "8px 16px" }}>Submit</button>
        </div>
      )}
      {done && (
        <div>
          <h2>Done</h2>
          <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(done, null, 2)}</pre>
          {/* TODO: fetch + render the real report (per-competency level + overall %/band) */}
        </div>
      )}
    </main>
  );
}
