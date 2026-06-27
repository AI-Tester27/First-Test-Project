import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import { ArrowLeft, UserPlus, Loader2 } from "lucide-react";

const SOURCES = [
  { value: "TELEVISION", label: "Television" },
  { value: "NEWSPAPER", label: "Newspaper" },
  { value: "MEDICAL_CAMPS", label: "Medical Camps" },
  { value: "SIGN_BOARDS", label: "Sign Boards" },
  { value: "BANNERS", label: "Banners" },
  { value: "NEARBY_RESIDENCE", label: "Nearby Residence" },
  { value: "SOCIAL_MEDIA", label: "Social Media" },
  { value: "YOUTUBE", label: "YouTube" },
  { value: "FACEBOOK", label: "Facebook" },
  { value: "INSTAGRAM", label: "Instagram" },
  { value: "ONLINE_SEARCH", label: "Online Search" },
  { value: "REFERRAL", label: "Referral" },
  { value: "OTHERS", label: "Others" },
];

const initialForm = {
  first_name: "", last_name: "", gender: "MALE", age: "",
  marital_status: "SINGLE", phone: "", address: "",
  height_cm: "", weight_kg: "",
  consulting_doctor_id: "",
  sources: [],
  referral_name: "",
  chief_complaint: "",
  visit_type: "WALK_IN",
  preferred_language: "EN",
};

