import { NavLink, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { ROLE_LABELS } from "@/lib/api";
import {
  LayoutDashboard, Users, FileText, Pill, ReceiptText,
  ShieldCheck, ClipboardList, LogOut, Leaf, FileDown,
} from "lucide-react";

const NAV_BY_ROLE = {
  ADMIN: [
    { to: "/admin", label: "Overview", icon: LayoutDashboard, end: true },
    { to: "/admin/users", label: "Users", icon: Users },
    { to: "/admin/audit", label: "Audit Log", icon: ClipboardList },
    { to: "/admin/cases", label: "All Cases", icon: FileText },
    { to: "/admin/exports", label: "Exports", icon: FileDown },
  ],
  OWNER_DOCTOR: [
    { to: "/doctor", label: "My Queue", icon: LayoutDashboard, end: true },
    { to: "/doctor/all", label: "All Cases", icon: FileText },
    { to: "/doctor/reminders", label: "Reminders", icon: ClipboardList },
  ],
  DOCTOR: [
    { to: "/doctor", label: "My Queue", icon: LayoutDashboard, end: true },
    { to: "/doctor/reminders", label: "Reminders", icon: ClipboardList },
  ],
  RECEPTION: [
    { to: "/reception", label: "Today's Queue", icon: LayoutDashboard, end: true },
    { to: "/reception/patients", label: "Patients", icon: Users },
    { to: "/reception/new-visit", label: "New Visit", icon: FileText },
  ],
  PHARMACY: [
    { to: "/pharmacy", label: "Dispensing Queue", icon: Pill, end: true },
  ],
  PRO: [
    { to: "/pro", label: "Billing Queue", icon: ReceiptText, end: true },
  ],
};

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;
  const nav = NAV_BY_ROLE[user.role] || [];

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col" data-testid="app-sidebar">
        <div className="p-5 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-md bg-teal-700 text-white grid place-items-center">
              <Leaf size={18} strokeWidth={1.5} />
            </div>
            <div>
              <div className="font-display font-semibold text-[15px] text-gray-900 leading-tight">Sparsa</div>
              <div className="text-[11px] uppercase tracking-wider text-gray-500">Homeoclinic</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-0.5" data-testid="app-nav">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              data-testid={`nav-${label.toLowerCase().replace(/\s+/g, "-")}`}
            >
              <Icon size={16} strokeWidth={1.5} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-gray-200">
          <div className="px-2 py-2 mb-2">
            <div className="text-[11px] uppercase tracking-wider text-gray-500">Signed in</div>
            <div className="font-medium text-sm text-gray-900" data-testid="user-display-name">{user.name}</div>
            <div className="text-xs text-gray-500">{ROLE_LABELS[user.role]}</div>
          </div>
          <button
            onClick={async () => { await logout(); navigate("/login"); }}
            className="nav-link w-full hover:bg-red-50 hover:text-red-700"
            data-testid="logout-button"
          >
            <LogOut size={16} strokeWidth={1.5} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-auto" data-testid="app-main">
        <Outlet />
      </main>
    </div>
  );
}
