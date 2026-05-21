import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import StatusBadge, { PaymentBadge } from "@/components/StatusBadge";
import { Plus, Search, UserPlus, Loader2 } from "lucide-react";

export default function ReceptionDashboard() {
  const [cases, setCases] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/cases");
      setCases(data.cases);
    } catch (e) {
      setErr(fmtErr(e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const filtered = cases.filter((c) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      c.patient?.first_name?.toLowerCase().includes(s) ||
      c.patient?.last_name?.toLowerCase().includes(s) ||
      c.patient?.phone?.toLowerCase().includes(s) ||
      c.patient?.patient_uid?.toLowerCase().includes(s) ||
      c.case_uid?.toLowerCase().includes(s)
    );
  });

  return (
    <div className="p-8 max-w-7xl mx-auto" data-testid="reception-dashboard">
      <div className="flex items-end justify-between mb-8">
        <div>
          <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Reception</div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Today's Queue</h1>
        </div>
        <div className="flex gap-2">
          <Link to="/reception/patients/new" className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-gray-200 rounded-md text-sm font-medium hover:border-teal-600" data-testid="new-patient-btn">
            <UserPlus size={15} strokeWidth={1.5} /> New Patient
          </Link>
          <Link to="/reception/new-visit" className="inline-flex items-center gap-2 px-3.5 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium" data-testid="new-visit-btn">
            <Plus size={15} strokeWidth={1.5} /> New Visit
          </Link>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-md">
        <div className="p-4 border-b border-gray-200 flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name, phone, or patient ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-md focus-ring"
              data-testid="patient-search-input"
            />
          </div>
          <div className="text-xs text-gray-500 tabular-nums">{filtered.length} cases</div>
        </div>

        {err && <div className="p-4 text-sm text-red-700">{err}</div>}
        {loading ? (
          <div className="p-12 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>
        ) : (
          <table className="w-full text-sm" data-testid="cases-table">
            <thead>
              <tr className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 text-left">
                <th className="px-4 py-3 font-semibold">Case</th>
                <th className="px-4 py-3 font-semibold">Patient</th>
                <th className="px-4 py-3 font-semibold">Phone</th>
                <th className="px-4 py-3 font-semibold">Doctor</th>
                <th className="px-4 py-3 font-semibold">Complaint</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Payment</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="p-12 text-center text-gray-400">No cases yet. Create a new visit to get started.</td></tr>
              )}
              {filtered.map((c) => (
                <tr key={c.id} className="border-t border-gray-100 hover:bg-gray-50" data-testid={`case-row-${c.id}`}>
                  <td className="px-4 py-3 tabular-nums text-gray-600 text-xs">{c.case_uid}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{c.patient?.first_name} {c.patient?.last_name}</div>
                    <div className="text-xs text-gray-500 tabular-nums">{c.patient?.patient_uid}</div>
                  </td>
                  <td className="px-4 py-3 tabular-nums text-gray-700">{c.patient?.phone}</td>
                  <td className="px-4 py-3 text-gray-700">{c.doctor?.display_name}</td>
                  <td className="px-4 py-3 text-gray-700 max-w-xs truncate">{c.complaint_text}</td>
                  <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                  <td className="px-4 py-3"><PaymentBadge status={c.payment_status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
