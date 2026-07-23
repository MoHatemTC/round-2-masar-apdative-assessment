"use client";

import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";

export default function AdminNav() {
  return (
    <nav className="flex items-center justify-between border-b border-gray-200 dark:border-neutral-700 px-4 sm:px-6 py-3 bg-white dark:bg-neutral-900">

      <div className="flex items-center gap-6">
        <span className="font-semibold text-gray-900 dark:text-gray-100">
          Admin
        </span>

        <Link
          href="/admin"
          className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
        >
          Dashboard
        </Link>

        <Link
          href="/admin/questions"
          className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
        >
          Questions
        </Link>

        <Link
          href="/admin/import"
          className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
        >
          Import Bank
        </Link>
      </div>

      <ThemeToggle />

    </nav>
  );
}