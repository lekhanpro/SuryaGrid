interface Props {
  title: string;
  value: string | number;
  unit?: string;
  color?: "blue" | "red" | "green" | "yellow" | "purple" | "orange";
  subtitle?: string;
}

const accents: Record<string, { bar: string; value: string; glow: string }> = {
  blue:   { bar: "from-blue-500 to-cyan-400",    value: "text-blue-200",    glow: "shadow-blue-500/10" },
  red:    { bar: "from-red-500 to-rose-400",     value: "text-red-200",     glow: "shadow-red-500/10" },
  green:  { bar: "from-emerald-500 to-green-400", value: "text-emerald-200", glow: "shadow-emerald-500/10" },
  yellow: { bar: "from-amber-500 to-yellow-400", value: "text-amber-200",   glow: "shadow-amber-500/10" },
  purple: { bar: "from-purple-500 to-fuchsia-400", value: "text-purple-200", glow: "shadow-purple-500/10" },
  orange: { bar: "from-orange-500 to-amber-400", value: "text-orange-200",  glow: "shadow-orange-500/10" },
};

export default function MetricCard({ title, value, unit, color = "blue", subtitle }: Props) {
  const a = accents[color] ?? accents.blue;
  return (
    <div className={`glass-card glass-hover relative overflow-hidden p-5 ${a.glow}`}>
      <div className={`absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b ${a.bar}`} />
      <div className="eyebrow">{title}</div>
      <div className={`text-2xl font-bold mt-1.5 ${a.value}`}>
        {value}
        {unit && <span className="text-sm font-normal text-white/40 ml-1">{unit}</span>}
      </div>
      {subtitle && <div className="text-xs text-white/35 mt-1">{subtitle}</div>}
    </div>
  );
}
