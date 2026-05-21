import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import StatusBadge, { PaymentBadge } from "@/components/StatusBadge";
import { ArrowLeft, Loader2, FileText, Pill, ReceiptText, Paperclip, Calendar } from "lucide-react";

export default function PatientTimeline() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try { const r = await api.get(`/patients/${id}/timeline`); setData(r.data); }
      catch (e) { setErr(fmtErr(e)); }
    })();
  }, [id]);

  if (err) return <div className="p-8 text-red-700">{err}</div>;
  if (!data) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  const p = data.patient;

  return (
    <div className="p-8 max-w-4xl mx-auto" data-testid="patient-timeline">
      <Link to="/reception/patients" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-3">
        <ArrowLeft size={14} /> Back to patients
      </Link>
      <div className="bg-white border border-gray-200 rounded-md p-6 mb-6">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1 tabular-nums">{p.patient_uid}</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">{p.first_name} {p.last_name}</h1>
        <div className="text-sm text-gray-600 mt-1 tabular-nums">
          {p.gender} · {p.age}y · {p.phone} · {p.preferred_language === "TE" ? "Telugu" : "English"}
        </div>
        {p.address && <div className="text-sm text-gray-500 mt-1">{p.address}</div>}
      </div>

      <div className="flex items-center gap-2 mb-4">
        <Calendar size={15} strokeWidth={1.5} className="text-gray-500" />
        <h2 className="font-display text-base font-semibold text-gray-900">Visit history</h2>
        <span className="text-xs text-gray-500 tabular-nums ml-1">({data.timeline.length})</span>
      </div>

      {data.timeline.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-md p-12 text-center text-sm text-gray-400">No visits yet.</div>
      ) : (
        <div className="space-y-4">
          {data.timeline.map((t) => (
            <article key={t.case.id} className="bg-white border border-gray-200 rounded-md p-5" data-testid={`timeline-${t.case.id}`}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1 tabular-nums">{t.case.case_uid}</div>
                  <div className="text-sm text-gray-700">{t.case.complaint_text}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {new Date(t.case.created_at).toLocaleString()} · {t.doctor?.display_name}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <StatusBadge status={t.case.status} />
                  {t.payment && <PaymentBadge status={t.payment.payment_status} />}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 text-xs">
                {t.clinical_notes ? (
                  <Section icon={FileText} title="Notes">
                    {t.clinical_notes.diagnosis_summary && <p className="text-gray-700 line-clamp-3">{t.clinical_notes.diagnosis_summary}</p>}
                    {t.clinical_notes.sensitivity_allergies && <p className="text-gray-500 mt-1"><span className="text-[10px] uppercase tracking-wider">Allergies:</span> {t.clinical_notes.sensitivity_allergies}</p>}
                  </Section>
                ) : <Section icon={FileText} title="Notes"><p className="text-gray-400">—</p></Section>}

                {t.prescriptions?.length > 0 ? (
                  <Section icon={Pill} title={`Prescription v${t.prescriptions[0].version_no}`}>
                    {t.prescriptions[0].items?.slice(0, 3).map((i, idx) => (
                      <div key={idx} className="text-gray-700">{i.medicine_name} {i.potency} · {i.frequency || ""}</div>
                    ))}
                    {t.prescriptions[0].items?.length > 3 && <div className="text-gray-400 mt-0.5">+{t.prescriptions[0].items.length - 3} more</div>}
                  </Section>
                ) : <Section icon={Pill} title="Prescription"><p className="text-gray-400">—</p></Section>}

                {t.payment ? (
                  <Section icon={ReceiptText} title="Payment">
                    <div className="tabular-nums text-gray-700">Total ₹{Number(t.payment.total_amount).toFixed(0)}</div>
                    <div className="text-gray-500">{t.payment.payment_mode || "—"} · Receipt {t.payment.receipt_no}</div>
                  </Section>
                ) : <Section icon={ReceiptText} title="Payment"><p className="text-gray-400">—</p></Section>}
              </div>

              {t.attachments_count > 0 && (
                <div className="mt-3 inline-flex items-center gap-1 text-xs text-gray-500">
                  <Paperclip size={12} /> {t.attachments_count} attachment{t.attachments_count !== 1 ? "s" : ""}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function Section({ icon: Icon, title, children }) {
  return (
    <div className="border border-gray-100 rounded p-3 bg-gray-50/50">
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon size={12} strokeWidth={1.5} className="text-gray-400" />
        <span className="text-[10px] uppercase tracking-wider font-semibold text-gray-500">{title}</span>
      </div>
      {children}
    </div>
  );
}
