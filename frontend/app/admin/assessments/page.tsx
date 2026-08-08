"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import Card from "@/components/ui/Card";
import Table from "@/components/ui/Table";
import Button from "@/components/ui/Button";
import Pagination from "@/components/ui/Pagination";
import { getAssessments, getQuestionSets, type Assessment, type PaginationMeta, type QuestionSet } from "@/lib/api";

function AssessmentsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const pageParam = Number(searchParams.get("page")) || 1;
  const [currentPage, setCurrentPage] = useState(pageParam);

  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [questionSets, setQuestionSets] = useState<Record<string, string>>({});
  const [meta, setMeta] = useState<PaginationMeta>({ currentPage: 1, totalPages: 1, totalItems: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getAssessments(currentPage),
      getQuestionSets().catch(() => [])
    ])
      .then(([res, sets]) => {
        setAssessments(res.data);
        setMeta(res.meta);

        const setsMap: Record<string, string> = {};
        sets.forEach(s => {
          setsMap[s.id] = s.name;
        });
        setQuestionSets(setsMap);

        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load assessments");
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

  const tableHeaders = ["Title", "Time Limit (min)", "Question Set", "ID", "Candidates"];

  const tableRows = assessments.map((a) => [
    a.title,
    a.time_limit_min ?? "—",
    questionSets[a.question_set_id] || a.question_set_id,
    <span key={a.id} className="text-xs text-gray-400 font-mono">
      {a.id.slice(0, 8)}…
    </span>,
    <Link
      key={`invite-${a.id}`}
      href={`/admin/invitations?assessmentId=${a.id}`}
    >
      <Button>
        Invitations
      </Button>
    </Link>,
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
        <Pagination
          currentPage={meta.currentPage}
          totalPages={meta.totalPages}
          onPageChange={handlePageChange}
        />
      </Card>
    </div>
  );
}

export default function AssessmentsPage() {
  return (
    <Suspense fallback={<div className="p-6 sm:p-10"><Card><div className="flex items-center justify-center py-12"><div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" /><span className="ml-3 text-sm text-gray-500 dark:text-gray-400">Loading…</span></div></Card></div>}>
      <AssessmentsContent />
    </Suspense>
  );
}
