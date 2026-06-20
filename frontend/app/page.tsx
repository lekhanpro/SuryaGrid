import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh]">
      <h1 className="text-4xl font-bold mb-2">Suryagrid AI</h1>
      <p className="text-lg text-gray-600 mb-2">Solar Nowcasting &amp; DSM Penalty Prediction System</p>
      <p className="text-sm text-gray-500 mb-8">Phase 1 &mdash; Deterministic Simulation Mode</p>
      <Link href="/dashboard" className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
        Open Monitoring Dashboard
      </Link>
    </div>
  );
}
