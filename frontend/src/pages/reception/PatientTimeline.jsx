import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import StatusBadge, { PaymentBadge } from "@/components/StatusBadge";
import { ArrowLeft, Loader2, FileText, Pill, ReceiptText, Paperclip, Calendar, Sparkles, X, FilePlus } from "lucide-react";

function Markdown({ source }) {
  // Minimal markdown → JSX renderer for AI output (headings, bullets, bold).
  const lines = (source || "").split("\n");
  const out = [];
  let listBuf = [];
  const flushList = () => {
    if (listBuf.length) {
      out.push(<ul key={out.length} className="list-disc pl-5 space-y-0.5">{listBuf.map((t, i) => <li key={i}>{inline(t)}</li>)}</ul>);
      listBuf = [];
    }
  };
  const inline = (txt) => {
    const parts = [];
    let i = 0; let key = 0;
    txt.replace(/\*\*(.+?)\*\*/g, (m, b, idx) => {
      if (idx > i) parts.push(txt.slice(i, idx));
      parts.push(<strong key={key++}>{b}</strong>);
      i = idx + m.length;
      return m;
    });
    if (i < txt.length) parts.push(txt.slice(i));
    return parts.length ? parts : txt;
  };
  for (const raw of lines) {
    const l = raw.trimEnd();
    if (/^##\s+/.test(l)) { flushList(); out.push(<h2 key={out.length}>{l.replace(/^##\s+/, "")}</h2>); }
    else if (/^#\s+/.test(l)) { flushList(); out.push(<h2 key={out.length}>{l.replace(/^#\s+/, "")}</h2>); }
    else if (/^[-*]\s+/.test(l)) { listBuf.push(l.replace(/^[-*]\s+/, "")); }
    else if (l.trim() === "") { flushList(); }
    else { flushList(); out.push(<p key={out.length}>{inline(l)}</p>); }
  }
  flushList();
  return <>{out}</>;
}

export default function PatientTimeline() {
  const { id } = useParams();
  const { user } = useAuth();
  const isDoctor = user?.role === "DOCTOR" || user?.role === "OWNER_DOCTOR";
  const basePath = isDoctor ? "/doctor" : "/reception";
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [recap, setRecap] = useState(null);
  const [recapBusy, setRecapBusy] = useState(false);
  const [recapErr, setRecapErr] = useState("");

  useEffect(() => {
    (async () => {
      try { const r = await api.get(`/patients/${id}/timeline`); setData(r.data); }
      catch (e) { setErr(fmtErr(e)); }
    })();
  }, [id]);

  const runRecap = async (mode = "brief") => {
    setRecapBusy(true); setRecapErr(""); setRecap(null);
    try {
      const { data } = await api.post(`/patients/${id}/ai/recap?mode=${mode}`);
      setRecap(data);
    } catch (e) { setRecapErr(fmtErr(e)); }
    finally { setRecapBusy(false); }
  };

  if (err) return <div className="p-8 text-red-700">{err}</div>;
  if (!data) return <div className="p-8 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>;

  const p = data.patient;

  return (
    <div className="p-8 max-w-4xl mx-auto" data-testid="patient-timeline">
      <Link to={`${basePath}/patients`} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-3">
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

      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2">
          <Calendar size={15} strokeWidth={1.5} className="text-gray-500" />
          <h2 className="font-display text-base font-semibold text-gray-900">Visit history</h2>
          <span className="text-xs text-gray-500 tabular-nums ml-1">({data.timeline.length})</span>
        </div>
        <div className="flex gap-2">
          {!isDoctor && (
            <Link
              to={`/reception/patients/${id}/past-visit`}
              className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-gray-200 hover:border-teal-600 text-gray-900 rounded-md text-sm font-medium"
              data-testid="add-past-visit-btn"
            >
              <FilePlus size={14} strokeWidth={1.5} /> Add past visit
            </Link>
          )}
          {data.timeline.length > 0 && (
            <>
              <button
                onClick={() => runRecap("brief")}
                disabled={recapBusy}
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-teal-200 hover:border-teal-600 text-teal-800 disabled:opacity-60 rounded-md text-sm font-medium"
                data-testid="ai-recap-btn"
              >
                {recapBusy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} strokeWidth={1.5} />}
                AI 5-line briefing
              </button>
              {user?.role === "OWNER_DOCTOR" && (
                <button
                  onClick={() => runRecap("detailed")}
                  disabled={recapBusy}
                  className="inline-flex items-center gap-2 px-3.5 py-2 bg-gradient-to-r from-teal-700 to-teal-600 hover:from-teal-800 hover:to-teal-700 disabled:opacity-60 text-white rounded-md text-sm font-medium shadow-sm"
                  data-testid="ai-detailed-btn"
                >
                  {recapBusy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} strokeWidth={1.5} />}
                  Comprehensive analysis
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {(recap || recapErr || recapBusy) && (
        <div className="bg-gradient-to-br from-teal-50/80 to-white border border-teal-200 rounded-md p-5 mb-5 relative" data-testid="recap-card">
          <button onClick={() => { setRecap(null); setRecapErr(""); }} className="absolute top-3 right-3 text-gray-400 hover:text-gray-700"><X size={14} /></button>
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={14} strokeWidth={1.5} className="text-teal-700" />
            <div className="text-xs uppercase tracking-wider font-semibold text-teal-800">
              {recap?.mode === "detailed" ? "Comprehensive AI analysis" : "5-line AI briefing"}
              {recap?.visits_analysed ? <span className="text-gray-500 tabular-nums"> · {recap.visits_analysed} visits analysed</span> : null}
            </div>
          </div>
          {recapBusy && <div className="text-sm text-gray-500 inline-flex items-center gap-2"><Loader2 size={14} className="animate-spin" /> Reading visit history…</div>}
          {recapErr && <div className="text-sm text-red-700">{recapErr}</div>}
          {recap?.result && (
            <div className={`text-sm text-gray-800 leading-relaxed ${recap.mode === "detailed" ? "prose prose-sm max-w-none prose-headings:font-display prose-headings:text-teal-900 prose-h2:text-base prose-h2:font-semibold prose-h2:mt-4 prose-h2:mb-2 prose-p:my-1 prose-ul:my-1 prose-li:my-0" : "whitespace-pre-wrap"}`} data-testid="recap-result">
              {recap.mode === "detailed" ? <Markdown source={recap.result} /> : recap.result}
            </div>
          )}
          {recap?.mode === "detailed" && (
            <div className="mt-4 px-3 py-2 rounded border border-amber-300 bg-amber-50 text-[11px] text-amber-900 leading-relaxed" data-testid="ai-disclaimer">
              <strong>For doctor review only.</strong> AI-generated mother-tincture suggestions and possible diagnoses are decision-support
              prompts — not prescriptions. Confirm dosage, potency and clinical fit before sharing with the patient.
            </div>
          )}
        </div>
      )}

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
