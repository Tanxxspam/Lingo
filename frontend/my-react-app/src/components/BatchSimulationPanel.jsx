import { useState } from "react";
import { api } from "../api";
import { formatRupees, humanizeActionType } from "../lib/format";

const DEFAULT_NUM_SESSIONS = 200;
const MAX_NUM_SESSIONS = 5000;

export default function BatchSimulationPanel() {
  const [numSessions, setNumSessions] = useState(DEFAULT_NUM_SESSIONS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const runSimulation = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.simulateBatch(numSessions);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-ink/10 bg-surface p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-ink/40">Batch simulation</p>
      <h2 className="mt-1 font-display text-lg text-ink">
        Measure recovered revenue across simulated sessions
      </h2>

      <div className="mt-4 flex items-center gap-3">
        <label htmlFor="num-sessions" className="sr-only">
          Number of sessions to simulate
        </label>
        <input
          id="num-sessions"
          type="number"
          min="1"
          max={MAX_NUM_SESSIONS}
          value={numSessions}
          onChange={(e) => setNumSessions(Number(e.target.value))}
          className="w-28 rounded-md border border-ink/15 px-3 py-2 text-sm focus:border-teal focus:outline-none focus:ring-1 focus:ring-teal"
        />
        <button
          onClick={runSimulation}
          disabled={loading}
          className="rounded-md bg-ink px-4 py-2 text-sm font-medium text-white transition hover:bg-ink/90 focus:outline-none focus:ring-2 focus:ring-ink focus:ring-offset-2 disabled:opacity-50"
        >
          {loading ? "Running…" : "Run batch simulation"}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-brick">{error}</p>}

      {result && (
        <div className="mt-6">
          <p className="font-display text-4xl text-teal">
            {formatRupees(result.recovered_revenue_paise)}
          </p>
          <p className="text-sm text-ink/50">recovered revenue across the batch</p>

          <div className="mt-5 grid grid-cols-2 gap-4 border-t border-ink/10 pt-5">
            <div>
              <p className="text-xs font-medium text-ink/40">Control (no agent)</p>
              <p className="mt-1 font-display text-xl text-ink">
                {(result.control.conversion_rate * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-ink/50">conversion rate</p>
            </div>
            <div>
              <p className="text-xs font-medium text-ink/40">Treatment (agent active)</p>
              <p className="mt-1 font-display text-xl text-ink">
                {(result.treatment.conversion_rate * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-ink/50">conversion rate</p>
            </div>
          </div>

          <div className="mt-5 border-t border-ink/10 pt-5">
            <p className="text-xs font-medium text-ink/40">By intervention type</p>
            <div className="mt-2 space-y-1.5">
              {Object.entries(result.breakdown_by_intervention).map(([type, stats]) => (
                <div key={type} className="flex justify-between text-sm">
                  <span className="text-ink/70">{humanizeActionType(type)}</span>
                  <span className="text-ink/50">
                    {stats.shown} shown · {stats.converted} converted
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}