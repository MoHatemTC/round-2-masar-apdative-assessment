"use client";

// Demo page for the voice E2E manual test. Wires the REAL VoiceRecorder
// component (the same one registered for tool_type: "voice" in
// app/assess/tools/registry.ts) into an actual page — record for real in the
// browser, submit for real to /api/sessions/.../voice-answer, then check the
// database with scripts/check_demo_answer.py.
//
// The question object below is intentionally hand-built with ONLY the fields
// VoiceRecorder needs (id, body, payload.time_limit_seconds). It deliberately
// does NOT include evaluation_criteria/answer_key/etc — mirroring the
// "answer-bearing fields never reach the browser" rule this codebase already
// has elsewhere (see the _ANSWER_KEYS comment in question_bank.py). This is a
// hand-built stand-in for the real "serve next question" endpoint, which
// belongs to the question-selection lane, not this one.

import { useState } from "react";
import { getAnswerComponent } from "@/app/assess/tools/registry";

const DEMO_SESSION_ID = "8f14e390-9b1a-4c1f-9e6a-9d6f0b7a1a22";
const DEMO_QUESTION_NUMBER = 1;

// Must match scripts/seed_demo_question.py — run that first.
const DEMO_QUESTION = {
  id: "8f14e390-9b1a-4c1f-9e6a-9d6f0b7a1a11",
  body:
    "You need to build a prompt that summarizes incoming customer support " +
    "tickets into structured fields (issue_category, severity, " +
    "customer_sentiment, requested_action) for automated triage. How would " +
    "you design and validate it before shipping?",
  payload: { time_limit_seconds: 120 },
};

export default function DemoVoicePage() {
  const [result, setResult] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  // Resolved through the real registry, exactly the way the actual
  // assessment flow picks a component for tool_type: "voice" — not imported
  // directly, so this page fails loudly if the registry mapping ever breaks.
  const VoiceRecorder = getAnswerComponent("voice");

  if (!VoiceRecorder) {
    return <div className="p-8 text-destructive">No component registered for tool_type "voice".</div>;
  }

  async function handleSubmit(res: unknown) {
    setSubmitting(true);
    setResult(res);
    setSubmitting(false);
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-xl font-semibold">Voice E2E demo</h1>
          <p className="text-sm text-muted-foreground">
            session_id: <code>{DEMO_SESSION_ID}</code> — question_number:{" "}
            <code>{DEMO_QUESTION_NUMBER}</code>
          </p>
        </div>

        <VoiceRecorder
          question={DEMO_QUESTION}
          sessionId={DEMO_SESSION_ID}
          onSubmit={handleSubmit}
          isSubmitting={submitting}
          questionNumber={DEMO_QUESTION_NUMBER} 
        />

        {result != null && (
          <div className="rounded-xl border border-border p-4 text-sm">
            <p className="font-medium mb-2">Response from /voice-answer:</p>
            <pre className="whitespace-pre-wrap break-words text-xs">
              {JSON.stringify(result, null, 2)}
            </pre>
            <p className="mt-3 text-muted-foreground">
              Now run <code>python scripts/check_demo_answer.py</code> to confirm this
              landed in the real `answers` table.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}