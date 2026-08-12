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
    data?: string;
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
  const data = question.payload.data;

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
      ) : data ? (
        <pre className="mb-4 whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-neutral-800 rounded-md p-4 border border-gray-200 dark:border-neutral-700">
          {data}
        </pre>
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

      <div className="flex flex-col-reverse sm:flex-row gap-3 pt-4">
        <Button variant="secondary" onClick={() => onSubmit({ skipped: true })} disabled={isSubmitting} className="w-full sm:w-auto">
          Skip
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting || !insights.trim()}
          className="w-full sm:w-auto sm:ml-auto"
        >
          {isSubmitting ? "Submitting…" : "Submit Answer"}
        </Button>
      </div>
    </div>
  );
}