import { useEffect, useState } from "react";
import { api, fmtErr } from "@/lib/api";
import { Users, FileText, Activity, IndianRupee, Loader2 } from "lucide-react";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try { const { data } = await api.get("/admin/stats"); setStats(data); }
      catch (e) { setErr(fmtErr(e)); }
    })();
  }, []);

  if (err) return <div className="p-8 text-red-700">{err}</div>;
  if (!stats) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  return (
    <div className="p-8 max-w-7xl mx-auto" data-testid="admin-dashboard">
      <div className="mb-8">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Admin</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Clinic overview</h1>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <KPI icon={Users} label="Patients" value={stats.total_patients} />
        <KPI icon={FileText} label="Cases" value={stats.total_cases} />
        <KPI icon={Activity} label="Active" value={stats.pending_cases} />
        <KPI icon={IndianRupee} label="Revenue" value={`₹${Number(stats.total_revenue || 0).toFixed(0)}`} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white border border-gray-200 rounded-md p-5">
          <div className="font-display font-semibold text-sm text-gray-900 mb-4">By Status</div>
          <div className="space-y-2">
            {Object.entries(stats.by_status).map(([k, v]) => (
              <div key={k} className="flex justify-between text-sm">
                <span className="text-gray-600">{k.replace(/_/g, " ")}</span>
                <span className="tabular-nums font-medium text-gray-900">{v}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-md p-5">
          <div className="font-display font-semibold text-sm text-gray-900 mb-4">By Doctor</div>
          <div className="space-y-2">
            {stats.by_doctor.map((d) => (
              <div key={d.doctor} className="flex justify-between text-sm">
                <span className="text-gray-600">{d.doctor}</span>
                <span className="tabular-nums font-medium text-gray-900">{d.cases}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function KPI({ icon: Icon, label, value }) {
  return (
    <div className="bg-white border border-gray-200 rounded-md p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs uppercase tracking-wider font-semibold text-gray-500">{label}</div>
        <Icon size={16} strokeWidth={1.5} className="text-teal-700" />
      </div>
      <div className="font-display text-3xl font-semibold tracking-tight text-gray-900 tabular-nums">{value}</div>
    </div>
  );
}
