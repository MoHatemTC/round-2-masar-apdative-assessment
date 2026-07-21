"use client";

import type { ReactNode } from "react";

interface ButtonProps {
  children: ReactNode;
  variant?: "primary" | "secondary";
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
}

export default function Button({
  children,
  variant = "primary",
  onClick,
  disabled = false,
  type = "button",
}: ButtonProps) {
  const baseClasses =
    "px-4 py-2 rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";

  const variantClasses =
    variant === "primary"
      ? "bg-blue-600 text-white hover:bg-blue-700 dark:hover:bg-blue-500"
      : "border border-gray-300 dark:border-neutral-700 text-gray-900 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-neutral-800";

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseClasses} ${variantClasses}`}
    >
      {children}
    </button>
  );
}