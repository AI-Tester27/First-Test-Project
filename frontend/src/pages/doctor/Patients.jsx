import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Search, Loader2, ChevronRight, Phone, MessageSquare } from "lucide-react";

const ROLE_OWNER_DOCTOR = "OWNER_DOCTOR";

export default function DoctorPatients() {
  const { user } = useAuth();
  const isOwner = user?.role === ROLE_OWNER_DOCTOR;
  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setErr("");
    try {
      const { data } = await api.get(`/patients?search=${encodeURIComponent(search)}`);
      setPatients(data.patients || []);
    } catch (e) { setErr(fmtErr(e)); }
    finally { setLoading(false); }
  }, [search]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <div className="p-8 max-w-6xl mx-auto" data-testid="doctor-patients-page">
      <div className="mb-6">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">{isOwner ? "Owner doctor · all patients" : "Doctor · my patients"}</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">{isOwner ? "Patient search" : "My patients"}</h1>
        <p className="text-sm text-gray-600 mt-2">
          {isOwner
            ? "Search across every patient in the clinic by name, patient ID or phone."
            : "Search the patients assigned to you. Only your own cases are visible (RBAC)."}
        </p>
      </div>

      <div className="relative mb-4 max-w-xl">
        <Search size={16} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search by name, patient ID, or phone…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:border-teal-700 focus:ring-2 focus:ring-teal-700/20"
          data-testid="doctor-patient-search"
        />
      </div>

      {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-3">{err}</div>}

      <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 text-xs uppercase tracking-wider text-gray-500">
            <tr>
              <th className="text-left px-4 py-2.5">Patient</th>
              <th className="text-left px-4 py-2.5">UID</th>
              <th className="text-left px-4 py-2.5">Age / Sex</th>
              <th className="text-left px-4 py-2.5">Phone</th>
              <th className="text-left px-4 py-2.5">Quick contact</th>
              <th className="text-right px-4 py-2.5">Open</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-gray-400"><Loader2 className="inline animate-spin" /></td></tr>
            ) : patients.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-gray-400">{search ? "No patients match this search." : (isOwner ? "No patients in system yet." : "You have no patients assigned yet.")}</td></tr>
            ) : patients.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50" data-testid={`patient-row-${p.id}`}>
                <td className="px-4 py-3 font-medium text-gray-900">{p.first_name} {p.last_name}</td>
                <td className="px-4 py-3 text-xs tabular-nums text-gray-600">{p.patient_uid}</td>
                <td className="px-4 py-3 text-gray-700">{p.age} · {p.gender}</td>
                <td className="px-4 py-3 tabular-nums text-gray-700">{p.phone}</td>
                <td className="px-4 py-3">
                  <QuickContact phone={p.phone} name={`${p.first_name} ${p.last_name}`} />
                </td>
                <td className="px-4 py-3 text-right">
                  <Link to={`/doctor/patients/${p.id}/timeline`} className="inline-flex items-center gap-1 text-sm text-teal-700 hover:text-teal-900 font-medium" data-testid={`open-${p.id}`}>
                    Open <ChevronRight size={14} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function QuickContact({ phone, name = "patient", message }) {
  if (!phone) return <span className="text-xs text-gray-400">—</span>;
  const cleaned = phone.replace(/[^0-9]/g, "");
  const wa = cleaned.length === 10 ? `91${cleaned}` : cleaned;
  const msg = encodeURIComponent(message || `Hi ${name}, this is from Sparsa Homeo Care.`);
  return (
    <div className="flex items-center gap-1">
      <a href={`tel:+${wa}`} title="Call" data-testid="qc-call"
        className="w-7 h-7 rounded-md grid place-items-center border border-gray-200 hover:border-teal-600 hover:text-teal-700 transition">
        <Phone size={13} strokeWidth={1.75} />
      </a>
      <a href={`sms:+${wa}?body=${msg}`} title="SMS" data-testid="qc-sms"
        className="w-7 h-7 rounded-md grid place-items-center border border-gray-200 hover:border-teal-600 hover:text-teal-700 transition">
        <MessageSquare size={13} strokeWidth={1.75} />
      </a>
      <a href={`https://wa.me/${wa}?text=${msg}`} target="_blank" rel="noreferrer" title="WhatsApp" data-testid="qc-whatsapp"
        className="w-7 h-7 rounded-md grid place-items-center border border-gray-200 hover:border-emerald-500 hover:text-emerald-600 transition">
        <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor"><path d="M19.05 4.95A10 10 0 0 0 4.06 18.6L2.92 22.7l4.18-1.1A10 10 0 0 0 22 12.07a9.94 9.94 0 0 0-2.95-7.12Zm-7 15.3a8.27 8.27 0 0 1-4.25-1.16l-.3-.18-2.49.65.67-2.42-.2-.32a8.31 8.31 0 1 1 6.57 3.43Zm4.55-6.18c-.25-.13-1.47-.72-1.7-.8s-.39-.13-.56.13-.65.8-.8.96-.29.2-.54.07a6.84 6.84 0 0 1-3.42-2.99c-.26-.45.26-.42.74-1.38.08-.16 0-.3-.06-.43s-.56-1.35-.77-1.84-.41-.41-.56-.42h-.48a.93.93 0 0 0-.67.31 2.83 2.83 0 0 0-.88 2.1c0 1.24.9 2.44 1.03 2.6s1.77 2.7 4.3 3.79c1.61.7 2.25.76 3.06.64.49-.07 1.47-.6 1.68-1.18s.21-1.06.15-1.18-.23-.17-.48-.3Z"/></svg>
      </a>
    </div>
  );
}
