// app/assess/tools/DataAnalysis.tsx
"use client";

import { useState } from "react";
import Table from "@/components/ui/Table";
import FormField from "@/components/ui/FormField";
import Button from "@/components/ui/Button";

export interface DataAnalysisQuestion {
  id: string;
  body: string;
  payload: {
    dataset?: {
      headers: string[];
      rows: (string | number)[][];
    };
  };
}

export interface DataAnalysisProps {
  question: DataAnalysisQuestion;
  onSubmit: (result: { insights_text: string } | { skipped: true }) => void;
  isSubmitting?: boolean;
}

export default function DataAnalysis({ question, onSubmit, isSubmitting = false }: DataAnalysisProps) {
  const [insights, setInsights] = useState("");
  const dataset = question.payload.dataset;

  const handleSubmit = () => {
    if (isSubmitting || !insights.trim()) return;
    onSubmit({ insights_text: insights });
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-4 sm:p-6 rounded-lg bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700">
      <h2 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
        {question.body}
      </h2>

      {dataset ? (
        <div className="mb-4">
          <Table headers={dataset.headers} rows={dataset.rows} />
        </div>
      ) : (
        <p className="text-sm text-gray-400 mb-4">No dataset provided for this question.</p>
      )}

      <FormField
        label="Your insights"
        value={insights}
        onChange={setInsights}
        type="textarea"
        rows={6}
        placeholder="What do you notice in this data?"
      />

      <div className="mt-4 flex gap-2">
        <Button onClick={handleSubmit} disabled={isSubmitting || !insights.trim()}>
          {isSubmitting ? "Submitting…" : "Submit Answer"}
        </Button>
        <Button variant="secondary" onClick={() => onSubmit({ skipped: true })} disabled={isSubmitting}>
          Skip
        </Button>
      </div>
    </div>
  );
}