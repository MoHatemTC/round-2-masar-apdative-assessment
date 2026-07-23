"use client";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";

export default function AdminNav() {
  const linkClasses =
    "relative text-sm font-medium text-muted-foreground transition-colors hover:text-foreground " +
    "after:absolute after:left-0 after:-bottom-1 after:h-[2px] after:w-0 after:bg-[color:var(--accent-strong)] " +
    "after:transition-all after:duration-200 hover:after:w-full " +
    "focus-visible:outline-none focus-visible:text-foreground";

  return (
    <nav className="sticky top-0 z-40 flex items-center justify-between border-b border-border bg-card/85 backdrop-blur-md px-4 sm:px-6 py-3 shadow-sm">
      <div className="flex items-center gap-6">
        <span className="inline-flex items-center gap-2 font-semibold tracking-tight text-foreground">
          <span
            aria-hidden="true"
            className="rounded-md bg-[color:var(--primary)] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-[color:var(--primary-foreground)]"
          >
            Admin
          </span>
        </span>
        <Link href="/admin" className={linkClasses}>
          Dashboard
        </Link>
        <Link href="/admin/questions" className={linkClasses}>
          Questions
        </Link>
        <Link href="/admin/import" className={linkClasses}>
          Import Bank
        </Link>
      </div>
      <ThemeToggle />
    </nav>
  );
}