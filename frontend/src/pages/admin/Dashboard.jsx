import { useEffect, useState } from "react";
import { api, fmtErr } from "@/lib/api";
import { Users, FileText, Activity, IndianRupee, Loader2, TrendingUp, Clock, Stethoscope } from "lucide-react";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [s, a] = await Promise.all([api.get("/admin/stats"), api.get("/admin/analytics")]);
        setStats(s.data);
        setAnalytics(a.data);
      } catch (e) { setErr(fmtErr(e)); }
    })();
  }, []);

  if (err) return <div className="p-8 text-red-700">{err}</div>;
  if (!stats || !analytics) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  const maxRev = Math.max(1, ...analytics.case_trend_30d.map((d) => d.revenue));
  const maxCases = Math.max(1, ...analytics.case_trend_30d.map((d) => d.cases));

  return (
    <div className="p-8 max-w-7xl mx-auto" data-testid="admin-dashboard">
      <div className="mb-8">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Admin · Analytics</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Clinic overview</h1>
      </div>

      <div className="grid grid-cols-5 gap-4 mb-8">
        <KPI icon={Users} label="Patients" value={stats.total_patients} />
        <KPI icon={FileText} label="Cases" value={stats.total_cases} />
        <KPI icon={Activity} label="Active cases" value={stats.pending_cases} accent="amber" />
        <KPI icon={IndianRupee} label="Revenue" value={`₹${Number(stats.total_revenue).toFixed(0)}`} accent="emerald" />
        <KPI icon={Clock} label="Avg turnaround" value={`${analytics.avg_turnaround_minutes}m`} accent="indigo" sub={`${analytics.closed_cases_30d} closed in 30d`} />
      </div>

      {/* 30-day trend */}
      <div className="bg-white border border-gray-200 rounded-md p-5 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={15} strokeWidth={1.5} className="text-teal-700" />
          <h2 className="font-display text-sm font-semibold text-gray-900">30-day activity (cases · revenue ₹)</h2>
        </div>
        <div className="flex items-end justify-between gap-1 h-32" data-testid="trend-30d">
          {analytics.case_trend_30d.map((d) => (
            <div key={d.date} className="flex-1 flex flex-col items-center justify-end gap-1 group" title={`${d.label}\n${d.cases} cases · ₹${d.revenue}`}>
              <div className="w-full flex items-end justify-center gap-0.5 h-28">
                <div className="w-1/2 bg-teal-600 rounded-t" style={{ height: `${(d.cases / maxCases) * 100}%`, minHeight: d.cases > 0 ? "2px" : "0" }} />
                <div className="w-1/2 bg-emerald-500 rounded-t" style={{ height: `${(d.revenue / maxRev) * 100}%`, minHeight: d.revenue > 0 ? "2px" : "0" }} />
              </div>
              <div className="text-[9px] text-gray-400 tabular-nums">{d.label.split(" ")[0]}</div>
            </div>
          ))}
        </div>
        <div className="flex gap-4 text-xs text-gray-500 mt-2">
          <span className="inline-flex items-center gap-1"><span className="w-2.5 h-2.5 bg-teal-600 rounded-sm" /> Cases</span>
          <span className="inline-flex items-center gap-1"><span className="w-2.5 h-2.5 bg-emerald-500 rounded-sm" /> Revenue</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-md p-5">
          <div className="font-display font-semibold text-sm text-gray-900 mb-4 flex items-center gap-2">
            <Stethoscope size={14} strokeWidth={1.5} className="text-teal-700" /> By Doctor
          </div>
          <div className="space-y-2">
            {stats.by_doctor.map((d) => (
              <div key={d.doctor} className="flex justify-between text-sm">
                <span className="text-gray-600">{d.doctor}</span>
                <span className="tabular-nums font-medium text-gray-900">{d.cases}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-md p-5">
          <div className="font-display font-semibold text-sm text-gray-900 mb-4">By Status</div>
          <div className="space-y-2 max-h-44 overflow-auto">
            {Object.entries(stats.by_status).map(([k, v]) => (
              <div key={k} className="flex justify-between text-sm">
                <span className="text-gray-600 text-xs">{k.replace(/_/g, " ")}</span>
                <span className="tabular-nums font-medium text-gray-900">{v}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-md p-5">
          <div className="font-display font-semibold text-sm text-gray-900 mb-4">Logins (30d)</div>
          {Object.keys(analytics.logins_by_role_30d).length === 0 ? (
            <div className="text-sm text-gray-400">No logins yet.</div>
          ) : (
            <div className="space-y-2">
              {Object.entries(analytics.logins_by_role_30d).map(([role, n]) => (
                <div key={role} className="flex justify-between text-sm">
                  <span className="text-gray-600">{role}</span>
                  <span className="tabular-nums font-medium text-gray-900">{n}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top complaints */}
      <div className="bg-white border border-gray-200 rounded-md p-5">
        <h2 className="font-display text-sm font-semibold text-gray-900 mb-4">Most-mentioned complaint terms</h2>
        {analytics.top_complaints.length === 0 ? (
          <div className="text-sm text-gray-400">No data yet.</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {analytics.top_complaints.map((t) => (
              <span key={t.term} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-teal-50 border border-teal-200 rounded-full text-xs">
                <span className="font-medium text-teal-900">{t.term}</span>
                <span className="tabular-nums text-teal-700">{t.count}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function KPI({ icon: Icon, label, value, accent = "teal", sub }) {
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
      {sub && <div className="text-[11px] text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}
