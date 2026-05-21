import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import { ArrowLeft, UserPlus, Loader2 } from "lucide-react";

export default function NewPatient() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    first_name: "", last_name: "", gender: "MALE", age: 30,
    phone: "", address: "", preferred_language: "EN",
  });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const { data } = await api.post("/patients", { ...form, age: Number(form.age) });
      navigate(`/reception/new-visit?patient_id=${data.patient.id}`);
    } catch (e2) {
      setErr(fmtErr(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto" data-testid="new-patient-page">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-4">
        <ArrowLeft size={14} /> Back
      </button>
      <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Reception</div>
      <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900 mb-8">New patient</h1>

      <form onSubmit={submit} className="bg-white border border-gray-200 rounded-md p-6 space-y-5" data-testid="new-patient-form">
        <div className="grid grid-cols-2 gap-4">
          <Field label="First name" required>
            <input className="input" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} required data-testid="first-name-input" />
          </Field>
          <Field label="Last name" required>
            <input className="input" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} required data-testid="last-name-input" />
          </Field>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <Field label="Gender" required>
            <select className="input" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })} data-testid="gender-select">
              <option value="MALE">Male</option>
              <option value="FEMALE">Female</option>
              <option value="OTHER">Other</option>
            </select>
          </Field>
          <Field label="Age" required>
            <input type="number" min={0} max={150} className="input tabular-nums" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} required data-testid="age-input" />
          </Field>
          <Field label="Language">
            <select className="input" value={form.preferred_language} onChange={(e) => setForm({ ...form, preferred_language: e.target.value })} data-testid="language-select">
              <option value="EN">English</option>
              <option value="TE">Telugu</option>
            </select>
          </Field>
        </div>

        <Field label="Phone" required>
          <input className="input tabular-nums" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} required data-testid="phone-input" />
        </Field>

        <Field label="Address">
          <textarea rows={2} className="input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} data-testid="address-input" />
        </Field>

        {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">{err}</div>}

        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={busy} className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium disabled:opacity-60" data-testid="save-patient-btn">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <UserPlus size={14} strokeWidth={1.5} />}
            Save and create visit
          </button>
        </div>
      </form>

      <style>{`.input { width:100%; padding:0.5rem 0.75rem; border:1px solid #e5e7eb; border-radius:0.375rem; font-size:0.875rem; outline:none; transition: all 150ms; }
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
