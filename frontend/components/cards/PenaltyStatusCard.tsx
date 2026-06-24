interface Props {
  status: string;
  cost: number;
  riskLevel: string;
  riskScore: number;
}

export default function PenaltyStatusCard({ status, cost, riskLevel, riskScore }: Props) {
  const isPenalty = status === "PENALTY_RISK";
  const riskColors: Record<string, string> = {
    LOW: "badge-green",
    MEDIUM: "badge-yellow",
    HIGH: "badge-orange",
    CRITICAL: "badge-red",
  };

  return (
    <div className="glass-card glass-hover relative overflow-hidden p-5">
      <div className={`absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b ${isPenalty ? "from-red-500 to-rose-400" : "from-emerald-500 to-green-400"}`} />
      <div className="flex items-center justify-between mb-3">
        <div className="eyebrow">DSM Status</div>
        <span className={`badge ${riskColors[riskLevel] || "badge-green"}`}>{riskLevel}</span>
      </div>
      <div className={`text-xl font-bold ${isPenalty ? "text-red-300" : "text-emerald-300"}`}>
        {isPenalty ? "PENALTY RISK" : "NO PENALTY"}
      </div>
      {isPenalty ? (
        <div className="mt-3 pt-3 border-t border-white/10">
          <div className="flex justify-between text-sm">
            <span className="text-white/50">Estimated Cost</span>
            <span className="font-semibold text-red-300">{"\u20B9"}{cost.toLocaleString()}</span>
          </div>
          <div className="flex justify-between text-sm mt-1">
            <span className="text-white/50">Risk Score</span>
            <span className="font-medium text-white/80">{riskScore.toFixed(1)} / 100</span>
          </div>
        </div>
      ) : (
        <div className="mt-2 text-sm text-emerald-300/80">Within DSM threshold. No action required.</div>
      )}
    </div>
  );
}
