import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { getCurrentUser, loginVendor, SESSION_EXPIRED_EVENT, type AuthUser } from "../../shared/api";
import { AuthContext, type AuthContextValue } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  const endSession = useCallback((expired: boolean) => {
    setToken(null); setUser(null); setExpiresAt(null); setSessionExpired(expired);
  }, []);

  useEffect(() => {
    const expire = () => endSession(true);
    window.addEventListener(SESSION_EXPIRED_EVENT, expire);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, expire);
  }, [endSession]);

  useEffect(() => {
    if (expiresAt === null) return;
    const timer = window.setTimeout(() => endSession(true), Math.max(0, expiresAt - Date.now()));
    return () => window.clearTimeout(timer);
  }, [expiresAt, endSession]);

  const login = useCallback(async (email: string, password: string) => {
    const tokenResponse = await loginVendor(email, password);
    try {
      const currentUser = await getCurrentUser(tokenResponse.access_token);
      setToken(tokenResponse.access_token);
      setUser(currentUser);
      setExpiresAt(Date.now() + tokenResponse.expires_in * 1000);
      setSessionExpired(false);
    } catch (error) {
      setToken(null);
      setUser(null);
      throw error;
    }
  }, []);

  const logout = useCallback(() => {
    endSession(false);
  }, [endSession]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, token, login, logout, sessionExpired }),
    [user, token, login, logout, sessionExpired],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
