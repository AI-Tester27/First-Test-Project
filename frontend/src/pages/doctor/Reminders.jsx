import { useEffect, useState, useCallback } from "react";
import { api, fmtErr, fmtIST, fmtIST_date, utcISOToIstLocal, istLocalToUtcISO } from "@/lib/api";
import { QuickContact } from "@/pages/doctor/Patients";
import { useAuth } from "@/contexts/AuthContext";
import { Loader2, BellRing, Calendar, CheckCircle2, Clock, Send, Trash2, AlarmClock } from "lucide-react";

const STATUS_TABS = [
  { key: "PENDING", label: "Pending" },
  { key: "SENT", label: "Sent" },
  { key: "COMPLETED", label: "Completed" },
  { key: "FAILED", label: "Failed" },
];

const STATUS_PILLS = {
  PENDING: "pill pill-waiting",
  SENT: "pill pill-in-consultation",
  COMPLETED: "pill pill-paid",
  FAILED: "pill pill-unpaid",
};

const AUDIENCE_TABS = [
  { key: "ALL", label: "All" },
  { key: "MINE", label: "Mine" },
  { key: "PHARMACY", label: "Pharmacy" },
];

export default function DoctorReminders() {
  const { user } = useAuth();
  const isOwner = user?.role === "OWNER_DOCTOR" || user?.role === "ADMIN";
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [tab, setTab] = useState("PENDING");
  const [audience, setAudience] = useState("ALL");
  const [search, setSearch] = useState("");
  const [snoozing, setSnoozing] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // 'ALL' is the backend default → omit the param. Sending audience=ALL would be a no-op.
      const audParam = isOwner && audience !== "ALL" ? `&audience=${audience}` : "";
      const { data } = await api.get(`/reminders?status=${tab}${audParam}`);
      setReminders(data.reminders);
    } catch (e) { setErr(fmtErr(e)); }
    finally { setLoading(false); }
  }, [tab, audience, isOwner]);

  useEffect(() => { load(); }, [load]);

  const complete = async (r) => {
    try { await api.patch(`/reminders/${r.id}`, { status: "COMPLETED" }); load(); }
    catch (e) { setErr(fmtErr(e)); }
  };

  const send = async (r) => {
    try { await api.post(`/reminders/${r.id}/send-now`); load(); }
    catch (e) { setErr(fmtErr(e)); }
  };

  const remove = async (r) => {
    if (!window.confirm("Delete this reminder?")) return;
    try { await api.delete(`/reminders/${r.id}`); load(); }
    catch (e) { setErr(fmtErr(e)); }
  };

  const submitSnooze = async () => {
    if (!snoozing?.at) return;
    try {
      await api.patch(`/reminders/${snoozing.r.id}`, { snooze_until: istLocalToUtcISO(snoozing.at) });
      setSnoozing(null);
      load();
    } catch (e) { setErr(fmtErr(e)); }
  };

  const visible = reminders.filter((r) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (r.patient_name || "").toLowerCase().includes(s)
        || (r.patient_uid || "").toLowerCase().includes(s)
        || (r.message || "").toLowerCase().includes(s);
  });

  return (
    <div className="p-8 max-w-4xl mx-auto" data-testid="reminders-page">
      <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Doctor</div>
      <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900 mb-1">Reminders</h1>
      <p className="text-sm text-gray-500 mb-6">All times shown in IST · Mark done when patient confirms or visit happens.</p>

      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-white border border-gray-200 rounded-md p-0.5" data-testid="status-tabs">
            {STATUS_TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-3 py-1.5 text-xs font-medium rounded ${tab === t.key ? "bg-teal-700 text-white" : "text-gray-600 hover:bg-gray-50"}`}
                data-testid={`tab-${t.key}`}
              >{t.label}</button>
            ))}
          </div>
          {isOwner && (
            <div className="flex gap-1 bg-white border border-gray-200 rounded-md p-0.5" data-testid="audience-tabs">
              {AUDIENCE_TABS.map((a) => (
                <button
                  key={a.key}
                  onClick={() => setAudience(a.key)}
                  className={`px-3 py-1.5 text-xs font-medium rounded ${audience === a.key ? "bg-indigo-600 text-white" : "text-gray-600 hover:bg-gray-50"}`}
                  data-testid={`audience-${a.key}`}
                >{a.label}</button>
              ))}
            </div>
          )}
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search patient or note…"
          className="px-3 py-1.5 text-sm border border-gray-200 rounded-md focus-ring flex-1 max-w-xs"
          data-testid="reminder-search"
        />
      </div>

      {err && <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">{err}</div>}

      {loading ? (
        <div className="grid place-items-center p-12 text-gray-400"><Loader2 className="animate-spin" /></div>
      ) : visible.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-md p-12 grid place-items-center text-center">
          <BellRing className="text-gray-300 mb-3" />
          <div className="text-sm text-gray-500">No reminders.</div>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-md divide-y divide-gray-100">
          {visible.map((r) => (
            <div key={r.id} className="p-4 flex items-start gap-4" data-testid={`reminder-${r.id}`}>
              <div className="w-9 h-9 rounded-md bg-amber-50 text-amber-700 grid place-items-center shrink-0"><Calendar size={16} strokeWidth={1.5} /></div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-gray-900 text-sm">{r.patient_name}</span>
                  <span className="text-xs text-gray-500 tabular-nums">{r.patient_uid}</span>
                  <span className={STATUS_PILLS[r.status] || "pill pill-waiting"} data-testid={`status-${r.id}`}>{r.status}</span>
                </div>
                <div className="text-xs text-gray-600 mt-1 tabular-nums">{r.scheduled_date ? new Date(r.scheduled_date + "T00:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : fmtIST_date(r.scheduled_at)}</div>
                {r.patient_phone && (
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-xs text-gray-600 tabular-nums">{r.patient_phone}</span>
                    <QuickContact phone={r.patient_phone} name={r.patient_name} message={r.message ? `Hi ${r.patient_name}, ${r.message}` : undefined} />
                  </div>
                )}
                {r.message && <div className="text-xs text-gray-700 mt-1">{r.message}</div>}
                {r.completed_at && <div className="text-[11px] text-emerald-700 mt-1">Completed {fmtIST(r.completed_at)} {r.completed_by_name ? `· by ${r.completed_by_name}` : ""}</div>}
                {r.fail_reason && <div className="text-[11px] text-red-700 mt-1">Failed: {r.fail_reason}</div>}
              </div>
              <div className="flex gap-1 shrink-0">
                {r.status !== "COMPLETED" && (
                  <button onClick={() => complete(r)} className="px-2.5 py-1.5 text-xs font-medium border border-gray-200 rounded hover:border-emerald-600 hover:text-emerald-700 inline-flex items-center gap-1" data-testid={`complete-${r.id}`}>
                    <CheckCircle2 size={12} /> Done
                  </button>
                )}
                {r.status === "PENDING" && (
                  <>
                    <button onClick={() => setSnoozing({ r, at: utcISOToIstLocal(new Date(Date.now() + 86400000).toISOString()) })} className="px-2.5 py-1.5 text-xs font-medium border border-gray-200 rounded hover:border-teal-600 inline-flex items-center gap-1" data-testid={`snooze-${r.id}`}>
                      <AlarmClock size={12} /> Snooze
                    </button>
                    <button onClick={() => send(r)} className="px-2.5 py-1.5 text-xs font-medium border border-gray-200 rounded hover:border-teal-600 inline-flex items-center gap-1" data-testid={`send-${r.id}`}>
                      <Send size={12} /> Send
                    </button>
                  </>
                )}
                <button onClick={() => remove(r)} className="px-2.5 py-1.5 text-xs text-gray-400 hover:text-red-600" data-testid={`delete-${r.id}`}>
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {snoozing && (
        <div className="fixed inset-0 bg-black/30 grid place-items-center z-50" onClick={() => setSnoozing(null)}>
          <div className="bg-white rounded-md p-5 max-w-sm w-full shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-3">
              <Clock size={16} className="text-teal-700" />
              <h3 className="font-display font-semibold text-base text-gray-900">Snooze reminder</h3>
            </div>
            <p className="text-xs text-gray-500 mb-3">Reschedule for {snoozing.r.patient_name} (IST):</p>
            <input
              type="datetime-local"
              value={snoozing.at}
              onChange={(e) => setSnoozing({ ...snoozing, at: e.target.value })}
              className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus-ring"
              data-testid="snooze-input"
            />
            <div className="flex gap-2 mt-4">
              <button onClick={submitSnooze} className="flex-1 px-3 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium" data-testid="snooze-confirm">Snooze</button>
              <button onClick={() => setSnoozing(null)} className="px-3 py-2 bg-white border border-gray-200 rounded-md text-sm font-medium">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
