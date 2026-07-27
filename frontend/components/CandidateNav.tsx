"use client";

import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";

export default function CandidateNav() {
  return (
    <nav className="sticky top-0 z-40 flex items-center justify-between border-b border-border bg-card/85 backdrop-blur-md px-4 sm:px-6 py-3 shadow-sm">
      <Link
        href="/assess"
        className="group inline-flex items-center gap-2 font-semibold tracking-tight text-foreground transition-colors hover:text-[color:var(--primary)]"
      >
        <span
          aria-hidden="true"
          className="inline-block h-2.5 w-2.5 rounded-full bg-[color:var(--accent-strong)] shadow-[0_0_0_3px_color-mix(in_oklab,var(--accent)_35%,transparent)] transition-transform group-hover:scale-110"
        />
        Adaptive Assessment
      </Link>
      <ThemeToggle />
    </nav>
  );
}
