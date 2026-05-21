import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

export function fmtErr(err) {
  const d = err?.response?.data?.detail;
  if (!d) return err?.message || "Something went wrong.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => e?.msg || JSON.stringify(e)).join(" ");
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
