import { useEffect, useRef, useState } from "react";
import { api, fmtErr, API } from "@/lib/api";
import { Loader2, Upload, FileText, Image as ImageIcon, Trash2, Download } from "lucide-react";

const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED = ["jpg", "jpeg", "png", "pdf"];

export default function AttachmentsTab({ caseId }) {
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const inputRef = useRef(null);

  const load = async () => {
    try {
      const { data } = await api.get(`/cases/${caseId}/attachments`);
      setFiles(data.attachments);
    } catch (e) { setErr(fmtErr(e)); }
  };
  useEffect(() => { load(); }, [caseId]);

  const onPick = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setErr("");
    const ext = file.name.split(".").pop().toLowerCase();
    if (!ALLOWED.includes(ext)) { setErr("Only JPG, PNG, PDF allowed."); return; }
    if (file.size > MAX_BYTES) { setErr("Max 10MB."); return; }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api.post(`/cases/${caseId}/attachments`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      await load();
    } catch (e2) { setErr(fmtErr(e2)); }
    finally { setBusy(false); }
  };

  const remove = async (f) => {
    if (!window.confirm(`Delete ${f.original_filename}?`)) return;
    try { await api.delete(`/attachments/${f.id}`); load(); }
    catch (e) { setErr(fmtErr(e)); }
  };

  const open = async (f) => {
    try {
      const resp = await api.get(`/attachments/${f.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(resp.data);
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) { setErr(fmtErr(e)); }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-md p-6" data-testid="attachments-tab">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-display text-base font-semibold text-gray-900">Attachments</h3>
          <p className="text-xs text-gray-500 mt-0.5">Lab reports, photos & PDFs. Max 10MB · JPG/PNG/PDF.</p>
        </div>
        <input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,.pdf" className="hidden" onChange={onPick} data-testid="attachment-file-input" />
        <button onClick={() => inputRef.current?.click()} disabled={busy} className="inline-flex items-center gap-2 px-3.5 py-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-60 text-white rounded-md text-sm font-medium" data-testid="upload-attachment-btn">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} strokeWidth={1.5} />}
          Upload
        </button>
      </div>
      {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-4">{err}</div>}
      {files.length === 0 ? (
        <div className="border border-dashed border-gray-200 rounded-md p-10 text-center text-sm text-gray-400">No files yet.</div>
      ) : (
        <div className="divide-y divide-gray-100 border border-gray-200 rounded-md">
          {files.map((f) => (
            <div key={f.id} className="px-4 py-3 flex items-center gap-3" data-testid={`attachment-${f.id}`}>
              <div className="w-9 h-9 rounded-md bg-teal-50 text-teal-700 grid place-items-center">
                {f.content_type?.startsWith("image/") ? <ImageIcon size={16} strokeWidth={1.5} /> : <FileText size={16} strokeWidth={1.5} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 truncate">{f.original_filename}</div>
                <div className="text-xs text-gray-500 tabular-nums">
                  {(f.size_bytes / 1024).toFixed(0)} KB · {new Date(f.created_at).toLocaleString()} · {f.uploaded_by_name}
                </div>
              </div>
              <button onClick={() => open(f)} className="px-2.5 py-1.5 text-xs font-medium border border-gray-200 rounded hover:border-teal-600 inline-flex items-center gap-1" data-testid={`open-${f.id}`}>
                <Download size={12} /> Open
              </button>
              <button onClick={() => remove(f)} className="text-gray-400 hover:text-red-600" data-testid={`delete-${f.id}`}>
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
