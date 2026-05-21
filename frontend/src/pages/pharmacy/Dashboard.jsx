import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import { Loader2, ChevronRight, Pill } from "lucide-react";

export default function PharmacyDashboard() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/cases?status=SENT_TO_PHARMACY,IN_PHARMACY");
        setCases(data.cases);
      } catch (e) { setErr(fmtErr(e)); }
      finally { setLoading(false); }
    })();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto" data-testid="pharmacy-dashboard">
      <div className="mb-8">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Pharmacy</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Dispensing queue</h1>
      </div>

      {err && <div className="text-sm text-red-700">{err}</div>}
      <div className="bg-white border border-gray-200 rounded-md">
        {loading ? (
          <div className="p-12 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>
        ) : cases.length === 0 ? (
          <div className="p-12 grid place-items-center text-center">
            <Pill className="text-gray-300 mb-2" />
            <div className="text-sm text-gray-500">No prescriptions waiting to dispense.</div>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 text-left">
                <th className="px-4 py-3 font-semibold">Case</th>
                <th className="px-4 py-3 font-semibold">Patient</th>
                <th className="px-4 py-3 font-semibold">Doctor</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 tabular-nums text-xs text-gray-500">{c.case_uid}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{c.patient?.first_name} {c.patient?.last_name}</div>
                    <div className="text-xs text-gray-500 tabular-nums">{c.patient?.patient_uid}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-700">{c.doctor?.display_name}</td>
                  <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                  <td className="px-4 py-3 text-right">
                    <Link to={`/pharmacy/cases/${c.id}`} className="inline-flex items-center gap-1 text-teal-700 hover:text-teal-800 text-sm font-medium" data-testid={`open-pharmacy-${c.id}`}>
                      Open <ChevronRight size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
