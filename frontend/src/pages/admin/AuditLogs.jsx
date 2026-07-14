import { useEffect, useState } from "react";
import { api, fmtErr } from "@/lib/api";
import { Loader2 } from "lucide-react";

export default function AdminAudit() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try { const { data } = await api.get("/admin/audit-logs?limit=300"); setLogs(data.audit_logs); }
      catch (e) { setErr(fmtErr(e)); }
      finally { setLoading(false); }
    })();
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto" data-testid="admin-audit">
      <div className="mb-6">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Admin</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Audit log</h1>
        <p className="text-sm text-gray-500 mt-1">Every action across the clinic, newest first.</p>
      </div>
      {err && <div className="text-sm text-red-700">{err}</div>}
      <div className="bg-white border border-gray-200 rounded-md">
        {loading ? (
          <div className="p-12 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 text-left">
                <th className="px-4 py-3 font-semibold">Time</th>
                <th className="px-4 py-3 font-semibold">Actor</th>
                <th className="px-4 py-3 font-semibold">Role</th>
                <th className="px-4 py-3 font-semibold">Action</th>
                <th className="px-4 py-3 font-semibold">Entity</th>
                <th className="px-4 py-3 font-semibold">Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 text-xs text-gray-500 tabular-nums">{new Date(l.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{l.actor_username || "—"}</td>
                  <td className="px-4 py-3 text-gray-700">{l.actor_role}</td>
                  <td className="px-4 py-3"><span className="pill pill-in-consultation">{l.action}</span></td>
                  <td className="px-4 py-3 text-gray-700 text-xs tabular-nums">{l.entity_type}<br /><span className="text-gray-400">{l.entity_id?.slice(0, 12)}…</span></td>
                  <td className="px-4 py-3 text-xs text-gray-600 max-w-md">{l.metadata && Object.keys(l.metadata).length > 0 ? JSON.stringify(l.metadata) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
