import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { fmtErr, roleHomePath } from "@/lib/api";
import { Leaf, Loader2 } from "lucide-react";

export default function LoginPage() {
  const { user, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  if (user) return <Navigate to={roleHomePath(user.role)} replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const u = await login(username.trim(), password);
      navigate(roleHomePath(u.role));
    } catch (e2) {
      setErr(fmtErr(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left: hero image with overlay */}
      <div
        className="hidden lg:flex flex-1 bg-cover bg-center relative"
        style={{ backgroundImage: "url('https://images.pexels.com/photos/7789602/pexels-photo-7789602.jpeg')" }}
        data-testid="login-hero"
      >
        <div className="absolute inset-0 bg-white/70 backdrop-blur-sm" />
        <div className="relative z-10 p-12 flex flex-col justify-end">
          <div className="max-w-md">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-teal-700 text-white rounded-full text-xs tracking-wider uppercase font-medium mb-6">
              <Leaf size={14} strokeWidth={1.5} /> Sparsa Homeoclinic
            </div>
            <h1 className="font-display text-4xl font-semibold tracking-tight text-gray-900 leading-tight">
              A calmer way to run your clinic.
            </h1>
            <p className="text-gray-700 mt-4 text-base leading-relaxed">
              Internal workflow for Reception, Doctors, Pharmacy and Billing — built for the way Dr. Jyothi Vani and Dr. Hemanth see patients every day.
            </p>
          </div>
        </div>
      </div>

      {/* Right: login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-sm">
          <div className="flex items-center gap-2 mb-10">
            <div className="w-10 h-10 rounded-md bg-teal-700 text-white grid place-items-center">
              <Leaf size={20} strokeWidth={1.5} />
            </div>
            <div>
              <div className="font-display font-semibold text-base text-gray-900">Sparsa Homeoclinic</div>
              <div className="text-[11px] uppercase tracking-wider text-gray-500">Internal Workspace</div>
            </div>
          </div>

          <h2 className="font-display text-2xl font-semibold text-gray-900 tracking-tight">Sign in</h2>
          <p className="text-sm text-gray-500 mt-1 mb-8">Use your clinic credentials.</p>

          <form onSubmit={onSubmit} className="space-y-4" data-testid="login-form">
            <div>
              <label className="text-xs uppercase tracking-wider font-semibold text-gray-500 block mb-1.5">Username</label>
              <input
                type="text"
                className="w-full px-3 py-2.5 border border-gray-200 rounded-md text-sm focus-ring"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
                data-testid="login-username-input"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider font-semibold text-gray-500 block mb-1.5">Password</label>
              <input
                type="password"
                className="w-full px-3 py-2.5 border border-gray-200 rounded-md text-sm focus-ring"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="login-password-input"
              />
            </div>

            {err && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2" data-testid="login-error">
                {err}
              </div>
            )}

            <button
              type="submit"
              disabled={busy}
              className="w-full bg-teal-700 hover:bg-teal-800 disabled:opacity-60 text-white text-sm font-medium py-2.5 rounded-md transition-colors flex items-center justify-center gap-2"
              data-testid="login-submit-button"
            >
              {busy && <Loader2 size={14} className="animate-spin" />}
              Sign in
            </button>
          </form>

          <div className="mt-8 text-xs text-gray-500 border-t border-gray-100 pt-5">
            <div className="text-gray-500 leading-relaxed">
              Trouble signing in? Contact the clinic administrator to reset your credentials.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
