import CheckoutPage from "./components/CheckoutPage";
import MetricsDashboard from "./components/MetricsDashboard";
import BatchSimulationPanel from "./components/BatchSimulationPanel";

export default function App() {
  return (
    <div className="min-h-screen bg-paper px-4 py-10">
      <header className="mx-auto mb-8 max-w-4xl">
        <p className="text-xs font-medium uppercase tracking-wide text-ink/40">
          Agentic Checkout Concierge
        </p>
        <h1 className="mt-1 font-display text-2xl text-ink">
          Recovering checkout revenue, one hesitation at a time
        </h1>
      </header>

      <main className="mx-auto grid max-w-4xl gap-8 md:grid-cols-2">
        <div>
          <CheckoutPage />
        </div>
        <div className="space-y-6">
          <MetricsDashboard />
          <BatchSimulationPanel />
        </div>
      </main>
    </div>
  );
}