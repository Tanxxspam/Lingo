import { actionButtonLabel } from "../lib/format";

export default function ConciergeWidget({ intervention, onRespond }) {
  if (!intervention) return null;

  const { message, intervention_id: interventionId, action_type: actionType } = intervention;

  return (
    <div
      className="concierge-enter mt-4 rounded-lg border-2 border-amber bg-amber/5 p-4"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-amber" aria-hidden="true" />
        <div className="flex-1">
          <p className="text-sm leading-relaxed text-ink">{message}</p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => onRespond(interventionId, "accepted")}
              className="rounded-md bg-amber px-3 py-1.5 text-sm font-medium text-white transition hover:bg-amber/90 focus:outline-none focus:ring-2 focus:ring-amber focus:ring-offset-2"
            >
              {actionButtonLabel(actionType)}
            </button>
            <button
              onClick={() => onRespond(interventionId, "rejected")}
              className="rounded-md px-3 py-1.5 text-sm font-medium text-ink/60 transition hover:text-ink focus:outline-none focus:ring-2 focus:ring-ink/30 focus:ring-offset-2"
            >
              No thanks
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}