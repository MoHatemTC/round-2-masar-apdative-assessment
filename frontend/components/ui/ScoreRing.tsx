"use client";

interface ScoreRingProps {
  /** Value between 0 and 100 */
  value: number;
  /** Diameter in pixels. Defaults to 160. */
  size?: number;
  /** Stroke width. Defaults to 10. */
  strokeWidth?: number;
  /** Optional label below the percentage */
  label?: string;
}

/**
 * An SVG-based circular progress ring with an animated fill.
 * Color shifts based on score range using design tokens:
 * - 0–39  → destructive (red)
 * - 40–69 → warning (amber)
 * - 70–89 → info (blue)
 * - 90+   → success (green)
 */
export default function ScoreRing({
  value,
  size = 160,
  strokeWidth = 10,
  label,
}: ScoreRingProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;

  // Choose a color class based on score range
  let strokeColor: string;
  let textColor: string;
  if (clamped >= 90) {
    strokeColor = "stroke-success";
    textColor = "text-success";
  } else if (clamped >= 70) {
    strokeColor = "stroke-info";
    textColor = "text-info";
  } else if (clamped >= 40) {
    strokeColor = "stroke-warning";
    textColor = "text-warning";
  } else {
    strokeColor = "stroke-destructive";
    textColor = "text-destructive";
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="-rotate-90"
        >
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            className="stroke-border"
          />
          {/* Animated progress arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={`${strokeColor} transition-[stroke-dashoffset] duration-1000 ease-out`}
          />
        </svg>
        {/* Centered percentage text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold tabular-nums ${textColor}`}>
            {clamped}%
          </span>
        </div>
      </div>
      {label && (
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
      )}
    </div>
  );
}
