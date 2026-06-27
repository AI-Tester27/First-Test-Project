import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import StatusBadge, { PaymentBadge } from "@/components/StatusBadge";
import { ArrowLeft, Loader2, Save, Printer, CheckCircle2, User, ListChecks, Upload, FileImage, Trash2 } from "lucide-react";

export default function BillingDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({
    consultation_amount: 500,
    medicines_taken: true,
    medicine_amount: 0,
    amount_paid: 0,
    payment_mode: "CASH",
  });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const reload = async () => {
    try {
      const { data } = await api.get(`/cases/${id}`);
      setData(data);
      if (data.payment) {
        setForm({
          consultation_amount: data.payment.consultation_amount,
          medicines_taken: data.payment.medicines_taken,
          medicine_amount: data.payment.medicine_amount,
          amount_paid: data.payment.amount_paid,
          payment_mode: data.payment.payment_mode || "CASH",
        });
      } else if (data.pharmacy_dispense?.medicine_amount) {
        setForm((f) => ({
          ...f,
          medicine_amount: data.pharmacy_dispense.medicine_amount,
          medicines_taken: data.pharmacy_dispense.patient_purchased_medicines,
        }));
      }
    } catch (e) { setErr(fmtErr(e)); }
  };
  useEffect(() => { reload(); }, [id]);

  if (err) return <div className="p-8 text-red-700">{err}</div>;
  if (!data) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  const c = data.case;
  const total = Number(form.consultation_amount || 0) + (form.medicines_taken ? Number(form.medicine_amount || 0) : 0);
  const balance = Math.max(0, total - Number(form.amount_paid || 0));
  const isClosed = c.status === "CLOSED" && data.payment?.payment_status === "PAID";

  const save = async () => {
    setBusy(true); setMsg("");
    try {
      await api.post(`/cases/${c.id}/payment`, {
        consultation_amount: Number(form.consultation_amount) || 0,
        medicines_taken: !!form.medicines_taken,
        medicine_amount: Number(form.medicine_amount) || 0,
        amount_paid: Number(form.amount_paid) || 0,
        payment_mode: form.payment_mode,
      });
      setMsg("Payment recorded.");
      reload();
    } catch (e) { setMsg(fmtErr(e)); }
    finally { setBusy(false); }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto" data-testid="billing-detail">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-3"><ArrowLeft size={14} /> Back</button>
      <div className="bg-white border border-gray-200 rounded-md p-6 mb-6 flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1 tabular-nums">{c.case_uid}</div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">{c.patient?.first_name} {c.patient?.last_name}</h1>
          <div className="text-sm text-gray-600 mt-1 tabular-nums">{c.patient?.patient_uid} · {c.patient?.phone} · Doctor: {c.doctor?.display_name}</div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <StatusBadge status={c.status} />
          {data.payment && <PaymentBadge status={data.payment.payment_status} />}
        </div>
      </div>

      {isClosed && (
        <div className="bg-gradient-to-br from-emerald-50 to-white border-2 border-emerald-200 rounded-md p-6 mb-6" data-testid="payment-success-card">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-700 grid place-items-center shrink-0">
              <CheckCircle2 size={24} strokeWidth={1.75} />
            </div>
            <div className="flex-1">
              <h2 className="font-display text-xl font-semibold text-emerald-900 tracking-tight">Payment received · Case closed</h2>
              <p className="text-sm text-emerald-800 mt-1">
                Receipt <span className="font-mono font-semibold tabular-nums">{data.payment.receipt_no}</span> · ₹{Number(data.payment.amount_paid).toFixed(0)} via <span className="font-medium">{data.payment.payment_mode || "—"}</span>.
                The case is now in the closed archive.
              </p>
              <div className="grid grid-cols-3 gap-3 mt-4 text-xs">
                <div className="bg-white border border-emerald-100 rounded p-2.5">
                  <div className="text-emerald-700 uppercase tracking-wider font-semibold text-[10px] mb-0.5">Consultation</div>
                  <div className="tabular-nums font-semibold text-gray-900">₹{Number(data.payment.consultation_amount).toFixed(2)}</div>
                </div>
                <div className="bg-white border border-emerald-100 rounded p-2.5">
                  <div className="text-emerald-700 uppercase tracking-wider font-semibold text-[10px] mb-0.5">Medicines</div>
                  <div className="tabular-nums font-semibold text-gray-900">₹{Number(data.payment.medicine_amount).toFixed(2)}</div>
                </div>
                <div className="bg-white border border-emerald-100 rounded p-2.5">
                  <div className="text-emerald-700 uppercase tracking-wider font-semibold text-[10px] mb-0.5">Total</div>
                  <div className="tabular-nums font-semibold text-gray-900">₹{Number(data.payment.total_amount).toFixed(2)}</div>
                </div>
              </div>
              <div className="flex gap-2 mt-5">
                <Link to={`/pro/cases/${c.id}/receipt`} target="_blank" className="inline-flex items-center gap-2 px-3.5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-md text-sm font-medium" data-testid="success-print-btn">
                  <Printer size={14} strokeWidth={1.5} /> Print receipt
                </Link>
                {c.patient?.id && (
                  <Link to={`/reception/patients/${c.patient.id}/timeline`} className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-gray-200 hover:border-emerald-600 rounded-md text-sm font-medium" data-testid="success-timeline-btn">
                    <User size={14} strokeWidth={1.5} /> Patient timeline
                  </Link>
                )}
                <Link to="/pro" className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-gray-200 hover:border-emerald-600 rounded-md text-sm font-medium" data-testid="success-queue-btn">
                  <ListChecks size={14} strokeWidth={1.5} /> Back to billing queue
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        <div className={`col-span-2 bg-white border border-gray-200 rounded-md p-6 ${isClosed ? "opacity-75" : ""}`}>
          <h2 className="font-display text-lg font-semibold text-gray-900 mb-4">
            {isClosed ? "Payment summary (closed)" : "Payment"}
          </h2>
          <fieldset disabled={isClosed} className="space-y-4 disabled:cursor-not-allowed">
            <Field label="Consultation amount (₹)">
              <input type="number" className="input tabular-nums" value={form.consultation_amount} onChange={(e) => setForm({ ...form, consultation_amount: e.target.value })} data-testid="consult-amount" />
              <div className="flex gap-2 mt-2">
                {[300, 500, 700, 1000].map((v) => (
                  <button key={v} type="button" onClick={() => setForm({ ...form, consultation_amount: v })} className="text-xs px-2 py-1 border border-gray-200 rounded hover:border-teal-600 tabular-nums">₹{v}</button>
                ))}
              </div>
            </Field>
            <Field label="Patient took medicines?">
              <select className="input" value={form.medicines_taken ? "Y" : "N"} onChange={(e) => setForm({ ...form, medicines_taken: e.target.value === "Y" })} data-testid="medicines-taken">
                <option value="Y">Yes</option>
                <option value="N">No (consultation only)</option>
              </select>
            </Field>
            {form.medicines_taken && (
              <Field label="Medicine amount (₹)">
                <input type="number" className="input tabular-nums" value={form.medicine_amount} onChange={(e) => setForm({ ...form, medicine_amount: e.target.value })} data-testid="medicine-amount" />
              </Field>
            )}
            <Field label="Amount paid (₹)">
              <input type="number" className="input tabular-nums" value={form.amount_paid} onChange={(e) => setForm({ ...form, amount_paid: e.target.value })} data-testid="amount-paid" />
              <button type="button" onClick={() => setForm((f) => ({ ...f, amount_paid: total }))} className="text-xs text-teal-700 hover:text-teal-800 mt-1">Pay total ₹{total}</button>
            </Field>
            <Field label="Payment mode">
              <div className="grid grid-cols-4 gap-2">
                {["CASH", "PHONEPE", "CARD", "OTHER"].map((m) => (
                  <button key={m} type="button" onClick={() => setForm({ ...form, payment_mode: m })} className={`px-3 py-2 rounded-md text-sm font-medium border ${form.payment_mode === m ? "bg-teal-700 text-white border-teal-700" : "bg-white border-gray-200 text-gray-700 hover:border-teal-600"}`} data-testid={`mode-${m}`}>
                    {m}
                  </button>
                ))}
              </div>
            </Field>

            <div className="flex items-center gap-3 pt-2">
              <button onClick={save} disabled={busy || isClosed} className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium disabled:opacity-60" data-testid="save-payment-btn">
                {busy ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} {isClosed ? "Already recorded" : "Record payment"}
              </button>
              {data.payment && !isClosed && (
                <Link to={`/pro/cases/${c.id}/receipt`} target="_blank" className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 hover:border-teal-600 rounded-md text-sm font-medium" data-testid="print-receipt-btn">
                  <Printer size={14} /> Print receipt
                </Link>
              )}
              {msg && <span className="text-sm text-gray-500">{msg}</span>}
            </div>
          </fieldset>
        </div>

        <div className="col-span-1 bg-white border border-gray-200 rounded-md p-6 h-fit">
          <h3 className="font-display text-sm font-semibold text-gray-900 mb-4">Summary</h3>
          <Row label="Consultation" value={Number(form.consultation_amount) || 0} />
          {form.medicines_taken && <Row label="Medicines" value={Number(form.medicine_amount) || 0} />}
          <div className="border-t border-gray-200 my-3" />
          <Row label="Total" value={total} bold />
          <Row label="Paid" value={Number(form.amount_paid) || 0} />
          <Row label="Balance" value={balance} bold />
        </div>
      </div>

      <PaymentProofPanel caseId={c.id} />
      <style>{`.input { width:100%; padding:0.5rem 0.75rem; border:1px solid #e5e7eb; border-radius:0.375rem; font-size:0.875rem; outline:none; }
      .input:focus { border-color:#0F766E; box-shadow: 0 0 0 3px rgba(15,118,110,.18); }`}</style>
    </div>
  );
}

function PaymentProofPanel({ caseId }) {
  const [proofs, setProofs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState("");
  const inputRef = useRef(null);

  const load = async () => {
    try {
      const { data } = await api.get(`/cases/${caseId}/attachments?kind=PAYMENT_PROOF`);
      setProofs(data.attachments || []);
    } catch (e) { setErr(fmtErr(e)); }
  };
  useEffect(() => { load(); }, [caseId]);

  const onFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true); setErr("");
    try {
      const fd = new FormData();
      fd.append("file", f);
      fd.append("kind", "PAYMENT_PROOF");
      await api.post(`/cases/${caseId}/attachments`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      await load();
    } catch (e2) { setErr(fmtErr(e2)); }
    finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const remove = async (a) => {
    if (!window.confirm("Remove this payment proof?")) return;
    try { await api.delete(`/attachments/${a.id}`); load(); }
    catch (e) { setErr(fmtErr(e)); }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-md p-6 mt-6" data-testid="payment-proof-panel">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-display text-sm font-semibold text-gray-900">Payment proof <span className="text-gray-400 font-normal">(optional)</span></h3>
          <p className="text-xs text-gray-500 mt-0.5">Upload a screenshot of the UPI / PhonePe / GPay confirmation. Stored against this case.</p>
        </div>
        <label className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 hover:border-teal-600 rounded-md text-sm font-medium cursor-pointer" data-testid="upload-proof-btn">
          {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
          Upload proof
          <input ref={inputRef} type="file" accept="image/*,.pdf" onChange={onFile} className="hidden" disabled={uploading} data-testid="proof-file-input" />
        </label>
      </div>
      {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-3">{err}</div>}
      {proofs.length === 0 ? (
        <div className="text-sm text-gray-400 py-4">No payment proof uploaded yet.</div>
      ) : (
        <ul className="divide-y divide-gray-100" data-testid="proof-list">
          {proofs.map((p) => (
            <li key={p.id} className="flex items-center justify-between py-2.5" data-testid={`proof-${p.id}`}>
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-8 h-8 rounded bg-teal-50 text-teal-700 grid place-items-center shrink-0"><FileImage size={14} /></div>
                <div className="min-w-0">
                  <div className="text-sm text-gray-900 truncate">{p.original_filename}</div>
                  <div className="text-[11px] text-gray-500 tabular-nums">{new Date(p.created_at).toLocaleString()} · {(p.size_bytes / 1024).toFixed(0)} KB · by {p.uploaded_by_name || "—"}</div>
                </div>
              </div>
              <div className="flex gap-1">
                <a href={`${process.env.REACT_APP_BACKEND_URL}/api/attachments/${p.id}/download`} target="_blank" rel="noreferrer" className="text-xs px-2.5 py-1.5 border border-gray-200 rounded hover:border-teal-600 hover:text-teal-700">View</a>
                <button onClick={() => remove(p)} className="text-xs px-2.5 py-1.5 border border-gray-200 rounded hover:border-red-500 hover:text-red-600 inline-flex items-center gap-1" data-testid={`del-proof-${p.id}`}><Trash2 size={12} /></button>
              </div>
            </li>
          ))}
        </ul>
      )}
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

function Row({ label, value, bold }) {
  return (
    <div className={`flex justify-between py-1.5 text-sm ${bold ? "font-semibold text-gray-900" : "text-gray-600"}`}>
      <span>{label}</span>
      <span className="tabular-nums">₹{Number(value).toFixed(2)}</span>
    </div>
  );
}
