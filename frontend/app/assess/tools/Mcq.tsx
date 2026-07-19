"use client";

import { useState } from "react";

// Types match the payload shape from schemas/question_types.py
export interface McqOption {
  id: string;
  text: string;
}

export interface McqQuestion {
  id: string;
  body: string;
  payload: {
    options: McqOption[];
    // answer_key intentionally NOT used here — grading is server-side only,
    // the candidate-facing question should never carry the correct answer.
  };
}

export interface McqProps {
  question: McqQuestion;
  onSubmit: (result: { selected_id: string | null } | { skipped: true }) => void;
  isSubmitting?: boolean;
}

export default function Mcq({ question, onSubmit, isSubmitting = false }: McqProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const handleSubmit = () => {
    if (isSubmitting || selected === null) return;
    onSubmit({ selected_id: selected });
  };
  const handleSkip = () => {
  if (isSubmitting) return;
  onSubmit({ skipped: true });
  };

  return (
    <div className="mcq-tool w-full max-w-xl mx-auto p-4 sm:p-6 rounded-lg bg-white dark:bg-neutral-900 text-black dark:text-white">
      <h2 className="text-lg sm:text-xl font-semibold mb-4">
        {question.body}
      </h2>

      <fieldset disabled={isSubmitting} className="flex flex-col gap-2 sm:gap-3">
        <legend className="sr-only">Choose one answer</legend>
        {question.payload.options.map((option) => (
          <label
            key={option.id}
            className={`flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-colors
              ${
                selected === option.id
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-950"
                  : "border-gray-200 dark:border-neutral-700 hover:bg-gray-50 dark:hover:bg-neutral-800"
              }`}
          >
            <input
              type="radio"
              name={`mcq-${question.id}`}
              value={option.id}
              checked={selected === option.id}
              onChange={() => setSelected(option.id)}
              className="h-4 w-4"
            />
            <span className="text-sm sm:text-base">{option.text}</span>
          </label>
        ))}
      </fieldset>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={isSubmitting || selected === null}
        className="flex-1 sm:flex-none px-4 py-2 rounded-md bg-blue-600 text-white font-medium
          disabled:opacity-50 disabled:cursor-not-allowed
          hover:bg-blue-700 dark:hover:bg-blue-500 transition-colors"
      >
        {isSubmitting ? "Submitting…" : "Submit Answer"}
      </button>
      <button
        type="button"
        onClick={handleSkip}
        disabled={isSubmitting}
        className="px-4 py-2 rounded-md border border-gray-300 dark:border-neutral-700 text-sm"
      >
        Skip
      </button>
    </div>
  );
}