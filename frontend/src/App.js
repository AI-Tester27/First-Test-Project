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
import PastVisitForm from "@/pages/reception/PastVisitForm";

import DoctorDashboard from "@/pages/doctor/Dashboard";
import DoctorCaseDetail from "@/pages/doctor/CaseDetail";
import DoctorReminders from "@/pages/doctor/Reminders";
import DoctorPatients from "@/pages/doctor/Patients";

import PharmacyDashboard from "@/pages/pharmacy/Dashboard";
import PharmacyCase from "@/pages/pharmacy/CaseDetail";
import PharmacyReminders from "@/pages/pharmacy/Reminders";

import ProDashboard from "@/pages/pro/Dashboard";
import BillingDetail from "@/pages/pro/BillingDetail";
import Receipt from "@/pages/pro/Receipt";
import ProFinancialSearch from "@/pages/pro/FinancialSearch";
import ProAnalytics from "@/pages/pro/Analytics";

import AdminDashboard from "@/pages/admin/Dashboard";
import AdminUsers from "@/pages/admin/Users";
import AdminAudit from "@/pages/admin/AuditLogs";
import AdminExports from "@/pages/admin/Exports";
import AdminMessagingSettings from "@/pages/admin/MessagingSettings";

// Role guards — declared once at module scope so React doesn't see a new array
// reference on every render (which would re-trigger RequireAuth memoization).
const RECEPTION_ROLES = ["RECEPTION", "OWNER_DOCTOR", "ADMIN"];
const DOCTOR_ROLES = ["DOCTOR", "OWNER_DOCTOR"];
const OWNER_ONLY = ["OWNER_DOCTOR"];
const PHARMACY_ROLES = ["PHARMACY", "OWNER_DOCTOR", "ADMIN"];
const PRO_ROLES = ["PRO", "OWNER_DOCTOR", "ADMIN"];
const ADMIN_ONLY = ["ADMIN"];

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
              element={<RequireAuth roles={PRO_ROLES}><Receipt /></RequireAuth>}
            />

            {/* Authenticated app shell */}
            <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
              {/* Reception */}
              <Route path="/reception" element={<RequireAuth roles={RECEPTION_ROLES}><ReceptionDashboard /></RequireAuth>} />
              <Route path="/reception/patients" element={<RequireAuth roles={RECEPTION_ROLES}><PatientsList /></RequireAuth>} />
              <Route path="/reception/patients/:id/timeline" element={<RequireAuth><PatientTimeline /></RequireAuth>} />
              <Route path="/reception/patients/:id/past-visit" element={<RequireAuth roles={RECEPTION_ROLES}><PastVisitForm /></RequireAuth>} />
              <Route path="/reception/patients/new" element={<RequireAuth roles={RECEPTION_ROLES}><NewPatient /></RequireAuth>} />
              <Route path="/reception/new-visit" element={<RequireAuth roles={RECEPTION_ROLES}><NewVisit /></RequireAuth>} />

              {/* Doctor */}
              <Route path="/doctor" element={<RequireAuth roles={DOCTOR_ROLES}><DoctorDashboard /></RequireAuth>} />
              <Route path="/doctor/all" element={<RequireAuth roles={OWNER_ONLY}><DoctorDashboard scope="all" /></RequireAuth>} />
              <Route path="/doctor/patients" element={<RequireAuth roles={DOCTOR_ROLES}><DoctorPatients /></RequireAuth>} />
              <Route path="/doctor/patients/:id/timeline" element={<RequireAuth roles={DOCTOR_ROLES}><PatientTimeline /></RequireAuth>} />
              <Route path="/doctor/cases/:id" element={<RequireAuth roles={DOCTOR_ROLES}><DoctorCaseDetail /></RequireAuth>} />
              <Route path="/doctor/reminders" element={<RequireAuth roles={DOCTOR_ROLES}><DoctorReminders /></RequireAuth>} />

              {/* Pharmacy */}
              <Route path="/pharmacy" element={<RequireAuth roles={PHARMACY_ROLES}><PharmacyDashboard /></RequireAuth>} />
              <Route path="/pharmacy/reminders" element={<RequireAuth roles={PHARMACY_ROLES}><PharmacyReminders /></RequireAuth>} />
              <Route path="/pharmacy/cases/:id" element={<RequireAuth roles={PHARMACY_ROLES}><PharmacyCase /></RequireAuth>} />

              {/* PRO */}
              <Route path="/pro" element={<RequireAuth roles={PRO_ROLES}><ProDashboard /></RequireAuth>} />
              <Route path="/pro/financial-search" element={<RequireAuth roles={PRO_ROLES}><ProFinancialSearch /></RequireAuth>} />
              <Route path="/pro/analytics" element={<RequireAuth roles={PRO_ROLES}><ProAnalytics /></RequireAuth>} />
              <Route path="/pro/cases/:id" element={<RequireAuth roles={PRO_ROLES}><BillingDetail /></RequireAuth>} />

              {/* Admin */}
              <Route path="/admin" element={<RequireAuth roles={ADMIN_ONLY}><AdminDashboard /></RequireAuth>} />
              <Route path="/admin/users" element={<RequireAuth roles={ADMIN_ONLY}><AdminUsers /></RequireAuth>} />
              <Route path="/admin/audit" element={<RequireAuth roles={ADMIN_ONLY}><AdminAudit /></RequireAuth>} />
              <Route path="/admin/exports" element={<RequireAuth roles={ADMIN_ONLY}><AdminExports /></RequireAuth>} />
              <Route path="/admin/messaging" element={<RequireAuth roles={ADMIN_ONLY}><AdminMessagingSettings /></RequireAuth>} />
              <Route path="/admin/cases" element={<RequireAuth roles={ADMIN_ONLY}><DoctorDashboard scope="all" /></RequireAuth>} />
            </Route>

            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
