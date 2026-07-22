"use client";
// Candidate flow: session start via link/token -> intake (self-ratings + optional CV) ->
// adaptive Q&A -> report. Logic lives in AssessFlow; this file only supplies the Suspense
// boundary Next.js requires around useSearchParams().
import { Suspense } from "react";
import AssessFlow from "./AssessFlow";

export default function AssessPage() {
  return (
    <Suspense
      fallback={
        <main className="max-w-2xl mx-auto p-8 text-gray-600 dark:text-gray-400">
          Loading your assessment…
        </main>
      }
    >
      <AssessFlow />
    </Suspense>
  );
}