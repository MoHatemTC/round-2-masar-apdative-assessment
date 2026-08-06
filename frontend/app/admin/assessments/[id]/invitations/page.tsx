"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import Table from "@/components/ui/Table";
import Button from "@/components/ui/Button";
import StatusBadge from "@/components/ui/StatusBadge";
import { getInvitations, type Invitation } from "@/lib/api";

export default function InvitationsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const assessmentId = params.id;

  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!assessmentId) return;
    getInvitations(assessmentId)
      .then((data) => {
        setInvitations(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load invitations");
        setLoading(false);
      });
  }, [assessmentId]);

  if (loading) {
    return (
      <div className="p-6 sm:p-10">
        <Card>
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
            <span className="ml-3 text-sm text-muted-foreground">Loading invitations…</span>
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

  // ── Empty state ──
  if (invitations.length === 0) {
    return (
      <div className="p-6 sm:p-10">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-foreground">Candidates</h1>
        </div>
        <Card className="flex flex-col items-center gap-4 py-16">
          {/* Empty inbox icon */}
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-7 w-7 text-muted-foreground"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21.75 9v.906a2.25 2.25 0 01-1.183 1.981l-6.478 3.488M2.25 9v.906a2.25 2.25 0 001.183 1.981l6.478 3.488m8.839 2.51l-4.66-2.51m0 0l-1.023-.55a2.25 2.25 0 00-2.134 0l-1.022.55m0 0l-4.661 2.51m16.5-1.826V9.748a2.25 2.25 0 00-1.183-1.981l-6.478-3.488a2.25 2.25 0 00-2.134 0L3.433 7.767A2.25 2.25 0 002.25 9.748v5.502"
              />
            </svg>
          </div>
          <p className="text-sm font-medium text-muted-foreground">
            No invitations sent yet.
          </p>
          <p className="max-w-xs text-center text-xs text-muted-foreground">
            Use the API or admin tools to invite candidates to this assessment.
          </p>
        </Card>
      </div>
    );
  }

  // ── Table ──
  const tableHeaders = ["Candidate Email", "Status", "Invited At"];

  const tableRows = invitations.map((inv) => [
    // Email
    <span key={`email-${inv.id}`} className="font-medium text-foreground">
      {inv.candidate_email}
    </span>,
    // Status badge
    <StatusBadge key={`status-${inv.id}`} status={inv.status} />,
    // Invited at — formatted date
    <span key={`date-${inv.id}`} className="text-sm text-muted-foreground tabular-nums">
      {new Date(inv.invited_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })}
    </span>,
  ]);

  return (
    <div className="p-6 sm:p-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Candidates</h1>
        <Button variant="secondary" onClick={() => router.push("/admin/assessments")}>
          ← Back to Assessments
        </Button>
      </div>
      <Card>
        {/* Custom table wrapper to make "taken" rows clickable */}
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
              {invitations.map((inv) => {
                const isTaken = inv.status === "taken";
                const handleRowClick = () => {
                  if (!isTaken) return;
                  if (!inv.session_id) {
                    console.error(
                      "Missing target report/session identifier for invitation marked as 'taken':",
                      inv
                    );
                    return;
                  }
                  router.push(`/admin/sessions/${inv.session_id}`);
                };
                return (
                  <tr
                    key={inv.id}
                    onClick={isTaken ? handleRowClick : undefined}
                    className={
                      "border-b border-border/60 last:border-b-0 transition-colors " +
                      (isTaken
                        ? "cursor-pointer hover:bg-primary/5 active:bg-primary/10"
                        : "hover:bg-subtle/70")
                    }
                  >
                    <td className="px-4 py-2.5 font-medium text-foreground">
                      {inv.candidate_email}
                    </td>
                    <td className="px-4 py-2.5" onClick={(e) => e.stopPropagation()}>
                      <StatusBadge status={inv.status} />
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground tabular-nums">
                      {new Date(inv.invited_at).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
