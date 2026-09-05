import { useState, useEffect } from "react";
import { api } from "../api";
import { formatRupees } from "../lib/format";

const POLL_INTERVAL_MS = 5000;

export default function MetricsDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const refresh = () => api.metricsSummary().then(setMetrics).catch(() => setError("Metrics unavailable"));
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  if (error) return <p className="text-sm text-ink/40">{error}</p>;
  if (!metrics) return null;

  return (
    <div className="rounded-xl border border-ink/10 bg-surface p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-ink/40">Live sessions</p>
      <div className="mt-3 grid grid-cols-3 gap-4">
        <div>
          <p className="font-display text-2xl text-ink">{metrics.total_sessions}</p>
          <p className="text-xs text-ink/50">Total sessions</p>
        </div>
        <div>
          <p className="font-display text-2xl text-ink">{metrics.converted_sessions}</p>
          <p className="text-xs text-ink/50">Converted</p>
        </div>
        <div>
          <p className="font-display text-2xl text-teal">
            {formatRupees(metrics.recovered_revenue_paise)}
          </p>
          <p className="text-xs text-ink/50">Recovered revenue</p>
        </div>
      </div>
    </div>
  );
}