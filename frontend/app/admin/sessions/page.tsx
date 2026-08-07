"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import StatusBadge from "@/components/ui/StatusBadge";
import Pagination from "@/components/ui/Pagination";
import { getSessions, type Session, type PaginationMeta } from "@/lib/api";

function SessionsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const pageParam = Number(searchParams.get("page")) || 1;
  const [currentPage, setCurrentPage] = useState(pageParam);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [meta, setMeta] = useState<PaginationMeta>({ currentPage: 1, totalPages: 1, totalItems: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getSessions(undefined, currentPage)
      .then((res) => {
        setSessions(res.data);
        setMeta(res.meta);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load sessions");
        setLoading(false);
      });
  }, [currentPage]);

  function handlePageChange(page: number) {
    setCurrentPage(page);
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(page));
    router.push(`?${params.toString()}`, { scroll: false });
  }

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
        <Pagination
          currentPage={meta.currentPage}
          totalPages={meta.totalPages}
          onPageChange={handlePageChange}
        />
      </Card>
    </div>
  );
}

export default function SessionsPage() {
  return (
    <Suspense fallback={<div className="p-6 sm:p-10"><Card><div className="flex items-center justify-center py-12"><div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" /><span className="ml-3 text-sm text-muted-foreground">Loading…</span></div></Card></div>}>
      <SessionsContent />
    </Suspense>
  );
}
