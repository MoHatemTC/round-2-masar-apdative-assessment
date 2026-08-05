"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  turn,
  type ToolResult,
  type Question,
  getAssessmentByToken,
  startSession,
  submitIntake,
  uploadCv,
  type AssessmentInfo,
} from "@/lib/api";
import { getAnswerComponent } from "./tools/registry";
import CompletionReport from "./CompletionReport";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import RatingScale from "@/components/ui/RatingScale";
import FrameCaptureRecorder from "@/components/proctoring/FrameCaptureRecorder";

type Step = "loading" | "invalid-link" | "welcome" | "intake" | "loop" | "done";

export default function AssessFlow() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const resumeSessionId = searchParams.get("session_id");

  const [step, setStep] = useState<Step>("loading");
  const [assessment, setAssessment] = useState<AssessmentInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [sessionId, setSessionId] = useState(resumeSessionId ?? "");
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [cvFeedback, setCvFeedback] = useState<string | null>(null);
  const [cvUploading, setCvUploading] = useState(false);
  const [intakeError, setIntakeError] = useState<string | null>(null);
  const [intakeSubmitting, setIntakeSubmitting] = useState(false);

  const [question, setQuestion] = useState<Question | null>(null);
  const [done, setDone] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loopError, setLoopError] = useState<string | null>(null);
  const [flushTick, setFlushTick] = useState(0);

  // Step 1: resolve the share-link token into which assessment + competencies to show.
  // If returning from consent with a session_id, skip straight to intake.
  useEffect(() => {
    if (!token) {
      setStep("invalid-link");
      return;
    }
    getAssessmentByToken(token)
      .then((info) => {
        setAssessment(info);
        setStep(resumeSessionId ? "intake" : "welcome");
      })
      .catch((err) => {
        setLoadError(err instanceof Error ? err.message : "Could not load this assessment link.");
        setStep("invalid-link");
      });
  }, [token, resumeSessionId]);

  async function beginIntake() {
    if (!assessment) return;
    setIntakeSubmitting(true);
    setIntakeError(null);
    try {
      const { session_id } = await startSession(assessment.assessment_id, token);
      setSessionId(session_id);
      // Redirect to consent + reference photo flow before starting the assessment.
      // The consent page redirects back here with ?token= after completion.
      router.push(
        `/assess/consent?session_id=${encodeURIComponent(session_id)}&token=${encodeURIComponent(token ?? "")}`,
      );
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
    setFlushTick((t) => t + 1); // flush proctoring frames on each submit
    setIsSubmitting(true);
    setLoopError(null);
    try {
      const r = await turn({
        session_id: sessionId,
        question_number: toolResult ? question?.question_number : undefined,
        tool_result: toolResult,
      });
      if (r.complete) {
        setDone(r.emit);
        setQuestion(null);
        setStep("done");
      } else {
        setQuestion(r.emit as Question);
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

  const allCompetenciesRated =
  assessment?.competencies.every((c) => ratings[c.id] !== undefined) ?? false;

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
      
          <div className="rounded-md bg-gray-100 dark:bg-neutral-800 p-4">
            <h3 className="font-medium">Assessment Summary</h3>

            <p className="mt-2 text-sm">
              Competencies:
              <strong> {assessment.competencies.length}</strong>
            </p>

            <p className="text-sm">
              Adaptive questions based on your responses.
            </p>
          </div>
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
              accept=".pdf,.doc,.docx,.txt"
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

          <Button
            onClick={submitIntakeAndBegin}
            disabled={!allCompetenciesRated || intakeSubmitting}
          >
            {intakeSubmitting ? "Starting…" : "Continue to Assessment"}
          </Button>
        </Card>
      </main>
    );
  }

  return (
    <main className="max-w-2xl mx-auto p-8">
      {/* Proctoring: capture frames every ~20s during the Q&A phase */}
      <FrameCaptureRecorder
        sessionId={sessionId}
        questionNumber={(question as any)?.question_number ?? null}
        isActive={step === "loop" && !done}
        flushSignal={flushTick}
      />

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
          key={(question as any).question_number ?? (question as any).id}
          question={question}
          onSubmit={(result: ToolResult) => next(result)}
          isSubmitting={isSubmitting}
          sessionId={sessionId}
          questionNumber={(question as any).question_number}
        />
      )}
      {question && !AnswerComponent && (
        <p className="text-red-600">Unsupported question type: {(question as any).tool_type}</p>
      )}
      {done && (
        <>
          <Card className="text-center py-8">
            <h2 className="text-2xl font-semibold text-green-600">
              Assessment Completed!
            </h2>

            <p className="mt-4 text-gray-600 dark:text-gray-400">
              Thank you for completing the assessment.
            </p>

            <p className="mt-2 text-gray-600 dark:text-gray-400">
              Your report is being generated and will be available shortly.
            </p>
          </Card>
          <CompletionReport
            overall_pct={done.overall_pct ?? 0}
            level_label={done.level_label ?? ""}
            message={done.message}
            has_low_confidence={done.has_low_confidence}
          />
        </>
      )}
    </main>
  );
}
