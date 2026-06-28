import { useEffect, useState, useCallback } from "react";
import { api, fmtErr, fmtIST, fmtIST_date, istLocalToUtcISO } from "@/lib/api";
import { QuickContact } from "@/pages/doctor/Patients";
import { Loader2, BellRing, CheckCircle2, ClipboardList, Clock } from "lucide-react";

export default function PharmacyReminders() {
  const [reminders, setReminders] = useState([]);
  const [tab, setTab] = useState("PENDING");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [snoozeFor, setSnoozeFor] = useState(null);
  const [snoozeUntil, setSnoozeUntil] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/reminders?status=${tab}`);
      setReminders(data.reminders);
    } catch (e) { setErr(fmtErr(e)); }
    finally { setLoading(false); }
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  const complete = async (r) => {
    try { await api.patch(`/reminders/${r.id}`, { status: "COMPLETED" }); load(); }
    catch (e) { setErr(fmtErr(e)); }
  };

  const doSnooze = async () => {
    if (!snoozeUntil) return;
    try {
      await api.patch(`/reminders/${snoozeFor.id}`, { snooze_until: istLocalToUtcISO(snoozeUntil) });
      setSnoozeFor(null); setSnoozeUntil("");
      load();
    } catch (e) { setErr(fmtErr(e)); }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto" data-testid="pharmacy-reminders">
      <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Pharmacy</div>
      <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900 mb-1">Reminders</h1>
      <p className="text-sm text-gray-500 mb-6">Follow-ups doctors flagged for pharmacy attention. Mark complete when handled. Times in IST.</p>

      <div className="flex gap-1 bg-white border border-gray-200 rounded-md p-0.5 mb-4 w-fit">
        {[["PENDING", "Active"], ["COMPLETED", "Completed"], ["SENT", "Sent"]].map(([k, lbl]) => (
          <button key={k} onClick={() => setTab(k)} className={`px-3 py-1.5 text-xs font-medium rounded ${tab === k ? "bg-teal-700 text-white" : "text-gray-600 hover:bg-gray-50"}`} data-testid={`tab-${k}`}>{lbl}</button>
        ))}
      </div>

      {err && <div className="mb-3 text-sm text-red-700">{err}</div>}

      {loading ? (
        <div className="grid place-items-center p-12 text-gray-400"><Loader2 className="animate-spin" /></div>
      ) : reminders.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-md p-12 grid place-items-center text-center">
          <BellRing className="text-gray-300 mb-3" />
          <div className="text-sm text-gray-500">No reminders in this tab.</div>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-md divide-y divide-gray-100">
          {reminders.map((r) => (
            <div key={r.id} className="p-4 flex items-start gap-4" data-testid={`reminder-${r.id}`}>
              <div className="w-9 h-9 rounded-md bg-indigo-50 text-indigo-700 grid place-items-center shrink-0"><ClipboardList size={16} strokeWidth={1.5} /></div>
              <div className="flex-1">
                <div className="font-medium text-gray-900 text-sm">{r.patient_name}</div>
                <div className="text-xs text-gray-500 tabular-nums">{r.patient_uid} · {r.scheduled_date ? new Date(r.scheduled_date + "T00:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : fmtIST_date(r.scheduled_at)}</div>
                {r.patient_phone && (
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-xs text-gray-600 tabular-nums">{r.patient_phone}</span>
                    <QuickContact phone={r.patient_phone} name={r.patient_name} message={r.message ? `Hi ${r.patient_name}, ${r.message}` : undefined} />
                  </div>
                )}
                {r.message && <div className="text-xs text-gray-700 mt-1">{r.message}</div>}
                {r.completed_at && <div className="text-[11px] text-emerald-700 mt-1">Completed {fmtIST(r.completed_at)} {r.completed_by_name ? `· by ${r.completed_by_name}` : ""}</div>}
              </div>
              {r.status !== "COMPLETED" && (
                <div className="flex gap-1">
                  <button onClick={() => { setSnoozeFor(r); setSnoozeUntil(""); }} className="px-2.5 py-1.5 text-xs font-medium border border-gray-200 rounded hover:border-amber-600 hover:text-amber-700 inline-flex items-center gap-1" data-testid={`snooze-${r.id}`}>
                    <Clock size={12} /> Snooze
                  </button>
                  <button onClick={() => complete(r)} className="px-2.5 py-1.5 text-xs font-medium border border-gray-200 rounded hover:border-emerald-600 hover:text-emerald-700 inline-flex items-center gap-1" data-testid={`complete-${r.id}`}>
                    <CheckCircle2 size={12} /> Mark complete
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {snoozeFor && (
        <div className="fixed inset-0 bg-black/40 grid place-items-center z-50" onClick={() => setSnoozeFor(null)} data-testid="snooze-modal">
          <div className="bg-white rounded-md shadow-xl border border-gray-200 p-6 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-display text-lg font-semibold text-gray-900 mb-1">Snooze reminder</h2>
            <p className="text-xs text-gray-600 mb-3">{snoozeFor.patient_name}</p>
            <label className="text-xs uppercase tracking-wider font-semibold text-gray-500 block mb-1.5">Snooze until (IST)</label>
            <input type="datetime-local" value={snoozeUntil} onChange={(e) => setSnoozeUntil(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:border-teal-700 focus:ring-2 focus:ring-teal-700/20" data-testid="snooze-input" />
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setSnoozeFor(null)} className="px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded">Cancel</button>
              <button onClick={doSnooze} disabled={!snoozeUntil} className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded text-sm font-medium" data-testid="snooze-confirm">Snooze</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
