import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "@/App.css";
import { AuthProvider } from "@/contexts/AuthContext";
import RequireAuth from "@/components/RequireAuth";
import AppLayout from "@/components/AppLayout";

import LoginPage from "@/pages/Login";

import ReceptionDashboard from "@/pages/reception/Dashboard";
import NewPatient from "@/pages/reception/NewPatient";
import NewVisit from "@/pages/reception/NewVisit";
import PatientsList from "@/pages/reception/PatientsList";
import PatientTimeline from "@/pages/reception/PatientTimeline";

import DoctorDashboard from "@/pages/doctor/Dashboard";
import DoctorCaseDetail from "@/pages/doctor/CaseDetail";
import DoctorReminders from "@/pages/doctor/Reminders";

import PharmacyDashboard from "@/pages/pharmacy/Dashboard";
import PharmacyCase from "@/pages/pharmacy/CaseDetail";

import ProDashboard from "@/pages/pro/Dashboard";
import BillingDetail from "@/pages/pro/BillingDetail";
import Receipt from "@/pages/pro/Receipt";

import AdminDashboard from "@/pages/admin/Dashboard";
import AdminUsers from "@/pages/admin/Users";
import AdminAudit from "@/pages/admin/AuditLogs";
import AdminExports from "@/pages/admin/Exports";

export default function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            {/* Receipt: print-friendly route without sidebar */}
            <Route
              path="/pro/cases/:id/receipt"
              element={<RequireAuth roles={["PRO", "OWNER_DOCTOR", "ADMIN"]}><Receipt /></RequireAuth>}
            />

            {/* Authenticated app shell */}
            <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
              {/* Reception */}
              <Route path="/reception" element={<RequireAuth roles={["RECEPTION", "OWNER_DOCTOR", "ADMIN"]}><ReceptionDashboard /></RequireAuth>} />
              <Route path="/reception/patients" element={<RequireAuth roles={["RECEPTION", "OWNER_DOCTOR", "ADMIN"]}><PatientsList /></RequireAuth>} />
              <Route path="/reception/patients/:id/timeline" element={<RequireAuth><PatientTimeline /></RequireAuth>} />
              <Route path="/reception/patients/new" element={<RequireAuth roles={["RECEPTION", "OWNER_DOCTOR", "ADMIN"]}><NewPatient /></RequireAuth>} />
              <Route path="/reception/new-visit" element={<RequireAuth roles={["RECEPTION", "OWNER_DOCTOR", "ADMIN"]}><NewVisit /></RequireAuth>} />

              {/* Doctor */}
              <Route path="/doctor" element={<RequireAuth roles={["DOCTOR", "OWNER_DOCTOR"]}><DoctorDashboard /></RequireAuth>} />
              <Route path="/doctor/all" element={<RequireAuth roles={["OWNER_DOCTOR"]}><DoctorDashboard scope="all" /></RequireAuth>} />
              <Route path="/doctor/cases/:id" element={<RequireAuth roles={["DOCTOR", "OWNER_DOCTOR"]}><DoctorCaseDetail /></RequireAuth>} />
              <Route path="/doctor/reminders" element={<RequireAuth roles={["DOCTOR", "OWNER_DOCTOR"]}><DoctorReminders /></RequireAuth>} />

              {/* Pharmacy */}
              <Route path="/pharmacy" element={<RequireAuth roles={["PHARMACY", "OWNER_DOCTOR", "ADMIN"]}><PharmacyDashboard /></RequireAuth>} />
              <Route path="/pharmacy/cases/:id" element={<RequireAuth roles={["PHARMACY", "OWNER_DOCTOR", "ADMIN"]}><PharmacyCase /></RequireAuth>} />

              {/* PRO */}
              <Route path="/pro" element={<RequireAuth roles={["PRO", "OWNER_DOCTOR", "ADMIN"]}><ProDashboard /></RequireAuth>} />
              <Route path="/pro/cases/:id" element={<RequireAuth roles={["PRO", "OWNER_DOCTOR", "ADMIN"]}><BillingDetail /></RequireAuth>} />

              {/* Admin */}
              <Route path="/admin" element={<RequireAuth roles={["ADMIN"]}><AdminDashboard /></RequireAuth>} />
              <Route path="/admin/users" element={<RequireAuth roles={["ADMIN"]}><AdminUsers /></RequireAuth>} />
              <Route path="/admin/audit" element={<RequireAuth roles={["ADMIN"]}><AdminAudit /></RequireAuth>} />
              <Route path="/admin/exports" element={<RequireAuth roles={["ADMIN"]}><AdminExports /></RequireAuth>} />
              <Route path="/admin/cases" element={<RequireAuth roles={["ADMIN"]}><DoctorDashboard scope="all" /></RequireAuth>} />
            </Route>

            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
