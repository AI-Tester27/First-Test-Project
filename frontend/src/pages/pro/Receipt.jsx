import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { Leaf, Printer } from "lucide-react";

export default function Receipt() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  useEffect(() => { (async () => { const r = await api.get(`/cases/${id}`); setData(r.data); })(); }, [id]);
  if (!data || !data.payment) return <div className="p-8">Loading…</div>;
  const c = data.case;
  const p = data.payment;
  const isTelugu = c.patient?.preferred_language === "TE";

  return (
    <div className="min-h-screen bg-gray-100 py-10">
      <div className="max-w-md mx-auto mb-4 no-print flex justify-end">
        <button onClick={() => window.print()} className="inline-flex items-center gap-2 px-3 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium" data-testid="print-btn">
          <Printer size={14} /> Print
        </button>
      </div>
      <div className="printable max-w-md mx-auto bg-white border border-gray-200 p-8 font-mono text-sm">
        <div className="flex items-center gap-2 border-b border-dashed border-gray-300 pb-3 mb-3">
          <div className="w-9 h-9 rounded-md bg-teal-700 text-white grid place-items-center"><Leaf size={16} strokeWidth={1.5} /></div>
          <div>
            <div className="font-display font-semibold text-base text-gray-900">Sparsa Homeoclinic</div>
            <div className="text-[11px] text-gray-500">Internal receipt · Non-GST</div>
          </div>
        </div>

        <div className="flex justify-between text-xs mb-3">
          <span>Receipt #</span>
          <span className="tabular-nums font-semibold">{p.receipt_no}</span>
        </div>
        <div className="flex justify-between text-xs mb-1">
          <span>Date</span>
          <span className="tabular-nums">{new Date(p.updated_at || p.created_at).toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-xs mb-3">
          <span>Case</span>
          <span className="tabular-nums">{c.case_uid}</span>
        </div>

        <div className="border-t border-dashed border-gray-300 pt-3 mb-3">
          <div className="text-xs uppercase tracking-wider text-gray-500 mb-1">Patient</div>
          <div className="font-semibold">{c.patient?.first_name} {c.patient?.last_name}</div>
          <div className="text-xs text-gray-600 tabular-nums">{c.patient?.patient_uid} · {c.patient?.phone}</div>
          <div className="text-xs text-gray-600 mt-1">Doctor: {c.doctor?.display_name}</div>
        </div>

        <div className="border-t border-dashed border-gray-300 pt-3 mb-3">
          <Row label="Consultation" labelTe="వైద్య సలహా" value={p.consultation_amount} showTe={isTelugu} />
          {p.medicines_taken && <Row label="Medicines" labelTe="మందులు" value={p.medicine_amount} showTe={isTelugu} />}
          <div className="border-t border-gray-300 my-2" />
          <Row label="Total" labelTe="మొత్తం" value={p.total_amount} bold showTe={isTelugu} />
          <Row label="Paid" labelTe="చెల్లించింది" value={p.amount_paid} showTe={isTelugu} />
          <Row label="Balance" labelTe="బ్యాలెన్స్" value={p.balance_amount} bold showTe={isTelugu} />
          <div className="flex justify-between text-xs mt-2">
            <span>Mode</span><span className="font-semibold">{p.payment_mode}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span>Status</span><span className="font-semibold">{p.payment_status}</span>
          </div>
        </div>

        <div className="text-center text-[11px] text-gray-500 mt-4 leading-relaxed">
          Thank you for visiting Sparsa Homeoclinic.<br />
          {isTelugu && <span>మీ సందర్శనకు ధన్యవాదాలు.</span>}
        </div>
      </div>
    </div>
  );
}

function Row({ label, labelTe, value, bold, showTe }) {
  return (
    <div className={`flex justify-between text-xs py-0.5 ${bold ? "font-semibold" : ""}`}>
      <span>{label}{showTe && labelTe ? ` · ${labelTe}` : ""}</span>
      <span className="tabular-nums">₹{Number(value).toFixed(2)}</span>
    </div>
  );
}
