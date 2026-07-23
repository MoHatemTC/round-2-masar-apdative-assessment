"use client";

import { useState } from "react";
import { getAnswerComponent } from "../assess/tools/registry";
import type { ToolResult } from "@/lib/api";

const sampleQuestion = {
  id: "q-voice-1",
  tool_type: "voice",
  body: "Were you ever a team leader.",
  payload: {
    time_limit_seconds: 90,
    evaluation_criteria: ["Names the situation", "Explains their actions", "Reflects on the outcome"],
  },
};

export default function TestOpenEndedPage() {
  const [result, setResult] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const AnswerComponent = getAnswerComponent(sampleQuestion.tool_type);

  async function handleSubmit(toolResult: ToolResult) {
    setIsSubmitting(true);
    try {
      const res = await fetch("http://localhost:8000/demo/grade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_type: sampleQuestion.tool_type,
          question: sampleQuestion,
          tool_result: toolResult,
          session_id: crypto.randomUUID(),
        }),
      });
      const graded = await res.json();
      setResult(graded);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <header className="mb-8 sm:mb-10">
    <div className="flex flex-col items-center gap-6 p-8">
      {AnswerComponent && (
        <AnswerComponent question={sampleQuestion} onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      )}
      {result && (
        <pre className="rounded-lg border border-border bg-subtle p-4 text-sm whitespace-pre-wrap">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
    </header>
  );
}