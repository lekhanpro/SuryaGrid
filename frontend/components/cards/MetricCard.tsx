interface Props {
  title: string;
  value: string | number;
  unit?: string;
  color?: string;
}

const borderColors: Record<string, string> = {
  blue: "border-l-blue-500",
  red: "border-l-red-500",
  green: "border-l-green-500",
  yellow: "border-l-amber-500",
  purple: "border-l-purple-500",
};

export default function MetricCard({ title, value, unit, color = "blue" }: Props) {
  return (
    <div className={`bg-white rounded-lg shadow p-4 border-l-4 ${borderColors[color] || borderColors.blue}`}>
      <div className="text-xs text-gray-500 uppercase tracking-wide">{title}</div>
      <div className="text-2xl font-bold mt-1">
        {value}
        {unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}
      </div>
    </div>
  );
}
