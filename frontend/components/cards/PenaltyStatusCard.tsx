interface Props {
  status: string;
  cost: number;
  riskLevel: string;
}

export default function PenaltyStatusCard({ status, cost, riskLevel }: Props) {
  const isPenalty = status === "PENALTY_RISK";
  return (
    <div className={`rounded-lg shadow p-4 border-l-4 ${isPenalty ? "bg-red-50 border-l-red-500" : "bg-green-50 border-l-green-500"}`}>
      <div className="text-xs text-gray-500 uppercase tracking-wide">DSM Penalty Status</div>
      <div className={`text-xl font-bold mt-1 ${isPenalty ? "text-red-700" : "text-green-700"}`}>
        {isPenalty ? "PENALTY RISK" : "NO PENALTY"}
      </div>
      {isPenalty && <div className="text-sm text-red-600 mt-1">Estimated Cost: &#x20B9;{cost.toLocaleString()}</div>}
      <div className="text-xs text-gray-500 mt-2">Fuzzy Risk Level: <span className="font-semibold">{riskLevel}</span></div>
    </div>
  );
}
