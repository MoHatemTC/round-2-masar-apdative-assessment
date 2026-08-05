// frontend/app/assess/consent/page.tsx
// -----------------------------------------------------------------------------
// Entry page for the proctoring pre-assessment flow.
//   Step 1: Consent (accept / decline)
//   Step 2 (if accepted): Reference photo capture
// On completion, the candidate is routed to /assess.
//
// Expects `?session_id=<UUID>&token=<share_token>` in the URL (the intake
// flow should link here with both the session id and the original share token).
// -----------------------------------------------------------------------------

"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ConsentScreen from "../../../components/proctoring/ConsentScreen";
import ReferencePhotoCapture from "../../../components/proctoring/ReferencePhotoCapture";
import { recordConsent } from "../../../lib/proctoring";

type Step = "consent" | "reference";

function ProctoringConsentInner() {
  const router = useRouter();
  const params = useSearchParams();
  const sessionId = params.get("session_id") ?? "";
  const token = params.get("token") ?? "";

  const [step, setStep] = useState<Step>("consent");
  const [error, setError] = useState<string>("");

  if (!sessionId) {
    return (
      <div className="max-w-xl mx-auto p-6">
        <p className="text-red-600">Missing session_id in URL.</p>
      </div>
    );
  }

  async function handleAccept() {
    try {
      await recordConsent(sessionId, true);
      setStep("reference");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not save consent.";
      setError(msg);
    }
  }

  async function handleDecline() {
    try {
      await recordConsent(sessionId, false);
    } catch {
      // best-effort; do not block the candidate
    }
    router.push(`/assess?token=${encodeURIComponent(token)}&session_id=${encodeURIComponent(sessionId)}`);
  }

  function handleReferenceConfirmed() {
    router.push(`/assess?token=${encodeURIComponent(token)}&session_id=${encodeURIComponent(sessionId)}`);
  }

  return (
    <main className="min-h-screen bg-gray-50">
      {error && (
        <div className="max-w-xl mx-auto px-6 pt-6">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}

      {step === "consent" && (
        <ConsentScreen onAccept={handleAccept} onDecline={handleDecline} />
      )}

      {step === "reference" && (
        <ReferencePhotoCapture
          sessionId={sessionId}
          onConfirmed={handleReferenceConfirmed}
        />
      )}
    </main>
  );
}

export default function ProctoringConsentPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-gray-500">Loading…</div>}>
      <ProctoringConsentInner />
    </Suspense>
  );
}
