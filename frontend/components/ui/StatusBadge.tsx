"use client";

type InvitationStatus = "not_taken" | "in_progress" | "taken";

interface StatusBadgeProps {
  status: InvitationStatus;
}

const config: Record<InvitationStatus, { label: string; classes: string }> = {
  not_taken: {
    label: "Not Taken",
    classes:
      "bg-muted text-muted-foreground",
  },
  in_progress: {
    label: "In Progress",
    classes:
      "bg-warning/15 text-warning-foreground border border-warning/30",
  },
  taken: {
    label: "Taken",
    classes:
      "bg-success/15 text-success border border-success/30",
  },
};

/**
 * A small pill badge for invitation/session status.
 * Colors are derived from the design token palette.
 */
export default function StatusBadge({ status }: StatusBadgeProps) {
  const { label, classes } = config[status] ?? config.not_taken;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold leading-5 ${classes}`}
    >
      {label}
    </span>
  );
}
