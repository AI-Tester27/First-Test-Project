import { API } from "@/lib/api";
import { Download, Users, FileText, ReceiptText, Pill, ClipboardList } from "lucide-react";

const EXPORTS = [
  { path: "patients.csv", label: "Patients", desc: "Full patient registry incl. demographics & language preference.", icon: Users },
  { path: "cases.csv", label: "Cases", desc: "Every visit with status, doctor, complaint and timestamps.", icon: FileText },
  { path: "payments.csv", label: "Payments", desc: "All receipts with consultation + medicine amounts and modes.", icon: ReceiptText },
  { path: "prescriptions.csv", label: "Prescriptions", desc: "Per-medicine line items across every version (incl. pharmacy edits).", icon: Pill },
  { path: "audit.csv", label: "Audit log", desc: "Complete activity trail — who did what and when.", icon: ClipboardList },
];

export default function AdminExports() {
  const download = (path) => {
    // browser will send cookies via credentials include due to same-origin; use API absolute url
    const a = document.createElement("a");
    a.href = `${API}/admin/export/${path}`;
    a.rel = "noopener";
    // Force a fresh fetch with credentials by clicking inside a link
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto" data-testid="admin-exports">
      <div className="mb-6">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Admin</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Exports</h1>
        <p className="text-sm text-gray-500 mt-1">Download CSVs for backup, accounting and analytics.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {EXPORTS.map((e) => (
          <button
            key={e.path}
            onClick={() => download(e.path)}
            className="text-left bg-white border border-gray-200 rounded-md p-5 hover:border-teal-600 transition-colors group"
            data-testid={`export-${e.path}`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="w-9 h-9 rounded-md bg-teal-50 text-teal-700 grid place-items-center">
                <e.icon size={16} strokeWidth={1.5} />
              </div>
              <Download size={14} strokeWidth={1.5} className="text-gray-400 group-hover:text-teal-700" />
            </div>
            <div className="font-display font-semibold text-sm text-gray-900 mb-1">{e.label}</div>
            <div className="text-xs text-gray-500 leading-relaxed">{e.desc}</div>
          </button>
        ))}
      </div>

      <div className="mt-8 bg-amber-50/50 border border-amber-100 rounded-md p-4 text-xs text-amber-900">
        <strong>Tip:</strong> For full disaster recovery, also run the daily backup script at <code className="bg-white px-1 py-0.5 rounded text-[11px]">/app/scripts/backup.sh</code>. CSVs are useful for accounting; the backup script preserves everything including indexes and history.
      </div>
    </div>
  );
}
