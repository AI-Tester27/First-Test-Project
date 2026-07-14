import { useEffect, useState } from "react";
import { api, fmtErr } from "@/lib/api";
import { Loader2, MessageSquare, Save, Trash2, CheckCircle2, XCircle, ShieldAlert } from "lucide-react";

const FIELDS = [
  { group: "whatsapp", label: "WhatsApp Cloud API", keys: [
    { name: "WHATSAPP_PHONE_NUMBER_ID", label: "Phone Number ID", placeholder: "e.g. 1234567890" },
    { name: "WHATSAPP_ACCESS_TOKEN", label: "Access Token", placeholder: "EAAB..." },
    { name: "WHATSAPP_API_VERSION", label: "API Version", placeholder: "v19.0 (default)" },
  ]},
  { group: "sms", label: "Twilio SMS", keys: [
    { name: "TWILIO_ACCOUNT_SID", label: "Account SID", placeholder: "AC..." },
    { name: "TWILIO_AUTH_TOKEN", label: "Auth Token", placeholder: "Auth token" },
    { name: "TWILIO_FROM", label: "From Number", placeholder: "+1XXXXXXXXXX" },
  ]},
];

export default function MessagingSettings() {
  const [data, setData] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    try {
      const r = await api.get("/admin/messaging-settings");
      setData(r.data);
      setDrafts({});
    } catch (e) { setErr(fmtErr(e)); }
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    const payload = Object.fromEntries(Object.entries(drafts).filter(([, v]) => v && v.length > 0));
    if (Object.keys(payload).length === 0) { setMsg("Nothing to save"); return; }
    setBusy(true); setErr(""); setMsg("");
    try {
      await api.post("/admin/messaging-settings", payload);
      setMsg("Saved. New keys are live.");
      await load();
    } catch (e) { setErr(fmtErr(e)); }
    finally { setBusy(false); }
  };

  const clearField = async (name) => {
    if (!window.confirm(`Clear ${name}?`)) return;
    setBusy(true); setErr(""); setMsg("");
    try {
      await api.post("/admin/messaging-settings", { [name]: "__CLEAR__" });
      setMsg(`${name} cleared.`);
      await load();
    } catch (e) { setErr(fmtErr(e)); }
    finally { setBusy(false); }
  };

  if (!data) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  return (
    <div className="p-8 max-w-3xl mx-auto" data-testid="messaging-settings">
      <div className="mb-8">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Admin · Integrations</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Messaging settings</h1>
        <p className="text-sm text-gray-600 mt-2">
          Set your <span className="font-medium">Twilio SMS</span> and <span className="font-medium">WhatsApp Cloud API</span> keys to enable real follow-up reminders.
          Until configured, reminders are stored and visible inside the app but no message is sent.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {FIELDS.map(({ group, label }) => {
          const enabled = data.status[group];
          const source = data.source[group];
          return (
            <div key={group} className="bg-white border border-gray-200 rounded-md p-4 flex items-center justify-between" data-testid={`status-${group}`}>
              <div>
                <div className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">{label}</div>
                <div className="font-display text-lg font-semibold mt-1 flex items-center gap-2">
                  {enabled ? <CheckCircle2 size={18} className="text-emerald-600" /> : <XCircle size={18} className="text-gray-400" />}
                  {enabled ? "Configured" : "Not configured"}
                </div>
                <div className="text-[11px] text-gray-500 mt-0.5">Source: {source}</div>
              </div>
              <MessageSquare size={28} strokeWidth={1.25} className={enabled ? "text-teal-700" : "text-gray-300"} />
            </div>
          );
        })}
      </div>

      {err && <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2" data-testid="err"><ShieldAlert size={14} />{err}</div>}
      {msg && <div className="mb-4 p-3 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm" data-testid="msg">{msg}</div>}

      <div className="space-y-6">
        {FIELDS.map(({ group, label, keys }) => (
          <div key={group} className="bg-white border border-gray-200 rounded-md p-5" data-testid={`group-${group}`}>
            <div className="font-display font-semibold text-sm text-gray-900 mb-4">{label}</div>
            <div className="space-y-3">
              {keys.map((k) => {
                const stored = data.stored?.[k.name];
                return (
                  <div key={k.name}>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">{k.label}</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        autoComplete="off"
                        placeholder={stored ? `Current: ${stored}` : k.placeholder}
                        value={drafts[k.name] || ""}
                        onChange={(e) => setDrafts((d) => ({ ...d, [k.name]: e.target.value }))}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm font-mono"
                        data-testid={`input-${k.name}`}
                      />
                      {stored && (
                        <button onClick={() => clearField(k.name)} disabled={busy}
                          className="px-3 py-2 border border-red-200 text-red-700 hover:bg-red-50 rounded-md text-xs inline-flex items-center gap-1"
                          data-testid={`clear-${k.name}`}>
                          <Trash2 size={13} /> Clear
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 flex items-center justify-between">
        <div className="text-xs text-gray-500">Values are stored in the database. Empty fields are ignored — use Clear to remove a value. Changes apply within ~30s for the background scheduler.</div>
        <button onClick={save} disabled={busy}
          className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 text-white rounded-md text-sm font-medium hover:bg-teal-800 disabled:opacity-50"
          data-testid="save-messaging-settings">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Save changes
        </button>
      </div>
    </div>
  );
}
