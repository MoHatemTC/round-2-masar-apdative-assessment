"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import Table from "@/components/ui/Table";
import Button from "@/components/ui/Button";
import StatusBadge from "@/components/ui/StatusBadge";
import { getSessions, type Session } from "@/lib/api";

export default function SessionsPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSessions()
      .then((data) => {
        setSessions(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load sessions");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="p-6 sm:p-10">
        <Card>
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
            <span className="ml-3 text-sm text-muted-foreground">Loading sessions…</span>
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

  const tableHeaders = ["Candidate", "Email", "Status", "Score", "Band", "Created"];

  const tableRows = sessions.map((s) => [
    <span key={`name-${s.id}`} className="font-medium text-foreground">
      {s.candidate_name || "—"}
    </span>,
    <span key={`email-${s.id}`} className="text-sm text-muted-foreground">
      {s.candidate_email || "—"}
    </span>,
    <StatusBadge key={`status-${s.id}`} status={s.status === "completed" ? "taken" : s.status === "in_progress" ? "in_progress" : "not_taken"} />,
    <span key={`score-${s.id}`} className="tabular-nums font-semibold text-foreground">
      {s.overall_pct != null ? `${Math.round(s.overall_pct)}%` : "—"}
    </span>,
    <span key={`band-${s.id}`} className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.level_label ? "bg-primary/15 text-primary" : "text-muted-foreground"}`}>
      {s.level_label || "—"}
    </span>,
    <span key={`date-${s.id}`} className="text-sm text-muted-foreground tabular-nums">
      {new Date(s.created_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })}
    </span>,
  ]);

  return (
    <div className="p-6 sm:p-10">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Sessions</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          All candidate assessment sessions. Click a completed session to view the full report.
        </p>
      </div>
      <Card>
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="bg-subtle/60">
              <tr className="border-b border-border">
                {tableHeaders.map((header, i) => (
                  <th
                    key={i}
                    className="px-4 py-2.5 font-semibold text-xs uppercase tracking-wider text-muted-foreground"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => {
                const isCompleted = s.status === "completed" || s.status === "taken";
                const handleRowClick = () => {
                  if (!isCompleted) return;
                  const targetId = s.session_id || s.id;
                  if (!targetId) {
                    console.error(
                      `Missing target report/session identifier for session marked as '${s.status}':`,
                      s
                    );
                    return;
                  }
                  router.push(`/admin/sessions/${targetId}`);
                };
                return (
                  <tr
                    key={s.id}
                    onClick={isCompleted ? handleRowClick : undefined}
                    className={
                      "border-b border-border/60 last:border-b-0 transition-colors " +
                      (isCompleted
                        ? "cursor-pointer hover:bg-primary/5 active:bg-primary/10"
                        : "hover:bg-subtle/70")
                    }
                  >
                    <td className="px-4 py-2.5 font-medium text-foreground">
                      {s.candidate_name || "—"}
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground">
                      {s.candidate_email || "—"}
                    </td>
                    <td className="px-4 py-2.5" onClick={(e) => e.stopPropagation()}>
                      <StatusBadge status={s.status === "completed" ? "taken" : s.status === "in_progress" ? "in_progress" : "not_taken"} />
                    </td>
                    <td className="px-4 py-2.5 tabular-nums font-semibold text-foreground">
                      {s.overall_pct != null ? `${Math.round(s.overall_pct)}%` : "—"}
                    </td>
                    <td className="px-4 py-2.5" onClick={(e) => e.stopPropagation()}>
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.level_label ? "bg-primary/15 text-primary" : "text-muted-foreground"}`}>
                        {s.level_label || "—"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground tabular-nums">
                      {new Date(s.created_at).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </td>
                  </tr>
                );
              })}
              {sessions.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-sm text-muted-foreground italic">
                    No sessions found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
