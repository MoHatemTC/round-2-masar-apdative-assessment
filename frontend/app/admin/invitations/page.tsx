"use client";

import { Suspense } from "react";
import InvitationsContent from "./InvitationsContent";

export default function InvitationsPage() {
  return (
    <Suspense fallback={<main className="max-w-5xl mx-auto p-8">Loading...</main>}>
      <InvitationsContent />
    </Suspense>
  );
}