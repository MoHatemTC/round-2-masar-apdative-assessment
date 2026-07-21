"use client";

import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export default function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4 sm:p-6 ${className}`}
    >
      {children}
    </div>
  );
}