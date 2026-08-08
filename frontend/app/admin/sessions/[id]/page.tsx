"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Table from "@/components/ui/Table";
import ScoreRing from "@/components/ui/ScoreRing";
import {
  getReport,
  type SessionReport,
  type AnswerDetail,
} from "@/lib/api";

export default function SessionReportPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id;

  const [report, setReport] = useState<SessionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Track which answer cards are expanded (accordion)
  const [expandedAnswers, setExpandedAnswers] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!sessionId) return;
    getReport(sessionId)
      .then((data) => {
        setReport(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load report");
        setLoading(false);
      });
  }, [sessionId]);

  function toggleAnswer(questionNumber: number) {
    setExpandedAnswers((prev) => {
      const next = new Set(prev);
      if (next.has(questionNumber)) {
        next.delete(questionNumber);
      } else {
        next.add(questionNumber);
      }
      return next;
    });
  }

  if (loading) {
    return (
      <div className="p-6 sm:p-10">
        <Card>
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
            <span className="ml-3 text-sm text-muted-foreground">Loading report…</span>
          </div>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 sm:p-10">
        <Card>
          <div className="flex flex-col items-center gap-3 py-12">
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="secondary" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!report) return null;

  // ── Competency results table ──
  const compHeaders = ["Competency ID", "Level", "Confidence", "Qs Asked", "Converged"];
  const compRows = report.competency_results.map((cr) => [
    <span key={`cid-${cr.competency_id}`} className="font-mono text-xs text-muted-foreground">
      {cr.competency_id.slice(0, 8)}…
    </span>,
    <span key={`lvl-${cr.competency_id}`} className="font-semibold text-foreground">
      {cr.final_level}
    </span>,
    <ConfidenceBar key={`conf-${cr.competency_id}`} value={cr.final_confidence} />,
    <span key={`qa-${cr.competency_id}`} className="tabular-nums text-foreground">
      {cr.questions_asked}
    </span>,
    <span
      key={`reason-${cr.competency_id}`}
      className="inline-flex items-center rounded-full bg-subtle px-2 py-0.5 text-xs font-medium text-subtle-foreground capitalize"
    >
      {cr.converged_reason}
    </span>,
  ]);

  return (
    <div className="p-6 sm:p-10">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Session Report</h1>
        <Button variant="secondary" onClick={() => router.back()}>
          ← Back
        </Button>
      </div>

      {/* ── Low confidence warning ── */}
      {report.has_low_confidence && (
        <div
          role="alert"
          className="mb-6 flex items-start gap-3 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3"
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
            Low Confidence: This session ended early or lacked sufficient data. Results may not
            fully reflect the candidate&apos;s ability.
          </p>
        </div>
      )}

      {/* ── Section 1: Summary ── */}
      <Card className="mb-6 flex flex-col sm:flex-row items-center gap-8 py-8">
        <ScoreRing value={report.overall_pct} size={160} strokeWidth={11} label="Overall Score" />

        <div className="flex flex-col items-center sm:items-start gap-3">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-muted-foreground">Band:</span>
            <span className="inline-flex items-center rounded-full bg-primary/15 px-3.5 py-1 text-sm font-semibold text-primary">
              {report.level_label}
            </span>
          </div>
          <p className="text-xs text-muted-foreground font-mono">
            Session: {report.session_id.slice(0, 8)}…
          </p>
        </div>
      </Card>

      {/* ── Section 2: Competency Results ── */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-foreground mb-3">Competency Results</h2>
        <Card>
          <Table headers={compHeaders} rows={compRows} />
        </Card>
      </div>

      {/* ── Section 3: Answer Drill-Down (Accordion) ── */}
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-3">
          Answer Drill-Down
          <span className="ml-2 text-sm font-normal text-muted-foreground">
            ({report.answers.length} question{report.answers.length !== 1 ? "s" : ""})
          </span>
        </h2>
        <div className="flex flex-col gap-3">
          {report.answers.map((answer) => (
            <AnswerCard
              key={answer.question_number}
              answer={answer}
              isExpanded={expandedAnswers.has(answer.question_number)}
              onToggle={() => toggleAnswer(answer.question_number)}
            />
          ))}
          {report.answers.length === 0 && (
            <Card className="py-8">
              <p className="text-center text-sm text-muted-foreground italic">
                No answers recorded for this session.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────
// Sub-components
// ────────────────────────────────────────────────────────

/** Compact confidence bar with percentage */
function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="h-2 flex-1 rounded-full bg-border overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground w-10 text-right">{pct}%</span>
    </div>
  );
}

/** Collapsible answer card for the drill-down accordion */
function AnswerCard({
  answer,
  isExpanded,
  onToggle,
}: {
  answer: AnswerDetail;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  // Score color: 0-1 red, 2 amber, 3 info-blue, 4-5 green
  let scoreColor: string;
  if (answer.score >= 4) scoreColor = "text-success bg-success/15";
  else if (answer.score === 3) scoreColor = "text-info bg-info/15";
  else if (answer.score === 2) scoreColor = "text-warning bg-warning/15";
  else scoreColor = "text-destructive bg-destructive/15";

  return (
    <div
      className={
        "rounded-xl border transition-colors duration-150 " +
        (answer.flagged
          ? "border-destructive/40 bg-destructive/5"
          : "border-border bg-card")
      }
    >
      {/* Header — always visible, clickable */}
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-subtle/50 rounded-xl"
      >
        {/* Question number */}
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground">
          {answer.question_number}
        </span>

        {/* Question body (truncated) */}
        <span className="flex-1 truncate text-sm font-medium text-foreground">
          {answer.question_body}
        </span>

        {/* Tool type badge */}
        <span className="hidden sm:inline-flex items-center rounded-md bg-subtle px-2 py-0.5 text-[11px] font-medium text-subtle-foreground capitalize">
          {answer.tool_type.replace(/_/g, " ")}
        </span>

        {/* Score pill */}
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold ${scoreColor}`}>
          {answer.score}/5
        </span>

        {/* Flagged indicator */}
        {answer.flagged && (
          <span className="inline-flex items-center rounded-full bg-destructive/15 px-2 py-0.5 text-xs font-semibold text-destructive">
            ⚑ Flagged
          </span>
        )}

        {/* Chevron */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-5 w-5 shrink-0 text-muted-foreground transition-transform duration-200 ${
            isExpanded ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* Expanded body */}
      {isExpanded && (
        <div className="border-t border-border/60 px-4 py-4 space-y-4">
          {/* Candidate's answer */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
              Candidate&apos;s Answer
            </h4>
            <p className="text-sm text-foreground whitespace-pre-wrap rounded-lg bg-subtle/60 px-3 py-2">
              {answer.transcript || answer.answer_text || <span className="italic text-muted-foreground">No answer provided</span>}
            </p>
          </div>

          {/* AI Rationale */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
              AI Grading Rationale
            </h4>
            <p className="text-sm text-foreground whitespace-pre-wrap rounded-lg bg-subtle/60 px-3 py-2">
              {answer.rationale || <span className="italic text-muted-foreground">No rationale available</span>}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
