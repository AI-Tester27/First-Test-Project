import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import { ArrowLeft, Loader2, Sparkles, Save, Plus, Trash2, FileText, Wand2 } from "lucide-react";

const EMPTY_ITEM = { medicine_name: "", potency: "", dosage: "", frequency: "", duration_days: "", instructions: "" };
const withKey = (it) => ({
  ...it,
  _key: it._key || (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`),
});

export default function PastVisitForm() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [patient, setPatient] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const [pasteText, setPasteText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseMsg, setParseMsg] = useState("");

  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    visit_date: today,
    assigned_doctor_id: "",
    complaint_text: "",
    diagnosis_summary: "",
    sensitivity_allergies: "",
    suggestions: "",
    additional_info: "",
    items: [withKey({ ...EMPTY_ITEM })],
    notes_for_patient: "",
    consultation_amount: 0,
    medicines_taken: false,
    medicine_amount: 0,
    amount_paid: 0,
    payment_mode: "CASH",
  });

  useEffect(() => {
    (async () => {
      try {
        const [p, d] = await Promise.all([
          api.get(`/patients/${id}`),
          api.get("/doctors"),
        ]);
        setPatient(p.data.patient);
        setDoctors(d.data.doctors);
        if (d.data.doctors[0]) setForm((f) => ({ ...f, assigned_doctor_id: d.data.doctors[0].id }));
      } catch (e) { setErr(fmtErr(e)); }
    })();
  }, [id]);

  const updateItem = (i, key, val) => {
    const next = [...form.items];
    next[i] = { ...next[i], [key]: val };
    setForm({ ...form, items: next });
  };

  const runParse = async () => {
    if (!pasteText.trim()) return;
    setParsing(true); setParseMsg(""); setErr("");
    try {
      const { data } = await api.post("/ai/parse-visit-notes", { text: pasteText, hint_doctor_id: form.assigned_doctor_id || null });
      const d = data.draft || {};
      setForm((f) => ({
        ...f,
        visit_date: d.visit_date || f.visit_date,
        complaint_text: d.complaint_text || f.complaint_text,
        diagnosis_summary: d.diagnosis_summary || f.diagnosis_summary,
        sensitivity_allergies: d.sensitivity_allergies || f.sensitivity_allergies,
        suggestions: d.suggestions || f.suggestions,
        additional_info: d.additional_info || f.additional_info,
        notes_for_patient: d.notes_for_patient || f.notes_for_patient,
        items: (d.prescription_items || []).length
          ? d.prescription_items.map((it) => withKey({
              medicine_name: it.medicine_name || "",
              potency: it.potency || "",
              dosage: it.dosage || "",
              frequency: it.frequency || "",
              duration_days: it.duration_days ?? "",
              instructions: it.instructions || "",
            }))
          : f.items,
        consultation_amount: d.consultation_amount ?? f.consultation_amount,
        medicine_amount: d.medicine_amount ?? f.medicine_amount,
        medicines_taken: (d.medicine_amount || 0) > 0 ? true : f.medicines_taken,
        amount_paid: d.amount_paid ?? f.amount_paid,
        payment_mode: d.payment_mode || f.payment_mode,
      }));
      setParseMsg(`Parsed ${(d.prescription_items || []).length} medicine(s). Please review every field before saving.`);
    } catch (e) {
      setParseMsg("");
      setErr(fmtErr(e));
    } finally {
      setParsing(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const isoDate = new Date(form.visit_date + "T10:00:00Z").toISOString();
      await api.post(`/patients/${id}/past-visit`, {
        visit_date: isoDate,
        assigned_doctor_id: form.assigned_doctor_id,
        complaint_text: form.complaint_text,
        diagnosis_summary: form.diagnosis_summary,
        sensitivity_allergies: form.sensitivity_allergies,
        suggestions: form.suggestions,
        additional_info: form.additional_info,
        prescription_items: form.items
          .filter((it) => it.medicine_name)
          .map(({ _key, ...it }) => ({ ...it, duration_days: it.duration_days ? Number(it.duration_days) : null })),
        notes_for_patient: form.notes_for_patient,
        consultation_amount: Number(form.consultation_amount) || 0,
        medicines_taken: !!form.medicines_taken,
        medicine_amount: Number(form.medicine_amount) || 0,
        amount_paid: Number(form.amount_paid) || 0,
        payment_mode: form.payment_mode || null,
      });
      navigate(`/reception/patients/${id}/timeline`);
    } catch (e2) {
      setErr(fmtErr(e2));
    } finally {
      setBusy(false);
    }
  };

  if (!patient) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  return (
    <div className="p-8 max-w-4xl mx-auto" data-testid="past-visit-page">
      <Link to={`/reception/patients/${id}/timeline`} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-3">
        <ArrowLeft size={14} /> Back to timeline
      </Link>
      <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1 tabular-nums">{patient.patient_uid}</div>
      <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900 mb-1">
        Add past visit · {patient.first_name} {patient.last_name}
      </h1>
      <p className="text-sm text-gray-500 mb-6">For migrating historical records from notebooks or Google Docs.</p>

      {/* Paste-and-parse panel */}
      <section className="bg-gradient-to-br from-teal-50/80 to-white border border-teal-200 rounded-md p-5 mb-6" data-testid="paste-panel">
        <div className="flex items-center gap-2 mb-3">
          <Wand2 size={15} strokeWidth={1.5} className="text-teal-700" />
          <h2 className="font-display text-sm font-semibold text-teal-900">Paste from Google Docs / notebook</h2>
        </div>
        <p className="text-xs text-gray-600 mb-3 leading-relaxed">
          Paste the entire visit note exactly as it appears in your Google Doc. AI extracts the structured fields below — you can review and edit everything before saving.
        </p>
        <textarea
          rows={6}
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          placeholder={`e.g.\n14 Jan 2024 — Mrs. Lakshmi, age 42\nComplaint: severe headache, neck stiffness for 3 days\nDiagnosis: tension headache, possibly migraine\nRx: Belladonna 30C, 4 globules thrice daily x 7 days\nConsultation ₹500, medicines ₹150, paid ₹650 cash`}
          className="w-full px-3 py-2 border border-teal-200 rounded-md text-sm focus-ring font-mono"
          data-testid="paste-textarea"
        />
        <div className="flex items-center gap-3 mt-3">
          <button
            type="button"
            onClick={runParse}
            disabled={!pasteText.trim() || parsing}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-60 text-white rounded-md text-sm font-medium"
            data-testid="parse-btn"
          >
            {parsing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} strokeWidth={1.5} />}
            Parse with AI
          </button>
          {parseMsg && <span className="text-xs text-teal-800">{parseMsg}</span>}
        </div>
      </section>

      <form onSubmit={submit} className="bg-white border border-gray-200 rounded-md p-6 space-y-5" data-testid="past-visit-form">
        <div className="grid grid-cols-3 gap-4">
          <Field label="Visit date" required>
            <input type="date" className="input" value={form.visit_date} onChange={(e) => setForm({ ...form, visit_date: e.target.value })} required data-testid="visit-date" />
          </Field>
          <Field label="Doctor" required>
            <select className="input" value={form.assigned_doctor_id} onChange={(e) => setForm({ ...form, assigned_doctor_id: e.target.value })} required data-testid="doctor-select">
              <option value="">— Select —</option>
              {doctors.map((d) => <option key={d.id} value={d.id}>{d.display_name}</option>)}
            </select>
          </Field>
        </div>

        <Field label="Complaint" required>
          <textarea rows={2} className="input" value={form.complaint_text} onChange={(e) => setForm({ ...form, complaint_text: e.target.value })} required data-testid="complaint-input" />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Diagnosis"><textarea rows={2} className="input" value={form.diagnosis_summary} onChange={(e) => setForm({ ...form, diagnosis_summary: e.target.value })} data-testid="diagnosis-input" /></Field>
          <Field label="Allergies"><textarea rows={2} className="input" value={form.sensitivity_allergies} onChange={(e) => setForm({ ...form, sensitivity_allergies: e.target.value })} /></Field>
          <Field label="Suggestions"><textarea rows={2} className="input" value={form.suggestions} onChange={(e) => setForm({ ...form, suggestions: e.target.value })} /></Field>
          <Field label="Additional info"><textarea rows={2} className="input" value={form.additional_info} onChange={(e) => setForm({ ...form, additional_info: e.target.value })} /></Field>
        </div>

        {/* Medicines */}
        <div>
          <label className="text-xs uppercase tracking-wider font-semibold text-gray-500 block mb-2">Prescription</label>
          <div className="space-y-2">
            {form.items.map((it, i) => (
              <div key={it._key} className="grid grid-cols-12 gap-2 border border-gray-200 rounded-md p-3" data-testid={`rx-item-${i}`}>
                <input className="input col-span-3" placeholder="Medicine" value={it.medicine_name} onChange={(e) => updateItem(i, "medicine_name", e.target.value)} />
                <input className="input col-span-2" placeholder="Potency" value={it.potency} onChange={(e) => updateItem(i, "potency", e.target.value)} />
                <input className="input col-span-2" placeholder="Dosage" value={it.dosage} onChange={(e) => updateItem(i, "dosage", e.target.value)} />
                <input className="input col-span-2" placeholder="Frequency" value={it.frequency} onChange={(e) => updateItem(i, "frequency", e.target.value)} />
                <input className="input col-span-2 tabular-nums" type="number" placeholder="Days" value={it.duration_days} onChange={(e) => updateItem(i, "duration_days", e.target.value)} />
                <button type="button" onClick={() => setForm({ ...form, items: form.items.filter((_, j) => j !== i) })} className="col-span-1 text-gray-400 hover:text-red-600 grid place-items-center"><Trash2 size={14} /></button>
              </div>
            ))}
          </div>
          <button type="button" onClick={() => setForm({ ...form, items: [...form.items, withKey({ ...EMPTY_ITEM })] })} className="inline-flex items-center gap-1 text-sm text-teal-700 hover:text-teal-800 font-medium mt-2">
            <Plus size={14} /> Add medicine
          </button>
        </div>

        {/* Payment */}
        <div className="border-t border-gray-100 pt-5">
          <label className="text-xs uppercase tracking-wider font-semibold text-gray-500 block mb-2">Payment (optional)</label>
          <div className="grid grid-cols-4 gap-3">
            <Field label="Consultation (₹)"><input type="number" className="input tabular-nums" value={form.consultation_amount} onChange={(e) => setForm({ ...form, consultation_amount: e.target.value })} /></Field>
            <Field label="Medicines taken">
              <select className="input" value={form.medicines_taken ? "Y" : "N"} onChange={(e) => setForm({ ...form, medicines_taken: e.target.value === "Y" })}>
                <option value="N">No</option>
                <option value="Y">Yes</option>
              </select>
            </Field>
            {form.medicines_taken && <Field label="Medicine (₹)"><input type="number" className="input tabular-nums" value={form.medicine_amount} onChange={(e) => setForm({ ...form, medicine_amount: e.target.value })} /></Field>}
            <Field label="Amount paid (₹)"><input type="number" className="input tabular-nums" value={form.amount_paid} onChange={(e) => setForm({ ...form, amount_paid: e.target.value })} /></Field>
            <Field label="Mode">
              <select className="input" value={form.payment_mode} onChange={(e) => setForm({ ...form, payment_mode: e.target.value })}>
                {["CASH", "PHONEPE", "CARD", "OTHER"].map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </Field>
          </div>
        </div>

        {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">{err}</div>}

        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={busy} className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-60 text-white rounded-md text-sm font-medium" data-testid="save-past-visit-btn">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save backdated visit
          </button>
          <Link to={`/reception/patients/${id}/timeline`} className="px-4 py-2 bg-white border border-gray-200 hover:border-gray-300 rounded-md text-sm font-medium">Cancel</Link>
        </div>
      </form>

      <style>{`.input { width:100%; padding:0.5rem 0.75rem; border:1px solid #e5e7eb; border-radius:0.375rem; font-size:0.875rem; outline:none; }
      .input:focus { border-color:#0F766E; box-shadow: 0 0 0 3px rgba(15,118,110,.18); }`}</style>
    </div>
  );
}

function Field({ label, required, children }) {
  return (
    <div>
      <label className="text-xs uppercase tracking-wider font-semibold text-gray-500 block mb-1.5">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}
