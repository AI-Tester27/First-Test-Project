import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtErr, fmtIST } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import { Loader2, ChevronRight, Pill, IndianRupee, ClipboardList, BellRing, CheckCircle2 } from "lucide-react";

export default function PharmacyDashboard() {
  const [cases, setCases] = useState([]);
  const [stats, setStats] = useState(null);
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [c, s, r] = await Promise.all([
        api.get("/cases?status=SENT_TO_PHARMACY,IN_PHARMACY"),
        api.get("/pharmacy/dashboard"),
        api.get("/reminders?status=PENDING"),
      ]);
      setCases(c.data.cases);
      setStats(s.data);
      setReminders(r.data.reminders);
    } catch (e) { setErr(fmtErr(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const completeReminder = async (id) => {
    try { await api.patch(`/reminders/${id}`, { status: "COMPLETED" }); load(); }
    catch (e) { setErr(fmtErr(e)); }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto" data-testid="pharmacy-dashboard">
      <div className="mb-8">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Pharmacy</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Counter dashboard</h1>
      </div>

      {err && <div className="mb-4 text-sm text-red-700">{err}</div>}

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <KPI icon={Pill} label="Pending dispense" value={stats?.pending_dispense_count ?? "—"} accent="amber" />
        <KPI icon={CheckCircle2} label="Dispensed today" value={stats?.dispensed_today_count ?? "—"} accent="emerald" />
        <KPI icon={IndianRupee} label="Medicine revenue today" value={`₹${Number(stats?.medicine_revenue_today || 0).toFixed(0)}`} accent="teal" />
        <KPI icon={BellRing} label="Active reminders" value={stats?.pharmacy_reminders_pending ?? "—"} accent="indigo" />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Dispensing queue */}
        <div className="col-span-2 bg-white border border-gray-200 rounded-md">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-display text-sm font-semibold text-gray-900">Dispensing queue</h2>
            <span className="text-xs text-gray-500 tabular-nums">{cases.length}</span>
          </div>
          {loading ? (
            <div className="p-12 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>
          ) : cases.length === 0 ? (
            <div className="p-10 grid place-items-center text-center">
              <Pill className="text-gray-300 mb-2" />
              <div className="text-sm text-gray-500">No prescriptions waiting.</div>
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

        {/* Reminders side panel */}
        <div className="col-span-1 bg-white border border-gray-200 rounded-md">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-display text-sm font-semibold text-gray-900">Reminders for pharmacy</h2>
            <span className="text-xs text-gray-500 tabular-nums">{reminders.length}</span>
          </div>
          {reminders.length === 0 ? (
            <div className="p-8 text-center text-sm text-gray-400">
              <ClipboardList className="text-gray-300 mb-2 mx-auto" />
              No active reminders.
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {reminders.map((r) => (
                <div key={r.id} className="p-3" data-testid={`pharm-reminder-${r.id}`}>
                  <div className="text-sm font-medium text-gray-900">{r.patient_name}</div>
                  <div className="text-xs text-gray-500 tabular-nums">{r.patient_uid} · {fmtIST(r.scheduled_at)}</div>
                  {r.message && <div className="text-xs text-gray-700 mt-1">{r.message}</div>}
                  <button onClick={() => completeReminder(r.id)} className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-800" data-testid={`complete-pharm-${r.id}`}>
                    <CheckCircle2 size={12} /> Mark complete
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function KPI({ icon: Icon, label, value, accent = "teal" }) {
  const map = {
    teal: "bg-teal-50 text-teal-700",
    amber: "bg-amber-50 text-amber-700",
    emerald: "bg-emerald-50 text-emerald-700",
    indigo: "bg-indigo-50 text-indigo-700",
  };
  return (
    <div className="bg-white border border-gray-200 rounded-md p-5">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs uppercase tracking-wider font-semibold text-gray-500">{label}</div>
        <div className={`w-7 h-7 rounded-md grid place-items-center ${map[accent]}`}><Icon size={14} strokeWidth={1.5} /></div>
      </div>
      <div className="font-display text-2xl font-semibold tracking-tight text-gray-900 tabular-nums">{value}</div>
    </div>
  );
}
