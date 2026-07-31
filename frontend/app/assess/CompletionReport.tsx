"use client";

import Card from "@/components/ui/Card";
import ScoreRing from "@/components/ui/ScoreRing";

interface CompletionReportProps {
  overall_pct: number;
  level_label: string;
  message?: string;
  has_low_confidence?: boolean;
}

/**
 * Candidate-facing completion screen.
 *
 * Renders the overall score and band label after the adaptive loop finishes.
 * Deliberately omits answer keys, correct answers, and grading rationale —
 * this component is on the candidate side and must NOT expose internal
 * assessment logic.
 */
export default function CompletionReport({
  overall_pct,
  level_label,
  message,
  has_low_confidence,
}: CompletionReportProps) {
  return (
    <div className="flex flex-col gap-5">
      {/* ── Low confidence warning ── */}
      {has_low_confidence && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="mt-0.5 h-5 w-5 shrink-0 text-warning"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z"
              clipRule="evenodd"
            />
          </svg>
          <p className="text-sm font-medium text-warning-foreground">
            Note: These results are marked as low confidence due to early
            termination or insufficient data.
          </p>
        </div>
      )}

      {/* ── Main result card ── */}
      <Card className="flex flex-col items-center gap-6 py-8">
        {/* Animated check mark */}
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-success/15">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-7 w-7 text-success"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        </div>

        <h2 className="text-xl font-semibold text-foreground">
          Assessment Complete
        </h2>

        {/* Score ring */}
        <ScoreRing value={overall_pct} size={180} strokeWidth={12} label="Overall Score" />

        {/* Band badge */}
        <span className="inline-flex items-center rounded-full bg-primary/15 px-4 py-1.5 text-sm font-semibold text-primary">
          {level_label}
        </span>

        {/* Optional message from the backend */}
        {message && (
          <p className="max-w-md text-center text-sm text-muted-foreground">
            {message}
          </p>
        )}

        <p className="max-w-sm text-center text-sm text-muted-foreground">
          Thank you for completing this assessment. Your results have been
          recorded and will be reviewed by the hiring team.
        </p>
      </Card>
    </div>
  );
}
