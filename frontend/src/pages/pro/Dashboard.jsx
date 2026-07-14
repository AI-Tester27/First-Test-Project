import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtErr, fmtIST } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import { QuickContact } from "@/pages/doctor/Patients";
import { Loader2, ChevronRight, ReceiptText, IndianRupee, AlertCircle, Users, Calendar, TrendingUp } from "lucide-react";

const MAX_BAR_VALUE = (trend) => Math.max(1, ...trend.map((t) => t.revenue || 0));

export default function ProDashboard() {
  const [stats, setStats] = useState(null);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [s, c] = await Promise.all([
          api.get("/pro/dashboard"),
          api.get("/cases?status=AWAITING_PRO_REVIEW,READY_FOR_BILLING,PAYMENT_PENDING,PARTIALLY_PAID"),
        ]);
        setStats(s.data);
        setCases(c.data.cases);
      } catch (e) { setErr(fmtErr(e)); }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;
  if (err) return <div className="p-8 text-red-700">{err}</div>;

  const maxRev = MAX_BAR_VALUE(stats.revenue_trend_7d);

  return (
    <div className="p-8 max-w-7xl mx-auto" data-testid="pro-dashboard">
      <div className="mb-8">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Billing · PRO</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Today at the clinic</h1>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-5 gap-4 mb-8">
        <KPI icon={IndianRupee} label="Revenue today" value={`₹${Number(stats.today_revenue).toFixed(0)}`} sub={`${stats.today_collections} collections`} accent="emerald" />
        <KPI icon={ReceiptText} label="Pending bills" value={stats.pending_billing_count} accent="amber" />
        <KPI icon={AlertCircle} label="Outstanding" value={`₹${Number(stats.outstanding_amount).toFixed(0)}`} sub={`${stats.outstanding_count} cases`} accent="rose" />
        <KPI icon={IndianRupee} label="Total revenue" value={`₹${Number(stats.total_revenue).toFixed(0)}`} accent="teal" />
        <KPI icon={Users} label="Total patients" value={stats.total_patients} accent="indigo" />
      </div>

      <div className="grid grid-cols-3 gap-6 mb-8">
        {/* Revenue trend */}
        <div className="col-span-2 bg-white border border-gray-200 rounded-md p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={15} strokeWidth={1.5} className="text-teal-700" />
            <h2 className="font-display text-sm font-semibold text-gray-900">7-day revenue trend</h2>
            <span className="text-xs text-gray-500 ml-auto">IST days</span>
          </div>
          <div className="flex items-end justify-between gap-2 h-32" data-testid="revenue-trend">
            {stats.revenue_trend_7d.map((d) => (
              <div key={d.date} className="flex-1 flex flex-col items-center gap-1.5">
                <div className="text-[10px] tabular-nums text-gray-500">₹{Number(d.revenue).toFixed(0)}</div>
                <div
                  className="w-full bg-gradient-to-t from-teal-700 to-teal-400 rounded-t"
                  style={{ height: `${Math.max(2, (d.revenue / maxRev) * 100)}%`, minHeight: "2px" }}
                />
                <div className="text-[11px] text-gray-500">{d.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Payment modes today */}
        <div className="bg-white border border-gray-200 rounded-md p-5">
          <h2 className="font-display text-sm font-semibold text-gray-900 mb-4">Modes today</h2>
          {Object.keys(stats.by_mode_today).length === 0 ? (
            <div className="text-sm text-gray-400 py-8 text-center">No collections yet today.</div>
          ) : (
            <div className="space-y-3">
              {Object.entries(stats.by_mode_today).map(([mode, amount]) => (
                <div key={mode}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-700">{mode}</span>
                    <span className="tabular-nums font-medium">₹{Number(amount).toFixed(0)}</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-teal-600" style={{ width: `${(amount / stats.today_revenue) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Two columns: billing queue + follow-ups today */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-white border border-gray-200 rounded-md">
          <div className="px-4 py-3 border-b border-gray-200 flex justify-between items-center">
            <h2 className="font-display text-sm font-semibold text-gray-900">Billing queue</h2>
            <span className="text-xs text-gray-500 tabular-nums">{cases.length}</span>
          </div>
          {cases.length === 0 ? (
            <div className="p-10 grid place-items-center text-center">
              <ReceiptText className="text-gray-300 mb-2" />
              <div className="text-sm text-gray-500">No pending bills.</div>
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
                      <Link to={`/pro/cases/${c.id}`} className="inline-flex items-center gap-1 text-teal-700 hover:text-teal-800 text-sm font-medium" data-testid={`open-billing-${c.id}`}>
                        Bill <ChevronRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="bg-white border border-gray-200 rounded-md">
          <div className="px-4 py-3 border-b border-gray-200 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Calendar size={14} strokeWidth={1.5} className="text-amber-700" />
              <h2 className="font-display text-sm font-semibold text-gray-900">Follow-ups today</h2>
            </div>
            <span className="text-xs text-gray-500 tabular-nums">{stats.followups_today_count}</span>
          </div>
          {stats.followups_today.length === 0 ? (
            <div className="p-8 text-center text-sm text-gray-400">None scheduled.</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {stats.followups_today.map((r) => (
                <div key={r.id} className="p-3" data-testid={`followup-${r.id}`}>
                  <div className="text-sm font-medium text-gray-900">{r.patient_name}</div>
                  <div className="text-xs text-gray-500 tabular-nums">{r.patient_uid} · {r.scheduled_date ? new Date(r.scheduled_date + "T00:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : fmtIST(r.scheduled_at)}</div>
                  {r.patient_phone && (
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className="text-xs text-gray-600 tabular-nums">{r.patient_phone}</span>
                      <QuickContact phone={r.patient_phone} name={r.patient_name} />
                    </div>
                  )}
                  {r.message && <div className="text-xs text-gray-700 mt-1 line-clamp-2">{r.message}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function KPI({ icon: Icon, label, value, sub, accent = "teal" }) {
  const map = {
    teal: "bg-teal-50 text-teal-700",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    rose: "bg-rose-50 text-rose-700",
    indigo: "bg-indigo-50 text-indigo-700",
  };
  return (
    <div className="bg-white border border-gray-200 rounded-md p-5">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs uppercase tracking-wider font-semibold text-gray-500">{label}</div>
        <div className={`w-7 h-7 rounded-md grid place-items-center ${map[accent]}`}><Icon size={14} strokeWidth={1.5} /></div>
      </div>
      <div className="font-display text-2xl font-semibold tracking-tight text-gray-900 tabular-nums">{value}</div>
      {sub && <div className="text-[11px] text-gray-500 mt-1 tabular-nums">{sub}</div>}
    </div>
  );
}
