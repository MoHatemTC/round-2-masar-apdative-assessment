"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import FormField from "@/components/ui/FormField";
import { createAssessment, getCompetencies } from "@/lib/api";

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function CreateAssessmentPage() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [questionSetId, setQuestionSetId] = useState("");
  const [timeLimit, setTimeLimit] = useState("30");
  const [competencies, setCompetencies] = useState<string[]>([]);
  const [competenciesLoading, setCompetenciesLoading] = useState(false);
  const [competenciesError, setCompetenciesError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!UUID_REGEX.test(questionSetId)) {
      setCompetencies([]);
      setCompetenciesError(null);
      return;
    }

    setCompetenciesLoading(true);
    setCompetenciesError(null);

    getCompetencies(questionSetId)
      .then((data) => {
        setCompetencies(data);
        setCompetenciesLoading(false);
      })
      .catch((err) => {
        setCompetenciesError(err instanceof Error ? err.message : "Failed to load competencies");
        setCompetencies([]);
        setCompetenciesLoading(false);
      });
  }, [questionSetId]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError(null);

    try {
      await createAssessment({
        title,
        question_set_id: questionSetId,
        time_limit_min: parseInt(timeLimit, 10) || 30,
      });
      router.push("/admin/assessments");
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to create assessment");
      setSubmitting(false);
    }
  };

  const isFormValid = title.trim() !== "" && UUID_REGEX.test(questionSetId) && parseInt(timeLimit, 10) > 0;

  return (
    <div className="p-6 sm:p-10">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Create Assessment</h1>
      </div>
      <Card className="max-w-2xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          className="flex flex-col gap-5"
        >
          <FormField
            label="Title"
            value={title}
            onChange={setTitle}
            placeholder="e.g. Frontend Developer Assessment"
          />

          <div className="flex flex-col gap-1">
            <FormField
              label="Question Set ID"
              value={questionSetId}
              onChange={setQuestionSetId}
              placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
            />
            {competenciesLoading && (
              <div className="mt-2 flex items-center gap-2">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                <span className="text-xs text-gray-500 dark:text-gray-400">Loading competencies…</span>
              </div>
            )}
            {competenciesError && (
              <p className="mt-2 text-xs text-red-600 dark:text-red-400">{competenciesError}</p>
            )}
            {competencies.length > 0 && (
              <div className="mt-2">
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  Competency Track IDs
                </span>
                <div className="mt-1 flex flex-wrap gap-2">
                  {competencies.map((id) => (
                    <span
                      key={id}
                      className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900/40 px-3 py-1 text-xs font-medium text-blue-800 dark:text-blue-300"
                    >
                      {id}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <FormField
            label="Time Limit (minutes)"
            value={timeLimit}
            onChange={setTimeLimit}
            type="number"
            placeholder="30"
          />

          {submitError && (
            <p className="text-sm text-red-600 dark:text-red-400">{submitError}</p>
          )}

          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" disabled={!isFormValid || submitting}>
              {submitting ? "Creating…" : "Create Assessment"}
            </Button>
            <Button variant="secondary" onClick={() => router.push("/admin/assessments")}>
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
