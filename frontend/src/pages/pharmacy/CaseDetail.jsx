import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import { ArrowLeft, Save, Loader2, Plus, Trash2, ArrowRight } from "lucide-react";

const EMPTY_ITEM = { medicine_name: "", potency: "", dosage: "", frequency: "", duration_days: "", instructions: "" };

export default function PharmacyCase() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [items, setItems] = useState([]);
  const [dispense, setDispense] = useState({ status: "FULL", medicine_amount: 0, patient_purchased_medicines: true, pharmacy_notes: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const reload = async () => {
    try {
      const { data } = await api.get(`/cases/${id}`);
      setData(data);
      setItems(data.latest_prescription?.items?.length ? data.latest_prescription.items : [{ ...EMPTY_ITEM }]);
      if (data.pharmacy_dispense) setDispense(data.pharmacy_dispense);
    } catch (e) { setErr(fmtErr(e)); }
  };
  useEffect(() => { reload(); }, [id]);

  if (err) return <div className="p-8 text-red-700">{err}</div>;
  if (!data) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  const c = data.case;

  const update = (i, k, v) => { const next = [...items]; next[i] = { ...next[i], [k]: v }; setItems(next); };

  const savePrescription = async () => {
    setBusy(true); setMsg("");
    try {
      await api.post(`/cases/${c.id}/prescription`, {
        items: items.filter((it) => it.medicine_name).map((it) => ({ ...it, duration_days: it.duration_days ? Number(it.duration_days) : null })),
        notes_for_patient: data.latest_prescription?.notes_for_patient || "",
      });
      setMsg("New prescription version saved.");
      reload();
    } catch (e) { setMsg(fmtErr(e)); }
    finally { setBusy(false); }
  };

  const saveDispense = async () => {
    setBusy(true); setMsg("");
    try {
      await api.post(`/cases/${c.id}/dispense`, { ...dispense, medicine_amount: Number(dispense.medicine_amount) || 0 });
      setMsg("Dispense saved. Case ready for billing.");
      reload();
    } catch (e) { setMsg(fmtErr(e)); }
    finally { setBusy(false); }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto" data-testid="pharmacy-case">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-3"><ArrowLeft size={14} /> Back</button>
      <div className="bg-white border border-gray-200 rounded-md p-6 mb-6 flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1 tabular-nums">{c.case_uid}</div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">{c.patient?.first_name} {c.patient?.last_name}</h1>
          <div className="text-sm text-gray-600 mt-1 tabular-nums">{c.patient?.patient_uid} · {c.patient?.gender} · {c.patient?.age}y</div>
        </div>
        <StatusBadge status={c.status} />
      </div>

      {/* Prescription editor */}
      <div className="bg-white border border-gray-200 rounded-md p-6 mb-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="font-display text-lg font-semibold text-gray-900">Prescription</h2>
            {data.latest_prescription && <div className="text-xs text-gray-500">Current version: v{data.latest_prescription.version_no}{data.latest_prescription.edited_by_pharmacy ? " (pharmacy edit)" : ""}</div>}
          </div>
        </div>
        <div className="space-y-3">
          {items.map((it, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-start border border-gray-200 rounded-md p-3">
              <input className="input col-span-3" placeholder="Medicine" value={it.medicine_name} onChange={(e) => update(i, "medicine_name", e.target.value)} />
              <input className="input col-span-2" placeholder="Potency" value={it.potency || ""} onChange={(e) => update(i, "potency", e.target.value)} />
              <input className="input col-span-2" placeholder="Dosage" value={it.dosage || ""} onChange={(e) => update(i, "dosage", e.target.value)} />
              <input className="input col-span-2" placeholder="Frequency" value={it.frequency || ""} onChange={(e) => update(i, "frequency", e.target.value)} />
              <input className="input col-span-2 tabular-nums" type="number" placeholder="Days" value={it.duration_days || ""} onChange={(e) => update(i, "duration_days", e.target.value)} />
              <button onClick={() => setItems(items.filter((_, j) => j !== i))} className="col-span-1 text-gray-400 hover:text-red-600 py-2 grid place-items-center"><Trash2 size={14} /></button>
            </div>
          ))}
          <button onClick={() => setItems([...items, { ...EMPTY_ITEM }])} className="inline-flex items-center gap-1 text-sm text-teal-700 hover:text-teal-800 font-medium"><Plus size={14} /> Add medicine</button>
        </div>
        <button onClick={savePrescription} disabled={busy} className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 hover:border-teal-600 text-gray-900 rounded-md text-sm font-medium disabled:opacity-60" data-testid="pharmacy-save-rx-btn">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save prescription edit
        </button>
      </div>

      {/* Dispense */}
      <div className="bg-white border border-gray-200 rounded-md p-6">
        <h2 className="font-display text-lg font-semibold text-gray-900 mb-4">Dispense</h2>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Status">
            <select className="input" value={dispense.status} onChange={(e) => setDispense({ ...dispense, status: e.target.value })} data-testid="dispense-status">
              <option value="FULL">Fully dispensed</option>
              <option value="PARTIAL">Partial</option>
              <option value="NOT_DISPENSED">Not dispensed</option>
            </select>
          </Field>
          <Field label="Medicine amount (₹)">
            <input type="number" min={0} step="0.01" className="input tabular-nums" value={dispense.medicine_amount} onChange={(e) => setDispense({ ...dispense, medicine_amount: e.target.value })} data-testid="dispense-amount" />
          </Field>
          <Field label="Patient took medicines?">
            <select className="input" value={dispense.patient_purchased_medicines ? "Y" : "N"} onChange={(e) => setDispense({ ...dispense, patient_purchased_medicines: e.target.value === "Y" })} data-testid="dispense-purchased">
              <option value="Y">Yes</option>
              <option value="N">No</option>
            </select>
          </Field>
          <Field label="Internal notes">
            <input className="input" value={dispense.pharmacy_notes || ""} onChange={(e) => setDispense({ ...dispense, pharmacy_notes: e.target.value })} />
          </Field>
        </div>
        <div className="flex items-center gap-3 mt-5">
          <button onClick={saveDispense} disabled={busy} className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium disabled:opacity-60" data-testid="save-dispense-btn">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />} Save & send to billing
          </button>
          {msg && <span className="text-sm text-gray-500">{msg}</span>}
        </div>
      </div>
      <style>{`.input { width:100%; padding:0.5rem 0.75rem; border:1px solid #e5e7eb; border-radius:0.375rem; font-size:0.875rem; outline:none; }
      .input:focus { border-color:#0F766E; box-shadow: 0 0 0 3px rgba(15,118,110,.18); }`}</style>
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
