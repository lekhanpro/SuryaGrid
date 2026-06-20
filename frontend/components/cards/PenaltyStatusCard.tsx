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
    <div className={`card border-l-4 ${isPenalty ? "border-l-red-500" : "border-l-emerald-500"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="card-header mb-0">DSM Status</div>
        <span className={`badge ${riskColors[riskLevel] || "badge-green"}`}>{riskLevel}</span>
      </div>
      <div className={`text-xl font-bold ${isPenalty ? "text-red-600" : "text-emerald-600"}`}>
        {isPenalty ? "PENALTY RISK" : "NO PENALTY"}
      </div>
      {isPenalty && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Estimated Cost</span>
            <span className="font-semibold text-red-600">{"\u20B9"}{cost.toLocaleString()}</span>
          </div>
          <div className="flex justify-between text-sm mt-1">
            <span className="text-gray-500">Risk Score</span>
            <span className="font-medium">{riskScore.toFixed(1)} / 100</span>
          </div>
        </div>
      )}
      {!isPenalty && (
        <div className="mt-2 text-sm text-emerald-600">Within DSM threshold. No action required.</div>
      )}
    </div>
  );
}
