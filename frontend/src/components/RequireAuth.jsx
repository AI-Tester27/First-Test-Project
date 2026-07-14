import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { roleHomePath } from "@/lib/api";

export default function RequireAuth({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center text-gray-500" data-testid="auth-loading">
        Loading…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={roleHomePath(user.role)} replace />;
  }
  return children;
}
