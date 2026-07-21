// app/assess/tools/OpenEndedText.tsx
"use client";

import { useState, useEffect, useRef } from "react";
import Button from "@/components/ui/Button";
import FormField from "@/components/ui/FormField";

export interface OpenEndedQuestion {
  id: string;
  body: string;
  payload: {
    time_limit_seconds?: number;
  };
}

export interface OpenEndedTextProps {
  question: OpenEndedQuestion;
  onSubmit: (result: { answer_text: string } | { skipped: true }) => void;
  isSubmitting?: boolean;
}

export default function OpenEndedText({ question, onSubmit, isSubmitting = false }: OpenEndedTextProps) {
  const [answer, setAnswer] = useState("");
  const timeLimit = question.payload.time_limit_seconds ?? 120; // fallback if not set
  const [secondsLeft, setSecondsLeft] = useState(timeLimit);
  const hasAutoSubmitted = useRef(false);

  useEffect(() => {
    if (secondsLeft <= 0) {
      if (!hasAutoSubmitted.current) {
        hasAutoSubmitted.current = true;
        onSubmit(answer.trim() ? { answer_text: answer } : { skipped: true });
      }
      return;
    }

    const timer = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft, answer, onSubmit]);

  const handleSubmit = () => {
    if (isSubmitting || !answer.trim()) return;
    onSubmit({ answer_text: answer });
  };

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;

  return (
    <div className="w-full max-w-xl mx-auto p-4 sm:p-6 rounded-lg bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-gray-100">
          {question.body}
        </h2>
        <span className={`text-sm font-mono ${secondsLeft <= 10 ? "text-red-500" : "text-gray-500 dark:text-gray-400"}`}>
          {minutes}:{seconds.toString().padStart(2, "0")}
        </span>
      </div>

      <FormField
        label="Your answer"
        value={answer}
        onChange={setAnswer}
        type="textarea"
        rows={6}
        placeholder="Type your answer here..."
      />

      <div className="mt-4 flex gap-2">
        <Button onClick={handleSubmit} disabled={isSubmitting || !answer.trim()}>
          {isSubmitting ? "Submitting…" : "Submit Answer"}
        </Button>
        <Button variant="secondary" onClick={() => onSubmit({ skipped: true })} disabled={isSubmitting}>
          Skip
        </Button>
      </div>
    </div>
  );
}