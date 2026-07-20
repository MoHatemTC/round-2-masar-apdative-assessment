"use client";

import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";

export default function CandidateNav() {
  return (
    <nav className="flex items-center justify-between border-b border-gray-200 dark:border-neutral-700 px-4 sm:px-6 py-3 bg-white dark:bg-neutral-900">
      <Link href="/assess" className="font-semibold text-gray-900 dark:text-gray-100">
        Adaptive Assessment
      </Link>
      <ThemeToggle />
    </nav>
  );
}