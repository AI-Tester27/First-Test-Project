import { STATUS_LABELS, STATUS_PILL_CLASS } from "@/lib/api";

export default function StatusBadge({ status }) {
  if (!status) return null;
  return (
    <span className={STATUS_PILL_CLASS[status] || "pill pill-waiting"} data-testid={`status-${status}`}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}

export function PaymentBadge({ status }) {
  if (!status) return <span className="text-xs text-gray-400">—</span>;
  const cls = {
    PAID: "pill pill-paid",
    PARTIAL: "pill pill-partial",
    UNPAID: "pill pill-unpaid",
  }[status] || "pill pill-unpaid";
  return <span className={cls} data-testid={`payment-${status}`}>{status}</span>;
}
