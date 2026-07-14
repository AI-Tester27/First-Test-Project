import { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { api, fmtErr } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data.user);
    } catch (error) {
      if (error?.response?.status !== 401) {
        // Only log unexpected failures; 401 just means "not signed in" which is normal.
        console.error("Auth refresh failed:", error);
      }
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (username, password) => {
    const { data } = await api.post("/auth/login", { username, password });
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch (error) {
      console.error("Logout request failed (clearing local session anyway):", error);
    }
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, logout, refresh, fmtErr }),
    [user, loading, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
