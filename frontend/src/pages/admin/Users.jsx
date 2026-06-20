import { useEffect, useState } from "react";
import { api, fmtErr } from "@/lib/api";
import { Plus, Loader2, X, Trash2 } from "lucide-react";

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [err, setErr] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ username: "", name: "", password: "", role: "RECEPTION", doctor_id: "" });
  const [busy, setBusy] = useState(false);

  const reload = async () => {
    try { const { data } = await api.get("/admin/users"); setUsers(data.users); }
    catch (e) { setErr(fmtErr(e)); }
  };
  useEffect(() => { reload(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      await api.post("/admin/users", { ...form, doctor_id: form.doctor_id || null });
      setForm({ username: "", name: "", password: "", role: "RECEPTION", doctor_id: "" });
      setShowForm(false);
      reload();
    } catch (e2) { setErr(fmtErr(e2)); }
    finally { setBusy(false); }
  };

  const toggleActive = async (u) => {
    await api.patch(`/admin/users/${u.id}`, { active: !u.active });
    reload();
  };

  const removeUser = async (u) => {
    if (!window.confirm(`Delete user ${u.username}? This cannot be undone.`)) return;
    try { await api.delete(`/admin/users/${u.id}`); reload(); }
    catch (e) { setErr(fmtErr(e)); }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto" data-testid="admin-users">
      <div className="flex items-end justify-between mb-6">
        <div>
          <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Admin</div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900">Users</h1>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="inline-flex items-center gap-2 px-3.5 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium" data-testid="add-user-btn">
          {showForm ? <X size={14} /> : <Plus size={14} />} {showForm ? "Cancel" : "New user"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={submit} className="bg-white border border-gray-200 rounded-md p-6 mb-6 grid grid-cols-2 gap-4" data-testid="user-form">
          <Field label="Username"><input className="input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required /></Field>
          <Field label="Name"><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></Field>
          <Field label="Password"><input type="password" className="input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} /></Field>
          <Field label="Role">
            <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              {["ADMIN", "OWNER_DOCTOR", "DOCTOR", "RECEPTION", "PHARMACY", "PRO"].map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </Field>
          {(form.role === "DOCTOR" || form.role === "OWNER_DOCTOR") && (
            <Field label="Doctor ID (optional)">
              <input className="input" placeholder="doctor-jyothi or doctor-hemanth" value={form.doctor_id} onChange={(e) => setForm({ ...form, doctor_id: e.target.value })} />
            </Field>
          )}
          <div className="col-span-2">
            <button type="submit" disabled={busy} className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-md text-sm font-medium disabled:opacity-60">
              {busy && <Loader2 size={14} className="animate-spin" />} Create user
            </button>
            {err && <div className="text-sm text-red-700 mt-2">{err}</div>}
          </div>
        </form>
      )}

      <div className="bg-white border border-gray-200 rounded-md">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 text-left">
              <th className="px-4 py-3 font-semibold">Username</th>
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">Role</th>
              <th className="px-4 py-3 font-semibold">Doctor</th>
              <th className="px-4 py-3 font-semibold">Active</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{u.username}</td>
                <td className="px-4 py-3 text-gray-700">{u.name}</td>
                <td className="px-4 py-3 text-gray-700">{u.role}</td>
                <td className="px-4 py-3 text-gray-700">{u.doctor_name || "—"}</td>
                <td className="px-4 py-3">
                  <span className={`pill ${u.active ? "pill-paid" : "pill-unpaid"}`}>{u.active ? "Active" : "Disabled"}</span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="inline-flex items-center gap-2">
                    <button onClick={() => toggleActive(u)} className="text-xs text-gray-600 hover:text-gray-900" data-testid={`toggle-user-${u.username}`}>
                      {u.active ? "Disable" : "Enable"}
                    </button>
                    <button onClick={() => removeUser(u)} className="text-gray-400 hover:text-red-600" data-testid={`delete-user-${u.username}`} title="Delete">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
