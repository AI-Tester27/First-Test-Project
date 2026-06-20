import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import { ArrowLeft, Loader2, Sparkles, Save, ArrowRight, Plus, Trash2, X } from "lucide-react";
import AttachmentsTab from "@/components/AttachmentsTab";
import { istLocalToUtcISO, utcISOToIstLocal } from "@/lib/api";

const TABS = ["Notes", "Prescription", "Attachments", "Follow-up", "AI Assist"];

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("Notes");
  const [err, setErr] = useState("");

  const reload = async () => {
    try { const r = await api.get(`/cases/${id}`); setData(r.data); }
    catch (e) { setErr(fmtErr(e)); }
  };
  useEffect(() => { reload(); }, [id]);

  if (err) return <div className="p-8 text-red-700">{err}</div>;
  if (!data) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  const c = data.case;

  const startConsult = async () => {
    await api.patch(`/cases/${c.id}/status`, { status: "IN_CONSULTATION" });
    reload();
  };
  const sendToPharmacy = async () => {
    await api.patch(`/cases/${c.id}/status`, { status: "SENT_TO_PHARMACY" });
    reload();
  };

  return (
    <div className="p-8 max-w-6xl mx-auto" data-testid="doctor-case-detail">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-3">
        <ArrowLeft size={14} /> Back to queue
      </button>

      <div className="bg-white border border-gray-200 rounded-md p-6 mb-6">
        <div className="flex items-start justify-between gap-6">
          <div>
            <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1 tabular-nums">{c.case_uid}</div>
            <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">
              {c.patient?.first_name} {c.patient?.last_name}
            </h1>
            <div className="text-sm text-gray-600 mt-1 tabular-nums">
              {c.patient?.patient_uid} · {c.patient?.gender} · {c.patient?.age}y · {c.patient?.phone}
            </div>
            <div className="text-sm text-gray-700 mt-3 max-w-xl">
              <span className="text-xs uppercase tracking-wider font-semibold text-gray-500 mr-2">Complaint:</span>
              {c.complaint_text}
            </div>
          </div>
          <div className="flex flex-col items-end gap-3">
            <StatusBadge status={c.status} />
            <div className="text-xs text-gray-500">Doctor: <span className="font-medium text-gray-900">{c.doctor?.display_name}</span></div>
            <div className="flex gap-2">
              {c.status === "WAITING_FOR_DOCTOR" && (
                <button onClick={startConsult} className="px-3 py-1.5 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-xs font-medium" data-testid="start-consult-btn">Start consultation</button>
              )}
              {(c.status === "IN_CONSULTATION" || c.status === "WAITING_FOR_DOCTOR") && (
                <button onClick={sendToPharmacy} className="inline-flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-xs font-medium" data-testid="send-pharmacy-btn">
                  Send to Pharmacy <ArrowRight size={12} />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === t ? "border-teal-700 text-teal-700" : "border-transparent text-gray-500 hover:text-gray-900"}`}
            data-testid={`tab-${t.toLowerCase().replace(/\s+/g, "-")}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Notes" && <NotesTab caseId={c.id} initial={data.clinical_notes} onSaved={reload} />}
      {tab === "Prescription" && <PrescriptionTab caseId={c.id} latest={data.latest_prescription} onSaved={reload} />}
      {tab === "Attachments" && <AttachmentsTab caseId={c.id} />}
      {tab === "Follow-up" && <FollowupTab caseData={c} onSaved={reload} />}
      {tab === "AI Assist" && <AiTab caseId={c.id} />}
    </div>
  );
}

