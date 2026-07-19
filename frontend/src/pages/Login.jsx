import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { fmtErr, roleHomePath } from "@/lib/api";
import Logo from "@/components/Logo";
import {
  Loader2,
  Leaf,
  Users,
  ShieldCheck,
} from "lucide-react";

import loginBg from "@/assets/images/pic.jpg";

export default function LoginPage() {
  const { user, login } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const navigate = useNavigate();

  if (user)
    return <Navigate to={roleHomePath(user.role)} replace />;

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
    <div
      className="min-h-screen bg-cover bg-center relative overflow-hidden"
      style={{
        backgroundImage: `url(${loginBg})`,
      }}
    >
      {/* Dark Overlay */}
      <div className="absolute inset-0 bg-black/45" />

      <div className="relative z-10 min-h-screen flex">

        {/* LEFT SECTION */}
        <div className="hidden lg:flex flex-1 flex-col px-16 py-14">

          {/* Branding */}
          <div className="flex flex-col items-start">

            <Logo size={85} />

            <h1
              className="mt-5 text-[60px] xl:text-[68px] text-white font-semibold"
              style={{
                fontFamily: "'Cormorant Garamond', serif",
              }}
            >
              Sparsha Homeo Care
            </h1>

            <p className="mt-2 text-green-200 uppercase tracking-[0.35em] text-lg">
              Clinical Management System
            </p>

            <div className="flex items-center gap-4 mt-4">
              <div className="w-28 h-[1px] bg-green-200/60" />
              <div className="text-green-200">✦</div>
              <div className="w-28 h-[1px] bg-green-200/60" />
            </div>
          </div>

          {/* Hero Content */}
          <div className="flex-1 flex flex-col justify-center">

            <h2
              className="text-[54px] leading-tight text-white"
              style={{
                fontFamily: "'Cormorant Garamond', serif",
              }}
            >
              Compassionate Care.
            </h2>

            <h2
              className="text-[54px] leading-tight text-[#9cff8a]"
              style={{
                fontFamily: "'Cormorant Garamond', serif",
              }}
            >
              Natural Healing.
            </h2>

            <p className="mt-6 text-xl text-white/90 leading-10 max-w-xl">
              A complete digital platform for managing patient
              consultations, pharmacy operations, billing and
              clinical workflows at Sparsha Homeo Care.
            </p>

            {/* Feature Cards */}
            <div className="flex gap-8 mt-16">

              {/* Card 1 */}
              <div className="w-52 rounded-3xl bg-white/10 backdrop-blur-md border border-white/10 p-6 text-center">

                <div className="w-16 h-16 rounded-full bg-green-900/50 flex items-center justify-center mx-auto">
                  <Leaf className="text-green-300" size={30} />
                </div>

                <h3 className="mt-5 text-4xl font-bold text-white">
                  100%
                </h3>

                <p className="mt-2 text-white/90">
                  Homeopathic Care
                </p>
              </div>

              {/* Card 2 */}
              <div className="w-52 rounded-3xl bg-white/10 backdrop-blur-md border border-white/10 p-6 text-center">

                <div className="w-16 h-16 rounded-full bg-green-900/50 flex items-center justify-center mx-auto">
                  <Users className="text-green-300" size={30} />
                </div>

                <h3 className="mt-5 text-4xl font-bold text-white">
                  24/7
                </h3>

                <p className="mt-2 text-white/90">
                  Patient Records
                </p>
              </div>

              {/* Card 3 */}
              <div className="w-52 rounded-3xl bg-white/10 backdrop-blur-md border border-white/10 p-6 text-center">

                <div className="w-16 h-16 rounded-full bg-green-900/50 flex items-center justify-center mx-auto">
                  <ShieldCheck
                    className="text-green-300"
                    size={30}
                  />
                </div>

                <h3 className="mt-5 text-4xl font-bold text-white">
                  Secure
                </h3>

                <p className="mt-2 text-white/90">
                  Clinical Workflow
                </p>
              </div>

            </div>
          </div>
        </div>

        {/* RIGHT LOGIN CARD */}
        <div className="w-full lg:w-[42%] flex items-center justify-center p-8">

          <div className="w-full max-w-md rounded-[36px]
                          bg-white/15 backdrop-blur-xl
                          border border-white/20
                          shadow-2xl p-10">

            <div className="flex flex-col items-center mb-10">

              <Logo size={70} />

              <h2
                className="mt-5 text-5xl text-white"
                style={{
                  fontFamily: "'Cormorant Garamond', serif",
                }}
              >
                Welcome Back
              </h2>

              <p className="text-white/80 text-lg mt-2">
                Sign in to your account
              </p>
            </div>

            <form
              onSubmit={onSubmit}
              className="space-y-5"
            >
              <div>
                <label className="block text-xs uppercase tracking-widest text-white/80 mb-2 font-semibold">
                  Username
                </label>

                <input
                  type="text"
                  value={username}
                  onChange={(e) =>
                    setUsername(e.target.value)
                  }
                  className="w-full rounded-xl px-5 py-4
                            bg-white/90
                            outline-none
                            focus:ring-2
                            focus:ring-green-600"
                  required
                />
              </div>

              <div>
                <label className="block text-xs uppercase tracking-widest text-white/80 mb-2 font-semibold">
                  Password
                </label>

                <input
                  type="password"
                  value={password}
                  onChange={(e) =>
                    setPassword(e.target.value)
                  }
                  className="w-full rounded-xl px-5 py-4
                            bg-white/90
                            outline-none
                            focus:ring-2
                            focus:ring-green-600"
                  required
                />
              </div>

              {err && (
                <div className="text-red-700 bg-red-50 rounded-xl p-3 text-sm">
                  {err}
                </div>
              )}

              <button
                type="submit"
                disabled={busy}
                className="w-full bg-[#06754f]
                          hover:bg-[#045c3e]
                          text-white py-4 rounded-xl
                          text-lg font-semibold
                          flex justify-center items-center gap-2"
              >
                {busy && (
                  <Loader2
                    size={18}
                    className="animate-spin"
                  />
                )}

                Sign In
              </button>
            </form>

            <div className="mt-8 pt-6 border-t border-white/20 text-center text-white/80 text-sm">
              Contact the clinic administrator if you are
              unable to access your account.
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}
