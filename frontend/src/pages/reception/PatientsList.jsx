import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import { Search, Loader2, ChevronRight, Pencil, Trash2, X, Save } from "lucide-react";

export default function PatientsList() {
  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get(`/patients?search=${encodeURIComponent(search)}`); setPatients(data.patients); }
    catch (e) { setErr(fmtErr(e)); }
    finally { setLoading(false); }
  }, [search]);

  useEffect(() => {
    const t = setTimeout(() => { load(); }, 200);
    return () => clearTimeout(t);
  }, [load]);

  const remove = async (p) => {
    if (!window.confirm(`Delete ${p.first_name} ${p.last_name}? Their visit history will also be permanently removed.`)) return;
    try { await api.delete(`/patients/${p.id}`); load(); }
    catch (e) { setErr(fmtErr(e)); }
  };

  const saveEdit = async () => {
    try {
      await api.patch(`/patients/${editing.id}`, {
        first_name: editing.first_name,
        last_name: editing.last_name,
        gender: editing.gender,
        age: Number(editing.age),
        phone: editing.phone,
        address: editing.address,
        preferred_language: editing.preferred_language,
      });
      setEditing(null);
      load();
    } catch (e) { setErr(fmtErr(e)); }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto" data-testid="patients-list">
      <div className="mb-6">
        <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Reception</div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Patients</h1>
      </div>

      <div className="bg-white border border-gray-200 rounded-md">
        <div className="p-4 border-b border-gray-200">
          <div className="relative max-w-md">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name, phone or patient ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-md focus-ring"
              data-testid="patients-search-input"
            />
          </div>
        </div>
        {err && <div className="p-4 text-sm text-red-700">{err}</div>}
        {loading ? (
          <div className="p-12 grid place-items-center text-gray-400"><Loader2 className="animate-spin" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 text-left">
                <th className="px-4 py-3 font-semibold">Patient ID</th>
                <th className="px-4 py-3 font-semibold">Name</th>
                <th className="px-4 py-3 font-semibold">Phone</th>
                <th className="px-4 py-3 font-semibold">Gender</th>
                <th className="px-4 py-3 font-semibold">Age</th>
                <th className="px-4 py-3 font-semibold">Lang</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {patients.length === 0 && (
                <tr><td colSpan={7} className="p-12 text-center text-gray-400">No patients found.</td></tr>
              )}
              {patients.map((p) => (
                <tr key={p.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 tabular-nums text-xs text-gray-700">{p.patient_uid}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{p.first_name} {p.last_name}</td>
                  <td className="px-4 py-3 tabular-nums text-gray-700">{p.phone}</td>
                  <td className="px-4 py-3 text-gray-700">{p.gender}</td>
                  <td className="px-4 py-3 tabular-nums text-gray-700">{p.age}</td>
                  <td className="px-4 py-3 text-gray-700">{p.preferred_language}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      <button onClick={() => setEditing({ ...p })} className="text-gray-500 hover:text-teal-700" data-testid={`edit-patient-${p.id}`} title="Edit">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => remove(p)} className="text-gray-400 hover:text-red-600" data-testid={`delete-patient-${p.id}`} title="Delete">
                        <Trash2 size={14} />
                      </button>
                      <Link to={`/reception/patients/${p.id}/timeline`} className="inline-flex items-center gap-1 text-teal-700 hover:text-teal-800 text-sm font-medium ml-2" data-testid={`open-timeline-${p.id}`}>
                        Timeline <ChevronRight size={14} />
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editing && (
        <div className="fixed inset-0 bg-black/30 grid place-items-center z-50" onClick={() => setEditing(null)}>
          <div className="bg-white rounded-md p-6 max-w-md w-full shadow-xl" onClick={(e) => e.stopPropagation()} data-testid="edit-patient-modal">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-semibold text-lg text-gray-900">Edit patient</h3>
              <button onClick={() => setEditing(null)} className="text-gray-400 hover:text-gray-700"><X size={16} /></button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="First name"><input className="input" value={editing.first_name} onChange={(e) => setEditing({ ...editing, first_name: e.target.value })} /></Field>
              <Field label="Last name"><input className="input" value={editing.last_name} onChange={(e) => setEditing({ ...editing, last_name: e.target.value })} /></Field>
              <Field label="Gender">
                <select className="input" value={editing.gender} onChange={(e) => setEditing({ ...editing, gender: e.target.value })}>
                  <option value="MALE">Male</option>
                  <option value="FEMALE">Female</option>
                  <option value="OTHER">Other</option>
                </select>
              </Field>
              <Field label="Age"><input type="number" className="input tabular-nums" value={editing.age} onChange={(e) => setEditing({ ...editing, age: e.target.value })} /></Field>
              <Field label="Phone"><input className="input tabular-nums" value={editing.phone} onChange={(e) => setEditing({ ...editing, phone: e.target.value })} /></Field>
              <Field label="Language">
                <select className="input" value={editing.preferred_language} onChange={(e) => setEditing({ ...editing, preferred_language: e.target.value })}>
                  <option value="EN">English</option>
                  <option value="TE">Telugu</option>
                </select>
              </Field>
              <div className="col-span-2"><Field label="Address"><textarea rows={2} className="input" value={editing.address || ""} onChange={(e) => setEditing({ ...editing, address: e.target.value })} /></Field></div>
            </div>
            <div className="flex gap-2 mt-5">
              <button onClick={saveEdit} className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium" data-testid="save-edit-patient">
                <Save size={14} /> Save changes
              </button>
              <button onClick={() => setEditing(null)} className="px-3 py-2 bg-white border border-gray-200 rounded-md text-sm font-medium">Cancel</button>
            </div>
          </div>
        </div>
      )}
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
