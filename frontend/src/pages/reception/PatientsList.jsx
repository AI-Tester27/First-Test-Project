import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import { Search, Loader2, ChevronRight } from "lucide-react";

export default function PatientsList() {
  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    const t = setTimeout(async () => {
      setLoading(true);
      try { const { data } = await api.get(`/patients?search=${encodeURIComponent(search)}`); setPatients(data.patients); }
      catch (e) { setErr(fmtErr(e)); }
      finally { setLoading(false); }
    }, 200);
    return () => clearTimeout(t);
  }, [search]);

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
                <th className="px-4 py-3 font-semibold">Language</th>
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
                    <Link to={`/reception/patients/${p.id}/timeline`} className="inline-flex items-center gap-1 text-teal-700 hover:text-teal-800 text-sm font-medium" data-testid={`open-timeline-${p.id}`}>
                      Timeline <ChevronRight size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
