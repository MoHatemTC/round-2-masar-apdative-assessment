"use client";

interface RatingScaleProps {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
  disabled?: boolean;
}

// A 1-5 self-rating control, styled to match Button/Card/FormField's existing conventions
// (rounded-md, blue-600 accent, dark: variants).
export default function RatingScale({ label, value, onChange, disabled = false }: RatingScaleProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
      <div className="flex gap-2" role="radiogroup" aria-label={label}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            disabled={disabled}
            onClick={() => onChange(n)}
            className={`h-10 w-10 inline-flex items-center justify-center rounded-md border text-sm font-medium transition-all duration-150 ease-out select-none active:translate-y-px disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none disabled:shadow-none ${
              value === n
                ? "bg-primary text-primary-foreground border-transparent shadow-sm hover:bg-[color:var(--primary-hover)] hover:shadow-md"
                : "bg-card text-foreground border-border hover:bg-subtle hover:border-[color:var(--accent-strong)]/50"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}