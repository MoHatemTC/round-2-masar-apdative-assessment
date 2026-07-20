"use client";

import CandidateNav from "@/components/CandidateNav";
import AdminNav from "@/components/AdminNav";

export default function TestNavigationPage() {
  return (
    <main className="min-h-screen bg-gray-100 dark:bg-neutral-950">
      <section className="mb-10">
        <h1 className="px-4 py-6 text-2xl font-bold text-gray-900 dark:text-gray-100">
          Candidate Navigation
        </h1>

        <CandidateNav />
      </section>

      <section>
        <h1 className="px-4 py-6 text-2xl font-bold text-gray-900 dark:text-gray-100">
          Admin Navigation
        </h1>

        <AdminNav />
      </section>
    </main>
  );
}