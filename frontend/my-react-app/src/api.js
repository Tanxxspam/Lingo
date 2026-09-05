const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  createSession: (orderAmount) =>
    request("/checkout/session", {
      method: "POST",
      body: JSON.stringify({ order_amount: orderAmount }),
    }),

  logEvent: (sessionId, eventType, metadata = {}) =>
    request("/checkout/event", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, event_type: eventType, metadata }),
    }),

  logOutcome: (interventionId, response, sessionConverted, revenueAmount) =>
    request("/agent/intervene", {
      method: "POST",
      body: JSON.stringify({
        intervention_id: interventionId,
        response,
        session_converted: sessionConverted,
        revenue_amount: revenueAmount,
      }),
    }),

  createPaymentLink: (sessionId) =>
    request(`/checkout/session/${sessionId}/payment-link`, { method: "POST" }),

  metricsSummary: () => request("/metrics/summary"),

  simulateBatch: (numSessions) =>
    request("/simulate/batch", {
      method: "POST",
      body: JSON.stringify({ num_sessions: numSessions }),
    }),
};