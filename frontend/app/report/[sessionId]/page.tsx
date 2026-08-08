"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getCandidateReport, type CandidateReport } from "@/lib/api";
import CompletionReport from "@/app/assess/CompletionReport";
import Card from "@/components/ui/Card";

export default function CandidateReportPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;

  const [report, setReport] = useState<CandidateReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    getCandidateReport(sessionId)
      .then((data) => {
        setReport(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load report");
        setLoading(false);
      });
  }, [sessionId]);

  if (loading) {
    return (
      <main className="max-w-2xl mx-auto p-8">
        <Card>
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
            <span className="ml-3 text-sm text-muted-foreground">Loading your report…</span>
          </div>
        </Card>
      </main>
    );
  }

  if (error) {
    return (
      <main className="max-w-2xl mx-auto p-8">
        <Card>
          <div className="flex flex-col items-center gap-3 py-12">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        </Card>
      </main>
    );
  }

  if (!report) return null;

  return (
    <main className="max-w-2xl mx-auto p-8">
      <CompletionReport
        overall_pct={report.overall_pct}
        level_label={report.level_label}
        has_low_confidence={report.has_low_confidence}
      />
    </main>
  );
}
