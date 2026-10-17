import { useCallback, useMemo, useState, type ReactNode } from "react";

import { getCurrentUser, loginVendor, type AuthUser } from "../../shared/api";
import { AuthContext, type AuthContextValue } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);

  const login = useCallback(async (email: string, password: string) => {
    const tokenResponse = await loginVendor(email, password);
    try {
      const currentUser = await getCurrentUser(tokenResponse.access_token);
      setToken(tokenResponse.access_token);
      setUser(currentUser);
    } catch (error) {
      setToken(null);
      setUser(null);
      throw error;
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, token, login, logout }),
    [user, token, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
