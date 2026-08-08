"use client";
import { useState } from "react";
import Button from "@/components/ui/Button";

// Types match the payload shape from schemas/question_types.py
export interface TextQuestion {
  id: string;
  body: string;
  payload: Record<string, unknown>;
}

export interface TextAnswerProps {
  question: TextQuestion;
  onSubmit: (result: { answer_text: string } | { skipped: true }) => void;
  isSubmitting?: boolean;
}

const MIN_CHARS = 10;

export default function TextAnswer({ question, onSubmit, isSubmitting = false }: TextAnswerProps) {
  const [answer, setAnswer] = useState("");

  const trimmedLength = answer.trim().length;
  const canSubmit = !isSubmitting && trimmedLength >= MIN_CHARS;

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit({ answer_text: answer.trim() });
  };

  const handleSkip = () => {
    if (isSubmitting) return;
    onSubmit({ skipped: true });
  };

  return (
    <div className="w-full max-w-xl mx-auto p-5 sm:p-7 rounded-2xl bg-card border border-border shadow-md">
      <h2 className="text-lg sm:text-xl font-semibold text-foreground leading-snug mb-5">
        {question.body}
      </h2>

      <label htmlFor={`text-answer-${question.id}`} className="sr-only">
        Your answer
      </label>
      <textarea
        id={`text-answer-${question.id}`}
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        disabled={isSubmitting}
        rows={6}
        placeholder="Type your answer here…"
        className="w-full rounded-lg border border-border bg-background
          p-3 text-sm sm:text-base text-foreground placeholder:text-muted-foreground
          focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent
          disabled:opacity-50 disabled:cursor-not-allowed
          resize-y transition-colors"
      />

      <div className="flex items-center justify-between mt-2 mb-5">
        <span className="text-xs text-muted-foreground tabular-nums">
          {trimmedLength < MIN_CHARS
            ? `Write at least ${MIN_CHARS} characters`
            : `${trimmedLength} characters`}
        </span>
      </div>

      <div className="flex flex-col-reverse sm:flex-row gap-3 pt-1">
        <Button variant="secondary" onClick={handleSkip} disabled={isSubmitting} className="w-full sm:w-auto">
          Skip
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full sm:w-auto sm:ml-auto"
        >
          {isSubmitting ? "Submitting…" : "Submit Answer"}
        </Button>
      </div>
    </div>
  );
}
