interface ReliabilityBadgeProps {
  score: number;
}

export function ReliabilityBadge({ score }: ReliabilityBadgeProps) {
  const pct = Math.round(score * 100);
  let label: string;
  let colorClass: string;

  if (score >= 0.8) {
    label = "高";
    colorClass = "bg-green-100 text-green-700";
  } else if (score >= 0.6) {
    label = "中";
    colorClass = "bg-yellow-100 text-yellow-700";
  } else {
    label = "低";
    colorClass = "bg-red-100 text-red-700";
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {label} {pct}%
    </span>
  );
}
