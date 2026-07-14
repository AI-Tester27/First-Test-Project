import { useEffect, useState } from "react";
import { api, fmtErr } from "@/lib/api";
import {
  Loader2, Sparkles, Save, Trash2, CheckCircle2, XCircle,
  ShieldAlert, FlaskConical, KeyRound,
} from "lucide-react";

const PROVIDER_META = {
  anthropic: { label: "Anthropic Claude", keyField: "ANTHROPIC_API_KEY", placeholder: "sk-ant-..." },
  openai: { label: "OpenAI GPT", keyField: "OPENAI_API_KEY", placeholder: "sk-..." },
  gemini: { label: "Google Gemini", keyField: "GEMINI_API_KEY", placeholder: "AIza..." },
};

export default function AISettings() {
  const [data, setData] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState("");
  const [testResults, setTestResults] = useState({});
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    try {
      const r = await api.get("/admin/ai-settings");
      setData(r.data);
      setProvider(r.data.active_provider);
      setModel(r.data.active_model);
      setDrafts({});
    } catch (e) { setErr(fmtErr(e)); }
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    const payload = Object.fromEntries(Object.entries(drafts).filter(([, v]) => v && v.length > 0));
    if (provider && provider !== data.active_provider) payload.AI_PROVIDER = provider;
    if (model && (model !== data.active_model || payload.AI_PROVIDER)) payload.AI_MODEL = model;
    if (payload.AI_MODEL && !payload.AI_PROVIDER && provider !== data.active_provider) payload.AI_PROVIDER = provider;
    if (Object.keys(payload).length === 0) { setMsg("Nothing to save"); return; }
    setBusy(true); setErr(""); setMsg("");
    try {
      await api.post("/admin/ai-settings", payload);
      setMsg("Saved. AI features now use this configuration.");
      await load();
    } catch (e) { setErr(fmtErr(e)); }
    finally { setBusy(false); }
  };

  const clearField = async (name) => {
    if (!window.confirm(`Clear ${name}? AI will fall back to the built-in key.`)) return;
    setBusy(true); setErr(""); setMsg("");
    try {
      await api.post("/admin/ai-settings", { [name]: "__CLEAR__" });
      setMsg(`${name} cleared.`);
      await load();
    } catch (e) { setErr(fmtErr(e)); }
    finally { setBusy(false); }
  };

  const testKey = async (p) => {
    setTesting(p); setErr("");
    setTestResults((t) => ({ ...t, [p]: null }));
    try {
      const draft = (drafts[PROVIDER_META[p].keyField] || "").trim();
      const r = await api.post("/admin/ai-settings/test", { provider: p, api_key: draft || null });
      setTestResults((t) => ({ ...t, [p]: r.data }));
    } catch (e) {
      setTestResults((t) => ({ ...t, [p]: { ok: false, error: fmtErr(e) } }));
    } finally { setTesting(""); }
  };

  if (!data) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  const usingOwnKey = data.key_source === "own";
  const modelsForProvider = data.models[provider] || [];

  return (
    <div className="p-8 max-w-3xl mx-auto" data-testid="ai-settings">
      <div className="mb-8">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Admin · Integrations</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">AI settings</h1>
        <p className="text-sm text-gray-600 mt-2">
          Add your own <span className="font-medium">Claude</span>, <span className="font-medium">GPT</span> or{" "}
          <span className="font-medium">Gemini</span> API key and pick the model used by all AI features
          (case summaries, visit recaps, notes parsing). If your key is missing or fails,
          the app automatically falls back to the built-in key so AI never breaks.
        </p>
      </div>

      {/* Status cards */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-md p-4 flex items-center justify-between" data-testid="status-active-model">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">Active model</div>
            <div className="font-display text-lg font-semibold mt-1">{PROVIDER_META[data.active_provider]?.label}</div>
            <div className="text-[11px] text-gray-500 mt-0.5 font-mono">{data.active_model}</div>
          </div>
          <Sparkles size={28} strokeWidth={1.25} className="text-teal-700" />
        </div>
        <div className="bg-white border border-gray-200 rounded-md p-4 flex items-center justify-between" data-testid="status-key-source">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">API key in use</div>
            <div className="font-display text-lg font-semibold mt-1 flex items-center gap-2">
              {usingOwnKey ? <CheckCircle2 size={18} className="text-emerald-600" /> : <XCircle size={18} className="text-gray-400" />}
              {usingOwnKey ? "Your own key" : "Built-in key"}
            </div>
            <div className="text-[11px] text-gray-500 mt-0.5">
              {usingOwnKey ? "Billed to your provider account" : "Uses the app's built-in universal key"}
            </div>
          </div>
          <KeyRound size={28} strokeWidth={1.25} className={usingOwnKey ? "text-teal-700" : "text-gray-300"} />
        </div>
      </div>

      {err && <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm flex items-center gap-2" data-testid="err"><ShieldAlert size={14} />{err}</div>}
      {msg && <div className="mb-4 p-3 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm" data-testid="msg">{msg}</div>}

      {/* Provider + model selection */}
      <div className="bg-white border border-gray-200 rounded-md p-5 mb-6" data-testid="group-model-selection">
        <div className="font-display font-semibold text-sm text-gray-900 mb-4">Provider &amp; model</div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">AI provider</label>
            <select
              value={provider}
              onChange={(e) => { const p = e.target.value; setProvider(p); setModel(data.models[p][0]); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
              data-testid="select-ai-provider"
            >
              {Object.entries(PROVIDER_META).map(([p, m]) => (
                <option key={p} value={p}>{m.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white font-mono"
              data-testid="select-ai-model"
            >
              {modelsForProvider.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
        </div>
        <div className="text-[11px] text-gray-500 mt-3">
          The selected provider &amp; model apply to every AI feature in the app. Remember to press <span className="font-medium">Save changes</span>.
        </div>
      </div>

      {/* API keys */}
      <div className="space-y-6">
        {Object.entries(PROVIDER_META).map(([p, meta]) => {
          const stored = data.stored?.[meta.keyField];
          const configured = data.keys_configured?.[p];
          const result = testResults[p];
          return (
            <div key={p} className="bg-white border border-gray-200 rounded-md p-5" data-testid={`group-${p}`}>
              <div className="flex items-center justify-between mb-4">
                <div className="font-display font-semibold text-sm text-gray-900 flex items-center gap-2">
                  {meta.label}
                  {configured
                    ? <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">Key added</span>
                    : <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-gray-50 text-gray-500 border border-gray-200">No key</span>}
                </div>
              </div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">API key</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  autoComplete="off"
                  placeholder={stored ? `Current: ${stored}` : meta.placeholder}
                  value={drafts[meta.keyField] || ""}
                  onChange={(e) => setDrafts((d) => ({ ...d, [meta.keyField]: e.target.value }))}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm font-mono"
                  data-testid={`input-${meta.keyField}`}
                />
                <button
                  onClick={() => testKey(p)}
                  disabled={busy || testing !== "" || (!configured && !(drafts[meta.keyField] || "").trim())}
                  className="px-3 py-2 border border-teal-200 text-teal-700 hover:bg-teal-50 rounded-md text-xs inline-flex items-center gap-1 disabled:opacity-40"
                  data-testid={`test-${p}`}
                >
                  {testing === p ? <Loader2 size={13} className="animate-spin" /> : <FlaskConical size={13} />} Test key
                </button>
                {stored && (
                  <button onClick={() => clearField(meta.keyField)} disabled={busy}
                    className="px-3 py-2 border border-red-200 text-red-700 hover:bg-red-50 rounded-md text-xs inline-flex items-center gap-1"
                    data-testid={`clear-${meta.keyField}`}>
                    <Trash2 size={13} /> Clear
                  </button>
                )}
              </div>
              {result && (
                <div
                  className={`mt-2 text-xs p-2 rounded-md border flex items-center gap-1.5 ${result.ok ? "bg-emerald-50 border-emerald-200 text-emerald-700" : "bg-red-50 border-red-200 text-red-700"}`}
                  data-testid={`test-result-${p}`}
                >
                  {result.ok ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                  {result.ok ? "Key works — model responded successfully." : `Key failed: ${result.error}`}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center justify-between">
        <div className="text-xs text-gray-500">
          Keys are stored in the database and never shown in full. Empty fields are ignored — use Clear to remove a key.
        </div>
        <button onClick={save} disabled={busy}
          className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 text-white rounded-md text-sm font-medium hover:bg-teal-800 disabled:opacity-50"
          data-testid="save-ai-settings">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Save changes
        </button>
      </div>
    </div>
  );
}