function NotesTab({ caseId, initial, onSaved }) {
  const [form, setForm] = useState(initial || { diagnosis_summary: "", sensitivity_allergies: "", safety_notes: "", suggestions: "", additional_info: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const save = async () => {
    setBusy(true); setMsg("");
    try { await api.put(`/cases/${caseId}/notes`, form); setMsg("Saved."); onSaved(); }
    catch (e) { setMsg(fmtErr(e)); }
    finally { setBusy(false); }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-md p-6 space-y-4" data-testid="notes-tab">
      <Field label="Diagnosis / Assessment Summary">
        <textarea rows={3} className="input" value={form.diagnosis_summary || ""} onChange={(e) => setForm({ ...form, diagnosis_summary: e.target.value })} data-testid="diagnosis-input" />
      </Field>
      <Field label="Sensitivity / Allergies">
        <textarea rows={2} className="input" value={form.sensitivity_allergies || ""} onChange={(e) => setForm({ ...form, sensitivity_allergies: e.target.value })} data-testid="allergies-input" />
      </Field>
      <Field label="Safety / Precautions">
        <textarea rows={2} className="input" value={form.safety_notes || ""} onChange={(e) => setForm({ ...form, safety_notes: e.target.value })} />
      </Field>
      <Field label="Suggestions / Advice">
        <textarea rows={2} className="input" value={form.suggestions || ""} onChange={(e) => setForm({ ...form, suggestions: e.target.value })} />
      </Field>
      <Field label="Additional information">
        <textarea rows={2} className="input" value={form.additional_info || ""} onChange={(e) => setForm({ ...form, additional_info: e.target.value })} />
      </Field>
      <div className="flex items-center gap-3 pt-2">
        <button onClick={save} disabled={busy} className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium disabled:opacity-60" data-testid="save-notes-btn">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          Save notes
        </button>
        {msg && <span className="text-sm text-gray-500">{msg}</span>}
      </div>
      <style>{`.input { width:100%; padding:0.5rem 0.75rem; border:1px solid #e5e7eb; border-radius:0.375rem; font-size:0.875rem; outline:none; }
      .input:focus { border-color:#0F766E; box-shadow: 0 0 0 3px rgba(15,118,110,.18); }`}</style>
    </div>
  );
}

const EMPTY_ITEM = { medicine_name: "", potency: "", dosage: "", frequency: "", duration_days: "", instructions: "" };
const withKey = (it) => ({
  ...it,
  _key: it._key || (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`),
});

function PrescriptionTab({ caseId, latest, onSaved }) {
  const [items, setItems] = useState(
    latest?.items?.length ? latest.items.map(withKey) : [withKey({ ...EMPTY_ITEM })]
  );
  const [notesForPatient, setNotesForPatient] = useState(latest?.notes_for_patient || "");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const update = (i, key, value) => {
    const next = [...items];
    next[i] = { ...next[i], [key]: value };
    setItems(next);
  };

  const save = async () => {
    setBusy(true); setMsg("");
    try {
      await api.post(`/cases/${caseId}/prescription`, {
        items: items
          .filter((it) => it.medicine_name)
          .map(({ _key, ...it }) => ({ ...it, duration_days: it.duration_days ? Number(it.duration_days) : null })),
        notes_for_patient: notesForPatient,
      });
      setMsg("New prescription version saved.");
      onSaved();
    } catch (e) { setMsg(fmtErr(e)); }
    finally { setBusy(false); }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-md p-6 space-y-5" data-testid="prescription-tab">
      {latest && <div className="text-xs text-gray-500">Current version: <span className="tabular-nums font-medium text-gray-700">v{latest.version_no}</span></div>}
      <div className="space-y-3">
        {items.map((it, i) => (
          <div key={it._key} className="grid grid-cols-12 gap-2 items-start border border-gray-200 rounded-md p-3" data-testid={`rx-item-${i}`}>
            <input className="input col-span-3" placeholder="Medicine" value={it.medicine_name} onChange={(e) => update(i, "medicine_name", e.target.value)} />
            <input className="input col-span-2" placeholder="Potency (e.g. 30C)" value={it.potency} onChange={(e) => update(i, "potency", e.target.value)} />
            <input className="input col-span-2" placeholder="Dosage" value={it.dosage} onChange={(e) => update(i, "dosage", e.target.value)} />
            <input className="input col-span-2" placeholder="Frequency" value={it.frequency} onChange={(e) => update(i, "frequency", e.target.value)} />
            <input className="input col-span-2 tabular-nums" type="number" placeholder="Days" value={it.duration_days} onChange={(e) => update(i, "duration_days", e.target.value)} />
            <button onClick={() => setItems(items.filter((_, j) => j !== i))} className="col-span-1 text-gray-400 hover:text-red-600 py-2 grid place-items-center">
              <Trash2 size={14} />
            </button>
            <textarea rows={1} className="input col-span-12 mt-1" placeholder="Instructions (optional)" value={it.instructions} onChange={(e) => update(i, "instructions", e.target.value)} />
          </div>
        ))}
        <button onClick={() => setItems([...items, withKey({ ...EMPTY_ITEM })])} className="inline-flex items-center gap-1 text-sm text-teal-700 hover:text-teal-800 font-medium" data-testid="add-rx-item-btn">
          <Plus size={14} /> Add medicine
        </button>
      </div>
      <Field label="Notes for patient (printable)">
        <textarea rows={3} className="input" value={notesForPatient} onChange={(e) => setNotesForPatient(e.target.value)} />
      </Field>
      <div className="flex items-center gap-3 pt-1">
        <button onClick={save} disabled={busy} className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium disabled:opacity-60" data-testid="save-rx-btn">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save prescription
        </button>
        {msg && <span className="text-sm text-gray-500">{msg}</span>}
      </div>
      <style>{`.input { padding:0.5rem 0.625rem; border:1px solid #e5e7eb; border-radius:0.375rem; font-size:0.875rem; outline:none; width:100%; }
      .input:focus { border-color:#0F766E; box-shadow: 0 0 0 3px rgba(15,118,110,.18); }`}</style>
    </div>
  );
}

function FollowupTab({ caseData, onSaved }) {
  const initial = caseData.next_followup_at ? utcISOToIstLocal(caseData.next_followup_at) : "";
  const [at, setAt] = useState(initial);
  const [note, setNote] = useState(caseData.followup_note || "");
  const [notifyPharmacy, setNotifyPharmacy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const save = async () => {
    setBusy(true); setMsg("");
    try {
      await api.post(`/cases/${caseData.id}/followup`, {
        next_followup_at: istLocalToUtcISO(at),
        followup_note: note,
        notify_pharmacy: notifyPharmacy,
      });
      setMsg(`Follow-up saved (IST). ${notifyPharmacy ? "Pharmacy notified." : "On-screen reminder scheduled."}`);
      onSaved();
    } catch (e) { setMsg(fmtErr(e)); }
    finally { setBusy(false); }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-md p-6 space-y-4 max-w-xl" data-testid="followup-tab">
      <Field label="Next follow-up date / time (IST)">
        <input type="datetime-local" className="input" value={at} onChange={(e) => setAt(e.target.value)} data-testid="followup-datetime" />
      </Field>
      <Field label="Note">
        <textarea rows={3} className="input" value={note} onChange={(e) => setNote(e.target.value)} />
      </Field>
      <label className="flex items-center gap-2 text-sm text-gray-700">
        <input type="checkbox" checked={notifyPharmacy} onChange={(e) => setNotifyPharmacy(e.target.checked)} data-testid="notify-pharmacy" />
        Also notify pharmacy (will appear on their dashboard until completed)
      </label>
      <button onClick={save} disabled={busy || !at} className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white rounded-md text-sm font-medium" data-testid="save-followup-btn">
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save follow-up
      </button>
      {msg && <div className="text-sm text-gray-500">{msg}</div>}
      <style>{`.input { width:100%; padding:0.5rem 0.75rem; border:1px solid #e5e7eb; border-radius:0.375rem; font-size:0.875rem; outline:none; }
      .input:focus { border-color:#0F766E; box-shadow: 0 0 0 3px rgba(15,118,110,.18); }`}</style>
    </div>
  );
}

function AiTab({ caseId }) {
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  const run = async (action) => {
    setBusy(action); setErr(""); setResult("");
    try {
      const { data } = await api.post(`/cases/${caseId}/ai/${action}`);
      setResult(data.result);
    } catch (e) { setErr(fmtErr(e)); }
    finally { setBusy(""); }
  };

  const actions = [
    { key: "summarize", label: "Summarize complaint", desc: "Drafts an assessment summary from the patient's complaint." },
    { key: "advice", label: "Draft patient advice", desc: "Patient-friendly follow-up advice (uses preferred language)." },
    { key: "instructions", label: "Prescription instructions", desc: "Numbered medication instructions for the patient." },
  ];

  return (
    <div className="grid grid-cols-3 gap-4" data-testid="ai-tab">
      <div className="col-span-1 space-y-3">
        {actions.map((a) => (
          <button
            key={a.key}
            onClick={() => run(a.key)}
            disabled={!!busy}
            className="w-full text-left bg-gradient-to-br from-teal-50 to-white border border-teal-100 rounded-md p-4 hover:border-teal-300 transition-colors disabled:opacity-60"
            data-testid={`ai-${a.key}-btn`}
          >
            <div className="flex items-center gap-2 mb-1">
              {busy === a.key ? <Loader2 size={14} className="animate-spin text-teal-700" /> : <Sparkles size={14} strokeWidth={1.5} className="text-teal-700" />}
              <div className="font-semibold text-sm text-gray-900">{a.label}</div>
            </div>
            <div className="text-xs text-gray-500 leading-relaxed">{a.desc}</div>
          </button>
        ))}
      </div>
      <div className="col-span-2 bg-white border border-gray-200 rounded-md p-5 min-h-[300px]">
        <div className="text-xs uppercase tracking-wider font-semibold text-gray-500 mb-3">AI draft</div>
        {err && <div className="text-sm text-red-700">{err}</div>}
        {!err && !result && !busy && <div className="text-sm text-gray-400">Pick an action on the left to generate a draft. Drafts are never auto-saved.</div>}
        {busy && <div className="text-sm text-gray-500 inline-flex items-center gap-2"><Loader2 size={14} className="animate-spin" /> Thinking…</div>}
        {result && (
          <div className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed" data-testid="ai-result">{result}</div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="text-xs uppercase tracking-wider font-semibold text-gray-500 block mb-1.5">{label}</label>
      {children}
    </div>
  );
}
