
"use client";

import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export default function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={
        "rounded-xl border border-border bg-card text-card-foreground " +
        "p-4 sm:p-6 shadow-sm hover:shadow-md transition-shadow duration-200 " +
        className
      }
    >
      {children}
    </div>
  );
}
