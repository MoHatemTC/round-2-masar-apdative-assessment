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
            className={`h-10 w-10 rounded-md border text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              value === n
                ? "bg-blue-600 border-blue-600 text-white"
                : "border-gray-300 dark:border-neutral-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-neutral-800"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}