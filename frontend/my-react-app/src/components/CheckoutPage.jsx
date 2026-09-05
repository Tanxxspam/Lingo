import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../api";
import { formatRupees } from "../lib/format";
import ConciergeWidget from "./ConciergeWidget";

const DEMO_PRODUCT = { name: "Wireless Noise-Cancelling Headphones", price: 649900 }; // paise
const IDLE_CHECK_MS = 1000;
const IDLE_TRIGGER_SECONDS = 20;
const OTP_SUCCESS_CODE = "0000";

export default function CheckoutPage() {
  const [session, setSession] = useState(null);
  const [sessionError, setSessionError] = useState("");
  const [intervention, setIntervention] = useState(null);
  const [otpValue, setOtpValue] = useState("");
  const [otpError, setOtpError] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const lastActivityRef = useRef(Date.now());

  // --- Session bootstrap ---
  useEffect(() => {
    api
      .createSession(DEMO_PRODUCT.price)
      .then(setSession)
      .catch(() => setSessionError("Could not start a session — check the backend is running."));
  }, []);

  const fireEvent = useCallback(
    async (eventType, metadata = {}) => {
      if (!session || intervention) return; // stopping rule: don't stack while one is showing
      try {
        const result = await api.logEvent(session.session_id, eventType, metadata);
        if (result.decision.action !== "no_action") {
          setIntervention({
            intervention_id: result.intervention_id,
            action_type: result.decision.action,
            message: result.message,
          });
        }
      } catch {
        // A failed hesitation-signal call shouldn't break checkout itself.
      }
    },
    [session, intervention]
  );

  // --- Real detection: idle timer ---
  useEffect(() => {
    const resetIdle = () => {
      lastActivityRef.current = Date.now();
    };
    window.addEventListener("mousemove", resetIdle);
    window.addEventListener("keydown", resetIdle);

    const interval = setInterval(() => {
      const idleFor = Math.floor((Date.now() - lastActivityRef.current) / 1000);
      if (idleFor === IDLE_TRIGGER_SECONDS) {
        fireEvent("idle", { idle_seconds: idleFor });
      }
    }, IDLE_CHECK_MS);

    return () => {
      window.removeEventListener("mousemove", resetIdle);
      window.removeEventListener("keydown", resetIdle);
      clearInterval(interval);
    };
  }, [fireEvent]);

  // --- Real detection: back button ---
  useEffect(() => {
    window.history.pushState({ checkout: true }, "");
    const handlePopState = () => {
      fireEvent("back_button");
      window.history.pushState({ checkout: true }, "");
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [fireEvent]);

  // --- Mocked OTP failure ---
  const handleOtpSubmit = (e) => {
    e.preventDefault();
    if (otpValue !== OTP_SUCCESS_CODE) {
      setOtpError(true);
      fireEvent("otp_fail");
    } else {
      setOtpError(false);
      setStatusMessage("Payment verified — order complete.");
    }
  };

  const handleRespond = async (interventionId, response) => {
    setIntervention(null);
    const sessionConverted = response === "accepted";
    // Simplification for the hackathon demo: accepting an offer is treated
    // as completing the sale, so the full order amount is credited as
    // recovered revenue. A production version would wait for an actual
    // payment confirmation (e.g. via the Payment Link's webhook) before
    // marking session_converted / revenue_amount.
    const revenueAmount = sessionConverted ? session.order_amount : null;
    try {
      await api.logOutcome(interventionId, response, sessionConverted, revenueAmount);
      if (sessionConverted) {
        setStatusMessage("Offer applied — continue checking out below.");
      }
    } catch {
      // demo-safe: outcome logging failure shouldn't block the UI
    }
  };

  return (
    <div className="mx-auto max-w-md">
      <div className="rounded-xl border border-ink/10 bg-surface p-6 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-wide text-ink/40">Checkout</p>
        <h1 className="mt-1 font-display text-lg text-ink">{DEMO_PRODUCT.name}</h1>
        <p className="mt-1 text-2xl font-display text-ink">{formatRupees(DEMO_PRODUCT.price)}</p>

        {sessionError && <p className="mt-3 text-sm text-brick">{sessionError}</p>}

        <form onSubmit={handleOtpSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="card-number" className="block text-sm font-medium text-ink/70">
              Card number
            </label>
            <input
              id="card-number"
              type="text"
              placeholder="4111 1111 1111 1111"
              className="mt-1 w-full rounded-md border border-ink/15 px-3 py-2 text-sm focus:border-teal focus:outline-none focus:ring-1 focus:ring-teal"
            />
          </div>
          <div>
            <label htmlFor="otp" className="block text-sm font-medium text-ink/70">
              Enter OTP
            </label>
            <input
              id="otp"
              type="text"
              value={otpValue}
              onChange={(e) => setOtpValue(e.target.value)}
              placeholder={`Try entering anything but ${OTP_SUCCESS_CODE}`}
              aria-invalid={otpError}
              className="mt-1 w-full rounded-md border border-ink/15 px-3 py-2 text-sm focus:border-teal focus:outline-none focus:ring-1 focus:ring-teal"
            />
            {otpError && <p className="mt-1 text-xs text-brick">Incorrect OTP — please try again.</p>}
          </div>
          <button
            type="submit"
            disabled={!session}
            className="w-full rounded-md bg-teal px-4 py-2 text-sm font-medium text-white transition hover:bg-teal/90 focus:outline-none focus:ring-2 focus:ring-teal focus:ring-offset-2 disabled:opacity-50"
          >
            Pay {formatRupees(DEMO_PRODUCT.price)}
          </button>
        </form>

        {statusMessage && <p className="mt-4 text-sm text-teal" role="status">{statusMessage}</p>}

        <ConciergeWidget intervention={intervention} onRespond={handleRespond} />
      </div>

      {/* Manual demo triggers — fire the same events real detection would */}
      <div className="mt-4 rounded-lg border border-dashed border-ink/15 p-4">
        <p className="text-xs font-medium text-ink/50">
          Demo controls — trigger the same signals real detection would send
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            onClick={() => fireEvent("idle", { idle_seconds: 25 })}
            className="rounded-md border border-ink/15 px-3 py-1.5 text-xs text-ink/70 hover:bg-ink/5 focus:outline-none focus:ring-2 focus:ring-ink/30"
          >
            Simulate idle
          </button>
          <button
            onClick={() => fireEvent("back_button")}
            className="rounded-md border border-ink/15 px-3 py-1.5 text-xs text-ink/70 hover:bg-ink/5 focus:outline-none focus:ring-2 focus:ring-ink/30"
          >
            Simulate back button
          </button>
          <button
            onClick={() => {
              setOtpError(true);
              fireEvent("otp_fail");
            }}
            className="rounded-md border border-ink/15 px-3 py-1.5 text-xs text-ink/70 hover:bg-ink/5 focus:outline-none focus:ring-2 focus:ring-ink/30"
          >
            Simulate OTP failure
          </button>
        </div>
      </div>
    </div>
  );
}