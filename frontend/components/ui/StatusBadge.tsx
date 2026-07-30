interface StatusBadgeProps {
  status: "taken" | "in_progress" | "not_taken";
}

export default function StatusBadge({
  status,
}: StatusBadgeProps) {

  const styles = {
    taken:
      "bg-green-100 text-green-700",

    in_progress:
      "bg-yellow-100 text-yellow-700",

    not_taken:
      "bg-gray-100 text-gray-700",
  };

  const labels = {
    taken: "Taken",
    in_progress: "In Progress",
    not_taken: "Not Taken",
  };

  return (
    <span
      className={`px-3 py-1 rounded-full text-sm font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}