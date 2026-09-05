import { formatRupees, humanizeActionType, actionButtonLabel } from "../src/lib/format.js";

function assertEqual(actual, expected, label) {
  if (actual !== expected) {
    console.error(`FAIL: ${label} — expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
    process.exitCode = 1;
  } else {
    console.log(`PASS: ${label}`);
  }
}

assertEqual(formatRupees(649900), "₹6,499", "formatRupees: whole product price");
assertEqual(formatRupees(50000), "₹500", "formatRupees: round number");
assertEqual(formatRupees(100000000), "₹10,00,000", "formatRupees: large amount uses Indian grouping");
assertEqual(formatRupees(150), "₹2", "formatRupees: rounds fractional rupees");

assertEqual(humanizeActionType("suggest_payment_method"), "suggest payment method", "humanizeActionType: multi-word");
assertEqual(humanizeActionType("no_action"), "no action", "humanizeActionType: two-word");

assertEqual(actionButtonLabel("offer_discount"), "Apply discount", "actionButtonLabel: discount");
assertEqual(actionButtonLabel("suggest_payment_method"), "Switch method", "actionButtonLabel: method switch");
assertEqual(actionButtonLabel("offer_emi"), "Split with EMI", "actionButtonLabel: EMI");
assertEqual(actionButtonLabel("unknown_type"), "Accept offer", "actionButtonLabel: fallback for unrecognized type");

if (process.exitCode === 1) {
  console.error("\nSome tests failed.");
} else {
  console.log("\nAll format.js tests passed.");
}