export default function NewPatient() {
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [doctors, setDoctors] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const { data } = await api.get("/doctors");
      setDoctors(data.doctors || []);
    })();
  }, []);

  const bmi = (() => {
    const h = parseFloat(form.height_cm);
    const w = parseFloat(form.weight_kg);
    if (!h || !w || h <= 0) return null;
    const m = h / 100;
    return (w / (m * m)).toFixed(1);
  })();

  const showReferralName = form.sources.includes("REFERRAL") || form.sources.includes("OTHERS");

  const toggleSource = (val) => {
    setForm((f) => ({
      ...f,
      sources: f.sources.includes(val) ? f.sources.filter((s) => s !== val) : [...f.sources, val],
    }));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!form.consulting_doctor_id) { setErr("Please select a consulting doctor."); return; }
    setBusy(true); setErr("");
    try {
      const payload = {
        ...form,
        age: Number(form.age),
        height_cm: form.height_cm ? Number(form.height_cm) : null,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        referral_name: showReferralName ? (form.referral_name || null) : null,
      };
      // Remove null/empty optional fields
      Object.keys(payload).forEach((k) => {
        if (payload[k] === "" || payload[k] === null) delete payload[k];
      });
      const { data } = await api.post("/patients/fir", payload);
      navigate(`/reception/patients/${data.patient.id}/timeline`);
    } catch (e2) {
      setErr(fmtErr(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto" data-testid="new-patient-fir-page">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-4">
        <ArrowLeft size={14} /> Back
      </button>
      <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Reception · First Information Report</div>
      <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900 mb-8">New patient registration</h1>

      <form onSubmit={submit} className="space-y-6" data-testid="fir-form">
        {/* Patient Information */}
        <Section title="Patient Information">
          <div className="grid grid-cols-3 gap-4">
            <Field label="First name" required>
              <input className="input" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} required data-testid="first-name-input" />
            </Field>
            <Field label="Last name">
              <input className="input" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} data-testid="last-name-input" />
            </Field>
            <Field label="Age" required>
              <input type="number" min={0} max={150} className="input tabular-nums" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} required data-testid="age-input" />
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
            <Field label="Marital status">
              <select className="input" value={form.marital_status} onChange={(e) => setForm({ ...form, marital_status: e.target.value })} data-testid="marital-select">
                <option value="SINGLE">Single</option>
                <option value="MARRIED">Married</option>
                <option value="DIVORCED">Divorced</option>
                <option value="WIDOWED">Widowed</option>
                <option value="OTHER">Other</option>
              </select>
            </Field>
            <Field label="Language">
              <select className="input" value={form.preferred_language} onChange={(e) => setForm({ ...form, preferred_language: e.target.value })} data-testid="language-select">
                <option value="EN">English</option>
                <option value="TE">Telugu</option>
              </select>
            </Field>
          </div>

          <Field label="Phone number" required>
            <input className="input tabular-nums" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} required data-testid="phone-input" />
          </Field>

          <Field label="Address">
            <textarea rows={2} className="input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} data-testid="address-input" />
          </Field>

          <div className="grid grid-cols-3 gap-4">
            <Field label="Height (cm)">
              <input type="number" step="0.1" className="input tabular-nums" value={form.height_cm} onChange={(e) => setForm({ ...form, height_cm: e.target.value })} data-testid="height-input" />
            </Field>
            <Field label="Weight (kg)">
              <input type="number" step="0.1" className="input tabular-nums" value={form.weight_kg} onChange={(e) => setForm({ ...form, weight_kg: e.target.value })} data-testid="weight-input" />
            </Field>
            <Field label="BMI (auto)">
              <input className="input bg-gray-50 tabular-nums" value={bmi || ""} readOnly placeholder="—" data-testid="bmi-display" />
            </Field>
          </div>

          <Field label="Consulting doctor" required>
            <select className="input" value={form.consulting_doctor_id} onChange={(e) => setForm({ ...form, consulting_doctor_id: e.target.value })} required data-testid="consulting-doctor-select">
              <option value="">— Select —</option>
              {doctors.map((d) => <option key={d.id} value={d.id}>{d.display_name}</option>)}
            </select>
          </Field>
        </Section>

        {/* Patient Source */}
        <Section title="How did you know about us?" subtitle="Select all that apply">
          <div className="grid grid-cols-3 gap-2" data-testid="sources-grid">
            {SOURCES.map((s) => (
              <label key={s.value} className={`flex items-center gap-2 px-3 py-2 border rounded-md text-sm cursor-pointer transition ${form.sources.includes(s.value) ? "bg-teal-50 border-teal-300 text-teal-900" : "border-gray-200 hover:bg-gray-50"}`}>
                <input
                  type="checkbox"
                  checked={form.sources.includes(s.value)}
                  onChange={() => toggleSource(s.value)}
                  className="accent-teal-700"
                  data-testid={`source-${s.value}`}
                />
                {s.label}
              </label>
            ))}
          </div>
          {showReferralName && (
            <Field label="Referral person name">
              <input className="input" value={form.referral_name} onChange={(e) => setForm({ ...form, referral_name: e.target.value })} data-testid="referral-name-input" />
            </Field>
          )}
        </Section>

        {/* Medical Information */}
        <Section title="Medical Information">
          <Field label="Nature of health problem / chief complaint" required>
            <textarea rows={3} className="input" value={form.chief_complaint} onChange={(e) => setForm({ ...form, chief_complaint: e.target.value })} required data-testid="chief-complaint-input" />
          </Field>
          <Field label="Visit type" required>
            <div className="flex gap-3">
              {["WALK_IN", "APPOINTMENT"].map((v) => (
                <label key={v} className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border rounded-md text-sm cursor-pointer ${form.visit_type === v ? "bg-teal-50 border-teal-300 text-teal-900 font-medium" : "border-gray-200 hover:bg-gray-50"}`}>
                  <input type="radio" name="visit_type" value={v} checked={form.visit_type === v} onChange={() => setForm({ ...form, visit_type: v })} className="accent-teal-700" data-testid={`visit-type-${v}`} />
                  {v === "WALK_IN" ? "Walk-in" : "Appointment"}
                </label>
              ))}
            </div>
          </Field>
        </Section>

        {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2" data-testid="fir-error">{err}</div>}

        <div className="flex gap-2 pt-2">
          <button type="submit" disabled={busy} className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium disabled:opacity-60" data-testid="save-patient-btn">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <UserPlus size={14} strokeWidth={1.5} />}
            Register patient & start visit
          </button>
        </div>
      </form>

      <style>{`.input { width:100%; padding:0.5rem 0.75rem; border:1px solid #e5e7eb; border-radius:0.375rem; font-size:0.875rem; outline:none; transition: all 150ms; }
      .input:focus { border-color:#0F766E; box-shadow: 0 0 0 3px rgba(15,118,110,.18); }`}</style>
    </div>
  );
}

function Section({ title, subtitle, children }) {
  return (
    <div className="bg-white border border-gray-200 rounded-md p-6 space-y-4">
      <div>
        <div className="font-display font-semibold text-base text-gray-900">{title}</div>
        {subtitle && <div className="text-xs text-gray-500 mt-0.5">{subtitle}</div>}
      </div>
      {children}
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
