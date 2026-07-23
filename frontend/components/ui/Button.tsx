
"use client";

import type { ReactNode } from "react";

interface ButtonProps {
  children: ReactNode;
  variant?: "primary" | "secondary";
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;   
}

export default function Button({
  children,
  variant = "primary",
  onClick,
  disabled = false,
  type = "button",
  className = "",  
}: ButtonProps) {
  const baseClasses =
    "inline-flex items-center justify-center px-4 py-2 rounded-md text-sm font-medium " +
    "transition-all duration-150 ease-out select-none " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background " +
    "active:translate-y-px " +
    "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none disabled:shadow-none";

  const variantClasses =
    variant === "primary"
      ? "bg-primary text-primary-foreground shadow-sm hover:bg-[color:var(--primary-hover)] hover:shadow-md"
      : "bg-card text-foreground border border-border hover:bg-subtle hover:border-[color:var(--accent-strong)]/50";

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseClasses} ${variantClasses} ${className}`}
    >
      {children}
    </button>
  );
}
