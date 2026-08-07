"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Pagination from "@/components/ui/Pagination";
import {
  getInvitations,
  getAssessments,
  sendInvitation,
  type Invitation,
  type Assessment,
  type PaginationMeta,
} from "@/lib/api";

export default function InvitationsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");

  const pageParam = Number(searchParams.get("page")) || 1;
  const [currentPage, setCurrentPage] = useState(pageParam);

  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [meta, setMeta] = useState<PaginationMeta>({ currentPage: 1, totalPages: 1, totalItems: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [selectedAssessment, setSelectedAssessment] = useState("");
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);

  const [assessmentSearchTerm, setAssessmentSearchTerm] = useState("");
  const [assessmentDropdownOpen, setAssessmentDropdownOpen] = useState(false);
  const assessmentComboboxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (assessmentComboboxRef.current && !assessmentComboboxRef.current.contains(e.target as Node)) {
        setAssessmentDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredAssessments = useMemo(() => {
    if (!assessmentSearchTerm.trim()) return assessments;
    const lower = assessmentSearchTerm.toLowerCase();
    return assessments.filter(
      (a) => a.title.toLowerCase().includes(lower)
    );
  }, [assessments, assessmentSearchTerm]);

  const selectedAssessmentTitle = useMemo(() => {
    const found = assessments.find((a) => a.id === selectedAssessment);
    return found?.title || "";
  }, [assessments, selectedAssessment]);

  function handleSelectAssessment(a: Assessment) {
    handleAssessmentChange(a.id);
    setAssessmentSearchTerm(a.title);
    setAssessmentDropdownOpen(false);
  }

  function handleAssessmentInputChange(value: string) {
    setAssessmentSearchTerm(value);
    setAssessmentDropdownOpen(true);
  }

  function handleAssessmentInputFocus() {
    setAssessmentDropdownOpen(true);
    if (selectedAssessment && selectedAssessmentTitle) {
      setAssessmentSearchTerm(selectedAssessmentTitle);
    }
  }

  const handleRowClick = (invite: Invitation, e: React.MouseEvent) => {
    const isTaken = invite.status === "taken";
    if (!isTaken) return;

    if (!invite.session_id) {
      console.error(
        "Missing target report/session identifier for invitation marked as 'taken':",
        invite
      );
      return;
    }

    router.push(`/admin/sessions/${invite.session_id}`);
  };

  useEffect(() => {
    getAssessments(1, 100)
        .then((res) => setAssessments(res.data))
        .catch((err) =>
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load assessments"
        )
    );
  }, []);

  useEffect(() => {
    if (!selectedAssessment) {
        setInvitations([]);
        setMeta({ currentPage: 1, totalPages: 1, totalItems: 0 });
        setLoading(false);
        return;
    }

    setLoading(true);

    getInvitations(selectedAssessment, currentPage)
        .then((res) => {
            setInvitations(res.data);
            setMeta(res.meta);
            setError(null);
        })
        .catch((err) => {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load invitations"
            );
        })
        .finally(() => setLoading(false));
  }, [selectedAssessment, currentPage]);

  function handleAssessmentChange(value: string) {
    setSelectedAssessment(value);
    setCurrentPage(1);
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", "1");
    if (value) {
      params.set("assessmentId", value);
    } else {
      params.delete("assessmentId");
    }
    router.push(`?${params.toString()}`, { scroll: false });
  }

  function handlePageChange(page: number) {
    setCurrentPage(page);
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(page));
    router.push(`?${params.toString()}`, { scroll: false });
  }

