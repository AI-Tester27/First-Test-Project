import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import { Loader2, ChevronRight } from "lucide-react";

export default function DoctorDashboard({ scope }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const statusParam = scope === "all"
          ? ""
          : "?status=WAITING_FOR_DOCTOR,IN_CONSULTATION,SENT_TO_PHARMACY,IN_PHARMACY,READY_FOR_BILLING,PAYMENT_PENDING,PARTIALLY_PAID";
        const { data } = await api.get(`/cases${statusParam}`);
        setCases(data.cases);
      } catch (e) { setErr(fmtErr(e)); }
      finally { setLoading(false); }
    })();
  }, [scope]);

  const myActive = cases.filter((c) =>
    ["WAITING_FOR_DOCTOR", "IN_CONSULTATION"].includes(c.status)
  );

  return (
    <div className="p-8 max-w-7xl mx-auto" data-testid="doctor-dashboard">
      <div className="mb-8">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Doctor</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">
          {scope === "all" ? "All Cases" : "My Queue"}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {scope === "all" ? "Every case across the clinic." : "Patients waiting for consultation."}
        </p>
      </div>

      {err && <div className="mb-4 text-sm text-red-700">{err}</div>}

      {scope !== "all" && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          <KPI label="In queue" value={cases.filter(c => c.status === "WAITING_FOR_DOCTOR").length} />
          <KPI label="In consultation" value={cases.filter(c => c.status === "IN_CONSULTATION").length} />
          <KPI label="Sent to pharmacy" value={cases.filter(c => c.status === "SENT_TO_PHARMACY").length} />
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-md">
        <div className="px-4 py-3 border-b border-gray-200 flex justify-between items-center">
          <h2 className="font-display text-sm font-semibold text-gray-900">{scope === "all" ? "All cases" : "Active cases"}</h2>
          <div className="text-xs text-gray-500 tabular-nums">{(scope === "all" ? cases : myActive).length}</div>
        </div>

        {loading ? (
          <div className="p-12 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 text-left">
                <th className="px-4 py-3 font-semibold">Case</th>
                <th className="px-4 py-3 font-semibold">Patient</th>
                <th className="px-4 py-3 font-semibold">Complaint</th>
                <th className="px-4 py-3 font-semibold">Doctor</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {(scope === "all" ? cases : myActive).length === 0 && (
                <tr><td colSpan={6} className="p-12 text-center text-gray-400">Nothing here. Reception will add new cases shortly.</td></tr>
              )}
              {(scope === "all" ? cases : myActive).map((c) => (
                <tr key={c.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 tabular-nums text-xs text-gray-500">{c.case_uid}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{c.patient?.first_name} {c.patient?.last_name}</div>
                    <div className="text-xs text-gray-500 tabular-nums">{c.patient?.patient_uid} · {c.patient?.gender} · {c.patient?.age}y</div>
                  </td>
                  <td className="px-4 py-3 text-gray-700 max-w-md truncate">{c.complaint_text}</td>
                  <td className="px-4 py-3 text-gray-700">{c.doctor?.display_name}</td>
                  <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                  <td className="px-4 py-3 text-right">
                    <Link to={`/doctor/cases/${c.id}`} className="inline-flex items-center gap-1 text-teal-700 hover:text-teal-800 text-sm font-medium" data-testid={`open-case-${c.id}`}>
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

function KPI({ label, value }) {
  return (
    <div className="bg-white border border-gray-200 rounded-md p-5">
      <div className="text-xs uppercase tracking-wider font-semibold text-gray-500">{label}</div>
      <div className="font-display text-3xl font-semibold tracking-tight text-gray-900 mt-1 tabular-nums">{value}</div>
    </div>
  );
}
