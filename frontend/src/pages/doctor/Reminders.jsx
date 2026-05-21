import { useEffect, useState } from "react";
import { api, fmtErr } from "@/lib/api";
import { Loader2, BellRing, Calendar } from "lucide-react";

export default function Reminders() {
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try { const { data } = await api.get("/reminders"); setReminders(data.reminders); }
      catch (e) { setErr(fmtErr(e)); }
      finally { setLoading(false); }
    })();
  }, []);

  return (
    <div className="p-8 max-w-3xl mx-auto" data-testid="reminders-page">
      <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Doctor</div>
      <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900 mb-1">Reminders</h1>
      <p className="text-sm text-gray-500 mb-8">Patient follow-ups scheduled by you or the clinic.</p>

      {err && <div className="text-sm text-red-700">{err}</div>}
      {loading ? (
        <div className="grid place-items-center p-12 text-gray-400"><Loader2 className="animate-spin" /></div>
      ) : reminders.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-md p-12 grid place-items-center text-center">
          <BellRing className="text-gray-300 mb-3" />
          <div className="text-sm text-gray-500">No reminders scheduled.</div>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-md divide-y divide-gray-100">
          {reminders.map((r) => (
            <div key={r.id} className="p-4 flex items-center gap-4" data-testid={`reminder-${r.id}`}>
              <div className="w-9 h-9 rounded-md bg-amber-50 text-amber-700 grid place-items-center"><Calendar size={16} strokeWidth={1.5} /></div>
              <div className="flex-1">
                <div className="font-medium text-gray-900 text-sm">{r.patient_name}</div>
                <div className="text-xs text-gray-500 tabular-nums">{r.patient_uid} · {new Date(r.scheduled_at).toLocaleString()}</div>
                {r.message && <div className="text-xs text-gray-600 mt-1">{r.message}</div>}
              </div>
              <span className="pill pill-waiting tabular-nums">{r.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
