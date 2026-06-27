import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

// Friendly labels for backend field paths in validation errors.
const FIELD_LABELS = {
  height_cm: "Height (cm)",
  weight_kg: "Weight (kg)",
  age: "Age",
  phone: "Phone",
  first_name: "First name",
  last_name: "Last name",
  consulting_doctor_id: "Consulting doctor",
  chief_complaint: "Chief complaint",
  visit_type: "Visit type",
  marital_status: "Marital status",
  password: "Password",
  username: "Username",
  next_followup_date: "Follow-up date",
};

export function fmtErr(err) {
  const d = err?.response?.data?.detail;
  if (!d) return err?.message || "Something went wrong.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d.map((e) => {
      const path = (e?.loc || []).filter((p) => p !== "body");
      const last = path[path.length - 1];
      const label = FIELD_LABELS[last] || (typeof last === "string" ? last.replace(/_/g, " ") : "Value");
      return `${label}: ${e?.msg || "invalid value"}`;
    }).join(" · ");
  }
  return JSON.stringify(d);
}

export const STATUS_LABELS = {
  WAITING_FOR_DOCTOR: "Waiting for Doctor",
  IN_CONSULTATION: "In Consultation",
  SENT_TO_PHARMACY: "Sent to Pharmacy",
  IN_PHARMACY: "In Pharmacy",
  READY_FOR_BILLING: "Ready for Billing",
  PAYMENT_PENDING: "Payment Pending",
  PARTIALLY_PAID: "Partially Paid",
  CLOSED: "Closed",
};

export const STATUS_PILL_CLASS = {
  WAITING_FOR_DOCTOR: "pill pill-waiting",
  IN_CONSULTATION: "pill pill-in-consultation",
  SENT_TO_PHARMACY: "pill pill-sent-pharmacy",
  IN_PHARMACY: "pill pill-in-pharmacy",
  READY_FOR_BILLING: "pill pill-ready-billing",
  PAYMENT_PENDING: "pill pill-payment-pending",
  PARTIALLY_PAID: "pill pill-partially-paid",
  CLOSED: "pill pill-closed",
};

export const ROLE_LABELS = {
  ADMIN: "Admin",
  OWNER_DOCTOR: "Owner / Lead Doctor",
  DOCTOR: "Doctor",
  RECEPTION: "Reception",
  PHARMACY: "Pharmacy",
  PRO: "Billing / PRO",
};

export function roleHomePath(role) {
  switch (role) {
    case "ADMIN": return "/admin";
    case "OWNER_DOCTOR":
    case "DOCTOR": return "/doctor";
    case "RECEPTION": return "/reception";
    case "PHARMACY": return "/pharmacy";
    case "PRO": return "/pro";
    default: return "/login";
  }
}

// ─── IST helpers ────────────────────────────────────────────────
const IST_LOCALE = "en-IN";
const IST_TZ = { timeZone: "Asia/Kolkata" };

export function fmtIST(iso, { withTime = true } = {}) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(IST_LOCALE, {
      ...IST_TZ,
      day: "2-digit",
      month: "short",
      year: "numeric",
      ...(withTime ? { hour: "2-digit", minute: "2-digit", hour12: true } : {}),
    });
  } catch {
    return iso;
  }
}

export function fmtIST_time(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString(IST_LOCALE, { ...IST_TZ, hour: "2-digit", minute: "2-digit", hour12: true });
  } catch { return iso; }
}

export function fmtIST_date(iso) {
  return fmtIST(iso, { withTime: false });
}

/** Convert datetime-local input ("2024-01-15T10:00") interpreted as IST to UTC ISO. */
export function istLocalToUtcISO(localStr) {
  if (!localStr) return null;
  // localStr is like "2024-01-15T10:00" (browser local). User intends this as IST.
  const [date, time] = localStr.split("T");
  const [y, m, d] = date.split("-").map(Number);
  const [hh, mm] = (time || "00:00").split(":").map(Number);
  // Build UTC time = IST time - 5h30m
  const utc = new Date(Date.UTC(y, m - 1, d, hh, mm) - (5 * 60 + 30) * 60000);
  return utc.toISOString();
}

/** Convert a UTC ISO timestamp to a datetime-local input value in IST. */
export function utcISOToIstLocal(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const ist = new Date(d.getTime() + (5 * 60 + 30) * 60000);
  return ist.toISOString().slice(0, 16);
}
