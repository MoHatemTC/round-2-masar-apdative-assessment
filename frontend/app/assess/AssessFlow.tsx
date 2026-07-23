"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  turn,
  type ToolResult,
  getAssessmentByToken,
  startSession,
  submitIntake,
  uploadCv,
  type AssessmentInfo,
} from "@/lib/api";
import { getAnswerComponent } from "./tools/registry";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import RatingScale from "@/components/ui/RatingScale";

type Step = "loading" | "invalid-link" | "welcome" | "intake" | "loop" | "done";

export default function AssessFlow() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [step, setStep] = useState<Step>("loading");
  const [assessment, setAssessment] = useState<AssessmentInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [sessionId, setSessionId] = useState("");
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [cvFeedback, setCvFeedback] = useState<string | null>(null);
  const [cvUploading, setCvUploading] = useState(false);
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [intakeSubmitting, setIntakeSubmitting] = useState(false);

  const [question, setQuestion] = useState<any>(null);
  const [done, setDone] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loopError, setLoopError] = useState<string | null>(null);

  // Step 1: resolve the share-link token into which assessment + competencies to show.
  useEffect(() => {
    if (!token) {
      setStep("invalid-link");
      return;
    }
    getAssessmentByToken(token)
      .then((info) => {
        setAssessment(info);
        setStep("welcome");
      })
      .catch((err) => {
        setLoadError(err instanceof Error ? err.message : "Could not load this assessment link.");
        setStep("invalid-link");
      });
  }, [token]);

  async function beginIntake() {
    if (!assessment) return;
    setIntakeSubmitting(true);
    setIntakeError(null);
    try {
      const { session_id } = await startSession(assessment.assessment_id);
      setSessionId(session_id);
      setStep("intake");
    } catch (err) {
      setIntakeError(err instanceof Error ? err.message : "Could not start the assessment.");
    } finally {
      setIntakeSubmitting(false);
    }
  }

  async function handleCvUpload(file: File) {
    setCvFeedback(null);
    setCvUploading(true);
    try {
      const result = await uploadCv(sessionId, file);
      setCvFeedback(
        `"${result.filename}" received (${result.characters_extracted.toLocaleString()} characters read).`
      );
    } catch (err) {
      setCvFeedback(err instanceof Error ? `Upload failed: ${err.message}` : "Upload failed.");
    } finally {
      setCvUploading(false);
    }
  }

  async function submitIntakeAndBegin() {
    if (!assessment) return;
    const missing = assessment.competencies.filter((c) => !ratings[c.id]);
    if (missing.length > 0) {
      setIntakeError(`Please rate: ${missing.map((c) => c.name).join(", ")}`);
      return;
    }
    setIntakeSubmitting(true);
    setIntakeError(null);
    try {
      await submitIntake(sessionId, ratings);
      setStep("loop");
      await next(); // errors from next() itself are caught inside next(), not here
    } catch (err) {
      setIntakeError(err instanceof Error ? err.message : "Could not save your ratings.");
    } finally {
      setIntakeSubmitting(false);
    }
  }

  async function next(toolResult?: ToolResult) {
    setIsSubmitting(true);
    setLoopError(null);
    try {
      const r = await turn({ session_id: sessionId, tool_result: toolResult });
      if (r.complete) {
        setDone(r.emit);
        setQuestion(null);
        setStep("done");
      } else {
        setQuestion(r.emit);
      }
    } catch (err) {
      // Without this, a failed turn (network issue, or a not-yet-implemented backend route)
      // left the screen blank with no indication anything went wrong.
      setLoopError(
        err instanceof Error ? err.message : "Something went wrong while loading the next question."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const AnswerComponent = question ? getAnswerComponent((question as any).tool_type) : null;

  if (step === "loading") {
    return (
      <main className="max-w-2xl mx-auto p-8 text-gray-600 dark:text-gray-400">
        Loading your assessment…
      </main>
    );
  }

  if (step === "invalid-link") {
    return (
      <main className="max-w-2xl mx-auto p-8">
        <Card>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Link not found</h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            {loadError ||
              "This assessment link is missing or invalid. Please use the link your recruiter sent you."}
          </p>
        </Card>
      </main>
    );
  }

  if (step === "welcome" && assessment) {
    return (
      <main className="max-w-2xl mx-auto p-8">
        <Card className="flex flex-col gap-4">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{assessment.title}</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            You&apos;ll first rate yourself on {assessment.competencies.length}{" "}
            competenc{assessment.competencies.length === 1 ? "y" : "ies"}, then answer a short set of
            adaptive questions.
          </p>
          {intakeError && <p className="text-sm text-red-600">{intakeError}</p>}
          <Button onClick={beginIntake} disabled={intakeSubmitting}>
            {intakeSubmitting ? "Starting…" : "Begin Assessment"}
          </Button>
        </Card>
      </main>
    );
  }

  if (step === "intake" && assessment) {
    return (
      <main className="max-w-2xl mx-auto p-8">
        <Card className="flex flex-col gap-6">
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Rate yourself</h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              For each competency, choose the level that best reflects your current skill (1 = novice,
              5 = expert).
            </p>
          </div>

          <div className="flex flex-col gap-5">
            {assessment.competencies.map((c) => (
              <RatingScale
                key={c.id}
                label={c.name}
                value={ratings[c.id] ?? null}
                onChange={(n) => setRatings((prev) => ({ ...prev, [c.id]: n }))}
                disabled={intakeSubmitting}
              />
            ))}
          </div>

          <div className="flex flex-col gap-2 border-t border-gray-200 dark:border-neutral-700 pt-4">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Upload your CV (optional)
            </label>
            <input
              type="file"
              accept=".pdf,.txt"
              disabled={cvUploading || intakeSubmitting}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleCvUpload(file);
              }}
              className="text-sm text-gray-600 dark:text-gray-400 file:mr-3 file:rounded-md file:border-0 file:bg-gray-100 dark:file:bg-neutral-800 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-gray-700 dark:file:text-gray-200 hover:file:bg-gray-200 dark:hover:file:bg-neutral-700"
            />
            {cvUploading && <p className="text-sm text-gray-500">Uploading…</p>}
            {cvFeedback && !cvUploading && (
              <p
                className={`text-sm ${
                  cvFeedback.startsWith("Upload failed") ? "text-red-600" : "text-green-600"
                }`}
              >
                {cvFeedback}
              </p>
            )}
          </div>

          {intakeError && <p className="text-sm text-red-600">{intakeError}</p>}

          <Button onClick={submitIntakeAndBegin} disabled={intakeSubmitting}>
            {intakeSubmitting ? "Starting…" : "Continue to Assessment"}
          </Button>
        </Card>
      </main>
    );
  }

  return (
    <main className="max-w-2xl mx-auto p-8">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Take the assessment
      </h1>

      {loopError && (
        <Card className="mb-4">
          <p className="text-sm text-red-600">Something went wrong: {loopError}</p>
        </Card>
      )}

      {question && AnswerComponent && (
        <AnswerComponent
          question={question}
          onSubmit={(result: ToolResult) => next(result)}
          isSubmitting={isSubmitting}
        />
      )}
      {question && !AnswerComponent && (
        <p className="text-red-600">Unsupported question type: {(question as any).tool_type}</p>
      )}
      {done && (
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Done</h2>
          <pre className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
            {JSON.stringify(done, null, 2)}
          </pre>
        </Card>
      )}
    </main>
  );
}