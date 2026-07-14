import { useState, useCallback, useEffect } from "react";
import { Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import { Search, Loader2, IndianRupee, Phone, FileText, ChevronRight, AlertCircle } from "lucide-react";

const fINR = (n) => `₹${Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
const PAY_PILLS = {
  PAID: "bg-emerald-50 text-emerald-800 border-emerald-200",
  PARTIAL: "bg-amber-50 text-amber-800 border-amber-200",
  UNPAID: "bg-rose-50 text-rose-800 border-rose-200",
  UNBILLED: "bg-gray-100 text-gray-600 border-gray-200",
};

export default function FinancialSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [searched, setSearched] = useState(false);

  const run = useCallback(async () => {
    if (q.trim().length < 2) { setResults([]); setSearched(false); return; }
    setLoading(true); setErr("");
    try {
      const { data } = await api.get(`/pro/financial-search?q=${encodeURIComponent(q.trim())}`);
      setResults(data.results || []);
      setSearched(true);
    } catch (e) { setErr(fmtErr(e)); }
    finally { setLoading(false); }
  }, [q]);

  useEffect(() => {
    const t = setTimeout(run, 300);
    return () => clearTimeout(t);
  }, [run]);

  return (
    <div className="p-8 max-w-5xl mx-auto" data-testid="financial-search-page">
      <div className="mb-6">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">PRO · Billing</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Patient financial search</h1>
        <p className="text-sm text-gray-600 mt-2">Look up a patient by name, ID or phone number to see their complete billing & payment history.</p>
      </div>

      <div className="relative mb-5 max-w-xl">
        <Search size={16} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          autoFocus
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Type name, patient ID, or phone (min 2 chars)…"
          className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:border-teal-700 focus:ring-2 focus:ring-teal-700/20"
          data-testid="fin-search-input"
        />
      </div>

      {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-3 flex items-center gap-2"><AlertCircle size={14} /> {err}</div>}
      {loading && <div className="text-sm text-gray-500 inline-flex items-center gap-2"><Loader2 size={14} className="animate-spin" /> Searching…</div>}

      {!loading && searched && results.length === 0 && (
        <div className="bg-white border border-gray-200 rounded-md p-12 text-center text-gray-400">
          No patients match &ldquo;<span className="font-medium">{q}</span>&rdquo;.
        </div>
      )}

      <div className="space-y-4">
        {results.map((r) => (
          <article key={r.patient.id} className="bg-white border border-gray-200 rounded-md overflow-hidden" data-testid={`fin-result-${r.patient.id}`}>
            <div className="p-5 flex items-start justify-between gap-4 border-b border-gray-100">
              <div>
                <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-0.5 tabular-nums">{r.patient.patient_uid}</div>
                <div className="font-display text-lg font-semibold text-gray-900">{r.patient.first_name} {r.patient.last_name}</div>
                <div className="text-xs text-gray-600 mt-0.5 tabular-nums inline-flex items-center gap-3">
                  <span>{r.patient.age}y · {r.patient.gender}</span>
                  <span className="inline-flex items-center gap-1"><Phone size={11} /> {r.patient.phone}</span>
                  <span>{r.visits_count} visit{r.visits_count !== 1 ? "s" : ""}</span>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-right">
                <Metric label="Billed" value={fINR(r.total_billed)} />
                <Metric label="Paid" value={fINR(r.total_paid)} positive />
                <Metric label="Outstanding" value={fINR(r.outstanding)} negative={r.outstanding > 0} />
              </div>
            </div>
            {r.visits.length > 0 ? (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
                  <tr>
                    <th className="text-left px-5 py-2">Visit</th>
                    <th className="text-left px-5 py-2">Date</th>
                    <th className="text-left px-5 py-2">Complaint</th>
                    <th className="text-right px-5 py-2">Total</th>
                    <th className="text-right px-5 py-2">Paid</th>
                    <th className="text-right px-5 py-2">Bal</th>
                    <th className="text-left px-5 py-2">Mode</th>
                    <th className="text-left px-5 py-2">Status</th>
                    <th className="text-right px-5 py-2">Open</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {r.visits.map((v) => (
                    <tr key={v.case_id} data-testid={`visit-${v.case_id}`}>
                      <td className="px-5 py-2.5 font-mono text-xs tabular-nums">{v.case_uid}</td>
                      <td className="px-5 py-2.5 text-xs tabular-nums text-gray-600">{new Date(v.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" })}</td>
                      <td className="px-5 py-2.5 text-xs text-gray-700 max-w-xs truncate" title={v.complaint}>{v.complaint || "—"}</td>
                      <td className="px-5 py-2.5 text-right tabular-nums">{fINR(v.total_amount)}</td>
                      <td className="px-5 py-2.5 text-right tabular-nums text-emerald-700">{fINR(v.amount_paid)}</td>
                      <td className={`px-5 py-2.5 text-right tabular-nums ${v.balance_amount > 0 ? "text-rose-700" : "text-gray-500"}`}>{fINR(v.balance_amount)}</td>
                      <td className="px-5 py-2.5 text-xs text-gray-600">{v.payment_mode || "—"}</td>
                      <td className="px-5 py-2.5"><span className={`inline-block px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider rounded border ${PAY_PILLS[v.payment_status] || PAY_PILLS.UNBILLED}`}>{v.payment_status}</span></td>
                      <td className="px-5 py-2.5 text-right">
                        <Link to={`/pro/cases/${v.case_id}`} className="inline-flex items-center gap-1 text-xs text-teal-700 hover:text-teal-900 font-medium"><FileText size={12} /> Open</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-5 text-sm text-gray-400">No visits recorded yet.</div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value, positive, negative }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">{label}</div>
      <div className={`text-sm font-semibold tabular-nums ${negative ? "text-rose-700" : positive ? "text-emerald-700" : "text-gray-900"}`}>{value}</div>
    </div>
  );
}
