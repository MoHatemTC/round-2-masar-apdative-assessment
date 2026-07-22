"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import Table from "@/components/ui/Table";
import Button from "@/components/ui/Button";
import { getAssessments, type Assessment } from "@/lib/api";

export default function AssessmentsPage() {
  const router = useRouter();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAssessments()
      .then((data) => {
        setAssessments(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load assessments");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="p-6 sm:p-10">
        <Card>
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
            <span className="ml-3 text-sm text-gray-500 dark:text-gray-400">Loading assessments…</span>
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
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            <Button variant="secondary" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  const tableHeaders = ["Title", "Time Limit (min)", "Question Set ID", "Actions"];

  const tableRows = assessments.map((a) => [
    a.title,
    a.time_limit_min ?? "—",
    a.question_set_id,
    <Button
      key={a.id}
      variant="secondary"
      onClick={() => router.push(`/admin/assessments/${a.id}/invitations`)}
    >
      View Invitations
    </Button>,
  ]);

  return (
    <div className="p-6 sm:p-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Assessments</h1>
        <Link href="/admin/assessments/create">
          <Button>Create Assessment</Button>
        </Link>
      </div>
      <Card>
        <Table headers={tableHeaders} rows={tableRows} />
      </Card>
    </div>
  );
}
