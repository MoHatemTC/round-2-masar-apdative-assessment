
"use client";

interface FormFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: "text" | "textarea" | "number";
  rows?: number;
}

export default function FormField({
  label,
  value,
  onChange,
  placeholder = "",
  type = "text",
  rows = 4,
}: FormFieldProps) {
  const baseInputClasses =
    "w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground " +
    "placeholder:text-muted-foreground shadow-inner-sm " +
    "transition-colors duration-150 " +
    "hover:border-[color:var(--accent-strong)]/50 " +
    "focus:outline-none focus:border-[color:var(--ring)] focus:ring-2 focus:ring-ring/40 " +
    "disabled:opacity-50 disabled:cursor-not-allowed";

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-foreground/90 tracking-tight">
        {label}
      </label>
      {type === "textarea" ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={rows}
          className={`${baseInputClasses} resize-y min-h-[6rem] leading-relaxed`}
        />
      ) : (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={baseInputClasses}
        />
      )}
    </div>
  );
}
