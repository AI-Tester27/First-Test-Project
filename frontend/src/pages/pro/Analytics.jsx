import { useEffect, useState } from "react";
import { api, fmtErr } from "@/lib/api";
import { Loader2, IndianRupee, Users, Calendar, TrendingUp, Clock, AlertCircle } from "lucide-react";

const fINR = (n) => `₹${Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
const SOURCE_LABELS = {
  TELEVISION: "Television", NEWSPAPER: "Newspaper", MEDICAL_CAMPS: "Camps",
  SIGN_BOARDS: "Signs", BANNERS: "Banners", NEARBY_RESIDENCE: "Nearby",
  SOCIAL_MEDIA: "Social media", YOUTUBE: "YouTube", FACEBOOK: "Facebook",
  INSTAGRAM: "Instagram", ONLINE_SEARCH: "Search", REFERRAL: "Referral", OTHERS: "Others",
};

export default function ProAnalytics() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try { const { data } = await api.get("/pro/analytics"); setData(data); }
      catch (e) { setErr(fmtErr(e)); }
    })();
  }, []);

  if (err) return <div className="p-8 text-red-700">{err}</div>;
  if (!data) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  const pm = data.patient_metrics;
  const vm = data.visit_metrics;
  const rm = data.revenue_metrics;
  const om = data.operational_metrics;
  const fm = data.financial_metrics;
  const maxRev = Math.max(1, ...rm.trend_30d.map((d) => d.amount));

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8" data-testid="pro-analytics-page">
      <div>
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">PRO · Business analytics</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Clinic performance — last 30 days</h1>
      </div>

      {/* Top KPIs */}
      <div className="grid grid-cols-5 gap-4">
        <KPI icon={Users} label="Total patients" value={pm.total} sub={`+${pm.new_30d} in 30d`} />
        <KPI icon={Calendar} label="Visits (30d)" value={vm.last_30d} sub={`${vm.today} today`} accent="amber" />
        <KPI icon={IndianRupee} label="Revenue (30d)" value={fINR(rm.last_30d)} sub={`${fINR(rm.today)} today`} accent="emerald" />
        <KPI icon={Clock} label="Avg turnaround" value={`${om.avg_turnaround_minutes} min`} sub={`${om.closed_cases_30d} cases closed`} accent="indigo" />
        <KPI icon={AlertCircle} label="Outstanding" value={fINR(fm.outstanding_amount)} sub={`${fm.outstanding_count} bills`} accent={fm.outstanding_amount > 0 ? "rose" : "teal"} />
      </div>

      {/* Revenue trend chart */}
      <div className="bg-white border border-gray-200 rounded-md p-6" data-testid="revenue-trend">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-0.5">Revenue trend</div>
            <h2 className="font-display text-lg font-semibold text-gray-900">Collections — last 30 days</h2>
          </div>
          <TrendingUp size={18} className="text-gray-300" />
        </div>
        <div className="flex items-end gap-1 h-32">
          {rm.trend_30d.map((d, i) => (
            <div key={i} className="flex-1 group relative">
              <div className="w-full bg-teal-100 hover:bg-teal-300 transition-colors rounded-sm" style={{ height: `${Math.max(4, (d.amount / maxRev) * 100)}%` }} />
              <div className="absolute -top-7 left-1/2 -translate-x-1/2 hidden group-hover:block text-[10px] bg-gray-900 text-white px-1.5 py-0.5 rounded whitespace-nowrap z-10">{d.label}: {fINR(d.amount)}</div>
            </div>
          ))}
        </div>
        <div className="flex justify-between text-[10px] text-gray-400 mt-1 tabular-nums">
          <span>{rm.trend_30d[0]?.label}</span>
          <span>{rm.trend_30d.at(-1)?.label}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Patient demographics */}
        <Card title="Patient demographics">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold mb-2">By gender</div>
              <BarList data={Object.entries(pm.by_gender).map(([k, v]) => ({ label: k, value: v }))} />
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold mb-2">By age</div>
              <BarList data={pm.age_group_order.map((k) => ({ label: k, value: pm.by_age_group[k] || 0 }))} />
            </div>
          </div>
        </Card>

        {/* Source acquisition */}
        <Card title="Acquisition sources (30d)" empty={pm.sources_30d.length === 0 && "No sources recorded yet"}>
          <BarList data={pm.sources_30d.slice(0, 8).map((s) => ({ label: SOURCE_LABELS[s.source] || s.source, value: s.count }))} />
        </Card>

        {/* Visit metrics */}
        <Card title="Visits by doctor (30d)" empty={vm.by_doctor_30d.length === 0 && "No visits yet"}>
          <BarList data={vm.by_doctor_30d.map((d) => ({ label: d.doctor, value: d.count }))} />
        </Card>

        {/* Visit type */}
        <Card title="Visit type (30d)" empty={Object.keys(vm.by_visit_type_30d).length === 0 && "No visits yet"}>
          <BarList data={Object.entries(vm.by_visit_type_30d).map(([k, v]) => ({ label: k === "WALK_IN" ? "Walk-in" : k === "APPOINTMENT" ? "Appointment" : k, value: v }))} />
        </Card>

        {/* Revenue by mode */}
        <Card title="Revenue by mode (30d)" empty={rm.by_mode_30d.length === 0 && "No payments yet"}>
          <BarList data={rm.by_mode_30d.map((m) => ({ label: m.mode, value: m.amount, sublabel: `${m.count} tx` }))} formatter={fINR} />
        </Card>

        {/* Consultation vs Medicine */}
        <Card title="Consultation vs medicine (30d)">
          <BarList data={[
            { label: "Consultation", value: rm.consult_vs_medicine_30d.consultation },
            { label: "Medicine", value: rm.consult_vs_medicine_30d.medicine },
          ]} formatter={fINR} />
        </Card>
      </div>
    </div>
  );
}

function KPI({ icon: Icon, label, value, sub, accent = "teal" }) {
  const tones = {
    teal: "bg-teal-50 text-teal-700",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    rose: "bg-rose-50 text-rose-700",
    indigo: "bg-indigo-50 text-indigo-700",
  };
  return (
    <div className="bg-white border border-gray-200 rounded-md p-4">
      <div className="flex items-start justify-between mb-1">
        <div className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">{label}</div>
        <div className={`w-7 h-7 rounded grid place-items-center ${tones[accent]}`}><Icon size={14} strokeWidth={1.5} /></div>
      </div>
      <div className="font-display text-2xl font-semibold text-gray-900 tabular-nums tracking-tight">{value}</div>
      {sub && <div className="text-[11px] text-gray-500 mt-0.5 tabular-nums">{sub}</div>}
    </div>
  );
}

function Card({ title, children, empty }) {
  return (
    <div className="bg-white border border-gray-200 rounded-md p-5">
      <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3">{title}</div>
      {empty ? <div className="text-sm text-gray-400 py-4">{empty}</div> : children}
    </div>
  );
}

function BarList({ data, formatter }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  if (data.length === 0) return <div className="text-sm text-gray-400">No data.</div>;
  return (
    <div className="space-y-2">
      {data.map((d, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <div className="w-24 truncate text-gray-700 shrink-0" title={d.label}>{d.label}</div>
          <div className="flex-1 h-5 bg-gray-100 rounded-sm overflow-hidden">
            <div className="h-full bg-teal-500/70" style={{ width: `${(d.value / max) * 100}%` }} />
          </div>
          <div className="w-16 text-right tabular-nums text-gray-900 font-medium">{formatter ? formatter(d.value) : d.value}</div>
          {d.sublabel && <div className="w-12 text-right text-[10px] text-gray-500 tabular-nums">{d.sublabel}</div>}
        </div>
      ))}
    </div>
  );
}
