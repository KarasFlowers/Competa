interface ReliabilityBadgeProps {
  score: number;
}

export function ReliabilityBadge({ score }: ReliabilityBadgeProps) {
  const pct = Math.round(score * 100);
  let label: string;
  let colorClass: string;

  if (score >= 0.8) {
    label = "High";
    colorClass = "bg-green-100 text-green-700";
  } else if (score >= 0.6) {
    label = "Medium";
    colorClass = "bg-yellow-100 text-yellow-700";
  } else {
    label = "Low";
    colorClass = "bg-red-100 text-red-700";
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {label} {pct}%
    </span>
  );
}