async function handleInvite() {
  setSending(true);
  try {
    await sendInvitation({
      assessment_id: selectedAssessment,
      candidate_email: email,
    });

    setEmail("");

    const updated = await getInvitations(selectedAssessment, currentPage);
    setInvitations(updated.data);
    setMeta(updated.meta);

    setMsg("Invitation sent successfully.");
  } catch (err) {
    alert(
      err instanceof Error
        ? err.message
        : "Failed to send invitation."
    );
  }finally{
    setSending(false);
  }
}

  if (error) {
    return (
      <main className="max-w-5xl mx-auto p-8 text-red-600">
        {error}
      </main>
    );
  }

  return (
    <main className="max-w-5xl mx-auto p-8 space-y-6">

      <h1 className="text-3xl font-bold">
        Candidate Invitations
      </h1>

      <Card className="space-y-4">

        <h2 className="text-xl font-semibold">
          Send Invitation
        </h2>

        <div className="flex flex-col gap-1.5 z-10 relative">
          <div ref={assessmentComboboxRef} className="relative">
            <input
              type="text"
              value={assessmentSearchTerm}
              onChange={(e) => handleAssessmentInputChange(e.target.value)}
              onFocus={handleAssessmentInputFocus}
              placeholder={assessments.length === 0 ? "Loading assessments..." : "Search and select assessment..."}
              className={
                "w-full rounded-md border border-gray-300 bg-white p-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-white pr-8"
              }
            />
            {selectedAssessment && !assessmentDropdownOpen && (
              <button
                type="button"
                onClick={() => {
                  handleAssessmentChange("");
                  setAssessmentSearchTerm("");
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                  <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                </svg>
              </button>
            )}
            {assessmentDropdownOpen && (
              <ul className="absolute z-50 mt-1 max-h-56 w-full overflow-auto rounded-md border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800">
                {filteredAssessments.length === 0 ? (
                  <li className="px-3 py-2 text-sm text-gray-500 italic dark:text-gray-400">
                    No assessments found.
                  </li>
                ) : (
                  filteredAssessments.map((a) => (
                    <li
                      key={a.id}
                      onClick={() => handleSelectAssessment(a)}
                      className={
                        "flex cursor-pointer flex-col px-3 py-2 text-sm transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 " +
                        (a.id === selectedAssessment ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 font-medium" : "text-gray-900 dark:text-gray-100")
                      }
                    >
                      <span>{a.title}</span>
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        </div>

        <input
          type="email"
          placeholder="Candidate Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border border-gray-300 bg-white p-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
        />

        <Button
          onClick={handleInvite}
          disabled={sending || !email.trim() || !selectedAssessment || loading}
        >
          {sending ? "Sending..." : "Send Invitation"}
        </Button>

      </Card>

      <Card>

       <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold">
                Invitations
            </h2>

            <span className="text-sm text-gray-500 dark:text-gray-400">
                {selectedAssessment
                    ? `${meta.totalItems} invitation${meta.totalItems !== 1 ? "s" : ""}`
                    : "No assessment selected"}
            </span>
        </div>
        <div className="overflow-x-auto">
        <table className="w-full border-collapse">

          <thead className="bg-gray-50 dark:bg-gray-800">

            <tr className="border-b odd:bg-white even:bg-gray-50 dark:border-gray-700 dark:odd:bg-gray-900 dark:even:bg-gray-800">

              <th className="text-left p-3">
                Email
              </th>

              <th className="text-left p-3">
                Status
              </th>

            </tr>

          </thead>

          <tbody>
            { loading ? (
                <tr>
                    <td colSpan={2} className="py-8">
                        <div className="flex items-center justify-center gap-3">
                            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600"></div>
                            <span>Loading invitations...</span>
                        </div>
                    </td>
                </tr>
            ) : !selectedAssessment ? (
                <tr>
                    <td
                        colSpan={2}
                        className="p-8 text-center text-gray-500"
                    >
                        Select an assessment to view invitations.
                    </td>
                </tr>
            ) : invitations.length === 0 ? (
                <tr>
                    <td
                        colSpan={2}
                        className="p-8 text-center text-gray-500"
                    >
                        No invitations have been sent for this assessment yet.
                    </td>
                </tr>
            ) : (
                    invitations.map((invite) => {
                        const isTaken = invite.status === "taken";
                        return (
                            <tr
                                key={invite.id}
                                onClick={(e) => handleRowClick(invite, e)}
                                className={`border-b transition-colors ${
                                    isTaken
                                        ? "cursor-pointer hover:bg-blue-50/50 dark:hover:bg-blue-950/20 active:bg-blue-100/50 dark:active:bg-blue-900/30"
                                        : "hover:bg-gray-50 dark:hover:bg-gray-800 odd:bg-white even:bg-gray-50 dark:border-gray-700 dark:odd:bg-gray-900 dark:even:bg-gray-800"
                                }`}
                            >
                                <td className="p-3">
                                    {invite.candidate_email}
                                </td>

                                <td className="p-3">
                                    <span
                                        onClick={(e) => e.stopPropagation()}
                                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                                            invite.status === "taken"
                                                ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                                                : invite.status === "in_progress"
                                                ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300"
                                                : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                                        }`}
                                    >
                                        {invite.status.replace("_", " ")}
                                    </span>
                                </td>
                            </tr>
                        );
                    })
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

      {msg && (
        <Card>
            <p className="text-green-600 dark:text-green-400">
                {msg}
            </p>
        </Card>
       )}
    </main>
  );
}