"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import {
  getInvitations,
  getAssessments,
  sendInvitation,
  type Invitation,
  type Assessment
} from "@/lib/api";

export default function InvitationsPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");

  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [selectedAssessment, setSelectedAssessment] = useState("");
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);

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
    getAssessments()
        .then(setAssessments)
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
        setLoading(false);
        return;
    }

    setLoading(true);

    getInvitations(selectedAssessment)
        .then((data) => {
            setInvitations(data);
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
  }, [selectedAssessment]);

async function handleInvite() {
  setSending(true);
  try {
    await sendInvitation({
      assessment_id: selectedAssessment,
      candidate_email: email,
    });

    setEmail("");

    const updated = await getInvitations(selectedAssessment);
    setInvitations(updated);

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

        <select
            value={selectedAssessment}
            onChange={(e) => setSelectedAssessment(e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white p-2 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
        >
            {assessments.length === 0 ? (
                <option value="">No assessments available</option>
            ) : (
                <>
                    <option value="">Select Assessment</option>

                    {assessments.map((assessment) => (
                        <option
                            key={assessment.id}
                            value={assessment.id}
                        >
                            {assessment.title}
                        </option>
                    ))}
                </>
            )}
        </select>

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
                    ? `${invitations.length} invitation${invitations.length !== 1 ? "s" : ""}`
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