import { createContext } from "react";

import type { AuthUser } from "../../shared/api";

export type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
