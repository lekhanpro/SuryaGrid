export default function OfflineBanner({ base }: { base: string }) {
  return (
    <div className="glass-card border border-red-500/30 bg-red-500/5 p-5 mb-6">
      <div className="flex items-start gap-3">
        <span className="w-2.5 h-2.5 mt-1.5 rounded-full bg-red-400 animate-pulse shadow-lg shadow-red-400/50" />
        <div>
          <div className="text-red-300 font-semibold">Backend Offline — Live system unavailable</div>
          <div className="text-white/40 text-sm mt-1">
            Could not reach the API at <code className="text-white/70">{base}</code>. Start the
            backend (<code className="text-white/70">docker compose up</code>) and reload. No sample
            data is shown here — this dashboard never fakes live results.
          </div>
        </div>
      </div>
    </div>
  );
}
