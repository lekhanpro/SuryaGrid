interface Props {
  title: string;
  value: string | number;
  unit?: string;
  color?: "blue" | "red" | "green" | "yellow" | "purple" | "orange";
  subtitle?: string;
}

const accents: Record<string, { border: string; bg: string; icon: string }> = {
  blue:   { border: "border-l-blue-500", bg: "bg-blue-50", icon: "text-blue-500" },
  red:    { border: "border-l-red-500", bg: "bg-red-50", icon: "text-red-500" },
  green:  { border: "border-l-emerald-500", bg: "bg-emerald-50", icon: "text-emerald-500" },
  yellow: { border: "border-l-amber-500", bg: "bg-amber-50", icon: "text-amber-500" },
  purple: { border: "border-l-purple-500", bg: "bg-purple-50", icon: "text-purple-500" },
  orange: { border: "border-l-orange-500", bg: "bg-orange-50", icon: "text-orange-500" },
};

export default function MetricCard({ title, value, unit, color = "blue", subtitle }: Props) {
  const a = accents[color];
  return (
    <div className={`card border-l-4 ${a.border} hover:shadow-md transition-shadow`}>
      <div className="card-header">{title}</div>
      <div className="card-value">
        {value}
        {unit && <span className="text-sm font-normal text-gray-400 ml-1">{unit}</span>}
      </div>
      {subtitle && <div className="text-xs text-gray-400 mt-1">{subtitle}</div>}
    </div>
  );
}
