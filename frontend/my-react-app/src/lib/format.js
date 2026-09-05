/**
 * Format an amount in paise (Razorpay's smallest currency unit) as a
 * rupee display string, e.g. 649900 -> "₹6,499".
 */
export function formatRupees(paise) {
  return `₹${Math.round(paise / 100).toLocaleString("en-IN")}`;
}

/**
 * Turn a snake_case action type into a readable label,
 * e.g. "suggest_payment_method" -> "suggest payment method".
 */
export function humanizeActionType(actionType) {
  return actionType.replaceAll("_", " ");
}

/** Human-friendly button label per intervention action type. */
export function actionButtonLabel(actionType) {
  const labels = {
    offer_discount: "Apply discount",
    suggest_payment_method: "Switch method",
    offer_emi: "Split with EMI",
  };
  return labels[actionType] || "Accept offer";
}