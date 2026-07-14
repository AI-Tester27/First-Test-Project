import { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { api, fmtErr } from "@/lib/api";
import { ArrowLeft, FilePlus, Search, Loader2, UserPlus } from "lucide-react";

export default function NewVisit() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [doctors, setDoctors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState("");
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [doctorId, setDoctorId] = useState("");
  const [complaint, setComplaint] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const { data } = await api.get("/doctors");
      setDoctors(data.doctors);
      const presetPid = searchParams.get("patient_id");
      if (presetPid) {
        const { data: pd } = await api.get(`/patients/${presetPid}`);
        setSelectedPatient(pd.patient);
      }
    })();
  }, [searchParams]);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!search) { setPatients([]); return; }
      const { data } = await api.get(`/patients?search=${encodeURIComponent(search)}`);
      setPatients(data.patients);
    }, 200);
    return () => clearTimeout(t);
  }, [search]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const { data } = await api.post("/cases", {
        patient_id: selectedPatient.id,
        assigned_doctor_id: doctorId,
        complaint_text: complaint,
      });
      navigate("/reception");
    } catch (e2) {
      setErr(fmtErr(e2));
    } finally { setBusy(false); }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto" data-testid="new-visit-page">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-4">
        <ArrowLeft size={14} /> Back
      </button>
      <div className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Reception</div>
      <h1 className="font-display text-3xl font-semibold tracking-tight text-gray-900 mb-8">New visit</h1>

      <form onSubmit={submit} className="bg-white border border-gray-200 rounded-md p-6 space-y-6" data-testid="new-visit-form">
        {/* Patient */}
        <div>
          <label className="text-xs uppercase tracking-wider font-semibold text-gray-500 block mb-1.5">Patient</label>
          {selectedPatient ? (
            <div className="flex items-center justify-between border border-gray-200 rounded-md px-3 py-2.5 bg-teal-50/40" data-testid="selected-patient">
              <div>
                <div className="font-medium text-gray-900">{selectedPatient.first_name} {selectedPatient.last_name}</div>
                <div className="text-xs text-gray-500 tabular-nums">{selectedPatient.patient_uid} · {selectedPatient.phone} · {selectedPatient.gender} · {selectedPatient.age}y</div>
              </div>
              <button type="button" onClick={() => setSelectedPatient(null)} className="text-xs text-gray-500 hover:text-gray-900">Change</button>
            </div>
          ) : (
            <>
              <div className="relative">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by name, phone or patient ID…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-md focus-ring"
                  data-testid="patient-search-input"
                />
              </div>
              {patients.length > 0 && (
                <div className="mt-2 border border-gray-200 rounded-md divide-y divide-gray-100 max-h-64 overflow-auto">
                  {patients.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => { setSelectedPatient(p); setPatients([]); setSearch(""); }}
                      className="w-full text-left px-3 py-2.5 hover:bg-gray-50"
                      data-testid={`patient-result-${p.id}`}
                    >
                      <div className="text-sm font-medium text-gray-900">{p.first_name} {p.last_name}</div>
                      <div className="text-xs text-gray-500 tabular-nums">{p.patient_uid} · {p.phone}</div>
                    </button>
                  ))}
                </div>
              )}
              <div className="mt-3">
                <Link to="/reception/patients/new" className="inline-flex items-center gap-1.5 text-xs text-teal-700 hover:text-teal-800 font-medium">
                  <UserPlus size={13} strokeWidth={1.5} /> Register new patient
                </Link>
              </div>
            </>
          )}
        </div>

        {/* Doctor */}
        <div>
          <label className="text-xs uppercase tracking-wider font-semibold text-gray-500 block mb-1.5">Assign Doctor *</label>
          <select className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus-ring" value={doctorId} onChange={(e) => setDoctorId(e.target.value)} required data-testid="doctor-select">
            <option value="">— Select —</option>
            {doctors.map((d) => <option key={d.id} value={d.id}>{d.display_name}</option>)}
          </select>
        </div>

        {/* Complaint */}
        <div>
          <label className="text-xs uppercase tracking-wider font-semibold text-gray-500 block mb-1.5">Complaint / Problem *</label>
          <textarea rows={4} className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm focus-ring" value={complaint} onChange={(e) => setComplaint(e.target.value)} required data-testid="complaint-input" />
        </div>

        {err && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">{err}</div>}

        <button type="submit" disabled={busy || !selectedPatient} className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white rounded-md text-sm font-medium" data-testid="create-case-btn">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <FilePlus size={14} strokeWidth={1.5} />}
          Send to Doctor
        </button>
      </form>
    </div>
  );
}
