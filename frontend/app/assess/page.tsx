"use client";
// Candidate flow: intake (self-ratings) → adaptive Q&A → report.  [TODO: build out]
import { useState } from "react";
import { turn, type ToolResult } from "@/lib/api";
import { getAnswerComponent } from "./tools/registry";

export default function AssessPage() {
  const [sessionId, setSessionId] = useState("");
  const [question, setQuestion] = useState<any>(null);
  const [done, setDone] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function next(toolResult?: ToolResult) {
    setIsSubmitting(true);
    try {
      const r = await turn({ session_id: sessionId, tool_result: toolResult });
      if (r.complete) {
        setDone(r.emit);
        setQuestion(null);
      } else {
        setQuestion(r.emit);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  const AnswerComponent = question ? getAnswerComponent(question.tool_type) : null;

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
      {question && AnswerComponent && (
        <AnswerComponent
          question={question}
          onSubmit={(result: ToolResult) => next(result)}
          isSubmitting={isSubmitting}
        />
      )}
      {question && !AnswerComponent && (
        <p style={{ color: "red" }}>Unsupported question type: {question.tool_type}</p>
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